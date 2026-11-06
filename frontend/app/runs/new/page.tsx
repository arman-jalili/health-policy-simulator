"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { useSettings, useToast } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Checkbox, Field, TextArea, TextInput } from "@/components/ui/field";
import { PageHeader } from "@/components/ui/page-header";
import { ErrorState, LoadingBlock } from "@/components/ui/states";
import { useOpenRun } from "@/features/run/hooks";
import { useStakeholders } from "@/features/stakeholders/hooks";
import { addRunToIndex } from "@/lib/settings";
import { enumLabel } from "@/lib/i18n";
import { truncateMiddle } from "@/lib/format";

export default function NewRunPage() {
  const { t, locale, settings, hydrated } = useSettings();
  const { push } = useToast();
  const router = useRouter();
  const stakeholders = useStakeholders();
  const openRun = useOpenRun();
  const [question, setQuestion] = useState(settings.defaultQuestion);
  const [roundCap, setRoundCap] = useState(String(settings.roundCap));
  const [threshold, setThreshold] = useState(String(settings.consensusThreshold));
  const [selected, setSelected] = useState<readonly string[]>([]);
  const initialized = useRef(false);

  useEffect(() => {
    if (!hydrated) return;
    setQuestion(settings.defaultQuestion);
    setRoundCap(String(settings.roundCap));
    setThreshold(String(settings.consensusThreshold));
  }, [hydrated, settings.defaultQuestion, settings.roundCap, settings.consensusThreshold]);

  useEffect(() => {
    if (initialized.current || stakeholders.data === undefined) return;
    initialized.current = true;
    const all = stakeholders.data.items.map((item) => item.stakeholder_id);
    const preferred = settings.defaultStakeholderIds.filter((id) => all.includes(id));
    setSelected(preferred.length > 0 ? preferred : all);
  }, [stakeholders.data, settings.defaultStakeholderIds]);

  const items = stakeholders.data?.items ?? [];
  const validRoundCap = Number(roundCap);
  const validThreshold = Number(threshold);
  const questionError =
    question.trim().length === 0 || question.length > 4000 ? t("new.invalidQuestion") : undefined;
  const roundCapError =
    !Number.isInteger(validRoundCap) || validRoundCap < 1 || validRoundCap > 50
      ? t("new.invalidRoundCap")
      : undefined;
  const thresholdError =
    !Number.isFinite(validThreshold) || validThreshold <= 0 || validThreshold > 1
      ? t("new.invalidThreshold")
      : undefined;
  const selectionError = selected.length === 0 ? t("new.selectAtLeastOne") : undefined;
  const canSubmit =
    questionError === undefined &&
    roundCapError === undefined &&
    thresholdError === undefined &&
    selectionError === undefined &&
    !openRun.isPending;

  const toggle = (id: string): void => {
    setSelected((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  };

  const submit = (): void => {
    if (!canSubmit) return;
    openRun.mutate(
      {
        question,
        round_cap: validRoundCap,
        stakeholder_ids: [...selected],
        consensus_threshold: validThreshold,
      },
      {
        onSuccess: (result) => {
          addRunToIndex({
            runId: result.run_id,
            question,
            createdAt: new Date().toISOString(),
            phase: result.phase,
            round: 0,
            closed: false,
            mandateHash: result.mandate_hash,
            driver: "manual",
          });
          push(`${t("new.mandateHash")}: ${truncateMiddle(result.mandate_hash, 14, 6)}`, "ok");
          router.push(`/runs/${result.run_id}`);
        },
      },
    );
  };

  return (
    <div className="space-y-5">
      <PageHeader
        title={t("new.title")}
        subtitle={t("new.subtitle")}
        crumbs={[{ label: t("dashboard.title"), href: "/" }, { label: t("new.title") }]}
      />

      <form
        className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <Card>
          <CardHeader title={t("new.title")} />
          <CardBody className="space-y-4">
            <Field label={t("new.question")} htmlFor="question" hint={t("new.questionHint")} error={questionError}>
              <TextArea
                id="question"
                value={question}
                rows={5}
                maxLength={4000}
                onChange={(event) => setQuestion(event.target.value)}
                aria-describedby="question-hint"
                required
              />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={t("new.roundCap")} htmlFor="round-cap" hint={t("new.roundCapHint")} error={roundCapError}>
                <TextInput
                  id="round-cap"
                  type="number"
                  min={1}
                  max={50}
                  value={roundCap}
                  onChange={(event) => setRoundCap(event.target.value)}
                  aria-describedby="round-cap-hint"
                />
              </Field>
              <Field label={t("new.threshold")} htmlFor="threshold" hint={t("new.thresholdHint")} error={thresholdError}>
                <TextInput
                  id="threshold"
                  type="number"
                  min={0.01}
                  max={1}
                  step="any"
                  value={threshold}
                  onChange={(event) => setThreshold(event.target.value)}
                  aria-describedby="threshold-hint"
                />
              </Field>
            </div>

            <fieldset>
              <legend className="text-sm font-medium">{t("new.stakeholders")}</legend>
              <div className="mt-2 flex flex-wrap gap-2">
                <Button
                  size="sm"
                  onClick={() => setSelected(items.map((item) => item.stakeholder_id))}
                >
                  {t("new.selectAll")}
                </Button>
                <Button size="sm" onClick={() => setSelected([])}>
                  {t("new.clearAll")}
                </Button>
                <span className="self-center text-2xs text-ink-muted">
                  {t("new.selectedCount", { count: selected.length, total: items.length })}
                </span>
              </div>
              {selectionError !== undefined && (
                <p role="alert" className="mt-2 text-2xs text-danger">
                  {selectionError}
                </p>
              )}
              {stakeholders.isLoading ? (
                <div className="mt-3">
                  <LoadingBlock rows={4} />
                </div>
              ) : stakeholders.error !== null && stakeholders.error !== undefined ? (
                <div className="mt-3">
                  <ErrorState error={stakeholders.error} onRetry={() => void stakeholders.refetch()} />
                </div>
              ) : (
                <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                  {items.map((item) => (
                    <li key={item.stakeholder_id} className="rounded-md border border-line px-3 py-2">
                      <Checkbox
                        label={item.identity.short_name}
                        checked={selected.includes(item.stakeholder_id)}
                        onChange={() => toggle(item.stakeholder_id)}
                      />
                      <p className="mt-1 text-2xs text-ink-muted">
                        {enumLabel("institutionCategory", item.identity.category, locale)} ·{" "}
                        {item.identity.name}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </fieldset>
          </CardBody>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader title={t("new.turnOrder")} description={t("new.turnOrderHint")} />
            <CardBody>
              {selected.length === 0 ? (
                <p className="text-sm text-ink-muted">{t("new.defaultAll")}</p>
              ) : (
                <ol className="space-y-1 text-sm">
                  {items
                    .filter((item) => selected.includes(item.stakeholder_id))
                    .map((item, index) => (
                      <li key={item.stakeholder_id} className="flex items-center gap-2">
                        <span className="w-5 text-right font-mono text-2xs text-ink-muted">
                          {index + 1}
                        </span>
                        <span>{item.identity.short_name}</span>
                      </li>
                    ))}
                </ol>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardBody className="space-y-3">
              <Button
                type="submit"
                variant="primary"
                loading={openRun.isPending}
                disabled={!canSubmit}
                className="w-full"
              >
                {openRun.isPending ? t("new.submitting") : t("new.submit")}
              </Button>
              {openRun.error !== null && openRun.error !== undefined && (
                <ErrorState error={openRun.error} />
              )}
              <p className="text-2xs text-ink-muted">{t("new.mandateHashHint")}</p>
            </CardBody>
          </Card>
        </div>
      </form>
    </div>
  );
}
