"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Icon } from "@/components/icons";
import { useSettings, useToast } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { CopyButton } from "@/components/ui/copy-button";
import { ExpandableText } from "@/components/ui/expandable-text";
import { Field, Select, TextArea, TextInput } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { Stat } from "@/components/ui/stat";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/ui/states";
import { StatusPill, type StatusTone } from "@/components/ui/status-pill";
import {
  SOURCE_TYPES,
  type IngestionOutcomeValue,
  type IngestionRunStatus,
  type SourceType,
} from "@/features/corpus/contracts";
import {
  useIngestDocument,
  useIngestionRun,
  usePinSnapshot,
  usePublishDocument,
  useSnapshotDetails,
  useStartIngestionRun,
} from "@/features/corpus/hooks";
import { useReadyz } from "@/features/platform/hooks";
import { cn } from "@/lib/cn";
import {
  loadIngestionRuns,
  loadSnapshots,
  saveIngestionRun,
  saveSnapshot,
  type IngestionRunEntry,
  type SnapshotEntry,
} from "@/lib/corpus-history";
import { formatDateTime, formatDecimal, truncateMiddle } from "@/lib/format";
import { enumLabel } from "@/lib/i18n";

const DEFAULT_OUTLET = "APA-Journal Gesundheit";
const DEFAULT_MEDIUM = "online";

function lines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line !== "");
}

function runStatusTone(status: IngestionRunStatus): StatusTone {
  if (status === "completed") return "ok";
  if (status === "failed") return "danger";
  return "info";
}

function outcomeTone(outcome: IngestionOutcomeValue): StatusTone {
  if (outcome === "accepted") return "ok";
  if (outcome === "quarantined") return "warn";
  return "danger";
}

function isRunStatus(value: string): value is IngestionRunStatus {
  return value === "running" || value === "completed" || value === "failed";
}

export default function CorpusPage() {
  const { t, locale } = useSettings();
  const { push } = useToast();
  const readyz = useReadyz();

  const [shard, setShard] = useState("");
  const [pathsText, setPathsText] = useState("");
  const [runId, setRunId] = useState("");
  const [runLookup, setRunLookup] = useState("");
  const [history, setHistory] = useState<readonly IngestionRunEntry[]>([]);

  const [snapshotLabel, setSnapshotLabel] = useState("");
  const [documentIdsText, setDocumentIdsText] = useState("");
  const [snapshotId, setSnapshotId] = useState("");
  const [snapshotLookup, setSnapshotLookup] = useState("");
  const [snapshots, setSnapshots] = useState<readonly SnapshotEntry[]>([]);

  const [sourceUri, setSourceUri] = useState("");
  const [outlet, setOutlet] = useState(DEFAULT_OUTLET);
  const [publishedOn, setPublishedOn] = useState("");
  const [medium, setMedium] = useState(DEFAULT_MEDIUM);
  const [sourceType, setSourceType] = useState<SourceType>("press_report");
  const [documentId, setDocumentId] = useState("");

  const runQuery = useIngestionRun(runId);
  const snapshotQuery = useSnapshotDetails(snapshotId);
  const startBatch = useStartIngestionRun();
  const pin = usePinSnapshot();
  const ingest = useIngestDocument();
  const publish = usePublishDocument();

  useEffect(() => {
    setHistory(loadIngestionRuns());
    setSnapshots(loadSnapshots());
  }, []);

  useEffect(() => {
    const data = runQuery.data;
    if (data === undefined) return;
    const existing = loadIngestionRuns().find((item) => item.runId === data.run_id);
    saveIngestionRun({
      runId: data.run_id,
      shardLabel: data.shard_label,
      status: data.status,
      attempted: data.attempted,
      accepted: data.accepted,
      quarantined: data.quarantined,
      failed: data.failed,
      createdAt: existing?.createdAt ?? new Date().toISOString(),
    });
    setHistory(loadIngestionRuns());
  }, [runQuery.data]);

  useEffect(() => {
    const data = snapshotQuery.data;
    if (data === undefined) return;
    saveSnapshot({
      snapshotId: data.snapshot_id,
      label: data.label,
      manifestHash: data.manifest_hash,
      pinnedAt: data.pinned_at,
      documentCount: data.document_ids.length,
      passageCount: data.index.passage_count,
    });
    setSnapshots(loadSnapshots());
  }, [snapshotQuery.data]);

  const paths = useMemo(() => lines(pathsText), [pathsText]);
  const documentIds = useMemo(() => lines(documentIdsText), [documentIdsText]);
  const ocr = readyz.data?.checks["ocr"] ?? "unknown";
  const ocrAvailable = ocr === "available";
  const retrieval = readyz.data?.checks["evidence_retrieval_mode"];

  const canStart = shard.trim() !== "" && paths.length > 0;
  const canPin = snapshotLabel.trim() !== "";
  const canExtract =
    sourceUri.trim() !== "" && outlet.trim() !== "" && medium.trim() !== "";

  const startHandler = (): void => {
    if (!canStart) return;
    startBatch.mutate(
      { shard_label: shard.trim(), paths },
      {
        onSuccess: (result) => {
          saveIngestionRun({
            runId: result.run_id,
            shardLabel: shard.trim(),
            status: result.status,
            attempted: 0,
            accepted: 0,
            quarantined: 0,
            failed: 0,
            createdAt: new Date().toISOString(),
          });
          setHistory(loadIngestionRuns());
          setRunId(result.run_id);
          setRunLookup(result.run_id);
          push(t("corpus.started"), "ok");
        },
      },
    );
  };

  const loadRun = (): void => {
    const value = runLookup.trim();
    if (value === "") return;
    if (value === runId) void runQuery.refetch();
    else setRunId(value);
  };

  const pinHandler = (): void => {
    if (!canPin) return;
    pin.mutate(
      {
        label: snapshotLabel.trim(),
        ...(documentIds.length > 0 ? { document_ids: documentIds } : {}),
      },
      {
        onSuccess: (result) => {
          setSnapshotId(result.snapshot_id);
          setSnapshotLookup(result.snapshot_id);
          push(t("corpus.pinned"), "ok");
        },
      },
    );
  };

  const loadSnapshot = (): void => {
    const value = snapshotLookup.trim();
    if (value === "") return;
    if (value === snapshotId) void snapshotQuery.refetch();
    else setSnapshotId(value);
  };

  const extractHandler = (): void => {
    if (!canExtract) return;
    ingest.mutate(
      {
        source_uri: sourceUri.trim(),
        publication: {
          outlet: outlet.trim(),
          published_on: publishedOn === "" ? new Date().toISOString().slice(0, 10) : publishedOn,
          medium: medium.trim(),
        },
        source_type: sourceType,
      },
      {
        onSuccess: (result) => {
          setDocumentId(result.document_id);
          push(t("corpus.extracted"), "ok");
        },
      },
    );
  };

  const publishHandler = (): void => {
    if (documentId === "") return;
    publish.mutate(documentId, {
      onSuccess: () => push(t("corpus.published"), "ok"),
    });
  };

  const run = runQuery.data;
  const snapshot = snapshotQuery.data;

  return (
    <div className="space-y-4">
      <PageHeader
        title={t("corpus.title")}
        subtitle={t("corpus.subtitle")}
        meta={
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill tone={ocrAvailable ? "ok" : "warn"}>
              {t("corpus.ocr")}:{" "}
              {ocrAvailable ? t("corpus.ocrAvailable") : t("corpus.ocrAbsent")}
            </StatusPill>
            {retrieval !== undefined && <StatusPill tone="neutral">{retrieval}</StatusPill>}
          </div>
        }
      />

      {readyz.data !== undefined && !ocrAvailable && (
        <div
          role="status"
          className="flex items-start gap-2 border border-warn/40 bg-warn-quiet px-4 py-3 text-sm text-warn"
        >
          <span className="mt-0.5">
            <Icon name="warning" />
          </span>
          <p>{t("corpus.ocrWarning")}</p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title={t("corpus.batchTitle")} description={t("corpus.batchHint")} />
          <CardBody className="space-y-3">
            <div className="border border-warn/40 bg-warn-quiet px-3 py-2 text-2xs text-warn">
              {t("corpus.batchWarning")}
            </div>
            <Field label={t("corpus.shard")} htmlFor="batch-shard" hint={t("corpus.shardHint")}>
              <TextInput
                id="batch-shard"
                value={shard}
                onChange={(event) => setShard(event.target.value)}
                placeholder={t("corpus.shardPlaceholder")}
                autoComplete="off"
              />
            </Field>
            <Field label={t("corpus.paths")} htmlFor="batch-paths" hint={t("corpus.pathsHint")}>
              <TextArea
                id="batch-paths"
                rows={6}
                value={pathsText}
                onChange={(event) => setPathsText(event.target.value)}
                placeholder={t("corpus.pathsPlaceholder")}
                className="font-mono text-2xs"
              />
            </Field>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="primary"
                onClick={startHandler}
                disabled={!canStart}
                disabledReason={!canStart ? t("corpus.startDisabled") : undefined}
                loading={startBatch.isPending}
              >
                {startBatch.isPending ? t("corpus.starting") : t("corpus.start")}
              </Button>
              <span className="text-2xs text-ink-muted">
                {t("corpus.pathCount", { count: paths.length })}
              </span>
            </div>
            {!canStart && <p className="text-2xs text-ink-muted">{t("corpus.startDisabled")}</p>}
            {startBatch.error !== null && startBatch.error !== undefined && (
              <ErrorState error={startBatch.error} />
            )}
            <details className="border border-line bg-surface-muted">
              <summary className="cursor-pointer px-3 py-2 font-heading text-2xs font-bold uppercase tracking-[0.04em] text-ink-muted">
                {t("corpus.offline")}
              </summary>
              <div className="space-y-2 border-t border-line p-3">
                <p className="text-2xs text-ink-muted">{t("corpus.offlineHint")}</p>
                <pre className="overflow-x-auto bg-surface p-2 font-mono text-2xs">
                  {`cd backend\npython scripts/ingest_corpus.py material/ --snapshot-label ${
                    shard.trim() === "" ? "<label>" : shard.trim()
                  }`}
                </pre>
              </div>
            </details>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title={t("corpus.documentTitle")} description={t("corpus.documentHint")} />
          <CardBody className="space-y-3">
            <Field
              label={t("corpus.sourceUri")}
              htmlFor="document-uri"
              hint={t("corpus.sourceUriHint")}
            >
              <TextInput
                id="document-uri"
                value={sourceUri}
                onChange={(event) => setSourceUri(event.target.value)}
                placeholder={t("corpus.sourceUriPlaceholder")}
                className="font-mono text-2xs"
                autoComplete="off"
              />
            </Field>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label={t("corpus.outlet")} htmlFor="document-outlet">
                <TextInput
                  id="document-outlet"
                  value={outlet}
                  onChange={(event) => setOutlet(event.target.value)}
                />
              </Field>
              <Field label={t("corpus.publishedOn")} htmlFor="document-date">
                <TextInput
                  id="document-date"
                  type="date"
                  value={publishedOn}
                  onChange={(event) => setPublishedOn(event.target.value)}
                />
              </Field>
              <Field label={t("corpus.medium")} htmlFor="document-medium">
                <TextInput
                  id="document-medium"
                  value={medium}
                  onChange={(event) => setMedium(event.target.value)}
                />
              </Field>
              <Field label={t("corpus.sourceType")} htmlFor="document-type">
                <Select
                  id="document-type"
                  value={sourceType}
                  onChange={(event) => setSourceType(event.target.value as SourceType)}
                >
                  {SOURCE_TYPES.map((value) => (
                    <option key={value} value={value}>
                      {enumLabel("sourceType", value, locale)}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="primary"
                onClick={extractHandler}
                disabled={!canExtract}
                disabledReason={!canExtract ? t("corpus.extractDisabled") : undefined}
                loading={ingest.isPending}
              >
                {ingest.isPending ? t("corpus.extracting") : t("corpus.extract")}
              </Button>
              {documentId !== "" && (
                <Button onClick={publishHandler} loading={publish.isPending}>
                  {publish.isPending ? t("corpus.publishing") : t("corpus.publish")}
                </Button>
              )}
            </div>
            {!canExtract && <p className="text-2xs text-ink-muted">{t("corpus.extractDisabled")}</p>}
            {ingest.error !== null && ingest.error !== undefined && <ErrorState error={ingest.error} />}
            {publish.error !== null && publish.error !== undefined && (
              <ErrorState error={publish.error} />
            )}
            {ingest.data !== undefined && (
              <div className="space-y-2 border border-line bg-surface-muted p-3 text-sm">
                <p className="flex flex-wrap items-center gap-2">
                  <span className="text-ink-muted">{t("corpus.documentId")}:</span>
                  <span className="break-all font-mono text-2xs">{ingest.data.document_id}</span>
                  <CopyButton value={ingest.data.document_id} size="sm" />
                </p>
                {ingest.data.quality !== null && (
                  <p className="text-2xs text-ink-muted">
                    {t("corpus.qualityConfidence")}:{" "}
                    {formatDecimal(String(ingest.data.quality.confidence), locale)} ·{" "}
                    {t("corpus.qualityPages")}: {ingest.data.quality.page_count} ·{" "}
                    {t("corpus.qualityMethod")}: {ingest.data.quality.method} ·{" "}
                    {t("corpus.qualityGlyphs")}:{" "}
                    {formatDecimal(String(ingest.data.quality.missing_glyph_rate), locale)}
                  </p>
                )}
                <div className="flex flex-wrap items-center gap-2">
                  <StatusPill tone={ingest.data.citable ? "ok" : "warn"}>
                    {ingest.data.citable ? t("corpus.citable") : t("corpus.notCitable")}
                  </StatusPill>
                  {publish.data !== undefined ? (
                    <span className="text-2xs text-ink-muted">
                      {t("corpus.articleCount")}: {publish.data.article_count} ·{" "}
                      {t("corpus.passageCount")}: {publish.data.passage_count}
                      {publish.data.index !== null
                        ? ` · ${publish.data.index.index_version}`
                        : ""}
                    </span>
                  ) : (
                    <span className="text-2xs text-ink-muted">{t("corpus.notPublished")}</span>
                  )}
                </div>
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title={t("corpus.runTitle")} description={t("corpus.runHint")} />
          <CardBody className="space-y-4">
            <div className="flex flex-wrap items-end gap-2">
              <div className="min-w-0 flex-1">
                <Field label={t("corpus.runId")} htmlFor="run-lookup">
                  <TextInput
                    id="run-lookup"
                    value={runLookup}
                    onChange={(event) => setRunLookup(event.target.value)}
                    placeholder={t("corpus.runIdPlaceholder")}
                    className="font-mono text-2xs"
                    autoComplete="off"
                  />
                </Field>
              </div>
              <Button
                onClick={loadRun}
                disabled={runLookup.trim() === ""}
                disabledReason={
                  runLookup.trim() === "" ? t("corpus.loadRunDisabled") : undefined
                }
              >
                {t("corpus.load")}
              </Button>
              {runId !== "" && (
                <Button onClick={() => void runQuery.refetch()} loading={runQuery.isFetching}>
                  {t("corpus.refresh")}
                </Button>
              )}
            </div>

            <div>
              <h3 className="font-heading text-2xs font-bold uppercase tracking-[0.06em] text-ink-muted">
                {t("corpus.history")}
              </h3>
              {history.length === 0 ? (
                <p className="mt-2 text-sm text-ink-muted">{t("corpus.noHistory")}</p>
              ) : (
                <ul className="mt-2 divide-y divide-line border-y border-line">
                  {history.map((entry) => (
                    <li key={entry.runId}>
                      <button
                        type="button"
                        onClick={() => {
                          setRunId(entry.runId);
                          setRunLookup(entry.runId);
                        }}
                        aria-current={entry.runId === runId ? "true" : undefined}
                        className={cn(
                          "flex w-full flex-wrap items-center justify-between gap-2 py-2 text-left transition-colors hover:bg-surface-muted",
                          entry.runId === runId && "bg-accent-quiet px-2",
                        )}
                      >
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-medium text-ink">
                            {entry.shardLabel === "" ? entry.runId : entry.shardLabel}
                          </span>
                          <span className="block font-mono text-2xs text-ink-muted">
                            {truncateMiddle(entry.runId)} ·{" "}
                            {formatDateTime(entry.createdAt, locale)}
                          </span>
                        </span>
                        <StatusPill
                          tone={
                            isRunStatus(entry.status) ? runStatusTone(entry.status) : "neutral"
                          }
                        >
                          {isRunStatus(entry.status)
                            ? enumLabel("ingestionStatus", entry.status, locale)
                            : entry.status}
                        </StatusPill>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {runId === "" ? (
              <EmptyState title={t("corpus.noRun")} />
            ) : runQuery.isLoading ? (
              <LoadingBlock rows={3} />
            ) : runQuery.error !== null && runQuery.error !== undefined ? (
              <ErrorState error={runQuery.error} onRetry={() => void runQuery.refetch()} />
            ) : run !== undefined ? (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-heading text-lg font-semibold text-ink">
                      {run.shard_label}
                    </p>
                    <p className="font-mono text-2xs text-ink-muted">{run.run_id}</p>
                  </div>
                  <StatusPill tone={runStatusTone(run.status)}>
                    {enumLabel("ingestionStatus", run.status, locale)}
                  </StatusPill>
                </div>
                {run.status === "failed" &&
                  run.failure_reason !== null &&
                  run.failure_reason !== undefined && (
                    <div className="border border-danger/30 bg-danger-quiet px-3 py-2 text-sm text-danger">
                      <span className="font-medium">{t("corpus.failureReason")}: </span>
                      {run.failure_reason}
                    </div>
                  )}
                <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <Stat label={t("corpus.attempted")} value={run.attempted} />
                  <Stat label={t("corpus.accepted")} value={run.accepted} />
                  <Stat label={t("corpus.quarantined")} value={run.quarantined} />
                  <Stat label={t("corpus.failed")} value={run.failed} />
                </dl>
                <section>
                  <h3 className="font-heading text-2xs font-bold uppercase tracking-[0.06em] text-ink-muted">
                    {t("corpus.outcomes")}
                  </h3>
                  {run.outcomes.length === 0 ? (
                    <p className="mt-2 text-sm text-ink-muted">{t("corpus.noOutcomes")}</p>
                  ) : (
                    <ul className="mt-2 divide-y divide-line border-y border-line">
                      {run.outcomes.map((item, index) => (
                        <li key={`${item.path}-${index}`} className="space-y-1.5 py-2.5">
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <p className="min-w-0 break-all font-mono text-2xs text-ink">
                              {item.path}
                            </p>
                            <StatusPill tone={outcomeTone(item.outcome)}>
                              {enumLabel("ingestionOutcome", item.outcome, locale)}
                            </StatusPill>
                          </div>
                          {item.reason !== null && item.reason !== undefined && (
                            <ExpandableText text={item.reason} collapsedLines={3} />
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              </div>
            ) : null}
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title={t("corpus.snapshotTitle")}
            description={t("corpus.snapshotHint")}
          />
          <CardBody className="space-y-4">
            <Field
              label={t("corpus.snapshotLabel")}
              htmlFor="snapshot-label"
              hint={t("corpus.snapshotLabelHint")}
            >
              <TextInput
                id="snapshot-label"
                value={snapshotLabel}
                onChange={(event) => setSnapshotLabel(event.target.value)}
                placeholder={t("corpus.snapshotPlaceholder")}
                autoComplete="off"
              />
            </Field>
            <Field
              label={t("corpus.documentIds")}
              htmlFor="snapshot-documents"
              hint={t("corpus.documentIdsHint")}
            >
              <TextArea
                id="snapshot-documents"
                rows={3}
                value={documentIdsText}
                onChange={(event) => setDocumentIdsText(event.target.value)}
                placeholder={"doc_...\ndoc_..."}
                className="font-mono text-2xs"
              />
            </Field>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="primary"
                onClick={pinHandler}
                disabled={!canPin}
                disabledReason={!canPin ? t("corpus.pinDisabled") : undefined}
                loading={pin.isPending}
              >
                {pin.isPending ? t("corpus.pinning") : t("corpus.pin")}
              </Button>
              <Link href="/settings" className="text-2xs">
                {t("corpus.seedHint")}
              </Link>
            </div>
            {!canPin && <p className="text-2xs text-ink-muted">{t("corpus.pinDisabled")}</p>}
            {pin.error !== null && pin.error !== undefined && <ErrorState error={pin.error} />}

            <div className="flex flex-wrap items-end gap-2 border-t border-line pt-4">
              <div className="min-w-0 flex-1">
                <Field label={t("corpus.snapshotLookup")} htmlFor="snapshot-lookup">
                  <TextInput
                    id="snapshot-lookup"
                    value={snapshotLookup}
                    onChange={(event) => setSnapshotLookup(event.target.value)}
                    placeholder={t("corpus.snapshotIdPlaceholder")}
                    className="font-mono text-2xs"
                    autoComplete="off"
                  />
                </Field>
              </div>
              <Button
                onClick={loadSnapshot}
                disabled={snapshotLookup.trim() === ""}
                disabledReason={
                  snapshotLookup.trim() === ""
                    ? t("corpus.loadSnapshotDisabled")
                    : undefined
                }
              >
                {t("corpus.load")}
              </Button>
            </div>

            <div>
              <h3 className="font-heading text-2xs font-bold uppercase tracking-[0.06em] text-ink-muted">
                {t("corpus.snapshotHistory")}
              </h3>
              {snapshots.length === 0 ? (
                <p className="mt-2 text-sm text-ink-muted">{t("corpus.noSnapshots")}</p>
              ) : (
                <ul className="mt-2 divide-y divide-line border-y border-line">
                  {snapshots.map((entry) => (
                    <li key={entry.snapshotId}>
                      <button
                        type="button"
                        onClick={() => {
                          setSnapshotId(entry.snapshotId);
                          setSnapshotLookup(entry.snapshotId);
                        }}
                        aria-current={entry.snapshotId === snapshotId ? "true" : undefined}
                        className={cn(
                          "flex w-full flex-wrap items-center justify-between gap-2 py-2 text-left transition-colors hover:bg-surface-muted",
                          entry.snapshotId === snapshotId && "bg-accent-quiet px-2",
                        )}
                      >
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-medium text-ink">
                            {entry.label === "" ? entry.snapshotId : entry.label}
                          </span>
                          <span className="block font-mono text-2xs text-ink-muted">
                            {truncateMiddle(entry.snapshotId)} ·{" "}
                            {formatDateTime(entry.pinnedAt, locale)}
                          </span>
                        </span>
                        <span className="text-2xs text-ink-muted">
                          {t("corpus.documents")}: {entry.documentCount} ·{" "}
                          {t("corpus.passages")}: {entry.passageCount}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {snapshotId === "" ? null : snapshotQuery.isLoading ? (
              <LoadingBlock rows={3} />
            ) : snapshotQuery.error !== null && snapshotQuery.error !== undefined ? (
              <ErrorState error={snapshotQuery.error} onRetry={() => void snapshotQuery.refetch()} />
            ) : snapshot !== undefined ? (
              <dl className="grid grid-cols-1 gap-3 border-t border-line pt-4 text-sm sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <dt className="text-2xs text-ink-muted">{t("corpus.snapshotId")}</dt>
                  <dd className="flex flex-wrap items-center gap-2">
                    <span className="break-all font-mono text-2xs">{snapshot.snapshot_id}</span>
                    <CopyButton value={snapshot.snapshot_id} size="sm" />
                  </dd>
                </div>
                <div>
                  <dt className="text-2xs text-ink-muted">{t("corpus.snapshotLabel")}</dt>
                  <dd>{snapshot.label}</dd>
                </div>
                <div>
                  <dt className="text-2xs text-ink-muted">{t("corpus.pinnedAt")}</dt>
                  <dd>{formatDateTime(snapshot.pinned_at, locale)}</dd>
                </div>
                <div>
                  <dt className="text-2xs text-ink-muted">{t("corpus.manifestHash")}</dt>
                  <dd className="flex flex-wrap items-center gap-2">
                    <span className="break-all font-mono text-2xs">
                      {truncateMiddle(snapshot.manifest_hash, 18, 8)}
                    </span>
                    <CopyButton value={snapshot.manifest_hash} size="sm" />
                  </dd>
                </div>
                <div>
                  <dt className="text-2xs text-ink-muted">{t("corpus.documents")}</dt>
                  <dd>{snapshot.document_ids.length}</dd>
                </div>
                <div>
                  <dt className="text-2xs text-ink-muted">{t("corpus.indexVersion")}</dt>
                  <dd className="font-mono text-2xs">{snapshot.index.index_version}</dd>
                </div>
                <div>
                  <dt className="text-2xs text-ink-muted">{t("corpus.passages")}</dt>
                  <dd>{snapshot.index.passage_count}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-2xs text-ink-muted">{t("corpus.embeddingModel")}</dt>
                  <dd className="break-all font-mono text-2xs">{snapshot.index.embedding_model}</dd>
                </div>
              </dl>
            ) : null}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
