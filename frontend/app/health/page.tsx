"use client";

import Link from "next/link";
import { useMemo } from "react";

import { useSettings } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { CopyButton } from "@/components/ui/copy-button";
import { JsonBlock } from "@/components/ui/json-block";
import { ErrorState, LoadingBlock } from "@/components/ui/states";
import { PageHeader } from "@/components/ui/page-header";
import { StatusPill } from "@/components/ui/status-pill";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { useHealth, useOpenApiHead, useReadyz } from "@/features/platform/hooks";
import { buildDiagnostics } from "@/lib/diagnostics";

const GROUPS = [
  "database",
  "llm",
  "simulation",
  "negotiation_session",
  "consensus_analysis",
  "decision_brief",
  "governance",
  "stakeholder",
  "claim_validation",
  "evidence_retrieval",
  "attribution",
] as const;

export default function HealthPage() {
  const { t } = useSettings();
  const readyz = useReadyz();
  const health = useHealth();
  const openapi = useOpenApiHead();

  const groups = useMemo(() => {
    const map = new Map<string, [string, string][]>();
    for (const [key, value] of Object.entries(readyz.data?.checks ?? {})) {
      // Model ids are an implementation detail; the UI speaks "Live-LLM" / "Skript (Platzhalter)".
      if (key === "llm_model" || key === "simulation_model") continue;
      const group = GROUPS.find((prefix) => key.startsWith(prefix)) ?? "other";
      const entries = map.get(group) ?? [];
      entries.push([key, value]);
      map.set(group, entries);
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [readyz.data]);

  const copyDiagnostics = async (): Promise<void> => {
    const payload = buildDiagnostics({ settings: {}, readiness: readyz.data ?? null });
    await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
  };

  return (
    <div className="space-y-4">
      <PageHeader
        title={t("health.title")}
        subtitle={t("health.subtitle")}
        actions={
          <div className="flex flex-wrap gap-2">
            <CopyButton value={JSON.stringify(readyz.data ?? {}, null, 2)} />
            <Button
              onClick={() => {
                void copyDiagnostics();
              }}
            >
              {t("common.diagnostics")}
            </Button>
            <Link
              href="/api/hps/_platform/openapi.json"
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-9 items-center rounded-md border border-line px-3 text-sm no-underline"
            >
              {t("health.openapi")}
            </Link>
          </div>
        }
        meta={
          <div className="flex flex-wrap items-center gap-2">
            {readyz.data !== undefined && (
              <StatusPill tone={readyz.data.status === "ready" ? "ok" : "warn"}>
                {readyz.data.status === "ready" ? t("health.ready") : t("health.degraded")}
              </StatusPill>
            )}
            {health.data !== undefined && (
              <StatusPill tone="info">
                {health.data.service} · {health.data.version}
              </StatusPill>
            )}
            <StatusPill tone={openapi.data === true ? "ok" : "warn"}>
              OpenAPI: {openapi.data === true ? "HEAD 200" : "HEAD —"}
            </StatusPill>
          </div>
        }
      />

      {readyz.isLoading ? (
        <LoadingBlock rows={6} />
      ) : readyz.error !== null && readyz.error !== undefined ? (
        <ErrorState error={readyz.error} onRetry={() => void readyz.refetch()} />
      ) : readyz.data !== undefined ? (
        <>
          {groups.map(([group, entries]) => (
            <Card key={group}>
              <CardHeader title={group === "other" ? t("health.otherGroup") : group} />
              <CardBody>
                <div className="overflow-x-auto">
                  <Table caption={group}>
                    <THead>
                      <TR>
                        <TH>{t("health.checks")}</TH>
                        <TH>{t("health.status")}</TH>
                      </TR>
                    </THead>
                    <TBody>
                      {entries.map(([key, value]) => (
                        <TR key={key}>
                          <TD className="font-mono text-2xs">{key}</TD>
                          <TD>
                            <StatusPill
                              tone={
                                value === "ok" || value === "ready" || value === "wired"
                                  ? "ok"
                                  : value === "degraded" || value === "absent" || value === "missing"
                                    ? "warn"
                                    : "neutral"
                              }
                            >
                              {key === "llm"
                                ? value === "scripted"
                                  ? t("settings.modelScripted")
                                  : t("settings.modelLive")
                                : value}
                            </StatusPill>
                          </TD>
                        </TR>
                      ))}
                    </TBody>
                  </Table>
                </div>
              </CardBody>
            </Card>
          ))}
          <JsonBlock value={readyz.data} summary={t("settings.rawReadyz")} />
        </>
      ) : null}

      <p className="text-2xs text-ink-muted">
        {t("settings.authMode")}: {readyz.data?.checks["attribution"] ?? "—"}
      </p>
    </div>
  );
}
