"use client";

import { useParams } from "next/navigation";
import { useMemo, useState } from "react";

import { useSettings, useToast } from "@/components/providers";
import { engineLabel } from "@/lib/engine";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Checkbox, Field, Select, TextArea, TextInput } from "@/components/ui/field";
import { Drawer } from "@/components/ui/drawer";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/ui/states";
import { StanceBadge } from "@/features/run/components/stance-badge";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { AlignmentMatrix } from "@/features/positions/components/alignment-matrix";
import { StanceMatrix } from "@/features/positions/components/stance-matrix";
import {
  deriveArguments,
  deriveCoalitions,
  derivePositions,
  uniqueTopics,
  type PositionView,
} from "@/features/positions/derive";
import { useFormCoalition, useRevisePosition, useRunDriver, useRunFeed } from "@/features/run/hooks";
import { useStakeholderNames } from "@/features/stakeholders/names";
import { useDiscloseProvenance, useProvenance } from "@/features/governance/hooks";
import { ApiError } from "@/lib/http";
import { enumLabel } from "@/lib/i18n";
import { truncateMiddle } from "@/lib/format";

export default function PositionsPage() {
  const { t, locale } = useSettings();
  const { push } = useToast();
  const params = useParams<{ runId: string }>();
  const runId = typeof params.runId === "string" ? params.runId : "";
  const feed = useRunFeed(runId);
  const driver = useRunDriver(runId);
  const names = useStakeholderNames();
  const positions = useMemo(() => derivePositions(feed.events), [feed.events]);
  const argumentsList = useMemo(() => deriveArguments(feed.events), [feed.events]);
  const coalitions = useMemo(() => deriveCoalitions(feed.events), [feed.events]);
  const topics = useMemo(() => uniqueTopics(positions), [positions]);
  const stakeholderIds = feed.state?.bound_stakeholder_ids ?? [];
  const [selected, setSelected] = useState<PositionView | null>(null);
  const formCoalition = useFormCoalition(runId);
  const [coalitionTopic, setCoalitionTopic] = useState("");
  const [coalitionMembers, setCoalitionMembers] = useState<readonly string[]>([]);
  const [coalitionSummary, setCoalitionSummary] = useState("");

  if (feed.isLoading) return <LoadingBlock rows={6} />;
  if (feed.error !== null && feed.error !== undefined && feed.state === null) {
    return <ErrorState error={feed.error} onRetry={feed.refetch} />;
  }

  return (
    <div className="space-y-4">
      <p className="text-2xs text-ink-muted">{t("positions.eventsOnly")}</p>

      {positions.length === 0 ? (
        <EmptyState title={t("positions.noPositions")} />
      ) : (
        <>
          {driver.automated && (
            <p className="text-2xs text-ink-muted">{t("positions.automatedFootnote")}</p>
          )}
          <Card>
            <CardBody>
              <StanceMatrix
                positions={positions}
                stakeholderIds={stakeholderIds}
                stakeholderNames={names}
                topics={topics}
              />
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <AlignmentMatrix
                positions={positions}
                stakeholderIds={stakeholderIds}
                stakeholderNames={names}
              />
            </CardBody>
          </Card>
          <Card>
            <CardHeader title={t("positions.title")} />
            <div className="overflow-x-auto">
              <Table caption={t("positions.title")}>
                <THead>
                  <TR>
                    <TH>{t("common.topic")}</TH>
                    <TH>{t("common.stakeholder")}</TH>
                    <TH>{t("common.stance")}</TH>
                    <TH className="text-right">{t("common.round")}</TH>
                    <TH>{t("positions.evidenceIds")}</TH>
                    <TH>{t("common.actions")}</TH>
                  </TR>
                </THead>
                <TBody>
                  {positions.map((position) => (
                    <TR key={`${position.stakeholderId}-${position.topic}`}>
                      <TD>{position.topic}</TD>
                      <TD>{names.get(position.stakeholderId) ?? position.stakeholderId}</TD>
                      <TD>
                        <StanceBadge stance={position.stance} />
                      </TD>
                      <TD className="text-right tabular">{position.round}</TD>
                      <TD className="font-mono text-2xs">
                        {position.evidenceIds.length === 0
                          ? "—"
                          : position.evidenceIds.map((id) => truncateMiddle(id, 8, 4)).join(", ")}
                      </TD>
                      <TD>
                        <Button size="sm" onClick={() => setSelected(position)}>
                          {t("common.inspect")}
                        </Button>
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </div>
          </Card>
        </>
      )}

      <Card>
        <CardHeader title={t("positions.arguments")} />
        <CardBody>
          {argumentsList.length === 0 ? (
            <EmptyState title={t("positions.noArguments")} hint={t("positions.argumentTextUnavailable")} />
          ) : (
            <div className="overflow-x-auto">
              <Table caption={t("positions.arguments")}>
                <THead>
                  <TR>
                    <TH>{t("common.stakeholder")}</TH>
                    <TH>{t("common.topic")}</TH>
                    <TH>{t("common.stance")}</TH>
                    <TH className="text-right">{t("common.round")}</TH>
                    <TH>{t("console.invocationId")}</TH>
                  </TR>
                </THead>
                <TBody>
                  {argumentsList.map((argument) => (
                    <TR key={argument.argumentId}>
                      <TD>{names.get(argument.stakeholderId) ?? argument.stakeholderId}</TD>
                      <TD>{argument.topic}</TD>
                      <TD>
                        <StanceBadge stance={argument.stance} />
                      </TD>
                      <TD className="text-right tabular">{argument.round}</TD>
                      <TD className="font-mono text-2xs">
                        {argument.invocationId === null ? "—" : truncateMiddle(argument.invocationId, 12, 4)}
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </div>
          )}
          <p className="mt-2 text-2xs text-ink-subtle">{t("positions.argumentTextUnavailable")}</p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title={t("positions.coalition")} />
        <CardBody className="space-y-3">
          <form
            className="space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              formCoalition.mutate(
                {
                  topic: coalitionTopic,
                  member_ids: [...coalitionMembers],
                  proposal: { summary: coalitionSummary, components: [] },
                },
                {
                  onSuccess: () => {
                    push(t("positions.coalitionSuccess"), "ok");
                    setCoalitionSummary("");
                  },
                },
              );
            }}
          >
            <Field label={t("common.topic")} htmlFor="coalition-topic">
              <TextInput
                id="coalition-topic"
                value={coalitionTopic}
                onChange={(event) => setCoalitionTopic(event.target.value)}
                list="coalition-topics"
              />
            </Field>
            <datalist id="coalition-topics">
              {topics.map((topic) => (
                <option key={topic} value={topic} />
              ))}
            </datalist>
            <Field label={t("positions.coalitionMembers")} htmlFor="coalition-members">
              <div id="coalition-members" className="grid gap-1 sm:grid-cols-2">
                {stakeholderIds.map((id) => (
                  <Checkbox
                    key={id}
                    label={names.get(id) ?? id}
                    checked={coalitionMembers.includes(id)}
                    onChange={() =>
                      setCoalitionMembers((current) =>
                        current.includes(id)
                          ? current.filter((item) => item !== id)
                          : [...current, id],
                      )
                    }
                  />
                ))}
              </div>
            </Field>
            <Field label={t("positions.coalitionProposal")} htmlFor="coalition-summary">
              <TextArea
                id="coalition-summary"
                rows={3}
                value={coalitionSummary}
                onChange={(event) => setCoalitionSummary(event.target.value)}
              />
            </Field>
            {formCoalition.error !== null && formCoalition.error !== undefined && (
              <ErrorState error={formCoalition.error} />
            )}
            <Button
              type="submit"
              variant="primary"
              loading={formCoalition.isPending}
              disabledReason={
                coalitionTopic.trim() === ""
                  ? t("common.topic")
                  : coalitionMembers.length === 0
                    ? t("new.selectAtLeastOne")
                    : coalitionSummary.trim() === ""
                      ? t("positions.coalitionProposal")
                      : undefined
              }
            >
              {t("positions.submitCoalition")}
            </Button>
          </form>

          <div>
            <h3 className="mb-2 text-sm font-semibold">{t("positions.coalitionList")}</h3>
            {coalitions.length === 0 ? (
              <p className="text-sm text-ink-muted">{t("common.empty")}</p>
            ) : (
              <ul className="space-y-2">
                {coalitions.map((coalition) => (
                  <li key={coalition.coalitionId} className="rounded-md border border-line px-3 py-2">
                    <p className="text-sm font-medium">{coalition.topic}</p>
                    <p className="mt-0.5 text-sm text-ink-muted">{coalition.proposalSummary}</p>
                    <p className="mt-1 text-2xs text-ink-muted">
                      {coalition.members.map((id) => names.get(id) ?? id).join(", ")}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </CardBody>
      </Card>

      <PositionInspector
        position={selected}
        onClose={() => setSelected(null)}
        runId={runId}
        names={names}
        locale={locale}
        onRevised={() => {
          push(t("positions.revisionSuccess"), "ok");
          setSelected(null);
        }}
      />
    </div>
  );
}

function PositionInspector({
  position,
  onClose,
  runId,
  names,
  locale,
  onRevised,
}: {
  readonly position: PositionView | null;
  readonly onClose: () => void;
  readonly runId: string;
  readonly names: ReadonlyMap<string, string>;
  readonly locale: "de-AT" | "en";
  readonly onRevised: () => void;
}) {
  const { t } = useSettings();
  const positionId = position?.positionId ?? "";
  const provenance = useProvenance(positionId);
  const disclose = useDiscloseProvenance(positionId);
  const revise = useRevisePosition(runId);
  const [stance, setStance] = useState("support");
  const [argumentIds, setArgumentIds] = useState("");
  const [packIds, setPackIds] = useState("");
  const [driver, setDriver] = useState("");

  const notDisclosed =
    provenance.error instanceof ApiError ? provenance.error.status === 404 : false;
  const parseIds = (value: string): string[] =>
    value
      .split(",")
      .map((item) => item.trim())
      .filter((item) => item !== "");

  return (
    <Drawer open={position !== null} onClose={onClose} title={t("positions.details")}>
      {position !== null && (
        <div className="space-y-4">
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <dt className="text-2xs text-ink-muted">{t("common.stakeholder")}</dt>
              <dd>{names.get(position.stakeholderId) ?? position.stakeholderId}</dd>
            </div>
            <div>
              <dt className="text-2xs text-ink-muted">{t("common.topic")}</dt>
              <dd>{position.topic}</dd>
            </div>
            <div>
              <dt className="text-2xs text-ink-muted">{t("positions.initialStance")}</dt>
              <dd>{enumLabel("stance", position.initialStance, locale)}</dd>
            </div>
            <div>
              <dt className="text-2xs text-ink-muted">{t("common.stance")}</dt>
              <dd>
                <StanceBadge stance={position.stance} />
              </dd>
            </div>
            <div className="col-span-2">
              <dt className="text-2xs text-ink-muted">{t("positions.positionId")}</dt>
              <dd className="break-all font-mono text-2xs">{position.positionId}</dd>
            </div>
          </dl>
          {position.revisionDriver !== null && (
            <p className="rounded-xs border border-line bg-surface-muted px-2 py-1.5 text-sm">
              {t("positions.driver")}: {position.revisionDriver}
            </p>
          )}
          <p className="rounded-xs border border-warn/30 bg-warn-quiet px-2 py-1.5 text-2xs text-ink-muted">
            {t("positions.proposalUnavailable")}
          </p>

          <section>
            <h3 className="mb-2 text-sm font-semibold">{t("positions.provenance")}</h3>
            {notDisclosed ? (
              <div className="space-y-2">
                <p className="text-sm text-ink-muted">{t("positions.provenanceMissing")}</p>
                <Button
                  size="sm"
                  loading={disclose.isPending}
                  onClick={() => disclose.mutate({})}
                >
                  {t("positions.disclose")}
                </Button>
                {disclose.error !== null && disclose.error !== undefined && (
                  <ErrorState error={disclose.error} />
                )}
              </div>
            ) : provenance.isLoading ? (
              <LoadingBlock rows={2} />
            ) : provenance.error !== null && provenance.error !== undefined ? (
              <ErrorState error={provenance.error} />
            ) : provenance.data !== undefined ? (
              <dl className="grid grid-cols-2 gap-2 text-2xs">
                <div>
                  <dt className="text-ink-muted">{t("positions.disclosedAt")}</dt>
                  <dd>{provenance.data.disclosed_at}</dd>
                </div>
                <div>
                  <dt className="text-ink-muted">{t("governance.provenanceVersion")}</dt>
                  <dd>{provenance.data.version}</dd>
                </div>
                <div>
                  <dt className="text-ink-muted">{t("positions.model")}</dt>
                  <dd>{engineLabel(provenance.data.model, locale)}</dd>
                </div>
                <div>
                  <dt className="text-ink-muted">{t("positions.promptVersion")}</dt>
                  <dd className="font-mono break-all">{provenance.data.prompt_version}</dd>
                </div>
                <div className="col-span-2">
                  <dt className="text-ink-muted">{t("positions.invocation")}</dt>
                  <dd className="font-mono break-all">{provenance.data.invocation_id}</dd>
                </div>
              </dl>
            ) : null}
          </section>

          <form
            className="space-y-3 border-t border-line pt-3"
            onSubmit={(event) => {
              event.preventDefault();
              revise.mutate(
                {
                  positionId: position.positionId,
                  body: {
                    stance: stance as "support" | "oppose" | "qualify" | "conditional_accept",
                    reason: {
                      argument_ids: parseIds(argumentIds),
                      pack_ids: parseIds(packIds),
                      driver,
                    },
                  },
                },
                { onSuccess: onRevised },
              );
            }}
          >
            <h3 className="text-sm font-semibold">{t("positions.revise")}</h3>
            <p className="text-2xs text-ink-muted">{t("positions.reviseHint")}</p>
            <Field label={t("common.stance")} htmlFor="revise-stance">
              <Select
                id="revise-stance"
                value={stance}
                onChange={(event) => setStance(event.target.value)}
              >
                {["support", "oppose", "qualify", "conditional_accept"].map((value) => (
                  <option key={value} value={value}>
                    {enumLabel("stance", value, locale)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label={t("positions.argumentIds")} htmlFor="revise-arguments">
              <TextInput
                id="revise-arguments"
                value={argumentIds}
                onChange={(event) => setArgumentIds(event.target.value)}
                placeholder="arg_…, arg_…"
              />
            </Field>
            <Field label={t("positions.packIds")} htmlFor="revise-packs">
              <TextInput
                id="revise-packs"
                value={packIds}
                onChange={(event) => setPackIds(event.target.value)}
                placeholder="evp_…, evp_…"
              />
            </Field>
            <Field label={t("positions.reasonDriver")} htmlFor="revise-driver">
              <TextArea
                id="revise-driver"
                rows={2}
                value={driver}
                onChange={(event) => setDriver(event.target.value)}
              />
            </Field>
            {revise.error !== null && revise.error !== undefined && <ErrorState error={revise.error} />}
            <Button
              type="submit"
              variant="primary"
              loading={revise.isPending}
              disabledReason={
                parseIds(argumentIds).length === 0 && parseIds(packIds).length === 0
                  ? t("positions.revisionNeedsCause")
                  : undefined
              }
            >
              {t("positions.submitRevision")}
            </Button>
          </form>
        </div>
      )}
    </Drawer>
  );
}
