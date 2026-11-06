"use client";

import { scaleBand, scaleLinear } from "d3-scale";
import { useId } from "react";

import { useSettings } from "@/components/providers";
import { ChartFrame } from "@/components/ui/chart-frame";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import type { Candidate } from "@/features/evidence/contracts";
import { niceMax, readChartPalette } from "@/lib/chart/encoding";
import { useChartWidth } from "@/lib/chart/use-width";
import { formatDecimal, truncateMiddle } from "@/lib/format";
import type { Locale } from "@/lib/i18n";

const LEFT = 96;
const RIGHT = 64;
const ROW = 30;

const COMPONENTS = [
  { key: "authority", label: "evidence.authority", tone: "info" },
  { key: "lexical", label: "evidence.lexical", tone: "ink" },
  { key: "semantic", label: "evidence.semantic", tone: "accent" },
  { key: "recency", label: "evidence.recency", tone: "warn" },
  { key: "directness", label: "evidence.directness", tone: "ok" },
] as const;

export function ScoreDecompositionChart({
  candidates,
  locale,
}: {
  readonly candidates: readonly Candidate[];
  readonly locale: Locale;
}) {
  const { t } = useSettings();
  const palette = readChartPalette();
  const prefix = useId().replace(/:/g, "");
  const { ref, width: measured } = useChartWidth(760);
  const width = Math.max(420, measured);
  const visible = candidates.slice(0, 12);
  const totals = visible.map((candidate) =>
    COMPONENTS.reduce((sum, component) => sum + candidate.score[component.key], 0),
  );
  const max = niceMax([...totals, ...visible.map((candidate) => candidate.score.final)], 1);
  const x = scaleLinear().domain([0, max]).range([LEFT, width - RIGHT]);
  const y = scaleBand<string>()
    .domain(visible.map((candidate) => candidate.passage_id))
    .range([8, visible.length * ROW + 8])
    .paddingInner(0.28);
  const height = visible.length * ROW + 16;
  const toneColor: Record<string, string> = {
    info: palette.info,
    ink: palette.muted,
    accent: palette.accent,
    warn: palette.warn,
    ok: palette.ok,
  };

  return (
    <ChartFrame
      title={t("evidence.scores")}
      description={t("evidence.final")}
      table={
        <Table caption={t("evidence.scores")}>
          <THead>
            <TR>
              <TH>{t("evidence.passage")}</TH>
              {COMPONENTS.map((component) => (
                <TH key={component.key} className="text-right">
                  {t(component.label)}
                </TH>
              ))}
              <TH className="text-right">{t("evidence.final")}</TH>
            </TR>
          </THead>
          <TBody>
            {visible.map((candidate) => (
              <TR key={candidate.passage_id}>
                <TD className="font-mono text-2xs">{truncateMiddle(candidate.passage_id)}</TD>
                {COMPONENTS.map((component) => (
                  <TD key={component.key} className="text-right tabular">
                    {formatDecimal(String(candidate.score[component.key]), locale)}
                  </TD>
                ))}
                <TD className="text-right tabular font-semibold">
                  {formatDecimal(String(candidate.score.final), locale)}
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
          aria-label={t("evidence.scores")}
        >
          <title>{t("evidence.scores")}</title>
          <desc>{t("evidence.final")}</desc>
          <defs>
            {COMPONENTS.map((component, index) => (
              <pattern
                key={component.key}
                id={`${prefix}-${component.key}`}
                width="6"
                height="6"
                patternUnits="userSpaceOnUse"
                patternTransform={`rotate(${index * 20})`}
              >
                <rect width="6" height="6" fill={toneColor[component.tone]} fillOpacity={0.25} />
                <line
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="6"
                  stroke={toneColor[component.tone]}
                  strokeWidth={index % 2 === 0 ? 2 : 1}
                />
              </pattern>
            ))}
          </defs>
          {visible.map((candidate) => {
            const rowY = y(candidate.passage_id) ?? 0;
            const barHeight = Math.max(10, y.bandwidth());
            let offset = 0;
            return (
              <g key={candidate.passage_id}>
                <text
                  x={LEFT - 8}
                  y={rowY + barHeight / 2}
                  textAnchor="end"
                  dominantBaseline="middle"
                  fontSize={10}
                  fill={palette.ink}
                  fontFamily="monospace"
                >
                  {truncateMiddle(candidate.passage_id, 7, 5)}
                </text>
                {COMPONENTS.map((component) => {
                  const value = candidate.score[component.key];
                  const segment = Math.max(0, x(offset + value) - x(offset));
                  const start = x(offset);
                  offset += value;
                  return (
                    <rect
                      key={component.key}
                      x={start}
                      y={rowY}
                      width={segment}
                      height={barHeight}
                      fill={`url(#${prefix}-${component.key})`}
                      stroke={toneColor[component.tone]}
                      strokeOpacity={0.5}
                    >
                      <title>
                        {t(component.label)}: {formatDecimal(String(value), locale)}
                      </title>
                    </rect>
                  );
                })}
                <line
                  x1={x(candidate.score.final)}
                  x2={x(candidate.score.final)}
                  y1={rowY - 1}
                  y2={rowY + barHeight + 1}
                  stroke={palette.ink}
                  strokeWidth={2}
                />
                <text
                  x={Math.min(width - 4, x(candidate.score.final) + 4)}
                  y={rowY + barHeight / 2}
                  dominantBaseline="middle"
                  fontSize={10}
                  fill={palette.ink}
                  fontWeight={600}
                >
                  {formatDecimal(String(candidate.score.final), locale)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <ul className="mt-2 flex flex-wrap gap-3 text-2xs text-ink-muted">
        {COMPONENTS.map((component) => (
          <li key={component.key} className="flex items-center gap-1">
            <span
              aria-hidden="true"
              className="inline-block h-2.5 w-4 border"
              style={{
                backgroundColor: toneColor[component.tone],
                borderColor: toneColor[component.tone],
                opacity: 0.7,
              }}
            />
            {t(component.label)}
          </li>
        ))}
        <li>{t("evidence.final")}: ‖</li>
      </ul>
    </ChartFrame>
  );
}
