"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useSettings } from "@/components/providers";
import { StatusPill } from "@/components/ui/status-pill";
import { Tabs } from "@/components/ui/tabs";
import { ErrorState, LoadingBlock } from "@/components/ui/states";
import { RunDriverBadge, RunProvenanceBanner } from "@/features/run/components/run-provenance";
import { useRun, useLocalRuns, useRunDriver } from "@/features/run/hooks";
import { enumLabel } from "@/lib/i18n";
import { truncateMiddle } from "@/lib/format";
import { updateRunInIndex } from "@/lib/settings";
import type { MessageKey } from "@/lib/i18n";

const PHASES = ["draft", "position_formation", "debate", "negotiation", "compromise", "closed"] as const;

export function RunShell({ children }: { readonly children: ReactNode }) {
  const { t, locale } = useSettings();
  const params = useParams<{ runId: string }>();
  const runId = typeof params.runId === "string" ? params.runId : "";
  const run = useRun(runId);
  const driver = useRunDriver(runId);
  const localRuns = useLocalRuns();
  const entry = localRuns.find((item) => item.runId === runId);

  useEffect(() => {
    if (run.data === undefined) return;
    updateRunInIndex(runId, {
      phase: run.data.phase,
      round: run.data.round,
      closed: run.data.closed,
    });
  }, [run.data, runId]);

  const tabs = [
    { href: `/runs/${runId}`, labelKey: "run.tabs.console" as MessageKey, exact: true },
    { href: `/runs/${runId}/positions`, labelKey: "run.tabs.positions" as MessageKey },
    { href: `/runs/${runId}/evidence`, labelKey: "run.tabs.evidence" as MessageKey },
    { href: `/runs/${runId}/consensus`, labelKey: "run.tabs.consensus" as MessageKey },
    { href: `/runs/${runId}/brief`, labelKey: "run.tabs.brief" as MessageKey },
    { href: `/runs/${runId}/usage`, labelKey: "run.tabs.usage" as MessageKey },
    { href: `/runs/${runId}/governance`, labelKey: "run.tabs.governance" as MessageKey },
  ];

  const phaseIndex =
    run.data === undefined ? -1 : PHASES.indexOf(run.data.phase as (typeof PHASES)[number]);

  return (
    <div>
      <header className="mb-4 border-b border-line pb-4">
        <nav aria-label="Brotkrümel" className="mb-2 text-2xs text-ink-muted">
          <ol className="flex flex-wrap items-center gap-1">
            <li>
              <Link href="/" className="no-underline hover:underline">
                {t("dashboard.title")}
              </Link>
            </li>
            <li aria-hidden="true">/</li>
            <li>
              <span aria-current="page">{t("run.breadcrumb")}</span>
            </li>
            {run.data !== undefined && (
              <>
                <li aria-hidden="true">/</li>
                <li>
                  <span>{t("run.round", { round: run.data.round, cap: run.data.round_cap })}</span>
                </li>
              </>
            )}
          </ol>
        </nav>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="max-w-4xl text-xl font-light text-accent">
              {entry?.question !== undefined && entry.question !== ""
                ? entry.question
                : t("run.questionUnavailable")}
            </h1>
            <p className="mt-1 flex flex-wrap items-center gap-2 font-mono text-2xs text-ink-muted">
              <span>{truncateMiddle(runId, 14, 6)}</span>
              {entry?.mandateHash !== undefined && entry.mandateHash !== null && (
                <span title={entry.mandateHash}>
                  {t("new.mandateHash")}: {truncateMiddle(entry.mandateHash, 12, 6)}
                </span>
              )}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {run.isLoading && <StatusPill>{t("common.loading")}</StatusPill>}
            {run.data !== undefined && (
              <>
                <RunDriverBadge automated={driver.automated} known={driver.known} />
                <StatusPill tone={run.data.closed ? "neutral" : "ok"}>
                  {run.data.closed ? t("run.closed") : t("run.open")}
                </StatusPill>
                <StatusPill tone="info">
                  {enumLabel("phase", run.data.phase, locale)} ·{" "}
                  {t("run.round", { round: run.data.round, cap: run.data.round_cap })}
                </StatusPill>
              </>
            )}
          </div>
        </div>
        {run.data !== undefined && (
          <ol className="mt-3 flex flex-wrap gap-1" aria-label={t("run.phaseStepper")}>
            {PHASES.map((phase, index) => {
              const current = index === phaseIndex;
              const done = phaseIndex >= 0 && index < phaseIndex;
              return (
                <li
                  key={phase}
                  aria-current={current ? "step" : undefined}
                  className={
                    current
                      ? "rounded-xs border border-accent bg-accent-quiet px-2 py-0.5 text-2xs font-semibold text-accent"
                      : done
                        ? "rounded-xs border border-line bg-surface px-2 py-0.5 text-2xs text-ink"
                        : "rounded-xs border border-line px-2 py-0.5 text-2xs text-ink-subtle"
                  }
                >
                  {enumLabel("phase", phase, locale)}
                </li>
              );
            })}
          </ol>
        )}
        {run.isLoading && (
          <div className="mt-3">
            <LoadingBlock rows={2} />
          </div>
        )}
        {run.error !== null && run.error !== undefined && (
          <div className="mt-3">
            <ErrorState error={run.error} onRetry={() => void run.refetch()} />
          </div>
        )}
      </header>
      <div className="mb-4 space-y-3">
        <RunProvenanceBanner automated={driver.automated} scripted={driver.scripted} />
      </div>
      <Tabs items={tabs} />
      <div className="pt-4">{children}</div>
    </div>
  );
}
