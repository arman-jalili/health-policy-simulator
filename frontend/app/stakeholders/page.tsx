"use client";

import { useState } from "react";

import { Icon } from "@/components/icons";
import { useSettings, useToast } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Checkbox, Field, Select, TextArea, TextInput } from "@/components/ui/field";
import { Drawer } from "@/components/ui/drawer";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/ui/states";
import { PageHeader } from "@/components/ui/page-header";
import { StatusPill } from "@/components/ui/status-pill";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { useCitePower, useHistory, useRecordHistory, useStakeholders } from "@/features/stakeholders/hooks";
import type { StakeholderSummary } from "@/features/stakeholders/contracts";
import { formatDate, truncateMiddle } from "@/lib/format";
import { enumLabel } from "@/lib/i18n";

export default function StakeholdersPage() {
  const { t, locale } = useSettings();
  const stakeholders = useStakeholders();
  const [selected, setSelected] = useState<StakeholderSummary | null>(null);

  return (
    <div className="space-y-4">
      <PageHeader title={t("stakeholders.title")} subtitle={t("stakeholders.subtitle")} />

      <p className="rounded-md border border-line bg-surface px-3 py-2 text-2xs text-ink-muted">
        {t("stakeholders.noProfileDetail")}
      </p>

      {stakeholders.isLoading ? (
        <LoadingBlock rows={6} />
      ) : stakeholders.error !== null && stakeholders.error !== undefined ? (
        <ErrorState error={stakeholders.error} onRetry={() => void stakeholders.refetch()} />
      ) : (stakeholders.data?.items ?? []).length === 0 ? (
        <EmptyState title={t("console.noStakeholders")} />
      ) : (
        <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {stakeholders.data?.items.map((item) => (
            <li key={item.stakeholder_id}>
              <Card>
                <CardHeader
                  title={item.identity.short_name}
                  description={item.identity.name}
                  actions={<StatusPill>{item.profile_version}</StatusPill>}
                />
                <CardBody className="space-y-2">
                  <p className="text-2xs text-ink-muted">
                    {enumLabel("institutionCategory", item.identity.category, locale)} ·{" "}
                    <span className="font-mono">{item.identity.code}</span>
                  </p>
                  <div className="flex gap-4 text-2xs text-ink-muted">
                    <span>
                      {t("stakeholders.interests")}: {item.interest_count}
                    </span>
                    <span>
                      {t("stakeholders.constraints")}: {item.constraint_count}
                    </span>
                  </div>
                  <Button
                    size="sm"
                    icon={<Icon name="chevron-right" size={14} />}
                    onClick={() => setSelected(item)}
                  >
                    {t("stakeholders.openHistory")}
                  </Button>
                </CardBody>
              </Card>
            </li>
          ))}
        </ul>
      )}

      <StakeholderDrawer stakeholder={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

function StakeholderDrawer({
  stakeholder,
  onClose,
}: {
  readonly stakeholder: StakeholderSummary | null;
  readonly onClose: () => void;
}) {
  const { t, locale } = useSettings();
  const { push } = useToast();
  const stakeholderId = stakeholder?.stakeholder_id ?? "";
  const [usableOnly, setUsableOnly] = useState(false);
  const history = useHistory(stakeholderId, usableOnly);
  const record = useRecordHistory(stakeholderId);
  const cite = useCitePower(stakeholderId);
  const [stance, setStance] = useState("support");
  const [attribution, setAttribution] = useState("explicit");
  const [statedOn, setStatedOn] = useState("");
  const [passageId, setPassageId] = useState("");
  const [powerType, setPowerType] = useState("veto");
  const [proposalClass, setProposalClass] = useState("");
  const [citation, setCitation] = useState("");
  const [kind, setKind] = useState("statutory");
  const [asOf, setAsOf] = useState("");

  return (
    <Drawer open={stakeholder !== null} onClose={onClose} title={stakeholder?.identity.short_name ?? ""}>
      {stakeholder !== null && (
        <div className="space-y-5">
          <section className="space-y-1">
            <p className="text-sm">{stakeholder.identity.name}</p>
            <p className="text-2xs text-ink-muted">
              {enumLabel("institutionCategory", stakeholder.identity.category, locale)} ·{" "}
              {t("stakeholders.profileVersion")} {stakeholder.profile_version}
            </p>
            <p className="text-2xs text-ink-muted">{t("stakeholders.noProfileDetail")}</p>
          </section>

          <section>
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold">{t("stakeholders.history")}</h3>
              <Checkbox
                label={t("stakeholders.usableOnly")}
                checked={usableOnly}
                onChange={(event) => setUsableOnly(event.target.checked)}
              />
            </div>
            <p className="mt-1 text-2xs text-ink-muted">{t("stakeholders.historyHint")}</p>
            {history.isLoading ? (
              <div className="mt-2">
                <LoadingBlock rows={2} />
              </div>
            ) : history.error !== null && history.error !== undefined ? (
              <div className="mt-2">
                <ErrorState error={history.error} />
              </div>
            ) : (history.data?.positions ?? []).length === 0 ? (
              <p className="mt-2 text-sm text-ink-muted">{t("stakeholders.noHistory")}</p>
            ) : (
              <div className="mt-2 overflow-x-auto">
                <Table caption={t("stakeholders.history")}>
                  <THead>
                    <TR>
                      <TH>{t("common.stance")}</TH>
                      <TH>{t("stakeholders.attribution")}</TH>
                      <TH>{t("stakeholders.statedOn")}</TH>
                      <TH>{t("stakeholders.passageId")}</TH>
                      <TH>{t("common.status")}</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {history.data?.positions.map((position) => (
                      <TR key={position.position_id}>
                        <TD>{enumLabel("stance", position.stance, locale)}</TD>
                        <TD>{enumLabel("attribution", position.attribution, locale)}</TD>
                        <TD>{formatDate(position.stated_on, locale)}</TD>
                        <TD className="font-mono text-2xs">{truncateMiddle(position.passage_id)}</TD>
                        <TD>
                          {position.usable ? (
                            <StatusPill tone="ok">{t("health.ready")}</StatusPill>
                          ) : (
                            <StatusPill tone="warn">{t("stakeholders.notUsable")}</StatusPill>
                          )}
                        </TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              </div>
            )}
          </section>

          <form
            className="space-y-2 border-t border-line pt-3"
            onSubmit={(event) => {
              event.preventDefault();
              record.mutate(
                {
                  stance,
                  attribution: attribution as "explicit" | "reported" | "mention",
                  stated_on: statedOn === "" ? new Date().toISOString().slice(0, 10) : statedOn,
                  passage_id: passageId,
                },
                {
                  onSuccess: () => {
                    push(t("stakeholders.recordSuccess"), "ok");
                    setPassageId("");
                  },
                },
              );
            }}
          >
            <h3 className="text-sm font-semibold">{t("stakeholders.addHistory")}</h3>
            <div className="grid gap-2 sm:grid-cols-2">
              <Field label={t("common.stance")} htmlFor="history-stance">
                <Select id="history-stance" value={stance} onChange={(event) => setStance(event.target.value)}>
                  {["support", "oppose", "qualify", "conditional_accept", "abstain"].map((value) => (
                    <option key={value} value={value}>
                      {enumLabel("stance", value, locale)}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label={t("stakeholders.attribution")} htmlFor="history-attribution">
                <Select
                  id="history-attribution"
                  value={attribution}
                  onChange={(event) => setAttribution(event.target.value)}
                >
                  {["explicit", "reported", "mention"].map((value) => (
                    <option key={value} value={value}>
                      {enumLabel("attribution", value, locale)}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <Field label={t("stakeholders.statedOn")} htmlFor="history-date">
              <TextInput
                id="history-date"
                type="date"
                value={statedOn}
                onChange={(event) => setStatedOn(event.target.value)}
              />
            </Field>
            <Field label={t("stakeholders.passageId")} htmlFor="history-passage">
              <TextInput
                id="history-passage"
                value={passageId}
                onChange={(event) => setPassageId(event.target.value)}
                placeholder="psg_…"
                className="font-mono"
              />
            </Field>
            {record.error !== null && record.error !== undefined && <ErrorState error={record.error} />}
            <Button
              type="submit"
              size="sm"
              loading={record.isPending}
              disabledReason={passageId.trim() === "" ? t("stakeholders.passageId") : undefined}
            >
              {t("common.save")}
            </Button>
          </form>

          <form
            className="space-y-2 border-t border-line pt-3"
            onSubmit={(event) => {
              event.preventDefault();
              cite.mutate(
                {
                  power_type: powerType,
                  ...(proposalClass === ""
                    ? {}
                    : {
                        proposal_class: proposalClass as
                          | "statutory_benefit_change"
                          | "budget_frame"
                          | "service_catalogue"
                          | "fee_schedule"
                          | "hospital_plan"
                          | "other",
                      }),
                  citation,
                  kind: kind as
                    | "statutory"
                    | "contractual"
                    | "regulatory"
                    | "budgetary"
                    | "unspecified",
                  as_of: asOf === "" ? new Date().toISOString().slice(0, 10) : asOf,
                },
                { onSuccess: () => push(t("stakeholders.powerSuccess"), "ok") },
              );
            }}
          >
            <h3 className="text-sm font-semibold">{t("stakeholders.citePower")}</h3>
            <div className="grid gap-2 sm:grid-cols-2">
              <Field label={t("stakeholders.powerType")} htmlFor="power-type">
                <TextInput
                  id="power-type"
                  value={powerType}
                  onChange={(event) => setPowerType(event.target.value)}
                />
              </Field>
              <Field label={t("consensus.packages")} htmlFor="power-class">
                <Select
                  id="power-class"
                  value={proposalClass}
                  onChange={(event) => setProposalClass(event.target.value)}
                >
                  <option value="">{t("common.none")}</option>
                  {[
                    "statutory_benefit_change",
                    "budget_frame",
                    "service_catalogue",
                    "fee_schedule",
                    "hospital_plan",
                    "other",
                  ].map((value) => (
                    <option key={value} value={value}>
                      {enumLabel("proposalClass", value, locale)}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <Field label={t("stakeholders.citation")} htmlFor="power-citation">
              <TextArea
                id="power-citation"
                rows={2}
                value={citation}
                onChange={(event) => setCitation(event.target.value)}
              />
            </Field>
            <div className="grid gap-2 sm:grid-cols-2">
              <Field label={t("stakeholders.powerType")} htmlFor="power-kind">
                <Select id="power-kind" value={kind} onChange={(event) => setKind(event.target.value)}>
                  {["statutory", "contractual", "regulatory", "budgetary", "unspecified"].map((value) => (
                    <option key={value} value={value}>
                      {enumLabel("powerSource", value, locale)}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label={t("stakeholders.asOf")} htmlFor="power-date">
                <TextInput
                  id="power-date"
                  type="date"
                  value={asOf}
                  onChange={(event) => setAsOf(event.target.value)}
                />
              </Field>
            </div>
            {cite.error !== null && cite.error !== undefined && <ErrorState error={cite.error} />}
            {cite.data !== undefined && (
              <div className="rounded-xs border border-line bg-surface-muted px-2 py-1.5 text-sm">
                <StatusPill tone={cite.data.accepted ? "ok" : "warn"}>
                  {cite.data.accepted ? t("stakeholders.powerAccepted") : t("stakeholders.powerRejected")}
                </StatusPill>
                {cite.data.reason !== null && (
                  <p className="mt-1 text-2xs text-ink-muted">{cite.data.reason}</p>
                )}
              </div>
            )}
            <Button
              type="submit"
              size="sm"
              loading={cite.isPending}
              disabledReason={
                citation.trim() === "" ? t("stakeholders.citation") : undefined
              }
            >
              {t("stakeholders.citePower")}
            </Button>
          </form>
        </div>
      )}
    </Drawer>
  );
}
