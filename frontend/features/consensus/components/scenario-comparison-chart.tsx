"use client";

import { scaleLinear, scaleSqrt } from "d3-scale";

import { useSettings } from "@/components/providers";
import { ChartFrame } from "@/components/ui/chart-frame";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import type { ComparisonEntry } from "@/features/consensus/contracts";
import { readChartPalette } from "@/lib/chart/encoding";
import { useChartWidth } from "@/lib/chart/use-width";
import { formatEur, formatPercent, parseDecimal, truncateMiddle } from "@/lib/format";
import { enumLabel } from "@/lib/i18n";

const LEFT = 176;
const GAP = 16;
const ROW = 42;

export function ScenarioComparisonChart({ entries }: { readonly entries: readonly ComparisonEntry[] }) {
  const { t, locale } = useSettings();
  const palette = readChartPalette();
  const { ref, width: measured } = useChartWidth(760);
  const width = Math.max(520, measured);
  const height = Math.max(80, entries.length * ROW + 28);
  const available = width - LEFT - 16;
  const costWidth = available * 0.48;
  const acceptanceWidth = available * 0.3;
  const acceptanceX = LEFT + costWidth + GAP;
  const costs = entries.map((entry) => parseDecimal(entry.cost) ?? 0);
  const maxCost = Math.max(1, ...costs);
  const costScale = scaleSqrt().domain([0, maxCost]).range([0, costWidth]);
  const acceptanceScale = scaleLinear().domain([0, 1]).range([0, acceptanceWidth]);

  return (
    <ChartFrame
      title={t("consensus.comparison")}
      description={t("consensus.feasibility")}
      table={
        <Table caption={t("consensus.comparison")}>
          <THead>
            <TR>
              <TH className="text-right">{t("consensus.rank")}</TH>
              <TH>{t("consensus.packages")}</TH>
              <TH>{t("consensus.scenario")}</TH>
              <TH className="text-right">{t("consensus.cost")}</TH>
              <TH className="text-right">{t("consensus.acceptance")}</TH>
              <TH>{t("consensus.feasibility")}</TH>
            </TR>
          </THead>
          <TBody>
            {entries.map((entry) => (
              <TR key={`${entry.package_id}-${entry.scenario_id}`}>
                <TD className="text-right tabular">{entry.rank}</TD>
                <TD className="font-mono text-2xs">{truncateMiddle(entry.package_id)}</TD>
                <TD className="font-mono text-2xs">{truncateMiddle(entry.scenario_id)}</TD>
                <TD className="text-right tabular">{formatEur(entry.cost, locale)}</TD>
                <TD className="text-right tabular">{formatPercent(entry.acceptance, locale, 0)}</TD>
                <TD>
                  {enumLabel("feasibility", entry.feasibility.political, locale)} /{" "}
                  {enumLabel("feasibility", entry.feasibility.legal, locale)} /{" "}
                  {enumLabel("feasibility", entry.feasibility.administrative, locale)}
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      }
    >
      <div ref={ref} className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          width="100%"
          height={height}
          role="img"
          aria-label={t("consensus.comparison")}
        >
          <title>{t("consensus.comparison")}</title>
          <desc>{t("consensus.feasibility")}</desc>
          <text x={LEFT} y={12} fontSize={10} fill={palette.muted}>
            {t("consensus.cost")} (EUR)
          </text>
          <text x={acceptanceX} y={12} fontSize={10} fill={palette.muted}>
            {t("consensus.acceptance")}
          </text>
          {entries.map((entry, index) => {
            const y = 22 + index * ROW;
            const cost = parseDecimal(entry.cost) ?? 0;
            const acceptanceColor = entry.acceptance >= 0.5 ? palette.ok : palette.warn;
            return (
              <g key={`${entry.package_id}-${entry.scenario_id}`}>
                <text x={4} y={y + 14} fontSize={10} fill={palette.ink}>
                  #{entry.rank} {truncateMiddle(entry.package_id, 10, 4)}
                </text>
                <rect x={LEFT} y={y} width={costWidth} height={16} fill={palette.line} rx={2} />
                <rect
                  x={LEFT}
                  y={y}
                  width={Math.max(cost === 0 ? 1 : 2, costScale(cost))}
                  height={16}
                  fill={palette.info}
                  rx={2}
                >
                  <title>{formatEur(entry.cost, locale)}</title>
                </rect>
                <text x={LEFT + costWidth + GAP / 2} y={y + 12} fontSize={9} fill={palette.muted}>
                  {formatEur(entry.cost, locale, { compact: true })}
                </text>
                <rect
                  x={acceptanceX}
                  y={y}
                  width={acceptanceWidth}
                  height={16}
                  fill={palette.line}
                  rx={2}
                />
                <rect
                  x={acceptanceX}
                  y={y}
                  width={Math.max(1, acceptanceScale(entry.acceptance))}
                  height={16}
                  fill={acceptanceColor}
                  rx={2}
                >
                  <title>{formatPercent(entry.acceptance, locale, 0)}</title>
                </rect>
                <text
                  x={acceptanceX + acceptanceWidth + 6}
                  y={y + 12}
                  fontSize={9}
                  fill={palette.ink}
                >
                  {formatPercent(entry.acceptance, locale, 0)} ·{" "}
                  {enumLabel("feasibility", entry.feasibility.political, locale)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </ChartFrame>
  );
}
