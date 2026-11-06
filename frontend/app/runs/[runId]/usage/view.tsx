"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useSettings, useToast } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Field, TextInput } from "@/components/ui/field";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/ui/states";
import { StatusPill } from "@/components/ui/status-pill";
import { Stat } from "@/components/ui/stat";
import { getJob, getUsage } from "@/features/run/api";
import { usePauseRun, useResumeRun, useRun, useSeed, useStartRun } from "@/features/run/hooks";
import { useReadyz } from "@/features/platform/hooks";
import { UsageSmallMultiples } from "@/features/usage/components/usage-small-multiples";
import { ProgressEventSchema, type Budget, type ProgressEvent } from "@/features/run/contracts";
import { openEventStream } from "@/lib/sse";
import { enumLabel } from "@/lib/i18n";
import { formatEur, formatNumber } from "@/lib/format";

export default function UsagePage() {
  const { t, locale, settings } = useSettings();
  const { push } = useToast();
  const params = useParams<{ runId: string }>();
  const runId = typeof params.runId === "string" ? params.runId : "";
  const run = useRun(runId);
  const seed = useSeed();
  const readyz = useReadyz();
  const start = useStartRun(runId);
  const pause = usePauseRun(runId);
  const resume = useResumeRun(runId);
  const [maxInvocations, setMaxInvocations] = useState(String(settings.budgetMaxInvocations));
  const [maxTokens, setMaxTokens] = useState("");
  const [maxCost, setMaxCost] = useState("");
  const [jobId, setJobId] = useState("");
  const [jobInput, setJobInput] = useState("");
  const [frames, setFrames] = useState<readonly ProgressEvent[]>([]);
  const [streamClosed, setStreamClosed] = useState(false);
  const usage = useQuery({
    queryKey: ["run", runId, "usage"],
    queryFn: ({ signal }) => getUsage(runId, signal),
    enabled: runId !== "",
    refetchInterval: 5_000,
  });
  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: ({ signal }) => getJob(jobId, signal),
    enabled: jobId !== "",
    refetchInterval: 1_000,
  });

  useEffect(() => {
    if (runId === "") return;
    setFrames([]);
    setStreamClosed(false);
    const close = openEventStream(`/runs/${runId}/stream`, {
      onFrame: (frame) => {
        if (frame.data.trim() === "") return;
        try {
          const parsed = ProgressEventSchema.safeParse(JSON.parse(frame.data));
          if (!parsed.success) return;
          setFrames((current) => [...current, parsed.data].slice(-100));
          if (parsed.data.kind === "run.stream_closed") setStreamClosed(true);
        } catch {
          // ignore malformed frames
        }
      },
      onClose: () => setStreamClosed(true),
    });
    return close;
  }, [runId]);

  const pricing = readyz.data?.checks["simulation_pricing"];
  const buildBudget = (): Budget => {
    const budget: {
      max_invocations?: number;
      max_tokens?: number;
      max_cost?: string;
    } = {};
    if (maxInvocations.trim() !== "") budget.max_invocations = Number(maxInvocations);
    if (maxTokens.trim() !== "") budget.max_tokens = Number(maxTokens);
    if (maxCost.trim() !== "") budget.max_cost = maxCost;
    return budget;
  };

  return (
    <div className="space-y-4">
      {pricing === "zero" && (
        <div role="status" className="rounded-md border border-warn/40 bg-warn-quiet px-4 py-2 text-sm text-warn">
          {t("usage.pricingZero")}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <Card>
          <CardHeader title={t("usage.title")} />
          <CardBody className="space-y-4">
            {usage.isLoading ? (
              <LoadingBlock rows={5} />
            ) : usage.error !== null && usage.error !== undefined ? (
              <ErrorState error={usage.error} onRetry={() => void usage.refetch()} />
            ) : usage.data === undefined ? (
              <EmptyState title={t("usage.noUsage")} />
            ) : (
              <>
                <dl className="grid gap-2 sm:grid-cols-4">
                  <Stat label={t("usage.invocations")} value={formatNumber(usage.data.total_invocations, locale)} />
                  <Stat label={t("usage.inputTokens")} value={formatNumber(usage.data.input_tokens, locale)} />
                  <Stat label={t("usage.outputTokens")} value={formatNumber(usage.data.output_tokens, locale)} />
                  <Stat label={t("usage.cost")} value={formatEur(usage.data.cost, locale)} />
                </dl>
                <UsageSmallMultiples
                  usage={usage.data}
                  budget={buildBudget()}
                  defaultInvocations={settings.budgetMaxInvocations}
                />
              </>
            )}
          </CardBody>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader title={t("usage.startBudget")} />
            <CardBody className="space-y-2">
              <Field label={t("usage.maxInvocations")} htmlFor="max-invocations" hint={t("usage.budgetHint")}>
                <TextInput
                  id="max-invocations"
                  type="number"
                  min={0}
                  value={maxInvocations}
                  onChange={(event) => setMaxInvocations(event.target.value)}
                />
              </Field>
              <Field label={t("usage.maxTokens")} htmlFor="max-tokens">
                <TextInput
                  id="max-tokens"
                  type="number"
                  min={0}
                  value={maxTokens}
                  onChange={(event) => setMaxTokens(event.target.value)}
                />
              </Field>
              <Field label={t("usage.maxCost")} htmlFor="max-cost">
                <TextInput
                  id="max-cost"
                  inputMode="decimal"
                  value={maxCost}
                  onChange={(event) => setMaxCost(event.target.value)}
                />
              </Field>
              {start.error !== null && start.error !== undefined && <ErrorState error={start.error} />}
              <Button
                variant="primary"
                className="w-full"
                loading={start.isPending}
                disabledReason={
                  run.data?.closed === true
                    ? t("run.closed")
                    : seed === null
                      ? t("dashboard.seedMissing")
                      : undefined
                }
                onClick={() =>
                  start.mutate(
                    { budget: buildBudget() },
                    {
                      onSuccess: (result) => {
                        setJobId(result.job_id);
                        push(t("usage.startSuccess"), "ok");
                      },
                    },
                  )
                }
              >
                {t("usage.start")}
              </Button>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  loading={pause.isPending}
                  onClick={() =>
                    pause.mutate(
                      { action: "pause", reason: "client_request" },
                      { onSuccess: () => push(t("usage.pauseSuccess"), "ok") },
                    )
                  }
                >
                  {t("usage.pause")}
                </Button>
                <Button
                  loading={resume.isPending}
                  onClick={() =>
                    resume.mutate(
                      { action: "resume", reason: "client_request" },
                      { onSuccess: () => push(t("usage.resumeSuccess"), "ok") },
                    )
                  }
                >
                  {t("usage.resume")}
                </Button>
              </div>
              {pause.error !== null && pause.error !== undefined && <ErrorState error={pause.error} />}
              {resume.error !== null && resume.error !== undefined && <ErrorState error={resume.error} />}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title={t("usage.job")} />
            <CardBody className="space-y-2">
              <Field label={t("usage.trackJob")} htmlFor="job-id">
                <div className="flex gap-2">
                  <TextInput
                    id="job-id"
                    value={jobInput}
                    onChange={(event) => setJobInput(event.target.value)}
                    placeholder="job_…"
                    className="font-mono"
                  />
                  <Button size="sm" onClick={() => setJobId(jobInput.trim())}>
                    {t("usage.trackJob")}
                  </Button>
                </div>
              </Field>
              {jobId === "" ? (
                <p className="text-2xs text-ink-muted">{t("usage.jobId")}: —</p>
              ) : job.isLoading ? (
                <LoadingBlock rows={2} />
              ) : job.error !== null && job.error !== undefined ? (
                <ErrorState error={job.error} onRetry={() => void job.refetch()} />
              ) : job.data !== undefined ? (
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusPill
                      tone={
                        job.data.status === "completed"
                          ? "ok"
                          : job.data.status === "failed" || job.data.status === "dead_letter"
                            ? "danger"
                            : job.data.status === "paused"
                              ? "warn"
                              : "info"
                      }
                    >
                      {enumLabel("jobStatus", job.data.status, locale)}
                    </StatusPill>
                    <span className="font-mono text-2xs text-ink-muted">{job.data.job_id}</span>
                  </div>
                  <dl className="grid grid-cols-2 gap-2 text-2xs">
                    <div>
                      <dt className="text-ink-muted">{t("usage.attempts")}</dt>
                      <dd>{job.data.attempts}</dd>
                    </div>
                    <div>
                      <dt className="text-ink-muted">{t("usage.checkpoint")}</dt>
                      <dd>
                        {job.data.checkpoint.round} · {enumLabel("phase", job.data.checkpoint.phase, locale)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-ink-muted">{t("usage.nextActor")}</dt>
                      <dd className="font-mono">
                        {job.data.checkpoint.next_actor ?? "—"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-ink-muted">{t("usage.budgetUsed")}</dt>
                      <dd>
                        {job.data.checkpoint.budget_used_invocations} ·{" "}
                        {formatNumber(job.data.checkpoint.budget_used_tokens, locale)} ·{" "}
                        {formatEur(job.data.checkpoint.budget_used_cost, locale)}
                      </dd>
                    </div>
                  </dl>
                  {job.data.error !== null && (
                    <p className="rounded-xs border border-danger/30 bg-danger-quiet px-2 py-1 text-2xs text-danger">
                      {job.data.error}
                    </p>
                  )}
                </div>
              ) : null}
            </CardBody>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader
          title={t("usage.eventStream")}
          actions={<span className="text-2xs text-ink-muted">{streamClosed ? t("usage.streamClosed") : t("console.feedLive")}</span>}
        />
        <CardBody>
          {frames.length === 0 ? (
            <EmptyState title={t("usage.streamEmpty")} />
          ) : (
            <ol className="divide-y divide-line">
              {frames.map((frame) => (
                <li key={`${frame.event_id}-${frame.sequence}`} className="py-1.5">
                  <div className="flex flex-wrap items-center justify-between gap-2 text-2xs">
                    <span className="font-mono">{frame.kind}</span>
                    <span className="text-ink-muted">#{frame.sequence}</span>
                  </div>
                  <details className="mt-1">
                    <summary className="cursor-pointer text-2xs text-ink-subtle">
                      {t("common.details")}
                    </summary>
                    <pre className="mt-1 max-h-40 overflow-auto rounded-xs border border-line bg-surface-muted p-2 font-mono text-2xs">
                      {JSON.stringify(frame.payload, null, 2)}
                    </pre>
                  </details>
                </li>
              ))}
            </ol>
          )}
          {streamClosed && <p className="mt-2 text-2xs text-ink-muted">{t("usage.sseClosed")}</p>}
        </CardBody>
      </Card>

    </div>
  );
}
