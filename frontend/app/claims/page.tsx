"use client";

import { useState } from "react";

import { useSettings, useToast } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Field, Select, TextArea, TextInput } from "@/components/ui/field";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/ui/states";
import { PageHeader } from "@/components/ui/page-header";
import { StatusPill } from "@/components/ui/status-pill";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import {
  useClaim,
  useContradictions,
  useCreateReferenceFigure,
  useFlagClaim,
  useReferenceFigures,
  useReviewClaim,
  useVerifyClaim,
} from "@/features/claims/hooks";
import { useAuthorityRules } from "@/features/evidence/hooks";
import { enumLabel } from "@/lib/i18n";
import { formatDate, formatDecimal, truncateMiddle } from "@/lib/format";

const CLAIM_TYPES = ["quantitative", "legal", "causal", "qualitative"] as const;
const VERDICTS = ["verified", "contradicted", "unsupported", "ambiguous"] as const;
const TIERS = [
  "official_statistics",
  "legislation",
  "scientific_study",
  "institutional_statement",
  "press_report",
  "other",
] as const;

export default function ClaimsPage() {
  const { t, locale } = useSettings();
  const { push } = useToast();
  const verify = useVerifyClaim();
  const [claimId, setClaimId] = useState("");
  const claim = useClaim(claimId);
  const flag = useFlagClaim(claimId);
  const review = useReviewClaim(claimId);
  const contradictions = useContradictions();
  const figures = useReferenceFigures();
  const createFigure = useCreateReferenceFigure();
  const rules = useAuthorityRules();

  const [text, setText] = useState("");
  const [claimType, setClaimType] = useState("");
  const [measureName, setMeasureName] = useState("");
  const [unit, setUnit] = useState("");
  const [period, setPeriod] = useState("");
  const [geography, setGeography] = useState("");
  const [assertedValue, setAssertedValue] = useState("");
  const [reason, setReason] = useState("");
  const [reviewVerdict, setReviewVerdict] = useState("verified");
  const [reviewBasis, setReviewBasis] = useState("");
  const [figureMeasure, setFigureMeasure] = useState("");
  const [figureValue, setFigureValue] = useState("");
  const [figureTier, setFigureTier] = useState<string>("official_statistics");
  const [figureAsOf, setFigureAsOf] = useState("");
  const [figureSource, setFigureSource] = useState("");

  const tierOrder = new Map<string, number>();
  for (const rule of rules.data ?? []) {
    for (const tier of rule.ordered_tiers) {
      if (!tierOrder.has(tier)) tierOrder.set(tier, tierOrder.size);
    }
  }
  const sortedFigures = [...(figures.data?.items ?? [])].sort(
    (a, b) => (tierOrder.get(a.tier) ?? 99) - (tierOrder.get(b.tier) ?? 99),
  );
  const current = claim.data ?? verify.data;

  const toneFor = (verdict: string): "ok" | "danger" | "warn" | "info" | "neutral" => {
    switch (verdict) {
      case "verified":
        return "ok";
      case "contradicted":
        return "danger";
      case "unsupported":
        return "warn";
      case "ambiguous":
        return "info";
      default:
        return "neutral";
    }
  };

  return (
    <div className="space-y-4">
      <PageHeader title={t("claims.title")} subtitle={t("claims.subtitle")} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title={t("claims.verify")} description={t("claims.verifyHint")} />
          <CardBody className="space-y-3">
            <Field label={t("claims.text")} htmlFor="verify-text">
              <TextArea
                id="verify-text"
                rows={3}
                value={text}
                onChange={(event) => setText(event.target.value)}
              />
            </Field>
            <Field label={t("claims.claimType")} htmlFor="verify-type">
              <Select id="verify-type" value={claimType} onChange={(event) => setClaimType(event.target.value)}>
                <option value="">{t("common.unknown")}</option>
                {CLAIM_TYPES.map((value) => (
                  <option key={value} value={value}>
                    {enumLabel("claimType", value, locale)}
                  </option>
                ))}
              </Select>
            </Field>
            <fieldset className="space-y-2">
              <legend className="text-sm font-medium">{t("claims.measure")}</legend>
              <p className="text-2xs text-ink-muted">{t("claims.measureHint")}</p>
              <div className="grid gap-2 sm:grid-cols-2">
                <Field label={t("claims.measure")} htmlFor="verify-measure">
                  <TextInput
                    id="verify-measure"
                    value={measureName}
                    onChange={(event) => setMeasureName(event.target.value)}
                    placeholder="waiting_time_days"
                  />
                </Field>
                <Field label={t("claims.unit")} htmlFor="verify-unit">
                  <TextInput id="verify-unit" value={unit} onChange={(event) => setUnit(event.target.value)} />
                </Field>
                <Field label={t("claims.period")} htmlFor="verify-period">
                  <TextInput
                    id="verify-period"
                    value={period}
                    onChange={(event) => setPeriod(event.target.value)}
                  />
                </Field>
                <Field label={t("claims.geography")} htmlFor="verify-geography">
                  <TextInput
                    id="verify-geography"
                    value={geography}
                    onChange={(event) => setGeography(event.target.value)}
                  />
                </Field>
              </div>
            </fieldset>
            <Field label={t("claims.value")} htmlFor="verify-value">
              <TextInput
                id="verify-value"
                inputMode="decimal"
                value={assertedValue}
                onChange={(event) => setAssertedValue(event.target.value)}
              />
            </Field>
            {verify.error !== null && verify.error !== undefined && <ErrorState error={verify.error} />}
            <Button
              variant="primary"
              loading={verify.isPending}
              disabledReason={text.trim() === "" ? t("claims.text") : undefined}
              onClick={() =>
                verify.mutate(
                  {
                    text,
                    ...(claimType === ""
                      ? {}
                      : { claim_type: claimType }),
                    ...(measureName.trim() === ""
                      ? {}
                      : {
                          measure: {
                            measure: measureName,
                            unit,
                            period,
                            geography,
                          },
                        }),
                    ...(assertedValue.trim() === "" ? {} : { asserted_value: assertedValue }),
                  },
                  {
                    onSuccess: (verdict) => {
                      setClaimId(verdict.claim_id);
                      push(t("claims.verifySuccess"), "ok");
                    },
                  },
                )
              }
            >
              {t("claims.verify")}
            </Button>
            {current !== undefined && (
              <div className="space-y-2 rounded-xs border border-line bg-surface-muted px-3 py-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold">{t("claims.verdict")}:</span>
                  <StatusPill tone={toneFor(current.verdict)}>
                    {enumLabel("claimVerdict", current.verdict, locale)}
                  </StatusPill>
                  <span className="font-mono text-2xs text-ink-muted">{current.claim_id}</span>
                </div>
                <p className="text-2xs text-ink-muted">
                  {t("claims.path")}: {current.path} · {t("claims.claimType")}:{" "}
                  {enumLabel("claimType", current.claim_type, locale)}
                </p>
                {current.delta !== null && current.delta !== undefined && (
                  <p className="text-sm">
                    {t("claims.delta")}: {formatDecimal(current.delta, locale)}
                  </p>
                )}
                <p className="text-2xs text-ink-muted">
                  {t("claims.sources")}: {current.sources.join(", ") || "—"}
                </p>
                {claim.data !== undefined && claim.data.review_verdict !== null && (
                  <p className="text-2xs text-ink-muted">
                    {t("claims.review")}: {claim.data.review_verdict} · {claim.data.review_basis}
                  </p>
                )}
              </div>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title={t("claims.review")} />
          <CardBody className="space-y-3">
            <Field label={t("claims.claimId")} htmlFor="claim-id">
              <TextInput
                id="claim-id"
                value={claimId}
                onChange={(event) => setClaimId(event.target.value)}
                placeholder="clm_…"
                className="font-mono"
              />
            </Field>
            {claim.error !== null && claim.error !== undefined && <ErrorState error={claim.error} />}
            <form
              className="space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                flag.mutate(reason, {
                  onSuccess: () => {
                    push(t("claims.flagSuccess"), "ok");
                    setReason("");
                  },
                });
              }}
            >
              <Field label={t("claims.flagReason")} htmlFor="flag-reason">
                <TextInput
                  id="flag-reason"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                />
              </Field>
              {flag.error !== null && flag.error !== undefined && <ErrorState error={flag.error} />}
              <Button
                type="submit"
                size="sm"
                loading={flag.isPending}
                disabledReason={
                  claimId === "" ? t("claims.claimId") : reason.trim() === "" ? t("claims.flagReason") : undefined
                }
              >
                {t("claims.flag")}
              </Button>
            </form>
            <form
              className="space-y-2 border-t border-line pt-2"
              onSubmit={(event) => {
                event.preventDefault();
                review.mutate(
                  { verdict: reviewVerdict, basis: reviewBasis },
                  {
                    onSuccess: () => {
                      push(t("claims.reviewSuccess"), "ok");
                      setReviewBasis("");
                    },
                  },
                );
              }}
            >
              <Field label={t("claims.reviewVerdict")} htmlFor="review-verdict">
                <Select
                  id="review-verdict"
                  value={reviewVerdict}
                  onChange={(event) => setReviewVerdict(event.target.value)}
                >
                  {VERDICTS.map((value) => (
                    <option key={value} value={value}>
                      {enumLabel("claimVerdict", value, locale)}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label={t("claims.reviewBasis")} htmlFor="review-basis">
                <TextArea
                  id="review-basis"
                  rows={2}
                  value={reviewBasis}
                  onChange={(event) => setReviewBasis(event.target.value)}
                />
              </Field>
              {review.error !== null && review.error !== undefined && <ErrorState error={review.error} />}
              <Button
                type="submit"
                size="sm"
                loading={review.isPending}
                disabledReason={
                  claimId === "" || reviewBasis.trim() === "" ? t("claims.reviewBasis") : undefined
                }
              >
                {t("claims.review")}
              </Button>
            </form>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader title={t("claims.referenceFigures")} />
        <CardBody className="space-y-3">
          {figures.isLoading ? (
            <LoadingBlock rows={3} />
          ) : figures.error !== null && figures.error !== undefined ? (
            <ErrorState error={figures.error} onRetry={() => void figures.refetch()} />
          ) : sortedFigures.length === 0 ? (
            <EmptyState title={t("claims.noFigures")} />
          ) : (
            <div
              className="overflow-x-auto"
              role="region"
              aria-label={t("claims.referenceFigures")}
              tabIndex={0}
            >
              <Table caption={t("claims.referenceFigures")}>
                <THead>
                  <TR>
                    <TH>{t("common.id")}</TH>
                    <TH>{t("claims.measure")}</TH>
                    <TH className="text-right">{t("claims.value")}</TH>
                    <TH>{t("claims.unit")}</TH>
                    <TH>{t("claims.period")}</TH>
                    <TH>{t("claims.geography")}</TH>
                    <TH>{t("claims.tier")}</TH>
                    <TH>{t("common.status")}</TH>
                  </TR>
                </THead>
                <TBody>
                  {sortedFigures.map((figure) => (
                    <TR key={figure.figure_id}>
                      <TD className="font-mono text-2xs">{truncateMiddle(figure.figure_id)}</TD>
                      <TD>{figure.measure}</TD>
                      <TD className="text-right tabular">{figure.value}</TD>
                      <TD>{figure.unit}</TD>
                      <TD>{figure.period}</TD>
                      <TD>{figure.geography}</TD>
                      <TD>{enumLabel("authorityTier", figure.tier, locale)}</TD>
                      <TD>{formatDate(figure.as_of, locale)}</TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </div>
          )}

          <form
            className="space-y-2 border-t border-line pt-3"
            onSubmit={(event) => {
              event.preventDefault();
              createFigure.mutate(
                {
                  measure: {
                    measure: figureMeasure,
                    unit,
                    period,
                    geography,
                  },
                  value: figureValue,
                  tier: figureTier,
                  as_of: figureAsOf === "" ? new Date().toISOString().slice(0, 10) : figureAsOf,
                  source_id: figureSource,
                },
                {
                  onSuccess: () => {
                    push(t("claims.registerSuccess"), "ok");
                    setFigureMeasure("");
                    setFigureValue("");
                    setFigureSource("");
                  },
                },
              );
            }}
          >
            <h3 className="text-sm font-semibold">{t("claims.createFigure")}</h3>
            <div className="grid gap-2 sm:grid-cols-3">
              <Field label={t("claims.measure")} htmlFor="figure-measure">
                <TextInput
                  id="figure-measure"
                  value={figureMeasure}
                  onChange={(event) => setFigureMeasure(event.target.value)}
                />
              </Field>
              <Field label={t("claims.value")} htmlFor="figure-value">
                <TextInput
                  id="figure-value"
                  value={figureValue}
                  onChange={(event) => setFigureValue(event.target.value)}
                />
              </Field>
              <Field label={t("claims.tier")} htmlFor="figure-tier">
                <Select
                  id="figure-tier"
                  value={figureTier}
                  onChange={(event) => setFigureTier(event.target.value)}
                >
                  {TIERS.map((tier) => (
                    <option key={tier} value={tier}>
                      {enumLabel("authorityTier", tier, locale)}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label={t("claims.unit")} htmlFor="figure-unit">
                <TextInput id="figure-unit" value={unit} onChange={(event) => setUnit(event.target.value)} />
              </Field>
              <Field label={t("claims.period")} htmlFor="figure-period">
                <TextInput id="figure-period" value={period} onChange={(event) => setPeriod(event.target.value)} />
              </Field>
              <Field label={t("claims.geography")} htmlFor="figure-geography">
                <TextInput
                  id="figure-geography"
                  value={geography}
                  onChange={(event) => setGeography(event.target.value)}
                />
              </Field>
              <Field label={t("claims.sourceId")} htmlFor="figure-source">
                <TextInput
                  id="figure-source"
                  value={figureSource}
                  onChange={(event) => setFigureSource(event.target.value)}
                />
              </Field>
              <Field label={t("stakeholders.asOf")} htmlFor="figure-date">
                <TextInput
                  id="figure-date"
                  type="date"
                  value={figureAsOf}
                  onChange={(event) => setFigureAsOf(event.target.value)}
                />
              </Field>
            </div>
            {createFigure.error !== null && createFigure.error !== undefined && (
              <ErrorState error={createFigure.error} />
            )}
            <Button
              type="submit"
              size="sm"
              loading={createFigure.isPending}
              disabledReason={
                figureMeasure.trim() === "" || figureValue.trim() === "" || figureSource.trim() === ""
                  ? t("claims.createFigure")
                  : undefined
              }
            >
              {t("claims.registerFigure")}
            </Button>
          </form>
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title={t("claims.contradictions")} />
          <CardBody>
            {contradictions.isLoading ? (
              <LoadingBlock rows={2} />
            ) : contradictions.error !== null && contradictions.error !== undefined ? (
              <ErrorState error={contradictions.error} />
            ) : (contradictions.data?.items ?? []).length === 0 ? (
              <EmptyState title={t("claims.noContradictions")} />
            ) : (
              <Table caption={t("claims.contradictions")}>
                <THead>
                  <TR>
                    <TH>{t("claims.measure")}</TH>
                    <TH>{t("claims.claimId")}</TH>
                    <TH className="text-right">{t("claims.delta")}</TH>
                  </TR>
                </THead>
                <TBody>
                  {contradictions.data?.items.map((item) => (
                    <TR key={item.finding_id}>
                      <TD>{item.measure}</TD>
                      <TD className="font-mono text-2xs">
                        {truncateMiddle(item.claim_id_a)} / {truncateMiddle(item.claim_id_b)}
                      </TD>
                      <TD className="text-right tabular">{formatDecimal(item.delta, locale)}</TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title={t("claims.authorityOrder")} />
          <CardBody>
            {rules.isLoading ? (
              <LoadingBlock rows={3} />
            ) : rules.error !== null && rules.error !== undefined ? (
              <ErrorState error={rules.error} />
            ) : (
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
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
