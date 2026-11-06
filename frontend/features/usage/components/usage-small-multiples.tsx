"use client";

import { scaleLinear } from "d3-scale";

import { useSettings } from "@/components/providers";
import { ChartFrame } from "@/components/ui/chart-frame";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import type { Budget, UsageResponse } from "@/features/run/contracts";
import { readChartPalette } from "@/lib/chart/encoding";
import { useChartWidth } from "@/lib/chart/use-width";
import { formatEur, formatEurExact, formatNumber, parseDecimal, truncateMiddle } from "@/lib/format";

interface TokenRow {
  readonly label: string;
  readonly input: number;
  readonly output: number;
  readonly cost: string;
}

function TokenGrid({
  rows,
  names,
}: {
  readonly rows: readonly TokenRow[];
  readonly names?: ReadonlyMap<string, string>;
}) {
  const { t, locale } = useSettings();
  const palette = readChartPalette();
  const { ref, width: measured } = useChartWidth(760);
  const width = Math.max(420, measured);
  const columns = width > 640 ? 3 : width > 420 ? 2 : 1;
  const cellWidth = (width - 8) / columns;
  const cellHeight = 46;
  const rowCount = Math.ceil(rows.length / columns);
  const height = rowCount * cellHeight + 8;
  const maxTokens = Math.max(1, ...rows.flatMap((row) => [row.input, row.output]));
  const scale = scaleLinear().domain([0, maxTokens]).range([0, cellWidth - 96]);

  return (
    <div ref={ref} className="overflow-x-auto">
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} role="img" aria-label={t("usage.byStakeholder")}>
        <title>{t("usage.byStakeholder")}</title>
        <desc>{t("usage.inputTokens")}</desc>
        {rows.map((row, index) => {
          const col = index % columns;
          const line = Math.floor(index / columns);
          const x = col * cellWidth + 4;
          const y = line * cellHeight + 6;
          const label = names?.get(row.label) ?? truncateMiddle(row.label, 12, 4);
          return (
            <g key={row.label}>
              <text x={x} y={y + 10} fontSize={10} fill={palette.ink}>
                {label}
              </text>
              <rect x={x} y={y + 15} width={cellWidth - 96} height={7} fill={palette.line} rx={2} />
              <rect
                x={x}
                y={y + 15}
                width={Math.max(1, scale(row.input))}
                height={7}
                fill={palette.info}
                rx={2}
              >
                <title>{`${t("usage.inputTokens")}: ${formatNumber(row.input, locale)}`}</title>
              </rect>
              <rect x={x} y={y + 25} width={cellWidth - 96} height={7} fill={palette.line} rx={2} />
              <rect
                x={x}
                y={y + 25}
                width={Math.max(1, scale(row.output))}
                height={7}
                fill={palette.accent}
                rx={2}
              >
                <title>{`${t("usage.outputTokens")}: ${formatNumber(row.output, locale)}`}</title>
              </rect>
              <text x={x + cellWidth - 90} y={y + 22} fontSize={9} fill={palette.muted}>
                {formatNumber(row.input, locale)}
              </text>
              <text x={x + cellWidth - 90} y={y + 32} fontSize={9} fill={palette.muted}>
                {formatNumber(row.output, locale)} · {formatEur(row.cost, locale, { compact: true })}
              </text>
            </g>
          );
        })}
      </svg>
      <ul className="mt-1 flex gap-4 text-2xs text-ink-muted">
        <li>
          <span aria-hidden="true" className="mr-1 inline-block h-2 w-3 bg-info" />
          {t("usage.inputTokens")}
        </li>
        <li>
          <span aria-hidden="true" className="mr-1 inline-block h-2 w-3 bg-accent" />
          {t("usage.outputTokens")}
        </li>
      </ul>
    </div>
  );
}

function BudgetGauge({
  budget,
  usage,
  defaultInvocations,
}: {
  readonly budget: Budget | null;
  readonly usage: UsageResponse;
  readonly defaultInvocations: number;
}) {
  const { t, locale } = useSettings();
  const palette = readChartPalette();
  const invocationsLimit = budget?.max_invocations ?? defaultInvocations;
  const tokensLimit = budget?.max_tokens ?? null;
  const costLimit = parseDecimal(budget?.max_cost ?? null);
  const usedTokens = usage.input_tokens + usage.output_tokens;
  const usedCost = parseDecimal(usage.cost) ?? 0;
  const rows: { label: string; used: number; limit: number | null; text: string }[] = [
    {
      label: t("usage.invocations"),
      used: usage.total_invocations,
      limit: invocationsLimit,
      text: `${formatNumber(usage.total_invocations, locale)} / ${formatNumber(invocationsLimit, locale)}`,
    },
    {
      label: t("usage.inputTokens") + " + " + t("usage.outputTokens"),
      used: usedTokens,
      limit: tokensLimit,
      text:
        tokensLimit === null
          ? `${formatNumber(usedTokens, locale)} · ${t("usage.noLimit")}`
          : `${formatNumber(usedTokens, locale)} / ${formatNumber(tokensLimit, locale)}`,
    },
    {
      label: t("usage.cost"),
      used: usedCost,
      limit: costLimit,
      text:
        costLimit === null
          ? `${formatEur(usage.cost, locale)} · ${t("usage.noLimit")}`
          : `${formatEur(usage.cost, locale)} / ${formatEur(costLimit, locale)}`,
    },
  ];
  return (
    <div className="space-y-2">
      {rows.map((row) => {
        const ratio = row.limit === null || row.limit <= 0 ? 0 : Math.min(1, row.used / row.limit);
        const tone = ratio >= 1 ? palette.danger : ratio >= 0.8 ? palette.warn : palette.ok;
        return (
          <div key={row.label}>
            <div className="flex items-baseline justify-between text-2xs">
              <span className="text-ink-muted">{row.label}</span>
              <span className="tabular text-ink">{row.text}</span>
            </div>
            <div className="mt-1 h-2.5 rounded-xs bg-surface-muted">
              <div
                className="h-2.5 rounded-xs"
                style={{ width: `${Math.round(ratio * 100)}%`, backgroundColor: tone }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function UsageSmallMultiples({
  usage,
  budget,
  defaultInvocations,
}: {
  readonly usage: UsageResponse;
  readonly budget: Budget | null;
  readonly defaultInvocations: number;
}) {
  const { t, locale } = useSettings();
  const stakeholderRows: TokenRow[] = usage.by_stakeholder.map((item) => ({
    label: item.stakeholder,
    input: item.input_tokens,
    output: item.output_tokens,
    cost: item.cost,
  }));
  const roundRows: TokenRow[] = usage.by_round.map((item) => ({
    label: `Runde ${item.round}`,
    input: item.input_tokens,
    output: item.output_tokens,
    cost: item.cost,
  }));

  return (
    <div className="space-y-4">
      <section className="rounded-md border border-line bg-surface px-4 py-3">
        <h3 className="mb-2 text-sm font-semibold">{t("usage.budget")}</h3>
        <BudgetGauge budget={budget} usage={usage} defaultInvocations={defaultInvocations} />
      </section>
      <section className="rounded-md border border-line bg-surface px-4 py-3">
        <ChartFrame
          title={t("usage.byStakeholder")}
          table={
            <Table caption={t("usage.byStakeholder")}>
              <THead>
                <TR>
                  <TH>{t("common.stakeholder")}</TH>
                  <TH className="text-right">{t("usage.invocations")}</TH>
                  <TH className="text-right">{t("usage.inputTokens")}</TH>
                  <TH className="text-right">{t("usage.outputTokens")}</TH>
                  <TH className="text-right">{t("usage.cost")}</TH>
                </TR>
              </THead>
              <TBody>
                {usage.by_stakeholder.map((item) => (
                  <TR key={item.stakeholder}>
                    <TD className="font-mono text-2xs">{item.stakeholder}</TD>
                    <TD className="text-right tabular">{item.invocations}</TD>
                    <TD className="text-right tabular">{formatNumber(item.input_tokens, locale)}</TD>
                    <TD className="text-right tabular">{formatNumber(item.output_tokens, locale)}</TD>
                    <TD className="text-right tabular" title={formatEurExact(item.cost, locale)}>
                      {formatEur(item.cost, locale)}
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          }
        >
          <TokenGrid rows={stakeholderRows} />
        </ChartFrame>
      </section>
      <section className="rounded-md border border-line bg-surface px-4 py-3">
        <ChartFrame
          title={t("usage.byRound")}
          table={
            <Table caption={t("usage.byRound")}>
              <THead>
                <TR>
                  <TH className="text-right">{t("common.round")}</TH>
                  <TH className="text-right">{t("usage.invocations")}</TH>
                  <TH className="text-right">{t("usage.inputTokens")}</TH>
                  <TH className="text-right">{t("usage.outputTokens")}</TH>
                  <TH className="text-right">{t("usage.cost")}</TH>
                </TR>
              </THead>
              <TBody>
                {usage.by_round.map((item) => (
                  <TR key={item.round}>
                    <TD className="text-right tabular">{item.round}</TD>
                    <TD className="text-right tabular">{item.invocations}</TD>
                    <TD className="text-right tabular">{formatNumber(item.input_tokens, locale)}</TD>
                    <TD className="text-right tabular">{formatNumber(item.output_tokens, locale)}</TD>
                    <TD className="text-right tabular">{formatEur(item.cost, locale)}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          }
        >
          <TokenGrid rows={roundRows} />
        </ChartFrame>
      </section>
    </div>
  );
}
