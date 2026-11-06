"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

import { useSettings } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Field, Select, TextArea, TextInput } from "@/components/ui/field";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/ui/states";
import { StatusPill } from "@/components/ui/status-pill";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import {
  useAllowlist,
  useCheckText,
  useDiscloseProvenance,
  useProvenance,
  useViolations,
} from "@/features/governance/hooks";
import { ApiError } from "@/lib/http";
import { formatDateTime } from "@/lib/format";
import { enumLabel } from "@/lib/i18n";

const VIOLATION_CLASSES = [
  "person_named",
  "personal_quotation",
  "institution_ambiguous",
  "unsupported_fact",
  "contradicted_figure",
] as const;

export default function GovernancePage() {
  const { t, locale } = useSettings();
  const params = useParams<{ runId: string }>();
  const runId = typeof params.runId === "string" ? params.runId : "";
  const [violationClass, setViolationClass] = useState("");
  const violations = useViolations({
    runId,
    ...(violationClass === "" ? {} : { violationClass }),
    limit: 50,
  });
  const allowlist = useAllowlist();
  const check = useCheckText();
  const [text, setText] = useState("");
  const [speakerKind, setSpeakerKind] = useState("institution");
  const [positionId, setPositionId] = useState("");
  const provenance = useProvenance(positionId.trim());
  const disclose = useDiscloseProvenance(positionId.trim());

  const provenanceMissing =
    provenance.error instanceof ApiError ? provenance.error.status === 404 : false;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title={t("governance.violations")}
          actions={
            <div>
              <label htmlFor="violation-class" className="sr-only">
                {t("governance.selectClass")}
              </label>
              <Select
                id="violation-class"
                value={violationClass}
                onChange={(event) => setViolationClass(event.target.value)}
                className="h-8"
              >
                <option value="">{t("governance.allClasses")}</option>
                {VIOLATION_CLASSES.map((value) => (
                  <option key={value} value={value}>
                    {enumLabel("violationClass", value, locale)}
                  </option>
                ))}
              </Select>
            </div>
          }
        />
        <CardBody>
          {violations.isLoading ? (
            <LoadingBlock rows={3} />
          ) : violations.error !== null && violations.error !== undefined ? (
            <ErrorState error={violations.error} onRetry={() => void violations.refetch()} />
          ) : (violations.data?.items ?? []).length === 0 ? (
            <EmptyState title={t("governance.noViolations")} />
          ) : (
            <div className="overflow-x-auto">
              <Table caption={t("governance.violations")}>
                <THead>
                  <TR>
                    <TH>{t("governance.violationClass")}</TH>
                    <TH>{t("governance.rule")}</TH>
                    <TH>{t("governance.offending")}</TH>
                    <TH>{t("governance.rewritten")}</TH>
                    <TH>{t("common.status")}</TH>
                  </TR>
                </THead>
                <TBody>
                  {violations.data?.items.map((violation) => (
                    <TR key={violation.violation_id}>
                      <TD>{enumLabel("violationClass", violation.violation_class, locale)}</TD>
                      <TD>
                        <StatusPill tone="warn">
                          {violation.rule_id} · {violation.rule_version}
                        </StatusPill>
                      </TD>
                      <TD>
                        <span className="rounded-xs bg-danger-quiet px-1 text-danger">
                          {violation.offending_span}
                        </span>
                      </TD>
                      <TD>
                        {violation.rewritten_span === null ? (
                          <span className="text-ink-muted">{t("governance.noViolationDetail")}</span>
                        ) : (
                          <span className="rounded-xs bg-ok-quiet px-1 text-ok">
                            {violation.rewritten_span}
                          </span>
                        )}
                      </TD>
                      <TD className="text-2xs text-ink-muted">
                        {formatDateTime(violation.detected_at, locale)}
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </div>
          )}
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader
            title={t("governance.check")}
            description={t("settings.guardrailsHint")}
          />
          <CardBody className="space-y-3">
            <Field label={t("governance.checkText")} htmlFor="guard-text">
              <TextArea
                id="guard-text"
                rows={4}
                value={text}
                onChange={(event) => setText(event.target.value)}
              />
            </Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label={t("governance.speakerKind")} htmlFor="guard-speaker">
                <Select
                  id="guard-speaker"
                  value={speakerKind}
                  onChange={(event) => setSpeakerKind(event.target.value)}
                >
                  {["institution", "person", "anonymous"].map((value) => (
                    <option key={value} value={value}>
                      {enumLabel("speakerKind", value, locale)}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label={t("governance.invocationId")} htmlFor="guard-invocation">
                <TextInput id="guard-invocation" value="inv_ui_governance_check" readOnly className="font-mono" />
              </Field>
            </div>
            {check.error !== null && check.error !== undefined && <ErrorState error={check.error} />}
            <Button
              variant="primary"
              loading={check.isPending}
              disabledReason={text.trim() === "" ? t("governance.checkText") : undefined}
              onClick={() =>
                check.mutate({
                  text,
                  speaker_kind: speakerKind as "institution" | "person" | "anonymous",
                  invocation_id: "inv_ui_governance_check",
                  cited_passage_ids: [],
                  reference_figure_ids: [],
                })
              }
            >
              {t("governance.check")}
            </Button>
            {check.data !== undefined && (
              <div className="space-y-2 rounded-xs border border-line bg-surface-muted px-3 py-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold">{t("governance.decision")}:</span>
                  <StatusPill
                    tone={
                      check.data.decision === "accept"
                        ? "ok"
                        : check.data.decision === "rewrite"
                          ? "warn"
                          : "danger"
                    }
                  >
                    {enumLabel("guardDecision", check.data.decision, locale)}
                  </StatusPill>
                  <span className="font-mono text-2xs text-ink-muted">{check.data.rule_version}</span>
                </div>
                {check.data.violations.length === 0 ? (
                  <p className="text-sm text-ink-muted">{t("governance.noViolationDetail")}</p>
                ) : (
                  <ul className="space-y-1">
                    {check.data.violations.map((violation) => (
                      <li key={violation.violation_id} className="text-sm">
                        <span className="font-mono text-2xs text-warn">{violation.rule_id}</span>{" "}
                        <span className="rounded-xs bg-danger-quiet px-1 text-danger">
                          {violation.offending_span}
                        </span>
                        {violation.rewritten_span !== null && (
                          <>
                            {" → "}
                            <span className="rounded-xs bg-ok-quiet px-1 text-ok">
                              {violation.rewritten_span}
                            </span>
                          </>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
                {check.data.rewritten_text !== null && (
                  <p className="text-sm">
                    {t("governance.rewritten")}: {check.data.rewritten_text}
                  </p>
                )}
              </div>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title={t("governance.provenance")} />
          <CardBody className="space-y-3">
            <Field label={t("governance.provenanceId")} htmlFor="provenance-position">
              <TextInput
                id="provenance-position"
                value={positionId}
                onChange={(event) => setPositionId(event.target.value)}
                placeholder="pos_…"
                className="font-mono"
              />
            </Field>
            {positionId.trim() === "" ? (
              <EmptyState title={t("governance.loadProvenance")} />
            ) : provenance.isLoading ? (
              <LoadingBlock rows={2} />
            ) : provenanceMissing ? (
              <div className="space-y-2">
                <p className="text-sm text-ink-muted">{t("governance.notDisclosed")}</p>
                <Button
                  size="sm"
                  loading={disclose.isPending}
                  onClick={() => disclose.mutate({})}
                >
                  {t("governance.disclose")}
                </Button>
                {disclose.error !== null && disclose.error !== undefined && (
                  <ErrorState error={disclose.error} />
                )}
              </div>
            ) : provenance.error !== null && provenance.error !== undefined ? (
              <ErrorState error={provenance.error} />
            ) : provenance.data !== undefined ? (
              <dl className="grid grid-cols-2 gap-2 text-2xs">
                <div>
                  <dt className="text-ink-muted">{t("positions.disclosedAt")}</dt>
                  <dd>{formatDateTime(provenance.data.disclosed_at, locale)}</dd>
                </div>
                <div>
                  <dt className="text-ink-muted">{t("governance.provenanceVersion")}</dt>
                  <dd>{provenance.data.version}</dd>
                </div>
                <div>
                  <dt className="text-ink-muted">{t("positions.model")}</dt>
                  <dd className="break-all font-mono">{provenance.data.model}</dd>
                </div>
                <div>
                  <dt className="text-ink-muted">{t("positions.promptVersion")}</dt>
                  <dd className="break-all font-mono">{provenance.data.prompt_version}</dd>
                </div>
                <div className="col-span-2">
                  <dt className="text-ink-muted">{t("positions.invocation")}</dt>
                  <dd className="break-all font-mono">{provenance.data.invocation_id}</dd>
                </div>
              </dl>
            ) : null}
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader
          title={t("governance.allowlist")}
          description={
            allowlist.data === undefined ? undefined : `${t("governance.allowlistVersion")}: ${allowlist.data.version}`
          }
        />
        <CardBody>
          {allowlist.isLoading ? (
            <LoadingBlock rows={4} />
          ) : allowlist.error !== null && allowlist.error !== undefined ? (
            <ErrorState error={allowlist.error} onRetry={() => void allowlist.refetch()} />
          ) : (allowlist.data?.institutions ?? []).length === 0 ? (
            <EmptyState title={t("common.empty")} />
          ) : (
            <div className="overflow-x-auto">
              <Table caption={t("governance.allowlist")}>
                <THead>
                  <TR>
                    <TH>{t("common.id")}</TH>
                    <TH>{t("stakeholders.title")}</TH>
                    <TH>{t("stakeholders.powerType")}</TH>
                    <TH>{t("governance.aliases")}</TH>
                  </TR>
                </THead>
                <TBody>
                  {allowlist.data?.institutions.map((institution) => (
                    <TR key={institution.code}>
                      <TD className="font-mono text-2xs">{institution.code}</TD>
                      <TD>
                        <p className="text-sm">{institution.canonical_name}</p>
                        <p className="text-2xs text-ink-muted">{institution.short_name}</p>
                      </TD>
                      <TD>{institution.category}</TD>
                      <TD className="text-2xs">{institution.aliases.join(", ") || "—"}</TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
