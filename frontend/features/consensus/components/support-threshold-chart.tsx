"use client";

import { scaleBand, scaleLinear } from "d3-scale";
import { format } from "d3-format";

import { useSettings } from "@/components/providers";
import { ChartFrame } from "@/components/ui/chart-frame";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import type { ConsensusRecord } from "@/features/consensus/contracts";
import { outcomeTone, readChartPalette } from "@/lib/chart/encoding";
import { useChartWidth } from "@/lib/chart/use-width";
import { formatPercent } from "@/lib/format";
import { enumLabel } from "@/lib/i18n";

const ROW_HEIGHT = 34;
const LABEL_WIDTH = 150;
const VALUE_WIDTH = 132;

export function SupportThresholdChart({ records }: { readonly records: readonly ConsensusRecord[] }) {
  const { t, locale } = useSettings();
  const palette = readChartPalette();
  const { ref, width: measured } = useChartWidth(760);
  const height = Math.max(80, records.length * ROW_HEIGHT + 16);
  const width = Math.max(420, measured);
  const plotWidth = width - LABEL_WIDTH - VALUE_WIDTH;
  const x = scaleLinear().domain([0, 1]).range([0, plotWidth]);
  const y = scaleBand<string>()
    .domain(records.map((record) => record.topic))
    .range([8, height - 8])
    .paddingInner(0.25);
  const toneColor: Record<string, string> = {
    ok: palette.ok,
    warn: palette.warn,
    veto: palette.veto,
    danger: palette.danger,
    info: palette.info,
    neutral: palette.muted,
  };

  return (
    <ChartFrame
      title={t("consensus.records")}
      description={t("consensus.support")}
      table={
        <Table caption={t("consensus.records")}>
          <THead>
            <TR>
              <TH>{t("common.topic")}</TH>
              <TH className="text-right">{t("consensus.support")}</TH>
              <TH className="text-right">{t("consensus.threshold")}</TH>
              <TH>{t("common.status")}</TH>
            </TR>
          </THead>
          <TBody>
            {records.map((record) => (
              <TR key={record.consensus_id}>
                <TD>{record.topic}</TD>
                <TD className="text-right tabular">{formatPercent(record.support, locale, 0)}</TD>
                <TD className="text-right tabular">{formatPercent(record.threshold, locale, 0)}</TD>
                <TD>{enumLabel("consensusOutcome", record.outcome, locale)}</TD>
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
          aria-label={t("consensus.records")}
        >
          <title>{t("consensus.records")}</title>
          <desc>{t("consensus.support")}</desc>
          {records.map((record) => {
            const rowY = y(record.topic) ?? 0;
            const barHeight = Math.max(10, y.bandwidth() * 0.55);
            const tone = outcomeTone(record.outcome);
            const color = toneColor[tone] ?? palette.muted;
            return (
              <g key={record.consensus_id}>
                <text
                  x={LABEL_WIDTH - 8}
                  y={rowY + y.bandwidth() / 2}
                  textAnchor="end"
                  dominantBaseline="middle"
                  fontSize={12}
                  fill={palette.ink}
                >
                  {record.topic.length > 22 ? `${record.topic.slice(0, 21)}…` : record.topic}
                </text>
                <rect
                  x={LABEL_WIDTH}
                  y={rowY + (y.bandwidth() - barHeight) / 2}
                  width={x(1)}
                  height={barHeight}
                  fill={palette.line}
                  rx={2}
                />
                <rect
                  x={LABEL_WIDTH}
                  y={rowY + (y.bandwidth() - barHeight) / 2}
                  width={Math.max(2, x(record.support))}
                  height={barHeight}
                  fill={color}
                  rx={2}
                />
                <line
                  x1={LABEL_WIDTH + x(record.threshold)}
                  x2={LABEL_WIDTH + x(record.threshold)}
                  y1={rowY + 2}
                  y2={rowY + y.bandwidth() - 2}
                  stroke={palette.ink}
                  strokeWidth={2}
                  strokeDasharray="3 2"
                />
                <text
                  x={LABEL_WIDTH + plotWidth + 8}
                  y={rowY + y.bandwidth() / 2}
                  dominantBaseline="middle"
                  fontSize={11}
                  fill={color}
                  fontWeight={600}
                >
                  {format(".0%")(record.support)} · {enumLabel("consensusOutcome", record.outcome, locale)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </ChartFrame>
  );
}
