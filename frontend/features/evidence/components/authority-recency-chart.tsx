"use client";

import { scaleLinear, scaleSqrt, scaleTime } from "d3-scale";

import { useSettings } from "@/components/providers";
import { ChartFrame } from "@/components/ui/chart-frame";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import type { Candidate } from "@/features/evidence/contracts";
import { readChartPalette } from "@/lib/chart/encoding";
import { useChartWidth } from "@/lib/chart/use-width";
import { formatDate, formatDecimal, truncateMiddle } from "@/lib/format";
import type { Locale } from "@/lib/i18n";

const LEFT = 52;
const RIGHT = 16;
const TOP = 12;
const BOTTOM = 34;

interface Point {
  readonly candidate: Candidate;
  readonly date: Date;
}

export function AuthorityRecencyChart({
  candidates,
  snippets,
  locale,
}: {
  readonly candidates: readonly Candidate[];
  readonly snippets?: ReadonlyMap<string, string>;
  readonly locale: Locale;
}) {
  const { t } = useSettings();
  const palette = readChartPalette();
  const { ref, width: measured } = useChartWidth(760);
  const width = Math.max(420, measured);
  const height = 220;
  const points: Point[] = [];
  for (const candidate of candidates) {
    const iso = candidate.provenance?.published_on;
    if (iso === undefined || iso === null) continue;
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) continue;
    points.push({ candidate, date });
  }

  const domain = points.length === 0
    ? [new Date(0), new Date(0)]
    : [new Date(Math.min(...points.map((point) => point.date.getTime()))), new Date(Math.max(...points.map((point) => point.date.getTime())))];
  const x = scaleTime()
    .domain(domain)
    .range([LEFT, width - RIGHT]);
  const y = scaleLinear().domain([0, 1]).range([height - BOTTOM, TOP]);
  const radius = scaleSqrt()
    .domain([0, Math.max(1, ...points.map((point) => point.candidate.score.final))])
    .range([3, 11]);

  return (
    <ChartFrame
      title={t("evidence.authority")}
      description={t("evidence.authorityApprox")}
      table={
        <Table caption={t("evidence.authority")}>
          <THead>
            <TR>
              <TH>{t("evidence.passage")}</TH>
              <TH>{t("evidence.provenance")}</TH>
              <TH className="text-right">{t("evidence.authority")}</TH>
              <TH className="text-right">{t("evidence.final")}</TH>
            </TR>
          </THead>
          <TBody>
            {candidates.map((candidate) => (
              <TR key={candidate.passage_id}>
                <TD className="font-mono text-2xs">{truncateMiddle(candidate.passage_id)}</TD>
                <TD>
                  {candidate.provenance === null
                    ? "—"
                    : `${candidate.provenance.outlet}, ${formatDate(candidate.provenance.published_on, locale)}`}
                </TD>
                <TD className="text-right tabular">
                  {formatDecimal(String(candidate.score.authority), locale)}
                </TD>
                <TD className="text-right tabular">
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
          aria-label={t("evidence.authority")}
        >
          <title>{t("evidence.authority")}</title>
          <desc>{t("evidence.authorityApprox")}</desc>
          <line x1={LEFT} x2={LEFT} y1={TOP} y2={height - BOTTOM} stroke={palette.line} />
          <line
            x1={LEFT}
            x2={width - RIGHT}
            y1={height - BOTTOM}
            y2={height - BOTTOM}
            stroke={palette.line}
          />
          {[0, 0.5, 1].map((tick) => (
            <g key={tick}>
              <line
                x1={LEFT}
                x2={width - RIGHT}
                y1={y(tick)}
                y2={y(tick)}
                stroke={palette.line}
                strokeDasharray="2 3"
              />
              <text x={LEFT - 6} y={y(tick)} textAnchor="end" dominantBaseline="middle" fontSize={9} fill={palette.muted}>
                {tick.toFixed(1)}
              </text>
            </g>
          ))}
          {points.length > 0 &&
            x.ticks(5).map((tick) => (
              <text
                key={tick.toISOString()}
                x={x(tick)}
                y={height - BOTTOM + 14}
                textAnchor="middle"
                fontSize={9}
                fill={palette.muted}
              >
                {formatDate(tick.toISOString(), locale)}
              </text>
            ))}
          {points.map((point) => {
            const snippet = snippets?.get(point.candidate.passage_id) ?? "";
            const color =
              point.candidate.stance === "contradicting"
                ? palette.danger
                : point.candidate.stance === "supporting"
                  ? palette.ok
                  : palette.muted;
            return (
              <g key={point.candidate.passage_id}>
                <circle
                  cx={x(point.date)}
                  cy={y(point.candidate.score.authority)}
                  r={radius(point.candidate.score.final)}
                  fill={color}
                  fillOpacity={0.22}
                  stroke={color}
                  strokeWidth={1.5}
                >
                  <title>
                    {`${point.candidate.provenance?.outlet ?? "—"} · ${formatDate(point.date.toISOString(), locale)} · ${t("evidence.authority")} ${formatDecimal(String(point.candidate.score.authority), locale)}${snippet === "" ? "" : ` · ${snippet.slice(0, 80)}`}`}
                  </title>
                </circle>
                <circle
                  cx={x(point.date)}
                  cy={y(point.candidate.score.authority)}
                  r={1.5}
                  fill={color}
                  aria-hidden="true"
                />
              </g>
            );
          })}
          {points.length === 0 && (
            <text x={width / 2} y={height / 2} textAnchor="middle" fontSize={11} fill={palette.muted}>
              {t("common.empty")}
            </text>
          )}
        </svg>
      </div>
    </ChartFrame>
  );
}
