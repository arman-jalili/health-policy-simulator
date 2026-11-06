"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useSettings, useToast } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Field, TextArea, TextInput } from "@/components/ui/field";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/ui/states";
import { StatusPill } from "@/components/ui/status-pill";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { ScenarioComparisonChart } from "@/features/consensus/components/scenario-comparison-chart";
import { SupportThresholdChart } from "@/features/consensus/components/support-threshold-chart";
import {
  useAssessImpact,
  useComparison,
  useComposePackage,
  useConsensus,
  useDeriveConsensus,
  useOpenConflicts,
  usePackages,
} from "@/features/consensus/hooks";
import type { AssessImpactResponse } from "@/features/consensus/contracts";
import { StanceBadge } from "@/features/run/components/stance-badge";
import { useRun, useRunDriver } from "@/features/run/hooks";
import { useStakeholderNames } from "@/features/stakeholders/names";
import { enumLabel } from "@/lib/i18n";
import { formatEur, formatPercent, truncateMiddle } from "@/lib/format";

export default function ConsensusPage() {
  const { t, locale } = useSettings();
  const { push } = useToast();
  const params = useParams<{ runId: string }>();
  const runId = typeof params.runId === "string" ? params.runId : "";
  const run = useRun(runId);
  const driver = useRunDriver(runId);
  const names = useStakeholderNames();
  const consensus = useConsensus(runId);
  const openConflicts = useOpenConflicts(runId);
  const packages = usePackages(runId);
  const derive = useDeriveConsensus(runId);
  const compose = useComposePackage(runId);
  const [componentIds, setComponentIds] = useState("");
  const [rejectedIds, setRejectedIds] = useState("");
  const [selectedPackage, setSelectedPackage] = useState("");
  const [baselineLabel, setBaselineLabel] = useState("Status quo");
  const [baselineReference, setBaselineReference] = useState("");
  const [years, setYears] = useState("5");
  const [horizonDescription, setHorizonDescription] = useState("");
  const [assumption, setAssumption] = useState("");
  const assess = useAssessImpact(selectedPackage);
  const comparison = useComparison(selectedPackage);
  const [assessment, setAssessment] = useState<AssessImpactResponse | null>(null);

  useEffect(() => {
    if (selectedPackage === "" && packages.data !== undefined) {
      setSelectedPackage(packages.data.packages[0]?.package_id ?? "");
    }
  }, [packages.data, selectedPackage]);

  const records = consensus.data?.records ?? [];
  const closed = run.data?.closed ?? false;
  const parseIds = (value: string): string[] =>
    value
      .split(",")
      .map((item) => item.trim())
      .filter((item) => item !== "");

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title={t("consensus.records")}
          actions={
            <Button
              size="sm"
              loading={derive.isPending}
              disabledReason={closed ? undefined : t("error.runNotClosed")}
              onClick={() =>
                derive.mutate([], { onSuccess: () => push(t("consensus.deriveSuccess"), "ok") })
              }
            >
              {t("consensus.derive")}
            </Button>
          }
        />
        <CardBody className="space-y-3">
          {consensus.isLoading ? (
            <LoadingBlock rows={4} />
          ) : consensus.error !== null && consensus.error !== undefined ? (
            <ErrorState error={consensus.error} onRetry={() => void consensus.refetch()} />
          ) : records.length === 0 ? (
            <EmptyState
              title={closed ? t("consensus.noStances") : t("consensus.none")}
              hint={closed ? undefined : t("error.runNotClosed")}
            />
          ) : (
            <>
              <SupportThresholdChart records={records} />
              {driver.automated && (
                <p className="text-2xs text-ink-muted">{t("consensus.automatedFootnote")}</p>
              )}
              <div className="space-y-3">
                {records.map((record) => (
                  <div
                    key={record.consensus_id}
                    className={
                      record.outcome === "veto_blocked"
                        ? "rounded-md border border-veto/40 bg-veto-quiet px-3 py-2"
                        : "rounded-md border border-line px-3 py-2"
                    }
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="text-sm font-semibold">{record.topic}</h3>
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusPill
                          tone={
                            record.outcome === "consensus"
                              ? "ok"
                              : record.outcome === "partial"
                                ? "warn"
                                : record.outcome === "veto_blocked"
                                  ? "veto"
                                  : "danger"
                          }
                        >
                          {driver.automated && record.support >= 1
                            ? t("consensus.automatedSupport")
                            : enumLabel("consensusOutcome", record.outcome, locale)}
                        </StatusPill>
                        <span className="text-2xs tabular text-ink-muted">
                          {formatPercent(record.support, locale, 0)} /{" "}
                          {formatPercent(record.threshold, locale, 0)}
                        </span>
                      </div>
                    </div>
                    <p className="mt-1 text-2xs text-ink-muted">
                      {enumLabel("proposalClass", record.proposal_class, locale)}
                    </p>
                    {record.outcome === "veto_blocked" && (
                      <p className="mt-1 text-sm text-veto">
                        {t("consensus.vetoBlockedBy", {
                          support: formatPercent(record.support, locale, 0),
                          class: enumLabel("proposalClass", record.proposal_class, locale),
                          blockers: record.blockers
                            .map((id) => names.get(id) ?? id)
                            .join(", "),
                        })}
                      </p>
                    )}
                    <p className="mt-1 text-2xs text-ink-muted">
                      {t("consensus.supporters")}:{" "}
                      {record.supporters.length === 0
                        ? "—"
                        : record.supporters.map((id) => names.get(id) ?? id).join(", ")}
                    </p>
                    {record.blockers.length > 0 && (
                      <p className="mt-1 text-2xs text-ink-muted">
                        {t("consensus.blockers")}:{" "}
                        {record.blockers.map((id) => names.get(id) ?? id).join(", ")}
                      </p>
                    )}
                    {record.reason !== null && (
                      <p className="mt-1 text-2xs text-ink-muted">
                        {t("consensus.reason")}: {record.reason}
                      </p>
                    )}
                    {record.minorities.length > 0 && (
                      <div className="mt-2">
                        <p className="text-2xs font-medium uppercase tracking-wide text-ink-muted">
                          {t("consensus.minorities")}
                        </p>
                        <ul className="mt-1 space-y-1">
                          {record.minorities.map((minority, index) => (
                            <li key={index} className="text-sm">
                              <span className="font-medium">
                                {minority.holders.map((id) => names.get(id) ?? id).join(", ")}
                              </span>
                              {minority.objections.length > 0 && (
                                <ul className="ml-4 list-inside list-disc text-ink-muted">
                                  {minority.objections.map((objection) => (
                                    <li key={objection}>{objection}</li>
                                  ))}
                                </ul>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
          {derive.error !== null && derive.error !== undefined && <ErrorState error={derive.error} />}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title={t("consensus.openConflicts")} />
        <CardBody>
          {openConflicts.isLoading ? (
            <LoadingBlock rows={3} />
          ) : openConflicts.error !== null && openConflicts.error !== undefined ? (
            <ErrorState error={openConflicts.error} onRetry={() => void openConflicts.refetch()} />
          ) : (openConflicts.data?.conflicts ?? []).length === 0 ? (
            <EmptyState title={t("consensus.noOpenConflicts")} />
          ) : (
            <div className="overflow-x-auto">
              <Table caption={t("consensus.openConflicts")}>
                <THead>
                  <TR>
                    <TH>{t("common.topic")}</TH>
                    <TH>{t("common.stakeholder")}</TH>
                    <TH>{t("common.stance")}</TH>
                    <TH className="text-right">{t("console.materiality")}</TH>
                    <TH>{t("common.status")}</TH>
                  </TR>
                </THead>
                <TBody>
                  {openConflicts.data?.conflicts.flatMap((conflict) =>
                    conflict.positions.map((position) => (
                      <TR key={`${conflict.topic}-${position.stakeholder}`}>
                        <TD>{conflict.topic}</TD>
                        <TD>{names.get(position.stakeholder) ?? position.stakeholder}</TD>
                        <TD>
                          <StanceBadge stance={position.stance} />
                        </TD>
                        <TD className="text-right tabular">
                          {formatPercent(position.weight, locale, 0)}
                        </TD>
                        <TD>
                          {position.recorded ? t("health.ready") : t("console.statusSilent")}
                        </TD>
                      </TR>
                    )),
                  )}
                </TBody>
              </Table>
            </div>
          )}
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title={t("consensus.packages")} />
          <CardBody className="space-y-3">
            <form
              className="space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                compose.mutate(
                  {
                    component_ids: parseIds(componentIds),
                    rejected_ids: parseIds(rejectedIds),
                  },
                  { onSuccess: () => push(t("consensus.composeSuccess"), "ok") },
                );
              }}
            >
              <Field label={t("consensus.componentIds")} htmlFor="component-ids">
                <TextInput
                  id="component-ids"
                  value={componentIds}
                  onChange={(event) => setComponentIds(event.target.value)}
                  placeholder="cmp_…, cmp_…"
                />
              </Field>
              <Field label={t("consensus.rejectedIds")} htmlFor="rejected-ids">
                <TextInput
                  id="rejected-ids"
                  value={rejectedIds}
                  onChange={(event) => setRejectedIds(event.target.value)}
                  placeholder="cmp_…"
                />
              </Field>
              <p className="text-2xs text-ink-muted">{t("consensus.composeHint")}</p>
              {compose.error !== null && compose.error !== undefined && (
                <ErrorState error={compose.error} />
              )}
              <Button type="submit" size="sm" loading={compose.isPending}>
                {t("consensus.compose")}
              </Button>
            </form>

            {packages.isLoading ? (
              <LoadingBlock rows={2} />
            ) : packages.error !== null && packages.error !== undefined ? (
              <ErrorState error={packages.error} />
            ) : (packages.data?.packages ?? []).length === 0 ? (
              <EmptyState title={t("consensus.noPackages")} />
            ) : (
              <div className="overflow-x-auto">
                <Table caption={t("consensus.packages")}>
                  <THead>
                    <TR>
                      <TH>{t("evidence.pack")}</TH>
                      <TH>{t("common.status")}</TH>
                      <TH className="text-right">{t("consensus.componentIds")}</TH>
                      <TH className="text-right">{t("consensus.rejectedIds")}</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {packages.data?.packages.map((pack) => (
                      <TR key={pack.package_id}>
                        <TD>
                          <button
                            type="button"
                            className="font-mono text-2xs underline"
                            onClick={() => setSelectedPackage(pack.package_id)}
                          >
                            {truncateMiddle(pack.package_id)}
                          </button>
                        </TD>
                        <TD>{enumLabel("packageState", pack.state, locale)}</TD>
                        <TD className="text-right tabular">{pack.component_count}</TD>
                        <TD className="text-right tabular">{pack.rejected_count}</TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title={
              selectedPackage === ""
                ? t("consensus.scenario")
                : t("consensus.assessFor", { package: truncateMiddle(selectedPackage) })
            }
          />
          <CardBody className="space-y-3">
            <Field label={t("consensus.baseline")} htmlFor="baseline-label">
              <TextInput
                id="baseline-label"
                value={baselineLabel}
                onChange={(event) => setBaselineLabel(event.target.value)}
              />
            </Field>
            <Field label={t("consensus.reference")} htmlFor="baseline-reference">
              <TextInput
                id="baseline-reference"
                value={baselineReference}
                onChange={(event) => setBaselineReference(event.target.value)}
              />
            </Field>
            <Field label={t("consensus.horizon")} htmlFor="horizon-years">
              <TextInput
                id="horizon-years"
                type="number"
                min={1}
                max={50}
                value={years}
                onChange={(event) => setYears(event.target.value)}
              />
            </Field>
            <Field label={t("consensus.horizonDescription")} htmlFor="horizon-description">
              <TextInput
                id="horizon-description"
                value={horizonDescription}
                onChange={(event) => setHorizonDescription(event.target.value)}
              />
            </Field>
            <Field label={t("consensus.assumption")} htmlFor="assumption" hint={t("consensus.assumptionHint")}>
              <TextArea
                id="assumption"
                rows={2}
                value={assumption}
                onChange={(event) => setAssumption(event.target.value)}
              />
            </Field>
            {assess.error !== null && assess.error !== undefined && <ErrorState error={assess.error} />}
            <Button
              size="sm"
              variant="primary"
              loading={assess.isPending}
              disabledReason={
                selectedPackage === ""
                  ? t("consensus.selectPackage")
                  : baselineLabel.trim() === ""
                    ? t("consensus.baseline")
                    : undefined
              }
              onClick={() =>
                assess.mutate(
                  {
                    baseline: { label: baselineLabel, reference: baselineReference },
                    horizon: {
                      years: Number(years) >= 1 ? Number(years) : 5,
                      description: horizonDescription,
                    },
                    assumptions:
                      assumption.trim() === ""
                        ? []
                        : [
                            {
                              statement: assumption,
                              basis: { kind: "assumed", inputs: [] },
                            },
                          ],
                  },
                  {
                    onSuccess: (result) => {
                      setAssessment(result);
                      push(t("consensus.assessSuccess"), "ok");
                    },
                  },
                )
              }
            >
              {t("consensus.assess")}
            </Button>
            {assessment !== null && (
              <div className="space-y-2 rounded-xs border border-line bg-surface-muted px-3 py-2">
                <p className="text-sm font-semibold">{t("consensus.scenarioResults")}</p>
                <p className="font-mono text-2xs text-ink-muted">
                  {assessment.scenario_id} · {assessment.package_id}
                </p>
                <Table caption={t("consensus.scenarioResults")}>
                  <THead>
                    <TR>
                      <TH>{t("claims.measure")}</TH>
                      <TH className="text-right">{t("claims.value")}</TH>
                      <TH>{t("consensus.basis")}</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {assessment.figures.map((figure) => (
                      <TR key={figure.field}>
                        <TD>{figure.field}</TD>
                        <TD className="text-right tabular">{figure.value}</TD>
                        <TD>{enumLabel("uncertainty", figure.label, locale)}</TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
                {assessment.feasibility !== null && assessment.feasibility !== undefined && (
                  <p className="text-2xs text-ink-muted">
                    {t("consensus.feasibility")}:{" "}
                    {enumLabel("feasibility", assessment.feasibility.political, locale)} /{" "}
                    {enumLabel("feasibility", assessment.feasibility.legal, locale)} /{" "}
                    {enumLabel("feasibility", assessment.feasibility.administrative, locale)}
                  </p>
                )}
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader title={t("consensus.comparison")} />
        <CardBody>
          {selectedPackage === "" ? (
            <EmptyState title={t("consensus.selectPackage")} />
          ) : comparison.isLoading ? (
            <LoadingBlock rows={3} />
          ) : comparison.error !== null && comparison.error !== undefined ? (
            <ErrorState error={comparison.error} onRetry={() => void comparison.refetch()} />
          ) : (comparison.data?.entries ?? []).length === 0 ? (
            <EmptyState title={t("consensus.noComparison")} />
          ) : (
            <ScenarioComparisonChart entries={comparison.data?.entries ?? []} />
          )}
          {comparison.data !== undefined && (
            <p className="mt-2 text-2xs text-ink-muted">
              {t("consensus.cost")}:{" "}
              {comparison.data.entries
                .map((entry) => formatEur(entry.cost, locale, { compact: true }))
                .join(" · ")}
            </p>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
