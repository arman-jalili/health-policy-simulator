"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useSettings, useToast } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Checkbox, Field, Select, TextArea, TextInput } from "@/components/ui/field";
import { CopyButton } from "@/components/ui/copy-button";
import { JsonBlock } from "@/components/ui/json-block";
import { ErrorState, LoadingBlock } from "@/components/ui/states";
import { PageHeader } from "@/components/ui/page-header";
import { StatusPill } from "@/components/ui/status-pill";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { getSnapshot } from "@/features/corpus/api";
import { useAuthorityRules } from "@/features/evidence/hooks";
import { useAllowlist } from "@/features/governance/hooks";
import { getHealth, getReadyz, headOpenApi } from "@/features/platform/api";
import { useReadyz } from "@/features/platform/hooks";
import { useReferenceFigures } from "@/features/claims/hooks";
import { useStakeholders } from "@/features/stakeholders/hooks";
import { useSeed } from "@/features/run/hooks";
import {
  buildDiagnostics,
  failedRequests,
  subscribeFailures,
  type FailedRequest,
} from "@/lib/diagnostics";
import { fetchProxyMeta } from "@/lib/http";
import { enumLabel } from "@/lib/i18n";
import {
  DEFAULT_SETTINGS,
  SeedSchema,
  clearRunIndex,
  clearSeed,
  clearSettings,
  saveSeed,
} from "@/lib/settings";
import { truncateMiddle } from "@/lib/format";

export default function SettingsPage() {
  const { t, locale, settings, hydrated, setSettings, updateSettings } = useSettings();
  const { push } = useToast();
  const readyz = useReadyz();
  const seed = useSeed();
  const stakeholders = useStakeholders();
  const allowlist = useAllowlist();
  const figures = useReferenceFigures();
  const rules = useAuthorityRules();
  const meta = useQuery({ queryKey: ["proxy-meta"], queryFn: () => fetchProxyMeta() });
  const [seedText, setSeedText] = useState("");
  const [seedError, setSeedError] = useState<string | null>(null);
  const [failures, setFailures] = useState<readonly FailedRequest[]>(failedRequests());
  const [roundCap, setRoundCap] = useState(String(settings.roundCap));
  const [threshold, setThreshold] = useState(String(settings.consensusThreshold));
  const [budget, setBudget] = useState(String(settings.budgetMaxInvocations));
  const [question, setQuestion] = useState(settings.defaultQuestion);
  const [defaultIds, setDefaultIds] = useState<readonly string[]>(settings.defaultStakeholderIds);
  const [testResult, setTestResult] = useState<{
    readonly health: number;
    readonly readyz: number;
    readonly openapi: boolean;
    readonly totalMs: number;
    readonly status: "ok" | "failed";
    readonly version: string | null;
  } | null>(null);

  useEffect(() => subscribeFailures(setFailures), []);
  useEffect(() => {
    setRoundCap(String(settings.roundCap));
    setThreshold(String(settings.consensusThreshold));
    setBudget(String(settings.budgetMaxInvocations));
    setQuestion(settings.defaultQuestion);
    setDefaultIds(settings.defaultStakeholderIds);
  }, [settings]);
  useEffect(() => {
    if (seed !== null) setSeedText(JSON.stringify(seed, null, 2));
  }, [seed]);

  const test = useMutation({
    mutationFn: async () => {
      const started = performance.now();
      const healthStart = performance.now();
      const health = await getHealth();
      const healthMs = Math.round(performance.now() - healthStart);
      const readyzStart = performance.now();
      await getReadyz();
      const readyzMs = Math.round(performance.now() - readyzStart);
      const openapi = await headOpenApi();
      return {
        health: healthMs,
        readyz: readyzMs,
        openapi,
        totalMs: Math.round(performance.now() - started),
        status: "ok" as const,
        version: health.version,
      };
    },
    onSuccess: (result) => {
      setTestResult(result);
      push(t("settings.testOk"), "ok");
    },
    onError: () => {
      setTestResult(null);
      push(t("settings.testFailed"), "danger");
    },
  });

  const snapshot = useQuery({
    queryKey: ["snapshot", seed?.snapshot_id ?? ""],
    queryFn: ({ signal }) => getSnapshot(seed?.snapshot_id ?? "", signal),
    enabled: seed !== null,
  });

  if (!hydrated) {
    return <LoadingBlock rows={8} />;
  }

  const saveDefaults = (): void => {
    updateSettings({
      roundCap: Math.min(50, Math.max(1, Math.round(Number(roundCap)))),
      consensusThreshold: Math.min(1, Math.max(0.01, Number(threshold))),
      budgetMaxInvocations: Math.min(10_000, Math.max(1, Math.round(Number(budget)))),
      defaultQuestion: question,
      defaultStakeholderIds: [...defaultIds],
    });
    push(t("settings.saved"), "ok");
  };

  const importSeed = (): void => {
    try {
      const parsed = SeedSchema.safeParse(JSON.parse(seedText));
      if (!parsed.success) {
        setSeedError(t("settings.seedInvalid"));
        return;
      }
      saveSeed(parsed.data);
      setSeedError(null);
      push(t("settings.saved"), "ok");
    } catch {
      setSeedError(t("settings.seedInvalid"));
    }
  };

  const copyDiagnostics = async (): Promise<void> => {
    const payload = buildDiagnostics({ settings, readiness: readyz.data ?? null });
    try {
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
      push(t("settings.diagnosticsCopied"), "ok");
    } catch {
      push(t("common.error"), "danger");
    }
  };

  return (
    <div className="space-y-4">
      <PageHeader title={t("settings.title")} />

      <Card>
        <CardHeader title={t("settings.connection")} description={t("settings.connectionReadOnly")} />
        <CardBody className="space-y-3">
          {meta.isLoading ? (
            <LoadingBlock rows={2} />
          ) : meta.error !== null && meta.error !== undefined ? (
            <ErrorState error={meta.error} onRetry={() => void meta.refetch()} />
          ) : meta.data !== undefined ? (
            <dl className="grid gap-2 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-2xs text-ink-muted">{t("settings.proxy")}</dt>
                <dd className="font-mono">/api/hps</dd>
              </div>
              <div>
                <dt className="text-2xs text-ink-muted">{t("settings.baseUrl")}</dt>
                <dd className="font-mono">{meta.data.baseUrl}</dd>
              </div>
              <div>
                <dt className="text-2xs text-ink-muted">{t("settings.apiKey")}</dt>
                <dd>{meta.data.hasApiKey ? t("settings.apiKeySet") : t("settings.apiKeyUnset")}</dd>
              </div>
              <div>
                <dt className="text-2xs text-ink-muted">{t("settings.timeout")}</dt>
                <dd>{meta.data.timeoutMs} ms</dd>
              </div>
              <div>
                <dt className="text-2xs text-ink-muted">{t("settings.authMode")}</dt>
                <dd>{meta.data.hasApiKey ? t("settings.authStrict") : t("settings.authDemo")}</dd>
              </div>
            </dl>
          ) : null}
          <Button
            onClick={() => test.mutate()}
            loading={test.isPending}
          >
            {test.isPending ? t("settings.testing") : t("settings.test")}
          </Button>
          {test.error !== null && test.error !== undefined && <ErrorState error={test.error} />}
          {testResult !== null && (
            <div className="rounded-xs border border-line bg-surface-muted px-2 py-1.5 text-2xs">
              <p>
                {t("settings.testOk")} · {t("settings.latency")}: {testResult.totalMs} ms
              </p>
              <p>
                /healthz {testResult.health} ms · /readyz {testResult.readyz} ms · openapi{" "}
                {testResult.openapi ? "HEAD 200" : "HEAD —"}
              </p>
              {testResult.version !== null && (
                <p>
                  {t("settings.version")}: {testResult.version}
                </p>
              )}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title={t("settings.bootstrap")}
          description={seed === null ? t("settings.seedMissing") : t("dashboard.seedPresent")}
        />
        <CardBody className="space-y-3">
          <Field label={t("settings.seedTextarea")} htmlFor="seed-text">
            <TextArea
              id="seed-text"
              rows={8}
              value={seedText}
              onChange={(event) => setSeedText(event.target.value)}
              className="font-mono text-2xs"
            />
          </Field>
          <div className="flex flex-wrap items-center gap-2">
            <label className="inline-flex h-9 cursor-pointer items-center rounded-md border border-line-strong bg-surface px-3 text-sm">
              {t("settings.seedFile")}
              <input
                type="file"
                accept="application/json,.json"
                className="sr-only"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file === undefined) return;
                  void file.text().then((text) => setSeedText(text));
                }}
              />
            </label>
            <Button onClick={importSeed} disabledReason={seedText.trim() === "" ? t("settings.seedTextarea") : undefined}>
              {t("settings.seedLoad")}
            </Button>
            <Button
              onClick={() => {
                clearSeed();
                setSeedText("");
                push(t("settings.resetDone"), "ok");
              }}
            >
              {t("settings.resetSeed")}
            </Button>
          </div>
          {seedError !== null && <p role="alert" className="text-2xs text-danger">{seedError}</p>}
          <p className="text-2xs text-ink-muted">{t("settings.seedCommand")}:</p>
          <code className="block rounded-xs border border-line bg-surface-muted px-2 py-1.5 font-mono text-2xs">
            LOG_LEVEL=ERROR make -s demo-seed &gt; /tmp/demo-seed.json
          </code>
          {seed !== null && (
            <>
              <div className="overflow-x-auto">
                <Table caption={t("dashboard.seed")}>
                  <THead>
                    <TR>
                      <TH>{t("settings.seedTopic")}</TH>
                      <TH>{t("settings.seedPack")}</TH>
                      <TH>{t("common.actions")}</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {Object.entries(seed.pack_ids).map(([topic, packId]) => (
                      <TR key={topic}>
                        <TD>{topic}</TD>
                        <TD className="font-mono text-2xs">{packId}</TD>
                        <TD>
                          <CopyButton value={packId} />
                        </TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>
              <div className="rounded-xs border border-line bg-surface-muted px-2 py-1.5 text-2xs">
                {snapshot.isLoading ? (
                  <span>{t("common.loading")}</span>
                ) : snapshot.error !== null && snapshot.error !== undefined ? (
                  <ErrorState error={snapshot.error} />
                ) : snapshot.data !== undefined ? (
                  <span>
                    {t("evidence.snapshot")}: {snapshot.data.label} · {snapshot.data.index.passage_count}{" "}
                    {t("evidence.passage")} · {truncateMiddle(snapshot.data.manifest_hash, 14, 6)}
                  </span>
                ) : (
                  <span>{t("settings.seedSnapshotMissing")}</span>
                )}
              </div>
            </>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title={t("settings.defaults")} />
        <CardBody className="space-y-3">
          <Field label={t("settings.defaultQuestion")} htmlFor="default-question">
            <TextArea
              id="default-question"
              rows={3}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label={t("new.roundCap")} htmlFor="default-round-cap">
              <TextInput
                id="default-round-cap"
                type="number"
                min={1}
                max={50}
                value={roundCap}
                onChange={(event) => setRoundCap(event.target.value)}
              />
            </Field>
            <Field label={t("new.threshold")} htmlFor="default-threshold">
              <TextInput
                id="default-threshold"
                type="number"
                min={0.01}
                max={1}
                step="any"
                value={threshold}
                onChange={(event) => setThreshold(event.target.value)}
              />
            </Field>
            <Field label={t("usage.maxInvocations")} htmlFor="default-budget">
              <TextInput
                id="default-budget"
                type="number"
                min={1}
                value={budget}
                onChange={(event) => setBudget(event.target.value)}
              />
            </Field>
          </div>
          <fieldset>
            <legend className="text-sm font-medium">{t("settings.defaultStakeholders")}</legend>
            <div className="mt-2 grid gap-1 sm:grid-cols-2">
              {(stakeholders.data?.items ?? []).map((item) => (
                <Checkbox
                  key={item.stakeholder_id}
                  label={item.identity.short_name}
                  checked={defaultIds.includes(item.stakeholder_id)}
                  onChange={() =>
                    setDefaultIds((current) =>
                      current.includes(item.stakeholder_id)
                        ? current.filter((id) => id !== item.stakeholder_id)
                        : [...current, item.stakeholder_id],
                    )
                  }
                />
              ))}
            </div>
          </fieldset>
          <Button variant="primary" onClick={saveDefaults}>
            {t("settings.saveDefaults")}
          </Button>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title={t("settings.appearance")} />
        <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Field label={t("settings.language")} htmlFor="setting-locale">
            <Select
              id="setting-locale"
              value={settings.locale}
              onChange={(event) => updateSettings({ locale: event.target.value as "de-AT" | "en" })}
            >
              <option value="de-AT">Deutsch (AT)</option>
              <option value="en">English</option>
            </Select>
          </Field>
          <Field label={t("settings.theme")} htmlFor="setting-theme">
            <Select
              id="setting-theme"
              value={settings.theme}
              onChange={(event) =>
                updateSettings({
                  theme: event.target.value as "portal" | "contrast",
                })
              }
            >
              {["portal", "contrast"].map((value) => (
                <option key={value} value={value}>
                  {enumLabel("theme", value, locale)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t("settings.density")} htmlFor="setting-density">
            <Select
              id="setting-density"
              value={settings.density}
              onChange={(event) =>
                updateSettings({ density: event.target.value as "comfortable" | "compact" })
              }
            >
              {["comfortable", "compact"].map((value) => (
                <option key={value} value={value}>
                  {enumLabel("density", value, locale)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t("settings.motion")} htmlFor="setting-motion">
            <Select
              id="setting-motion"
              value={settings.motion}
              onChange={(event) => updateSettings({ motion: event.target.value as "full" | "reduced" })}
            >
              {["full", "reduced"].map((value) => (
                <option key={value} value={value}>
                  {enumLabel("motion", value, locale)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t("settings.timeZone")} htmlFor="setting-timezone">
            <TextInput id="setting-timezone" value={settings.timeZone} readOnly />
          </Field>
          <Field label={t("settings.numberFormat")} htmlFor="setting-number">
            <Select
              id="setting-number"
              value={settings.numberLocale}
              onChange={(event) => updateSettings({ numberLocale: event.target.value as "de-AT" | "en-GB" })}
            >
              <option value="de-AT">de-AT</option>
              <option value="en-GB">en-GB</option>
            </Select>
          </Field>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title={t("settings.guardrails")} description={t("settings.guardrailsHint")} />
        <CardBody className="space-y-3">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <StatusPill tone="info">
              {t("governance.allowlist")}: {allowlist.data?.institutions.length ?? "—"}
            </StatusPill>
            <StatusPill tone="info">
              {t("claims.referenceFigures")}: {figures.data?.items.length ?? "—"}
            </StatusPill>
            <Link href="/stakeholders" className="text-sm">
              {t("nav.stakeholders")}
            </Link>
            <Link href="/claims" className="text-sm">
              {t("nav.claims")}
            </Link>
          </div>
          {allowlist.isLoading ? (
            <LoadingBlock rows={2} />
          ) : allowlist.error !== null && allowlist.error !== undefined ? (
            <ErrorState error={allowlist.error} />
          ) : (
            <div className="overflow-x-auto">
              <Table caption={t("governance.allowlist")}>
                <THead>
                  <TR>
                    <TH>{t("governance.aliases")}</TH>
                    <TH>{t("stakeholders.title")}</TH>
                    <TH>{t("governance.allowlistVersion")}</TH>
                  </TR>
                </THead>
                <TBody>
                  {allowlist.data?.institutions.map((institution) => (
                    <TR key={institution.code}>
                      <TD className="font-mono text-2xs">{institution.aliases.join(", ") || "—"}</TD>
                      <TD>{institution.canonical_name}</TD>
                      <TD className="font-mono text-2xs">{institution.code}</TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </div>
          )}
          <div className="overflow-x-auto">
            <Table caption={t("claims.authorityOrder")}>
              <THead>
                <TR>
                  <TH>{t("claims.claimType")}</TH>
                  <TH>{t("claims.tier")}</TH>
                </TR>
              </THead>
              <TBody>
                {(rules.data ?? []).map((rule) => (
                  <TR key={rule.claim_type}>
                    <TD>{enumLabel("claimType", rule.claim_type, locale)}</TD>
                    <TD>
                      {rule.ordered_tiers
                        .map((tier) => enumLabel("authorityTier", tier, locale))
                        .join(" > ")}
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title={t("settings.capabilities")} />
        <CardBody className="space-y-3">
          {readyz.isLoading ? (
            <LoadingBlock rows={4} />
          ) : readyz.error !== null && readyz.error !== undefined ? (
            <ErrorState error={readyz.error} onRetry={() => void readyz.refetch()} />
          ) : readyz.data !== undefined ? (
            <>
              {readyz.data.checks["llm"] === "scripted" && (
                <p className="rounded-xs border border-warn/40 bg-warn-quiet px-2 py-1.5 text-sm text-warn">
                  {t("settings.scriptedCallout")}
                </p>
              )}
              {readyz.data.checks["simulation_pricing"] === "zero" && (
                <p className="rounded-xs border border-warn/40 bg-warn-quiet px-2 py-1.5 text-sm text-warn">
                  {t("settings.pricingCallout")}
                </p>
              )}
              <div className="overflow-x-auto">
                <Table caption={t("settings.capabilities")}>
                  <THead>
                    <TR>
                      <TH>{t("settings.capabilities")}</TH>
                      <TH>{t("health.status")}</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {Object.entries(readyz.data.checks).map(([key, value]) => (
                      <TR key={key}>
                        <TD className="font-mono text-2xs">{key}</TD>
                        <TD>
                          <StatusPill
                            tone={
                              value === "ok" || value === "ready" || value === "wired"
                                ? "ok"
                                : value === "degraded" || value === "absent"
                                  ? "warn"
                                  : "neutral"
                            }
                          >
                            {value}
                          </StatusPill>
                        </TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>
            </>
          ) : null}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title={t("settings.diagnostics")}
          actions={
            <div className="flex gap-2" data-print-hide>
              <CopyButton value={JSON.stringify(readyz.data ?? {}, null, 2)} label={t("common.copy")} />
              <Button size="sm" onClick={() => void copyDiagnostics()}>
                {t("common.diagnostics")}
              </Button>
              <Link
                href="/api/hps/_platform/openapi.json"
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-8 items-center rounded-md border border-line px-2.5 text-2xs no-underline"
              >
                {t("settings.openapiLink")}
              </Link>
            </div>
          }
        />
        <CardBody className="space-y-3">
          <JsonBlock value={readyz.data ?? {}} summary={t("settings.rawReadyz")} />
          <div>
            <h3 className="text-sm font-semibold">{t("settings.failedRequests")}</h3>
            {failures.length === 0 ? (
              <p className="mt-1 text-sm text-ink-muted">{t("settings.noFailedRequests")}</p>
            ) : (
              <ul className="mt-1 space-y-1 font-mono text-2xs">
                {failures.map((failure, index) => (
                  <li key={`${failure.at}-${index}`}>
                    {t("settings.failedRequestLine", {
                      method: failure.method,
                      path: failure.path,
                      status: failure.status,
                      code: failure.code,
                      time: failure.at,
                    })}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title={t("settings.reset")} />
        <CardBody className="space-y-2">
          <ResetRow
            label={t("settings.resetSettings")}
            hint={t("settings.resetSettingsHint")}
            confirm={t("settings.resetConfirm")}
            onReset={() => {
              clearSettings();
              setSettings(DEFAULT_SETTINGS);
              push(t("settings.resetDone"), "ok");
            }}
          />
          <ResetRow
            label={t("settings.resetSeed")}
            hint={t("settings.resetSeedHint")}
            confirm={t("settings.resetConfirm")}
            onReset={() => {
              clearSeed();
              setSeedText("");
              push(t("settings.resetDone"), "ok");
            }}
          />
          <ResetRow
            label={t("settings.resetRuns")}
            hint={t("settings.resetRunsHint")}
            confirm={t("settings.resetConfirm")}
            onReset={() => {
              clearRunIndex();
              push(t("settings.resetDone"), "ok");
            }}
          />
        </CardBody>
      </Card>
    </div>
  );
}

function ResetRow({
  label,
  hint,
  confirm,
  onReset,
}: {
  readonly label: string;
  readonly hint: string;
  readonly confirm: string;
  readonly onReset: () => void;
}) {
  const { t } = useSettings();
  const [armed, setArmed] = useState(false);
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-line px-3 py-2">
      <div className="min-w-0">
        <p className="text-sm font-medium">{label}</p>
        <p className="text-2xs text-ink-muted">{hint}</p>
      </div>
      <div className="flex items-center gap-2">
        {armed ? (
          <>
            <span className="text-2xs text-danger">{confirm}</span>
            <Button
              size="sm"
              variant="danger"
              onClick={() => {
                onReset();
                setArmed(false);
              }}
            >
              {label}
            </Button>
            <Button size="sm" onClick={() => setArmed(false)}>
              {t("common.cancel")}
            </Button>
          </>
        ) : (
          <Button size="sm" variant="danger" onClick={() => setArmed(true)}>
            {label}
          </Button>
        )}
      </div>
    </div>
  );
}
