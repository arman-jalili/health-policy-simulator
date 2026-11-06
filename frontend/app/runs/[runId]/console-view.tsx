"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";

import { useSettings, useToast } from "@/components/providers";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/ui/states";
import { EventFeed } from "@/features/run/components/event-feed";
import {
  AbstentionDrawer,
  MandateDrawer,
  PositionDrawer,
  RoundPanel,
  TurnDrawer,
} from "@/features/run/components/run-actions";
import { RoundTimeline } from "@/features/run/components/round-timeline";
import {
  useCloseRound,
  useLocalRuns,
  useOpenRound,
  useRun,
  useRunFeed,
  useSeed,
  useStartRun,
} from "@/features/run/hooks";
import {
  deriveTurnStatuses,
  turnOrderForRound,
  unaccountedStakeholders,
} from "@/features/positions/derive";
import { useStakeholders } from "@/features/stakeholders/hooks";
import { useStakeholderNames } from "@/features/stakeholders/names";
import { ApiError } from "@/lib/http";

type DrawerKind = "turn" | "position" | "abstention" | "mandate" | null;

export default function RunConsolePage() {
  const { t, settings } = useSettings();
  const { push } = useToast();
  const params = useParams<{ runId: string }>();
  const runId = typeof params.runId === "string" ? params.runId : "";
  const run = useRun(runId);
  const feed = useRunFeed(runId);
  const seed = useSeed();
  const localRuns = useLocalRuns();
  const stakeholders = useStakeholders();
  const names = useStakeholderNames();
  const openRound = useOpenRound(runId);
  const closeRound = useCloseRound(runId);
  const startRun = useStartRun(runId);
  const [drawer, setDrawer] = useState<DrawerKind>(null);
  const [stopping, setStopping] = useState<Readonly<Record<string, unknown>> | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);

  const state = feed.state ?? run.data;
  const entry = localRuns.find((item) => item.runId === runId);
  const bound = useMemo(
    () => state?.bound_stakeholder_ids ?? [],
    [state?.bound_stakeholder_ids],
  );
  const round = state?.round ?? 0;
  const turnOrder = useMemo(
    () => turnOrderForRound(feed.events, round, bound),
    [feed.events, round, bound],
  );
  const statuses = useMemo(
    () => deriveTurnStatuses(feed.events, round, turnOrder),
    [feed.events, round, turnOrder],
  );
  const unaccounted = useMemo(() => unaccountedStakeholders(statuses), [statuses]);
  const defaultTopic = seed?.topics[0]?.slug ?? entry?.question ?? "";
  const roundIsOpen = useMemo(() => {
    if (round === 0) return false;
    const closed = feed.events.filter((event) => event.event_type === "RoundClosed");
    return !closed.some((event) => event.payload["round"] === round);
  }, [feed.events, round]);
  const closeError = closeRound.error instanceof ApiError ? closeRound.error : null;
  const startDisabledReason =
    state?.closed === true
      ? t("run.closed")
      : seed === null
        ? t("dashboard.seedMissing")
        : undefined;

  if (run.isLoading && feed.state === null) {
    return <LoadingBlock rows={6} />;
  }
  if (run.error !== null && run.error !== undefined && feed.state === null) {
    return <ErrorState error={run.error} onRetry={() => void run.refetch()} />;
  }
  if (state === null || state === undefined) {
    return <EmptyState title={t("run.notFound")} action={<Link href="/">{t("nav.overview")}</Link>} />;
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
      <div className="space-y-4">
        {feed.error !== null && feed.error !== undefined && (
          <ErrorState error={feed.error} onRetry={feed.refetch} />
        )}
        <div className="flex flex-wrap items-center justify-between gap-2 text-2xs text-ink-muted">
          <span>
            {feed.pollMode === "closed"
              ? t("console.feedClosed")
              : feed.pollMode === "idle"
                ? t("console.feedIdle")
                : t("console.feedLive")}
          </span>
          {statuses.size > 0 && (
            <span>{t("new.selectedCount", { count: statuses.size - unaccounted.length, total: statuses.size })}</span>
          )}
        </div>
        <EventFeed events={feed.events} names={names} />
        {turnOrder.length > 0 && (
          <section className="rounded-md border border-line bg-surface px-4 py-3">
            <RoundTimeline
              events={feed.events}
              round={round}
              stakeholderIds={turnOrder}
              stakeholderNames={names}
              blocked={unaccounted}
            />
          </section>
        )}
      </div>

      <div className="space-y-4">
        <RoundPanel
          run={state}
          round={round}
          turnOrder={turnOrder}
          names={names}
          statuses={statuses}
          unaccounted={unaccounted}
          onOpenRound={() => openRound.mutate(undefined)}
          onCloseRound={(body) =>
            closeRound.mutate(
              { round, body },
              {
                onSuccess: (result) => {
                  setStopping(result.stopping_condition);
                  push(t("console.closeSuccess"), "ok");
                },
              },
            )
          }
          onAbstain={() => setDrawer("abstention")}
          onTurn={() => setDrawer("turn")}
          onPosition={() => setDrawer("position")}
          onMandate={() => setDrawer("mandate")}
          onStart={() =>
            startRun.mutate(
              { budget: { max_invocations: settings.budgetMaxInvocations } },
              {
                onSuccess: (result) => {
                  setJobId(result.job_id);
                  push(t("console.jobStarted", { job: result.job_id }), "ok");
                },
              },
            )
          }
          openRoundPending={openRound.isPending}
          closePending={closeRound.isPending}
          startPending={startRun.isPending}
          closeError={closeError}
          stoppingCondition={stopping}
          startDisabledReason={startDisabledReason}
          roundIsOpen={roundIsOpen}
        />
        {openRound.error !== null && openRound.error !== undefined && (
          <ErrorState error={openRound.error} />
        )}
        {startRun.error !== null && startRun.error !== undefined && (
          <ErrorState error={startRun.error} />
        )}
        {jobId !== null && (
          <div className="rounded-md border border-line bg-surface px-3 py-2 text-sm">
            <p className="font-mono text-2xs text-ink-muted">{jobId}</p>
            <Link href={`/runs/${runId}/usage`} className="mt-1 inline-block text-sm">
              {t("run.tabs.usage")}
            </Link>
          </div>
        )}
        {stakeholders.error !== null && stakeholders.error !== undefined && (
          <ErrorState error={stakeholders.error} />
        )}
        {stakeholders.data === undefined && (
          <div className="text-2xs text-ink-subtle">{t("console.noStakeholders")}</div>
        )}
      </div>

      <TurnDrawer
        runId={runId}
        round={round}
        stakeholderIds={turnOrder}
        names={names}
        defaultTopic={defaultTopic}
        seed={seed}
        open={drawer === "turn"}
        onClose={() => setDrawer(null)}
      />
      <PositionDrawer
        runId={runId}
        round={round}
        stakeholderIds={turnOrder}
        names={names}
        defaultTopic={defaultTopic}
        seed={seed}
        open={drawer === "position"}
        onClose={() => setDrawer(null)}
      />
      <AbstentionDrawer
        runId={runId}
        round={round}
        stakeholderIds={turnOrder}
        names={names}
        defaultTopic={defaultTopic}
        open={drawer === "abstention"}
        onClose={() => setDrawer(null)}
      />
      <MandateDrawer
        runId={runId}
        names={names}
        defaultMandate={entry?.question ?? settings.defaultQuestion}
        open={drawer === "mandate"}
        onClose={() => setDrawer(null)}
      />
    </div>
  );
}
