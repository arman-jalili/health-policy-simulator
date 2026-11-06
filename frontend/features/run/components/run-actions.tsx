"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Icon } from "@/components/icons";
import { useSettings, useToast } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Checkbox, Field, Select, TextArea, TextInput } from "@/components/ui/field";
import { Drawer } from "@/components/ui/drawer";
import { ErrorState } from "@/components/ui/states";
import { StatusPill, type StatusTone } from "@/components/ui/status-pill";
import {
  useBindStakeholders,
  useRecordAbstention,
  useSelectStakeholders,
  useStartRun,
  useSubmitPosition,
  useTakeTurn,
} from "@/features/run/hooks";
import type {
  CloseRoundBody,
  RunResponse,
  TargetInput,
} from "@/features/run/contracts";
import type { TurnStatus } from "@/features/positions/derive";
import { demoInvocationId } from "@/lib/ids";
import { ApiError } from "@/lib/http";
import type { DemoSeed } from "@/lib/settings";
import { enumLabel } from "@/lib/i18n";

interface BaseDrawerProps {
  readonly runId: string;
  readonly round: number;
  readonly stakeholderIds: readonly string[];
  readonly names: ReadonlyMap<string, string>;
  readonly defaultTopic: string;
  readonly open: boolean;
  readonly onClose: () => void;
}

function topicOrDefault(topic: string): string {
  return topic.trim();
}

export function TurnDrawer({
  runId,
  round,
  stakeholderIds,
  names,
  defaultTopic,
  open,
  onClose,
  seed,
}: BaseDrawerProps & { readonly seed: DemoSeed | null }) {
  const { t, locale } = useSettings();
  const { push } = useToast();
  const takeTurn = useTakeTurn(runId);
  const [stakeholderId, setStakeholderId] = useState(stakeholderIds[0] ?? "");
  const [stance, setStakeholderStance] = useState("support");
  const [topic, setTopic] = useState(defaultTopic);
  const [text, setText] = useState("");
  const [claims, setClaims] = useState<readonly string[]>([""]);
  const [packId, setPackId] = useState("");
  const [unsupported, setUnsupported] = useState(false);
  const [invocationCounter, setInvocationCounter] = useState(1);
  const packs = useMemo(() => Object.entries(seed?.pack_ids ?? {}), [seed]);

  useEffect(() => {
    if (open) {
      setTopic(defaultTopic);
      setStakeholderId((current) =>
        stakeholderIds.includes(current) ? current : (stakeholderIds[0] ?? ""),
      );
    }
  }, [open, defaultTopic, stakeholderIds]);

  useEffect(() => {
    if (packId === "" && packs.length > 0) setPackId(packs[0]?.[1] ?? "");
  }, [packId, packs]);

  const invocationId = demoInvocationId(runId, round, stakeholderId, invocationCounter);
  const needsEvidence = packId === "" && !unsupported;
  const disabledReason =
    stakeholderId === ""
      ? t("console.noStakeholders")
      : topic.trim() === ""
        ? t("console.topicHint")
        : text.trim() === ""
          ? t("console.turnText")
          : needsEvidence
            ? t("console.noEvidence")
            : undefined;

  const submit = (): void => {
    const target: TargetInput = { topic: topicOrDefault(topic) };
    takeTurn.mutate(
      {
        stakeholder_id: stakeholderId,
        target,
        stance: stance as "support" | "oppose" | "qualify" | "conditional_accept",
        text,
        claims: claims
          .map((claim) => claim.trim())
          .filter((claim) => claim !== "")
          .map((claim) => ({ text: claim })),
        evidence_ids: packId === "" ? [] : [packId],
        unsupported,
        invocation_id: invocationId,
      },
      {
        onSuccess: () => {
          push(t("console.turnSuccess"), "ok");
          setText("");
          setClaims([""]);
          setInvocationCounter((value) => value + 1);
          onClose();
        },
      },
    );
  };

  return (
    <Drawer open={open} onClose={onClose} title={t("console.takeTurn")}>
      <div className="space-y-4">
        <Field label={t("common.stakeholder")} htmlFor="turn-stakeholder">
          <Select
            id="turn-stakeholder"
            value={stakeholderId}
            onChange={(event) => setStakeholderId(event.target.value)}
          >
            {stakeholderIds.map((id) => (
              <option key={id} value={id}>
                {names.get(id) ?? id}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("common.topic")} htmlFor="turn-topic" hint={t("console.topicHint")}>
          <TextInput id="turn-topic" value={topic} onChange={(event) => setTopic(event.target.value)} />
        </Field>
        <Field label={t("common.stance")} htmlFor="turn-stance">
          <Select
            id="turn-stance"
            value={stance}
            onChange={(event) => setStakeholderStance(event.target.value)}
          >
            {["support", "oppose", "qualify", "conditional_accept"].map((value) => (
              <option key={value} value={value}>
                {enumLabel("stance", value, locale)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("console.turnText")} htmlFor="turn-text">
          <TextArea
            id="turn-text"
            rows={5}
            maxLength={8000}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
        </Field>
        <Field label={t("console.evidencePack")} htmlFor="turn-pack" hint={seed === null ? t("dashboard.seedMissing") : undefined}>
          <Select
            id="turn-pack"
            value={packId}
            onChange={(event) => setPackId(event.target.value)}
            disabled={packs.length === 0}
          >
            <option value="">{t("common.none")}</option>
            {packs.map(([topicKey, id]) => (
              <option key={id} value={id}>
                {topicKey} — {id}
              </option>
            ))}
          </Select>
        </Field>
        <Checkbox
          label={t("console.unsupported")}
          checked={unsupported}
          onChange={(event) => setUnsupported(event.target.checked)}
        />
        <fieldset>
          <legend className="text-sm font-medium">{t("console.claims")}</legend>
          <div className="mt-2 space-y-2">
            {claims.map((claim, index) => (
              <div key={index} className="flex items-center gap-2">
                <TextInput
                  aria-label={`${t("console.claimPlaceholder")} ${index + 1}`}
                  value={claim}
                  onChange={(event) =>
                    setClaims((current) =>
                      current.map((item, position) => (position === index ? event.target.value : item)),
                    )
                  }
                />
                <Button
                  size="sm"
                  aria-label={t("common.remove")}
                  onClick={() => setClaims((current) => current.filter((_, position) => position !== index))}
                  disabled={claims.length === 1}
                >
                  {t("common.remove")}
                </Button>
              </div>
            ))}
          </div>
          <Button size="sm" className="mt-2" onClick={() => setClaims((current) => [...current, ""])}>
            {t("console.addClaim")}
          </Button>
        </fieldset>
        <div className="rounded-xs border border-line bg-surface-muted px-2 py-1.5">
          <p className="text-2xs text-ink-muted">{t("console.invocationId")}</p>
          <p className="font-mono text-2xs text-ink">{invocationId}</p>
          <p className="mt-1 text-2xs text-ink-subtle">{t("console.invocationHint")}</p>
        </div>
        {takeTurn.error !== null && takeTurn.error !== undefined && (
          <ErrorState error={takeTurn.error} />
        )}
        <Button
          variant="primary"
          className="w-full"
          onClick={submit}
          loading={takeTurn.isPending}
          disabledReason={disabledReason}
        >
          {t("console.submitTurn")}
        </Button>
      </div>
    </Drawer>
  );
}

export function PositionDrawer({
  runId,
  round,
  stakeholderIds,
  names,
  defaultTopic,
  open,
  onClose,
  seed,
}: BaseDrawerProps & { readonly seed: DemoSeed | null }) {
  const { t, locale } = useSettings();
  const { push } = useToast();
  const submit = useSubmitPosition(runId);
  const [stakeholderId, setStakeholderId] = useState(stakeholderIds[0] ?? "");
  const [stance, setStance] = useState("support");
  const [topic, setTopic] = useState(defaultTopic);
  const [summary, setSummary] = useState("");
  const [packId, setPackId] = useState("");
  const packs = useMemo(() => Object.entries(seed?.pack_ids ?? {}), [seed]);

  useEffect(() => {
    if (!open) return;
    setTopic(defaultTopic);
    setStakeholderId((current) =>
      stakeholderIds.includes(current) ? current : (stakeholderIds[0] ?? ""),
    );
  }, [open, defaultTopic, stakeholderIds]);

  useEffect(() => {
    if (packId === "" && packs.length > 0) setPackId(packs[0]?.[1] ?? "");
  }, [packId, packs]);

  const disabledReason =
    seed === null
      ? t("dashboard.seedMissing")
      : stakeholderId === ""
        ? t("console.noStakeholders")
        : topic.trim() === ""
          ? t("console.topicHint")
          : summary.trim() === ""
            ? t("console.positionSummary")
            : packId === ""
              ? t("console.evidencePack")
              : undefined;

  const send = (): void => {
    submit.mutate(
      {
        stakeholder_id: stakeholderId,
        topic: topicOrDefault(topic),
        stance: stance as "support" | "oppose" | "qualify" | "conditional_accept",
        proposal: { summary, components: [] },
        evidence_ids: [packId],
      },
      {
        onSuccess: () => {
          push(t("console.positionSuccess"), "ok");
          setSummary("");
          onClose();
        },
      },
    );
  };

  return (
    <Drawer open={open} onClose={onClose} title={t("console.openPosition")}>
      <div className="space-y-4">
        {seed === null ? (
          <div className="rounded-md border border-warn/40 bg-warn-quiet px-3 py-2 text-sm">
            <p>{t("dashboard.seedMissing")}</p>
            <code className="mt-2 block rounded-xs border border-line bg-surface px-2 py-1.5 font-mono text-2xs">
              LOG_LEVEL=ERROR make -s demo-seed &gt; /tmp/demo-seed.json
            </code>
            <Link href="/settings" className="mt-2 inline-block text-sm">
              {t("dashboard.seedLink")}
            </Link>
          </div>
        ) : (
          <>
            <p className="text-2xs text-ink-muted">
              {t("console.eventRound", { round })}
            </p>
            <Field label={t("common.stakeholder")} htmlFor="position-stakeholder">
              <Select
                id="position-stakeholder"
                value={stakeholderId}
                onChange={(event) => setStakeholderId(event.target.value)}
              >
                {stakeholderIds.map((id) => (
                  <option key={id} value={id}>
                    {names.get(id) ?? id}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label={t("common.topic")} htmlFor="position-topic" hint={t("console.topicHint")}>
              <TextInput
                id="position-topic"
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
              />
            </Field>
            <Field label={t("common.stance")} htmlFor="position-stance">
              <Select
                id="position-stance"
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
            <Field label={t("console.positionSummary")} htmlFor="position-summary">
              <TextArea
                id="position-summary"
                rows={3}
                maxLength={2000}
                value={summary}
                onChange={(event) => setSummary(event.target.value)}
              />
            </Field>
            <Field label={t("console.evidencePack")} htmlFor="position-pack">
              <Select
                id="position-pack"
                value={packId}
                onChange={(event) => setPackId(event.target.value)}
              >
                {packs.map(([topicKey, id]) => (
                  <option key={id} value={id}>
                    {topicKey} — {id}
                  </option>
                ))}
              </Select>
            </Field>
            {submit.error !== null && submit.error !== undefined && <ErrorState error={submit.error} />}
            <Button
              variant="primary"
              className="w-full"
              onClick={send}
              loading={submit.isPending}
              disabledReason={disabledReason}
            >
              {t("console.submitPosition")}
            </Button>
          </>
        )}
      </div>
    </Drawer>
  );
}

export function AbstentionDrawer({
  runId,
  round,
  stakeholderIds,
  names,
  defaultTopic,
  open,
  onClose,
}: BaseDrawerProps) {
  const { t } = useSettings();
  const { push } = useToast();
  const abstain = useRecordAbstention(runId);
  const [stakeholderId, setStakeholderId] = useState(stakeholderIds[0] ?? "");
  const [topic, setTopic] = useState(defaultTopic);

  useEffect(() => {
    if (!open) return;
    setTopic(defaultTopic);
    setStakeholderId((current) =>
      stakeholderIds.includes(current) ? current : (stakeholderIds[0] ?? ""),
    );
  }, [open, defaultTopic, stakeholderIds]);

  const send = (): void => {
    abstain.mutate(
      { stakeholder_id: stakeholderId, topic: topicOrDefault(topic) },
      {
        onSuccess: () => {
          push(t("console.abstentionSuccess"), "ok");
          onClose();
        },
      },
    );
  };

  return (
    <Drawer open={open} onClose={onClose} title={t("console.absent")}>
      <div className="space-y-4">
        <p className="text-2xs text-ink-muted">{t("console.eventRound", { round })}</p>
        <Field label={t("common.stakeholder")} htmlFor="abstention-stakeholder">
          <Select
            id="abstention-stakeholder"
            value={stakeholderId}
            onChange={(event) => setStakeholderId(event.target.value)}
          >
            {stakeholderIds.map((id) => (
              <option key={id} value={id}>
                {names.get(id) ?? id}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("common.topic")} htmlFor="abstention-topic" hint={t("console.topicHint")}>
          <TextInput
            id="abstention-topic"
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
          />
        </Field>
        {abstain.error !== null && abstain.error !== undefined && <ErrorState error={abstain.error} />}
        <Button
          variant="primary"
          className="w-full"
          onClick={send}
          loading={abstain.isPending}
          disabledReason={topic.trim() === "" ? t("console.topicHint") : undefined}
        >
          {t("console.absent")}
        </Button>
      </div>
    </Drawer>
  );
}

export function MandateDrawer({
  runId,
  names,
  open,
  onClose,
  defaultMandate,
}: {
  readonly runId: string;
  readonly names: ReadonlyMap<string, string>;
  readonly open: boolean;
  readonly onClose: () => void;
  readonly defaultMandate: string;
}) {
  const { t } = useSettings();
  const { push } = useToast();
  const select = useSelectStakeholders(runId);
  const bind = useBindStakeholders(runId);
  const [mandate, setMandate] = useState(defaultMandate);
  const [chosen, setChosen] = useState<readonly string[]>([]);
  const [materiality, setMateriality] = useState<readonly { id: string; value: number }[]>([]);

  useEffect(() => {
    if (open) {
      setMandate(defaultMandate);
      setChosen([]);
      setMateriality([]);
    }
  }, [open, defaultMandate]);

  return (
    <Drawer open={open} onClose={onClose} title={t("console.mandateDrawer")}>
      <div className="space-y-4">
        <Field label={t("new.question")} htmlFor="mandate-text" hint={t("console.selectHelp")}>
          <TextArea
            id="mandate-text"
            rows={4}
            value={mandate}
            onChange={(event) => setMandate(event.target.value)}
          />
        </Field>
        <Button
          onClick={() =>
            select.mutate(
              { mandate },
              {
                onSuccess: (result) => {
                  const items = [...result.items].sort((a, b) => b.materiality - a.materiality);
                  setMateriality(
                    items.map((item) => ({ id: item.stakeholder_id, value: item.materiality })),
                  );
                  setChosen(items.map((item) => item.stakeholder_id));
                },
              },
            )
          }
          loading={select.isPending}
          disabledReason={mandate.trim() === "" ? t("new.invalidQuestion") : undefined}
        >
          {t("console.selectStakeholders")}
        </Button>
        {select.error !== null && select.error !== undefined && <ErrorState error={select.error} />}
        {materiality.length > 0 && (
          <fieldset>
            <legend className="text-sm font-medium">{t("console.materiality")}</legend>
            <ul className="mt-2 space-y-1">
              {materiality.map((item) => (
                <li key={item.id} className="flex items-center justify-between gap-2 rounded-xs border border-line px-2 py-1">
                  <Checkbox
                    label={names.get(item.id) ?? item.id}
                    checked={chosen.includes(item.id)}
                    onChange={() =>
                      setChosen((current) =>
                        current.includes(item.id)
                          ? current.filter((id) => id !== item.id)
                          : [...current, item.id],
                      )
                    }
                  />
                  <span className="text-2xs tabular text-ink-muted">
                    {(item.value * 100).toFixed(0)}%
                  </span>
                </li>
              ))}
            </ul>
          </fieldset>
        )}
        <Button
          variant="primary"
          className="w-full"
          onClick={() =>
            bind.mutate(
              { stakeholder_ids: [...chosen] },
              {
                onSuccess: () => {
                  push(t("console.bindSuccess"), "ok");
                  onClose();
                },
              },
            )
          }
          loading={bind.isPending}
          disabledReason={chosen.length === 0 ? t("new.selectAtLeastOne") : undefined}
        >
          {t("console.bindStakeholders")}
        </Button>
        <p className="text-2xs text-ink-muted">{t("console.bindHelp")}</p>
        {bind.error !== null && bind.error !== undefined && <ErrorState error={bind.error} />}
        <p className="text-2xs text-ink-subtle">{t("positions.eventsOnly")}</p>
      </div>
    </Drawer>
  );
}

const STATUS_TONE: Record<TurnStatus, StatusTone> = {
  pending: "neutral",
  turn: "ok",
  position: "info",
  abstention: "warn",
};

const STATUS_LABEL: Record<TurnStatus, "console.statusSilent" | "console.statusTurn" | "console.statusPosition" | "console.statusAbstention"> = {
  pending: "console.statusSilent",
  turn: "console.statusTurn",
  position: "console.statusPosition",
  abstention: "console.statusAbstention",
};

export function RoundPanel({
  run,
  round,
  turnOrder,
  names,
  statuses,
  unaccounted,
  onOpenRound,
  onCloseRound,
  onAbstain,
  onTurn,
  onPosition,
  onMandate,
  onStart,
  openRoundPending,
  closePending,
  startPending,
  closeError,
  stoppingCondition,
  startDisabledReason,
  roundIsOpen,
}: {
  readonly run: RunResponse;
  readonly round: number;
  readonly turnOrder: readonly string[];
  readonly names: ReadonlyMap<string, string>;
  readonly statuses: ReadonlyMap<string, TurnStatus>;
  readonly unaccounted: readonly string[];
  readonly onOpenRound: () => void;
  readonly onCloseRound: (body: CloseRoundBody) => void;
  readonly onAbstain: () => void;
  readonly onTurn: () => void;
  readonly onPosition: () => void;
  readonly onMandate: () => void;
  readonly onStart: () => void;
  readonly openRoundPending: boolean;
  readonly closePending: boolean;
  readonly startPending: boolean;
  readonly closeError: ApiError | null;
  readonly stoppingCondition: Readonly<Record<string, unknown>> | null;
  readonly startDisabledReason?: string | undefined;
  readonly roundIsOpen: boolean;
}) {
  const { t, locale } = useSettings();
  const [convergence, setConvergence] = useState("none");
  const [learning, setLearning] = useState("");
  const guardError = closeError?.code === "ROUND_CLOSE_GUARD_VIOLATION" ? closeError : null;

  return (
    <Card>
      <CardHeader
        title={`${t("console.roundPanel")} · ${round}`}
        actions={
          <StatusPill tone={run.closed ? "neutral" : "ok"}>
            {run.closed ? t("run.closed") : t("run.open")}
          </StatusPill>
        }
      />
      <CardBody className="space-y-4">
        {run.closed ? (
          <div className="space-y-3">
            <p className="text-sm text-ink-muted">{t("console.closedHint")}</p>
            {stoppingCondition !== null && (
              <div className="rounded-xs border border-line bg-surface-muted px-2 py-1.5">
                <p className="text-2xs uppercase tracking-wide text-ink-muted">
                  {t("console.stoppingCondition")}
                </p>
                <p className="mt-1 text-sm">
                  {typeof stoppingCondition["name"] === "string"
                    ? enumLabel("stoppingCondition", stoppingCondition["name"], locale)
                    : "—"}
                  {typeof stoppingCondition["fired"] === "boolean" &&
                    ` · ${String(stoppingCondition["fired"])}`}
                </p>
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              <Link href={`/runs/${run.run_id}/consensus`} className="text-sm">
                {t("run.tabs.consensus")}
              </Link>
              <span aria-hidden="true">·</span>
              <Link href={`/runs/${run.run_id}/brief`} className="text-sm">
                {t("run.tabs.brief")}
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div>
              <h3 className="mb-2 text-sm font-semibold">{t("console.turnOrder")}</h3>
              <ol className="space-y-1">
                {turnOrder.map((id) => {
                  const status = statuses.get(id) ?? "pending";
                  return (
                    <li key={id} className="flex items-center justify-between gap-2 py-0.5">
                      <span className="min-w-0 truncate text-sm">{names.get(id) ?? id}</span>
                      <StatusPill tone={STATUS_TONE[status]}>{t(STATUS_LABEL[status])}</StatusPill>
                    </li>
                  );
                })}
              </ol>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <Button
                size="sm"
                onClick={onOpenRound}
                loading={openRoundPending}
                disabledReason={roundIsOpen ? t("error.roundStillOpen") : undefined}
              >
                {t("console.openRound")}
              </Button>
              <Button
                size="sm"
                onClick={onTurn}
                disabledReason={round === 0 ? t("console.openRound") : undefined}
              >
                {t("console.takeTurn")}
              </Button>
              <Button
                size="sm"
                onClick={onPosition}
                disabledReason={round === 0 ? t("console.openRound") : undefined}
              >
                {t("console.openPosition")}
              </Button>
              <Button
                size="sm"
                onClick={onAbstain}
                disabledReason={round === 0 ? t("console.openRound") : undefined}
              >
                {t("console.absent")}
              </Button>
              <Button size="sm" onClick={onMandate}>
                {t("console.mandateDrawer")}
              </Button>
              <Button
                size="sm"
                onClick={onStart}
                loading={startPending}
                disabledReason={startDisabledReason}
              >
                {t("console.startJob")}
              </Button>
            </div>

            <form
              className="space-y-2 rounded-xs border border-line bg-surface-muted p-3"
              onSubmit={(event) => {
                event.preventDefault();
                onCloseRound({
                  learning:
                    learning.trim() === ""
                      ? []
                      : [
                          {
                            insight_type: "observation",
                            statement: learning.trim(),
                            derived_from: [],
                            round_number: round,
                          },
                        ],
                  convergence,
                });
              }}
            >
              <h3 className="text-sm font-semibold">{t("console.closeRound")}</h3>
              <Field label={t("console.convergence")} htmlFor="convergence">
                <Select
                  id="convergence"
                  value={convergence}
                  onChange={(event) => setConvergence(event.target.value)}
                >
                  <option value="none">{t("console.convergenceNone")}</option>
                  <option value="low">{t("console.convergenceLow")}</option>
                  <option value="medium">{t("console.convergenceMedium")}</option>
                  <option value="high">{t("console.convergenceHigh")}</option>
                </Select>
              </Field>
              <Field label={t("console.optionalLearning")} htmlFor="learning">
                <TextArea
                  id="learning"
                  rows={2}
                  value={learning}
                  onChange={(event) => setLearning(event.target.value)}
                />
              </Field>
              <Button
                type="submit"
                size="sm"
                variant="primary"
                loading={closePending}
                disabledReason={
                  round === 0
                    ? t("console.openRound")
                    : unaccounted.length > 0
                      ? t("console.closeRoundDisabled")
                      : undefined
                }
              >
                {t("console.closeRound")}
              </Button>
            </form>

            {guardError !== null && (
              <div className="space-y-2 rounded-md border border-warn/40 bg-warn-quiet px-3 py-2">
                <p className="text-sm font-medium text-warn">{t("console.guardFix")}</p>
                <ul className="list-inside list-disc text-sm">
                  {unaccounted.map((id) => (
                    <li key={id}>{names.get(id) ?? id}</li>
                  ))}
                </ul>
              </div>
            )}
            {closeError !== null && guardError === null && <ErrorState error={closeError} />}
          </>
        )}
      </CardBody>
    </Card>
  );
}

export function StartRunButton({
  runId,
  budgetMaxInvocations,
  disabledReason,
  onStarted,
}: {
  readonly runId: string;
  readonly budgetMaxInvocations: number;
  readonly disabledReason?: string;
  readonly onStarted: (jobId: string) => void;
}) {
  const { t } = useSettings();
  const { push } = useToast();
  const start = useStartRun(runId);
  return (
    <div className="space-y-2">
      <Button
        variant="primary"
        icon={<Icon name="play" size={15} />}
        loading={start.isPending}
        disabledReason={disabledReason}
        onClick={() =>
          start.mutate(
            { budget: { max_invocations: budgetMaxInvocations } },
            {
              onSuccess: (result) => {
                push(t("console.jobStarted", { job: result.job_id }), "ok");
                onStarted(result.job_id);
              },
            },
          )
        }
      >
        {t("console.startJob")}
      </Button>
      {start.error !== null && start.error !== undefined && <ErrorState error={start.error} />}
    </div>
  );
}
