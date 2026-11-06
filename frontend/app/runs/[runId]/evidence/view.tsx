"use client";

import { useQueries } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { useSettings, useToast } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Checkbox, Field, Select, TextArea, TextInput } from "@/components/ui/field";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/ui/states";
import { StatusPill } from "@/components/ui/status-pill";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { getPassage } from "@/features/corpus/api";
import { AuthorityRecencyChart } from "@/features/evidence/components/authority-recency-chart";
import { ScoreDecompositionChart } from "@/features/evidence/components/score-decomposition-chart";
import {
  useAssemblePack,
  useEvidencePack,
  useReweightPack,
  useSearchCandidates,
} from "@/features/evidence/hooks";
import type { Candidate } from "@/features/evidence/contracts";
import { useSeed } from "@/features/run/hooks";
import { enumLabel } from "@/lib/i18n";
import { formatDate, formatDecimal, truncateMiddle } from "@/lib/format";
import { SOURCE_TYPES } from "@/features/evidence/constants";

const CLAIM_TYPES = ["quantitative", "legal", "causal", "qualitative"] as const;

export default function EvidencePage() {
  const { t, locale } = useSettings();
  const { push } = useToast();
  const seed = useSeed();
  const [packId, setPackId] = useState("");
  const [claim, setClaim] = useState(seed?.topics[0]?.claim ?? "");
  const [claimType, setClaimType] = useState<(typeof CLAIM_TYPES)[number]>("qualitative");
  const [snapshotId, setSnapshotId] = useState(seed?.snapshot_id ?? "");
  const [limit, setLimit] = useState(20);
  const [halfLife, setHalfLife] = useState("540");
  const [exempt, setExempt] = useState<readonly string[]>([]);

  useEffect(() => {
    if (seed === null) return;
    setPackId((current) => (current === "" ? (Object.values(seed.pack_ids)[0] ?? "") : current));
    setSnapshotId((current) => (current === "" ? seed.snapshot_id : current));
    setClaim((current) => (current === "" ? (seed.topics[0]?.claim ?? "") : current));
  }, [seed]);

  const pack = useEvidencePack(packId);
  const search = useSearchCandidates();
  const assemble = useAssemblePack();
  const reweight = useReweightPack(packId);
  const candidates = useMemo<readonly Candidate[]>(() => pack.data?.candidates ?? [], [pack.data]);
  const passageQueries = useQueries({
    queries: candidates.map((candidate) => ({
      queryKey: ["passage", candidate.passage_id],
      queryFn: ({ signal }) => getPassage(candidate.passage_id, signal),
      staleTime: 60_000,
    })),
  });
  const snippets = useMemo(() => {
    const map = new Map<string, string>();
    candidates.forEach((candidate, index) => {
      const data = passageQueries[index]?.data;
      if (data !== undefined) map.set(candidate.passage_id, data.text);
    });
    return map;
  }, [candidates, passageQueries]);

  const runSearch = (): void => {
    search.mutate(
      { claim, claim_type: claimType, snapshot_id: snapshotId, limit },
      { onSuccess: () => push(t("evidence.searchSuccess"), "ok") },
    );
  };

  const runAssemble = (): void => {
    assemble.mutate(
      { claim, claim_type: claimType, snapshot_id: snapshotId },
      {
        onSuccess: (created) => {
          setPackId(created.pack_id);
          push(t("evidence.assembleSuccess"), "ok");
        },
      },
    );
  };

  const runReweight = (): void => {
    reweight.mutate(
      {
        policy: {
          half_life_days: Number(halfLife) > 0 ? Number(halfLife) : 540,
          exempt_source_types: exempt as (typeof SOURCE_TYPES)[number][],
        },
      },
      {
        onSuccess: (updated) => {
          setPackId(updated.pack_id);
          push(t("evidence.reweightSuccess"), "ok");
        },
      },
    );
  };

  const searchCandidates = search.data?.candidates ?? [];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title={t("evidence.title")} description={t("evidence.semanticNote")} />
        <CardBody className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={t("evidence.selectPack")} htmlFor="pack-id" hint={seed === null ? t("dashboard.seedMissing") : undefined}>
              <TextInput
                id="pack-id"
                value={packId}
                onChange={(event) => setPackId(event.target.value)}
                placeholder="evp_…"
                className="font-mono"
              />
            </Field>
            {seed !== null && (
              <Field label={t("dashboard.seed")} htmlFor="pack-select">
                <Select
                  id="pack-select"
                  value={Object.values(seed.pack_ids).includes(packId) ? packId : ""}
                  onChange={(event) => setPackId(event.target.value)}
                >
                  <option value="">{t("common.none")}</option>
                  {Object.entries(seed.pack_ids).map(([key, id]) => (
                    <option key={id} value={id}>
                      {key}
                    </option>
                  ))}
                </Select>
              </Field>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            <CodeChip label={t("evidence.snapshot")} value={snapshotId} />
            {pack.data !== undefined && (
              <>
                <StatusPill tone="info">{pack.data.trace.retrieval_mode}</StatusPill>
                <StatusPill>{t("evidence.frozenAt")}: {formatDate(pack.data.frozen_at, locale)}</StatusPill>
              </>
            )}
          </div>

          {packId === "" ? (
            <EmptyState title={t("evidence.noPack")} hint={t("dashboard.seedMissing")} />
          ) : pack.isLoading ? (
            <LoadingBlock rows={4} />
          ) : pack.error !== null && pack.error !== undefined ? (
            <ErrorState error={pack.error} onRetry={() => void pack.refetch()} />
          ) : pack.data === undefined ? null : (
            <>
              <p className="text-sm font-medium">{pack.data.claim}</p>
              {pack.data.absence !== null && pack.data.absence !== undefined && (
                <div className="rounded-md border border-warn/40 bg-warn-quiet px-3 py-2">
                  <p className="text-sm font-semibold text-warn">{t("evidence.absence")}</p>
                  <p className="mt-1 text-sm text-ink-muted">{t("evidence.absenceHint")}</p>
                  <p className="mt-1 text-2xs text-ink-muted">
                    {t("evidence.snapshot")}: <span className="font-mono">{pack.data.absence.snapshot_id}</span>
                  </p>
                  <p className="text-2xs text-ink-muted">{pack.data.absence.reason}</p>
                  <p className="mt-1 text-2xs text-ink-muted">{t("evidence.queries")}:</p>
                  <ul className="mt-1 list-inside list-disc font-mono text-2xs">
                    {pack.data.absence.queries.map((query) => (
                      <li key={query}>{query}</li>
                    ))}
                  </ul>
                </div>
              )}

              <details className="rounded-md border border-line bg-surface-muted">
                <summary className="cursor-pointer px-3 py-2 text-sm font-medium">
                  {t("evidence.trace")}
                </summary>
                <dl className="grid gap-2 border-t border-line px-3 py-2 text-2xs sm:grid-cols-2">
                  <div>
                    <dt className="text-ink-muted">{t("evidence.traceEmbedding")}</dt>
                    <dd className="font-mono">{pack.data.trace.embedding_model}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted">{t("evidence.traceReranker")}</dt>
                    <dd className="font-mono">{pack.data.trace.reranker_model}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted">{t("evidence.traceRewrite")}</dt>
                    <dd>{pack.data.trace.query_rewrite}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted">{t("evidence.traceMode")}</dt>
                    <dd>{pack.data.trace.retrieval_mode}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted">{t("evidence.traceIndex")}</dt>
                    <dd className="font-mono">{pack.data.trace.index_version}</dd>
                  </div>
                  <div>
                    <dt className="text-ink-muted">{t("evidence.traceStances")}</dt>
                    <dd>
                      {Object.entries(pack.data.trace.stance_counts)
                        .map(([stance, count]) => `${stance}: ${count}`)
                        .join(" · ")}
                    </dd>
                  </div>
                </dl>
              </details>

              {candidates.length === 0 ? (
                <EmptyState title={t("evidence.noCandidates")} />
              ) : (
                <>
                  <div className="grid gap-4 xl:grid-cols-2">
                    <Card>
                      <CardBody>
                        <ScoreDecompositionChart candidates={candidates} locale={locale} />
                      </CardBody>
                    </Card>
                    <Card>
                      <CardBody>
                        <AuthorityRecencyChart
                          candidates={candidates}
                          snippets={snippets}
                          locale={locale}
                        />
                      </CardBody>
                    </Card>
                  </div>
                  <div className="overflow-x-auto">
                    <Table caption={t("evidence.candidates")}>
                      <THead>
                        <TR>
                          <TH>{t("evidence.passage")}</TH>
                          <TH>{t("evidence.stance")}</TH>
                          <TH>{t("evidence.provenance")}</TH>
                          <TH className="text-right">{t("evidence.final")}</TH>
                        </TR>
                      </THead>
                      <TBody>
                        {candidates.map((candidate) => (
                          <TR key={candidate.passage_id}>
                            <TD className="max-w-md">
                              <p className="font-mono text-2xs text-ink-muted">
                                {truncateMiddle(candidate.passage_id)}
                              </p>
                              <p className="mt-1 text-sm">
                                {snippets.get(candidate.passage_id) ?? t("evidence.passageUnavailable")}
                              </p>
                            </TD>
                            <TD>
                              <StatusPill
                                tone={
                                  candidate.stance === "contradicting"
                                    ? "danger"
                                    : candidate.stance === "supporting"
                                      ? "ok"
                                      : "neutral"
                                }
                              >
                                {enumLabel("stanceLabel", candidate.stance, locale)}
                              </StatusPill>
                            </TD>
                            <TD className="text-2xs">
                              {candidate.provenance === null ? (
                                "—"
                              ) : (
                                <>
                                  {candidate.provenance.outlet} ·{" "}
                                  {formatDate(candidate.provenance.published_on, locale)} ·{" "}
                                  {t("evidence.page", {
                                    from: candidate.provenance.page_from,
                                    to: candidate.provenance.page_to,
                                  })}
                                </>
                              )}
                            </TD>
                            <TD className="text-right tabular">
                              {formatDecimal(String(candidate.score.final), locale)}
                            </TD>
                          </TR>
                        ))}
                      </TBody>
                    </Table>
                  </div>
                </>
              )}
            </>
          )}
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title={t("evidence.searchTitle")} />
          <CardBody className="space-y-3">
            <Field label={t("evidence.claim")} htmlFor="search-claim">
              <TextArea
                id="search-claim"
                rows={3}
                value={claim}
                onChange={(event) => setClaim(event.target.value)}
              />
            </Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label={t("evidence.claimType")} htmlFor="search-type">
                <Select
                  id="search-type"
                  value={claimType}
                  onChange={(event) => setClaimType(event.target.value as (typeof CLAIM_TYPES)[number])}
                >
                  {CLAIM_TYPES.map((value) => (
                    <option key={value} value={value}>
                      {enumLabel("claimType", value, locale)}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label={t("evidence.limit")} htmlFor="search-limit">
                <Select
                  id="search-limit"
                  value={String(limit)}
                  onChange={(event) => setLimit(Number(event.target.value))}
                >
                  {[5, 10, 20, 50].map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <Field label={t("evidence.snapshot")} htmlFor="search-snapshot">
              <TextInput
                id="search-snapshot"
                value={snapshotId}
                onChange={(event) => setSnapshotId(event.target.value)}
                className="font-mono"
                placeholder="snp_…"
              />
            </Field>
            {search.error !== null && search.error !== undefined && <ErrorState error={search.error} />}
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={runSearch}
                loading={search.isPending}
                disabledReason={snapshotId === "" ? t("evidence.snapshot") : undefined}
              >
                {t("evidence.search")}
              </Button>
              <Button
                onClick={runAssemble}
                loading={assemble.isPending}
                disabledReason={snapshotId === "" ? t("evidence.snapshot") : undefined}
              >
                {t("evidence.assemble")}
              </Button>
            </div>
            {assemble.error !== null && assemble.error !== undefined && (
              <ErrorState error={assemble.error} />
            )}
            {search.data !== undefined &&
              (searchCandidates.length === 0 ? (
                <EmptyState title={t("evidence.noCandidates")} />
              ) : (
              <div className="overflow-x-auto">
                <Table caption={t("evidence.searchTitle")}>
                  <THead>
                    <TR>
                      <TH>{t("evidence.passage")}</TH>
                      <TH>{t("evidence.stance")}</TH>
                      <TH className="text-right">{t("evidence.final")}</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {searchCandidates.map((candidate) => (
                      <TR key={candidate.passage_id}>
                        <TD className="font-mono text-2xs">{truncateMiddle(candidate.passage_id)}</TD>
                        <TD>{enumLabel("stanceLabel", candidate.stance, locale)}</TD>
                        <TD className="text-right tabular">
                          {formatDecimal(String(candidate.score.final), locale)}
                        </TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>
              ))}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title={t("evidence.reweight")} />
          <CardBody className="space-y-3">
            <Field label={t("evidence.halfLife")} htmlFor="half-life">
              <TextInput
                id="half-life"
                type="number"
                min={1}
                value={halfLife}
                onChange={(event) => setHalfLife(event.target.value)}
              />
            </Field>
            <fieldset>
              <legend className="text-sm font-medium">{t("evidence.exempt")}</legend>
              <div className="mt-2 grid gap-1 sm:grid-cols-2">
                {SOURCE_TYPES.map((value) => (
                  <Checkbox
                    key={value}
                    label={enumLabel("authorityTier", value, locale)}
                    checked={exempt.includes(value)}
                    onChange={() =>
                      setExempt((current) =>
                        current.includes(value)
                          ? current.filter((item) => item !== value)
                          : [...current, value],
                      )
                    }
                  />
                ))}
              </div>
            </fieldset>
            {reweight.error !== null && reweight.error !== undefined && (
              <ErrorState error={reweight.error} />
            )}
            <Button
              onClick={runReweight}
              loading={reweight.isPending}
              disabledReason={packId === "" ? t("evidence.selectPack") : undefined}
            >
              {t("evidence.reweight")}
            </Button>
            <p className="text-2xs text-ink-subtle">{t("evidence.semanticNote")}</p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function CodeChip({ label, value }: { readonly label: string; readonly value: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-xs border border-line bg-surface px-1.5 py-0.5 text-2xs">
      <span className="text-ink-muted">{label}:</span>
      <span className="font-mono">{value === "" ? "—" : truncateMiddle(value)}</span>
    </span>
  );
}
