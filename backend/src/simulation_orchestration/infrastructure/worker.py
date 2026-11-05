"""Background worker loop with bounded retries and crash recovery (issues #216, #235)."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import replace

from shared.log_setup import get_logger
from shared.metrics import METRICS
from simulation_orchestration.application.dto import JobRecord
from simulation_orchestration.application.rules import RetryPolicy
from simulation_orchestration.application.services import RunSimulationJob
from simulation_orchestration.application.values import JobStatus

logger = get_logger(__name__)


class BackgroundWorker:
    """Claim one job at a time and keep running across per-job failures."""

    def __init__(
        self,
        run_job: RunSimulationJob,
        *,
        worker_id: str = "worker-1",
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._run_job = run_job
        self._worker_id = worker_id
        self._retry_policy = retry_policy or RetryPolicy()

    async def recover(self) -> int:
        """Re-queue RUNNING jobs left by a dead worker; return the resumable count."""
        resumable = await self._run_job._jobs.list_resumable()
        recovered = 0
        for job in resumable:
            if job.status is not JobStatus.RUNNING:
                continue
            await self._run_job._jobs.save(
                replace(
                    job,
                    status=JobStatus.QUEUED,
                    claimed_by=None,
                    lease_expires_at=None,
                    error="recovered after worker restart",
                    updated_at=self._run_job._clock.now(),
                )
            )
            recovered += 1
        logger.info(
            "simulation_worker_recovered",
            resumable=len(resumable),
            requeued=recovered,
        )
        return len(resumable)

    async def run_once(self) -> bool:
        job = await self._run_job._jobs.claim_next(
            self._worker_id,
            self._run_job._clock.now(),
        )
        if job is None:
            return False
        try:
            await self._run_job.run(str(job.job_id))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            await self._handle_failure(job, error)
        return True

    async def _handle_failure(self, claimed: JobRecord, error: Exception) -> None:
        message = f"{type(error).__name__}: {error}".strip()
        job = await self._run_job._jobs.get(claimed.job_id) or claimed
        METRICS.increment("simulation_job_failures_total")
        retry = self._retry_policy.should_retry(attempts=job.attempts, error=message)
        status = (
            JobStatus.QUEUED if retry else (JobStatus.DEAD_LETTER if message else JobStatus.FAILED)
        )
        await self._run_job.record_failure(job.job_id, message, status=status)
        logger.warning(
            "simulation_job_failed",
            job_id=str(job.job_id),
            run_id=str(job.run_id),
            attempts=job.attempts,
            status=status.value,
            error=message,
        )
        if retry:
            await asyncio.sleep(self._retry_policy.delay_seconds(job.attempts))

    async def run_forever(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            worked = await self.run_once()
            if worked:
                continue
            with suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=0.05)

    async def run_supervised(self, stop: asyncio.Event) -> None:
        """Restart the loop after an unexpected infrastructure failure."""
        while not stop.is_set():
            try:
                await self.run_forever(stop)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                METRICS.increment("simulation_worker_restarts_total")
                logger.exception("simulation_worker_restarted", error=str(error))
                with suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=0.5)
