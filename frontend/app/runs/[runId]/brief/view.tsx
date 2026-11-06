"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Icon } from "@/components/icons";
import { useSettings, useToast } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Field, TextArea } from "@/components/ui/field";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/ui/states";
import { StatusPill } from "@/components/ui/status-pill";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import {
  useBrief,
  useBriefVersions,
  useCitations,
  useCreateBriefVersion,
  usePublishBrief,
} from "@/features/brief/hooks";
import type { BriefResponse, CitationList } from "@/features/brief/contracts";
import { ApiError } from "@/lib/http";
import { formatDate, formatDateTime, truncateMiddle } from "@/lib/format";
import { enumLabel } from "@/lib/i18n";

export default function BriefPage() {
  const { t, locale } = useSettings();
  const { push } = useToast();
  const params = useParams<{ runId: string }>();
  const runId = typeof params.runId === "string" ? params.runId : "";
  const versions = useBriefVersions(runId);
  const [selectedBriefId, setSelectedBriefId] = useState("");
  const [reason, setReason] = useState("");
  const brief = useBrief(selectedBriefId);
  const citations = useCitations(selectedBriefId);
  const publish = usePublishBrief(runId);
  const createVersion = useCreateBriefVersion(selectedBriefId, runId);

  useEffect(() => {
    const list = versions.data?.versions ?? [];
    if (list.length === 0) return;
    const exists = list.some((item) => item.brief_id === selectedBriefId);
    if (!exists) {
      const latest = list[list.length - 1];
      if (latest !== undefined) setSelectedBriefId(latest.brief_id);
    }
  }, [versions.data, selectedBriefId]);

  const markdown = brief.data === undefined ? "" : buildMarkdown(brief.data, citations.data, t, locale);
  const blockedError = publish.error instanceof ApiError ? publish.error : null;

  const copyMarkdown = async (): Promise<void> => {
    try {
      await navigator.clipboard.writeText(markdown);
      push(t("brief.exportMarkdownSuccess"), "ok");
    } catch {
      push(t("common.error"), "danger");
    }
  };

  const downloadJson = (): void => {
    if (brief.data === undefined) return;
    const blob = new Blob([JSON.stringify(brief.data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${brief.data.brief_id}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title={t("brief.title")}
          actions={
            <div className="flex flex-wrap gap-2" data-print-hide>
              <Button
                size="sm"
                variant="primary"
                loading={publish.isPending}
                onClick={() =>
                  publish.mutate(undefined, {
                    onSuccess: (created) => {
                      setSelectedBriefId(created.brief_id);
                      push(t("brief.publishSuccess"), "ok");
                    },
                  })
                }
              >
                {t("brief.publish")}
              </Button>
              <Button
                size="sm"
                icon={<Icon name="print" size={15} />}
                onClick={() => window.print()}
                disabledReason={brief.data === undefined ? t("brief.none") : undefined}
              >
                {t("brief.exportPrint")}
              </Button>
              <Button
                size="sm"
                icon={<Icon name="copy" size={15} />}
                onClick={() => void copyMarkdown()}
                disabledReason={brief.data === undefined ? t("brief.none") : undefined}
              >
                {t("brief.exportMarkdown")}
              </Button>
              <Button
                size="sm"
                icon={<Icon name="download" size={15} />}
                onClick={downloadJson}
                disabledReason={brief.data === undefined ? t("brief.none") : undefined}
              >
                {t("brief.exportJson")}
              </Button>
            </div>
          }
        />
        <CardBody className="space-y-3">
          {versions.isLoading ? (
            <LoadingBlock rows={2} />
          ) : versions.error !== null && versions.error !== undefined ? (
            <ErrorState error={versions.error} onRetry={() => void versions.refetch()} />
          ) : (versions.data?.versions ?? []).length === 0 ? (
            <EmptyState title={t("brief.none")} action={undefined} />
          ) : (
            <div className="flex flex-wrap items-center gap-2" data-print-hide>
              <label htmlFor="brief-version" className="text-sm font-medium">
                {t("brief.versions")}
              </label>
              <select
                id="brief-version"
                value={selectedBriefId}
                onChange={(event) => setSelectedBriefId(event.target.value)}
                className="h-9 rounded-md border border-line-strong bg-surface px-3 text-sm"
              >
                {(versions.data?.versions ?? []).map((version) => (
                  <option key={version.brief_id} value={version.brief_id}>
                    {t("brief.version", { version: version.version })} · {version.status} ·{" "}
                    {formatDate(version.generated_at, locale)}
                  </option>
                ))}
              </select>
            </div>
          )}

          {blockedError !== null && (
            <div className="rounded-md border border-danger/30 bg-danger-quiet px-3 py-2">
              <p className="text-sm font-semibold text-danger">{t("brief.blocked")}</p>
              <p className="mt-1 text-sm">
                {t("brief.publishBlockedCode", { code: blockedError.code })}
              </p>
              <p className="mt-1 text-sm text-ink-muted">{blockedError.message}</p>
              {blockedError.details.length > 0 && (
                <ul className="mt-2 list-inside list-disc text-2xs text-ink-muted">
                  {blockedError.details.map((detail, index) => (
                    <li key={`${detail.field ?? "detail"}-${index}`}>
                      {detail.field !== null && detail.field !== undefined && (
                        <span className="font-mono">{detail.field}: </span>
                      )}
                      {detail.message}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {publish.error !== null && publish.error !== undefined && blockedError === null && (
            <ErrorState error={publish.error} />
          )}
        </CardBody>
      </Card>

      {brief.isLoading ? (
        <LoadingBlock rows={8} />
      ) : brief.error !== null && brief.error !== undefined ? (
        <ErrorState error={brief.error} onRetry={() => void brief.refetch()} />
      ) : brief.data === undefined ? (
        <EmptyState title={t("brief.none")} />
      ) : (
        <>
          <Card>
            <CardHeader title={t("brief.title")} />
            <CardBody>
              <article className="brief-document mx-auto max-w-[72ch] space-y-5 text-ink">
                <header className="border-b border-line pb-3">
                  <h1 className="text-2xl font-semibold">{t("brief.title")}</h1>
                  <p className="mt-1 text-sm text-ink-muted">
                    {t("brief.version", { version: brief.data.version.number })} ·{" "}
                    {brief.data.status} · {formatDateTime(brief.data.version.generated_at, locale)}
                  </p>
                  <p className="mt-1 font-mono text-2xs text-ink-muted">
                    {brief.data.brief_id} · {brief.data.version.snapshot_ref}
                  </p>
                </header>

                {[...brief.data.sections]
                  .sort((a, b) => a.ordinal - b.ordinal)
                  .map((section) => (
                    <section key={`${section.kind}-${section.ordinal}`} aria-labelledby={`section-${section.ordinal}`}>
                      <h2 id={`section-${section.ordinal}`} className="text-lg font-semibold">
                        {section.ordinal}. {enumLabel("briefSection", section.kind, locale)}
                      </h2>
                      <ol className="mt-2 space-y-2">
                        {section.statements.map((statement, index) => (
                          <li key={`${section.kind}-${index}`} className="text-base leading-relaxed">
                            {statement.text}
                            {statement.citations.map((citation) => {
                              const number = citationNumber(citations.data, citation.passage_id);
                              return (
                                <sup key={citation.passage_id} className="ml-0.5">
                                  <a
                                    href={`#cit-${number}`}
                                    className={citation.resolved ? "" : "text-danger"}
                                    aria-label={`${t("brief.citations")} ${number}`}
                                  >
                                    [{number}]
                                  </a>
                                </sup>
                              );
                            })}
                            <span className="ml-2 align-middle">
                              <StatusPill
                                tone={
                                  statement.status === "evidenced"
                                    ? "ok"
                                    : statement.status === "unsupported"
                                      ? "danger"
                                      : "neutral"
                                }
                              >
                                {statement.status === "evidenced"
                                  ? t("brief.evidencedStatement")
                                  : statement.status === "unsupported"
                                    ? t("brief.unsupportedStatement")
                                    : t("brief.narrativeStatement")}
                              </StatusPill>
                            </span>
                          </li>
                        ))}
                      </ol>
                    </section>
                  ))}

                {brief.data.outcomes.length > 0 && (
                  <section>
                    <h2 className="text-lg font-semibold">{t("brief.outcomes")}</h2>
                    <Table caption={t("brief.outcomes")}>
                      <THead>
                        <TR>
                          <TH>{t("common.topic")}</TH>
                          <TH>{t("common.status")}</TH>
                          <TH>{t("consensus.blockers")}</TH>
                          <TH>{t("consensus.reason")}</TH>
                        </TR>
                      </THead>
                      <TBody>
                        {brief.data.outcomes.map((outcome) => (
                          <TR key={outcome.topic}>
                            <TD>{outcome.topic}</TD>
                            <TD>{outcome.kind}</TD>
                            <TD>{outcome.blocking_stakeholders.join(", ") || "—"}</TD>
                            <TD>{outcome.reason ?? "—"}</TD>
                          </TR>
                        ))}
                      </TBody>
                    </Table>
                  </section>
                )}

                {brief.data.rejected_proposals.length > 0 && (
                  <section className="rounded-md border border-warn/40 bg-warn-quiet px-3 py-2">
                    <h2 className="text-lg font-semibold">{t("brief.rejected")}</h2>
                    <ul className="mt-2 space-y-2">
                      {brief.data.rejected_proposals.map((proposal) => (
                        <li key={proposal.measure}>
                          <p className="text-base font-medium">{proposal.measure}</p>
                          <p className="text-sm text-ink-muted">
                            {t("consensus.blockers")}: {proposal.blocking_stakeholders.join(", ") || "—"}
                          </p>
                          {proposal.reasons.length > 0 && (
                            <ul className="ml-4 list-inside list-disc text-sm text-ink-muted">
                              {proposal.reasons.map((item) => (
                                <li key={item}>{item}</li>
                              ))}
                            </ul>
                          )}
                        </li>
                      ))}
                    </ul>
                  </section>
                )}

                <section className="border-t border-line pt-3">
                  <h2 className="text-base font-semibold">{t("brief.disclaimer")}</h2>
                  <p className="mt-1 text-sm">{brief.data.disclaimer.text}</p>
                  <p className="mt-1 font-mono text-2xs text-ink-muted">
                    {t("brief.modelReference")}: {brief.data.disclaimer.model_reference} ·{" "}
                    {t("brief.promptVersion")}: {brief.data.disclaimer.prompt_version}
                  </p>
                </section>
              </article>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title={t("brief.citations")} description={`${brief.data.citation_count}`} />
            <CardBody>
              {citations.isLoading ? (
                <LoadingBlock rows={3} />
              ) : citations.error !== null && citations.error !== undefined ? (
                <ErrorState error={citations.error} onRetry={() => void citations.refetch()} />
              ) : (citations.data?.items ?? []).length === 0 ? (
                <EmptyState title={t("brief.noCitations")} />
              ) : (
                <ol className="space-y-2">
                  {(citations.data?.items ?? []).map((citation, index) => (
                    <li
                      key={citation.passage_id}
                      id={`cit-${index + 1}`}
                      className="rounded-md border border-line px-3 py-2"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-2xs font-semibold">[{index + 1}]</span>
                        <StatusPill tone={citation.resolved ? "ok" : "danger"}>
                          {citation.resolved ? t("brief.citationResolved") : t("brief.citationUnresolved")}
                        </StatusPill>
                      </div>
                      {citation.quote !== null && (
                        <p className="mt-1 text-sm">
                          {t("brief.citationQuote")}: „{citation.quote}“
                        </p>
                      )}
                      <p className="mt-1 text-2xs text-ink-muted">
                        {citation.outlet ?? "—"} · {formatDate(citation.published_on, locale)} ·{" "}
                        {citation.medium ?? "—"} ·{" "}
                        {citation.page_from === null
                          ? "—"
                          : t("evidence.page", {
                              from: citation.page_from,
                              to: citation.page_to ?? citation.page_from,
                            })}
                      </p>
                      <p className="mt-0.5 break-all font-mono text-2xs text-ink-subtle">
                        {citation.passage_id}
                        {citation.source_uri !== null && (
                          <>
                            {" · "}
                            <a href={citation.source_uri} target="_blank" rel="noreferrer">
                              {truncateMiddle(citation.source_uri, 40, 10)}
                            </a>
                          </>
                        )}
                      </p>
                    </li>
                  ))}
                </ol>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title={t("brief.newVersion")} />
            <CardBody className="space-y-3">
              <Field label={t("brief.versionReason")} htmlFor="version-reason">
                <TextArea
                  id="version-reason"
                  rows={2}
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                />
              </Field>
              {createVersion.error !== null && createVersion.error !== undefined && (
                <ErrorState error={createVersion.error} />
              )}
              <Button
                loading={createVersion.isPending}
                disabledReason={reason.trim() === "" ? t("brief.versionReason") : undefined}
                onClick={() =>
                  createVersion.mutate(reason, {
                    onSuccess: () => {
                      push(t("brief.versionSuccess"), "ok");
                      setReason("");
                    },
                  })
                }
              >
                {t("brief.newVersion")}
              </Button>
            </CardBody>
          </Card>
        </>
      )}
    </div>
  );
}

function citationNumber(citations: CitationList | undefined, passageId: string): number {
  const index = citations?.items.findIndex((item) => item.passage_id === passageId) ?? -1;
  return index === -1 ? 0 : index + 1;
}

function buildMarkdown(
  brief: BriefResponse,
  citations: CitationList | undefined,
  t: (key: "brief.title" | "brief.citations" | "brief.outcomes" | "brief.rejected" | "brief.disclaimer") => string,
  locale: "de-AT" | "en",
): string {
  const lines: string[] = [];
  lines.push(`# ${t("brief.title")} — v${brief.version.number}`);
  lines.push("");
  lines.push(`> ${brief.disclaimer.text}`);
  lines.push("");
  for (const section of [...brief.sections].sort((a, b) => a.ordinal - b.ordinal)) {
    lines.push(`## ${section.ordinal}. ${enumLabel("briefSection", section.kind, locale)}`);
    for (const statement of section.statements) {
      const refs = statement.citations
        .map((citation) => `[${citationNumber(citations, citation.passage_id)}]`)
        .join(" ");
      lines.push(`- ${statement.text}${refs === "" ? "" : ` ${refs}`}`);
    }
    lines.push("");
  }
  if (brief.outcomes.length > 0) {
    lines.push(`## ${t("brief.outcomes")}`);
    for (const outcome of brief.outcomes) {
      lines.push(`- ${outcome.topic}: ${outcome.kind}`);
    }
    lines.push("");
  }
  if (brief.rejected_proposals.length > 0) {
    lines.push(`## ${t("brief.rejected")}`);
    for (const proposal of brief.rejected_proposals) {
      lines.push(`- ${proposal.measure} — ${proposal.reasons.join("; ")}`);
    }
    lines.push("");
  }
  lines.push(`## ${t("brief.citations")}`);
  for (const [index, citation] of (citations?.items ?? []).entries()) {
    lines.push(
      `${index + 1}. ${citation.outlet ?? "—"} · ${citation.published_on ?? "—"} · ${citation.passage_id}`,
    );
  }
  return lines.join("\n");
}
