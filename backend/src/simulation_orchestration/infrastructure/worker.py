"""Background worker loop (issue #216)."""

from __future__ import annotations

import asyncio
from contextlib import suppress

from simulation_orchestration.application.services import RunSimulationJob


class BackgroundWorker:
    def __init__(self, run_job: RunSimulationJob, *, worker_id: str = "worker-1") -> None:
        self._run_job = run_job
        self._worker_id = worker_id

    async def run_once(self) -> bool:
        job = await self._run_job._jobs.claim_next(
            self._worker_id,
            self._run_job._clock.now(),
        )
        if job is None:
            return False
        await self._run_job.run(str(job.job_id))
        return True

    async def run_forever(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            worked = await self.run_once()
            if worked:
                continue
            with suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=0.05)
