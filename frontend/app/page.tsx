"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { useMutation } from "@tanstack/react-query";

import { Icon } from "@/components/icons";
import { useSettings } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { CopyButton } from "@/components/ui/copy-button";
import { PageHeader } from "@/components/ui/page-header";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/ui/states";
import { StatusPill } from "@/components/ui/status-pill";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { getRun } from "@/features/run/api";
import { useLocalRuns, useSeed } from "@/features/run/hooks";
import { useReadyz } from "@/features/platform/hooks";
import { formatDate, truncateMiddle } from "@/lib/format";
import { engineKind, engineLabel } from "@/lib/engine";
import { enumLabel, type MessageKey } from "@/lib/i18n";

export default function DashboardPage() {
  const { t, locale } = useSettings();
  const router = useRouter();
  const readyz = useReadyz();
  const seed = useSeed();
  const runs = useLocalRuns();
  const [runId, setRunId] = useState("");
  const openById = useMutation({ mutationFn: (id: string) => getRun(id) });

  const checks = readyz.data?.checks ?? {};
  const cap = (key: string): string => checks[key] ?? t("common.unknown");

  return (
    <div className="space-y-5">
      <PageHeader
        title={t("dashboard.title")}
        subtitle={t("dashboard.subtitle")}
        actions={
          <Button
            variant="primary"
            icon={<Icon name="plus" />}
            onClick={() => router.push("/runs/new")}
          >
            {t("dashboard.newRun")}
          </Button>
        }
        meta={
          <div className="flex flex-wrap items-center gap-2">
            {readyz.isLoading && <StatusPill>{t("common.loading")}</StatusPill>}
            {readyz.data !== undefined && (
              <StatusPill tone={readyz.data.status === "ready" ? "ok" : "warn"}>
                {t("dashboard.readiness")}: {readyz.data.status}
              </StatusPill>
            )}
            <StatusPill tone="neutral">{`pricing: ${cap("simulation_pricing")}`}</StatusPill>
          </div>
        }
      />

      {readyz.error !== null && (
        <ErrorState error={readyz.error} onRetry={() => void readyz.refetch()} />
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader
            title={t("dashboard.recent")}
            actions={
              <Link href="/deferred" className="text-2xs">
                {t("dashboard.deferredLink")}
              </Link>
            }
          />
          <CardBody>
            {runs.length === 0 ? (
              <EmptyState
                title={t("dashboard.recentEmpty")}
                action={
                  <Button onClick={() => router.push("/runs/new")}>{t("dashboard.newRun")}</Button>
                }
              />
            ) : (
              <ul className="divide-y divide-line">
                {runs.map((run) => (
                  <li key={run.runId} className="flex items-center justify-between gap-3 py-2">
                    <div className="min-w-0">
                      <Link
                        href={`/runs/${run.runId}`}
                        className="block truncate text-sm font-medium no-underline"
                      >
                        {run.question === "" ? t("run.questionUnavailable") : run.question}
                      </Link>
                      <p className="mt-0.5 font-mono text-2xs text-ink-muted">
                        {truncateMiddle(run.runId)} · {formatDate(run.createdAt, locale)}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {run.model !== undefined && run.model !== null && run.model !== "" && (
                        <StatusPill tone={engineKind(run.model) === "scripted" ? "warn" : "ok"}>
                          {engineLabel(run.model, locale)}
                        </StatusPill>
                      )}
                      {run.phase !== null && (
                        <StatusPill>{enumLabel("phase", run.phase, locale)}</StatusPill>
                      )}
                      {run.closed === true ? (
                        <StatusPill tone="neutral">{t("run.closed")}</StatusPill>
                      ) : (
                        <StatusPill tone="ok">{t("run.open")}</StatusPill>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title={t("dashboard.openById")} description={t("dashboard.openByIdHint")} />
          <CardBody>
            <form
              className="flex gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                if (runId.trim() === "") return;
                openById.mutate(runId.trim(), {
                  onSuccess: (run) => router.push(`/runs/${run.run_id}`),
                });
              }}
            >
              <label htmlFor="open-run-id" className="sr-only">
                {t("dashboard.openById")}
              </label>
              <input
                id="open-run-id"
                value={runId}
                onChange={(event) => setRunId(event.target.value)}
                placeholder="run_…"
                className="h-9 min-w-0 flex-1 rounded-md border border-line-strong bg-surface px-3 font-mono text-sm"
              />
              <Button type="submit" loading={openById.isPending}>
                {t("dashboard.open")}
              </Button>
            </form>
            {openById.error !== null && openById.error !== undefined && (
              <div className="mt-3">
                <ErrorState error={openById.error} />
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader
            title={t("dashboard.seed")}
            actions={
              <Link href="/settings" className="text-2xs">
                {t("settings.bootstrap")}
              </Link>
            }
          />
          <CardBody>
            {seed === null ? (
              <div className="space-y-2">
                <p className="text-sm text-ink-muted">{t("dashboard.seedMissing")}</p>
                <code className="block rounded-xs border border-line bg-surface-muted px-2 py-1.5 font-mono text-2xs">
                  backend/samples/pressespiegel-2020-seed.json
                </code>
                <Link href="/settings" className="text-sm">
                  {t("dashboard.seedLink")}
                </Link>
              </div>
            ) : (
              <div>
                <p className="text-sm text-ink-muted">{t("dashboard.seedPresent")}</p>
                <TableWrapLocal>
                  <Table caption={t("dashboard.seed")}>
                    <THead>
                      <TR>
                        <TH>{t("common.topic")}</TH>
                        <TH>{t("evidence.pack")}</TH>
                      </TR>
                    </THead>
                    <TBody>
                      {Object.entries(seed.pack_ids).map(([topic, packId]) => (
                        <TR key={topic}>
                          <TD>{topic}</TD>
                          <TD>
                            <span className="flex items-center justify-between gap-2">
                              <span className="font-mono text-2xs">{truncateMiddle(packId)}</span>
                              <CopyButton value={packId} label={t("common.copy")} />
                            </span>
                          </TD>
                        </TR>
                      ))}
                    </TBody>
                  </Table>
                </TableWrapLocal>
              </div>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title={t("dashboard.readiness")}
            description={t("dashboard.readinessHint")}
            actions={
              <Link href="/health" className="text-2xs">
                {t("dashboard.viewHealth")}
              </Link>
            }
          />
          <CardBody>
            {readyz.isLoading ? (
              <LoadingBlock rows={4} />
            ) : (
              <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {[
                  { key: "negotiation_session", label: "dashboard.gate.negotiation" },
                  { key: "consensus_analysis", label: "dashboard.gate.consensus" },
                  { key: "decision_brief", label: "dashboard.gate.brief" },
                  { key: "evidence_retrieval_mode", label: "dashboard.gate.evidence" },
                ].map((row) => (
                  <div key={row.key} className="rounded-xs border border-line px-2 py-1.5">
                    <dt className="text-2xs text-ink-muted">{t(row.label as MessageKey)}</dt>
                    <dd className="mt-0.5 text-sm">{cap(row.key)}</dd>
                  </div>
                ))}
              </dl>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function TableWrapLocal({ children }: { readonly children: ReactNode }) {
  return <div className="mt-2 overflow-x-auto rounded-md border border-line">{children}</div>;
}
