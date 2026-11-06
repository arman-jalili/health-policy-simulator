"use client";

import { useSettings } from "@/components/providers";
import { ChartFrame } from "@/components/ui/chart-frame";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import type { PositionView } from "@/features/positions/derive";
import { readChartPalette } from "@/lib/chart/encoding";
import { useChartWidth } from "@/lib/chart/use-width";
import { formatPercent } from "@/lib/format";

const LEFT = 120;
const TOP = 96;

function pairScore(a: string, b: string): number {
  if (a === b) return 1;
  const set = new Set([a, b]);
  if (set.has("support") && set.has("conditional_accept")) return 0.75;
  if (set.has("qualify") && set.has("conditional_accept")) return 0.5;
  if (set.has("support") && set.has("oppose")) return 0;
  return 0.25;
}

function agreement(
  a: readonly PositionView[],
  b: readonly PositionView[],
): number | null {
  const byTopic = new Map(a.map((position) => [position.topic, position.stance]));
  const shared = b.filter((position) => byTopic.has(position.topic));
  if (shared.length === 0) return null;
  const total = shared.reduce((sum, position) => {
    const other = byTopic.get(position.topic);
    return other === undefined ? sum : sum + pairScore(other, position.stance);
  }, 0);
  return total / shared.length;
}

export function AlignmentMatrix({
  positions,
  stakeholderIds,
  stakeholderNames,
}: {
  readonly positions: readonly PositionView[];
  readonly stakeholderIds: readonly string[];
  readonly stakeholderNames: ReadonlyMap<string, string>;
}) {
  const { t, locale } = useSettings();
  const palette = readChartPalette();
  const { ref, width: measured } = useChartWidth(760);
  const width = Math.max(420, measured);
  const cell = Math.max(26, Math.min(56, (width - LEFT - 8) / Math.max(1, stakeholderIds.length)));
  const height = TOP + stakeholderIds.length * cell;
  const byStakeholder = new Map<string, readonly PositionView[]>();
  for (const id of stakeholderIds) {
    byStakeholder.set(id, positions.filter((position) => position.stakeholderId === id));
  }
  const rows: { a: string; b: string; score: number }[] = [];
  for (const a of stakeholderIds) {
    for (const b of stakeholderIds) {
      if (a === b) continue;
      const score = agreement(byStakeholder.get(a) ?? [], byStakeholder.get(b) ?? []);
      if (score !== null) rows.push({ a, b, score });
    }
  }

  const colorFor = (score: number | null): string => {
    if (score === null) return palette.surface;
    const percent = Math.round(score * 100);
    return score >= 0.5
      ? `color-mix(in oklab, ${palette.ok} ${percent}%, ${palette.surface})`
      : `color-mix(in oklab, ${palette.danger} ${Math.round((1 - score) * 100)}%, ${palette.surface})`;
  };

  return (
    <ChartFrame
      title={t("positions.alignment")}
      table={
        <Table caption={t("positions.alignment")}>
          <THead>
            <TR>
              <TH>{t("common.stakeholder")}</TH>
              <TH>{t("common.stakeholder")}</TH>
              <TH className="text-right">{t("positions.alignment")}</TH>
            </TR>
          </THead>
          <TBody>
            {rows.map((row) => (
              <TR key={`${row.a}-${row.b}`}>
                <TD>{stakeholderNames.get(row.a) ?? row.a}</TD>
                <TD>{stakeholderNames.get(row.b) ?? row.b}</TD>
                <TD className="text-right tabular">{formatPercent(row.score, locale, 0)}</TD>
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
          aria-label={t("positions.alignment")}
        >
          <title>{t("positions.alignment")}</title>
          <desc>{t("positions.alignment")}</desc>
          {stakeholderIds.map((id, index) => {
            const x = LEFT + index * cell + cell / 2;
            const y = TOP - 8;
            return (
              <text
                key={`col-${id}`}
                x={x}
                y={y}
                fontSize={10}
                fill={palette.ink}
                textAnchor="start"
                transform={`rotate(-45 ${x} ${y})`}
              >
                {(stakeholderNames.get(id) ?? id).slice(0, 12)}
              </text>
            );
          })}
          {stakeholderIds.map((rowId, rowIndex) => {
            const y = TOP + rowIndex * cell;
            return (
              <g key={`row-${rowId}`}>
                <text
                  x={LEFT - 8}
                  y={y + cell / 2}
                  textAnchor="end"
                  dominantBaseline="middle"
                  fontSize={11}
                  fill={palette.ink}
                >
                  {(stakeholderNames.get(rowId) ?? rowId).slice(0, 18)}
                </text>
                {stakeholderIds.map((colId, colIndex) => {
                  const score =
                    rowId === colId
                      ? null
                      : agreement(byStakeholder.get(rowId) ?? [], byStakeholder.get(colId) ?? []);
                  return (
                    <g key={`${rowId}-${colId}`}>
                      <rect
                        x={LEFT + colIndex * cell + 1}
                        y={y + 1}
                        width={cell - 2}
                        height={cell - 2}
                        rx={2}
                        fill={rowId === colId ? palette.line : colorFor(score)}
                        stroke={palette.line}
                      >
                        <title>
                          {rowId === colId
                            ? "—"
                            : `${stakeholderNames.get(rowId) ?? rowId} · ${stakeholderNames.get(colId) ?? colId}: ${score === null ? "—" : formatPercent(score, locale, 0)}`}
                        </title>
                      </rect>
                      {score !== null && (
                        <text
                          x={LEFT + colIndex * cell + cell / 2}
                          y={y + cell / 2}
                          textAnchor="middle"
                          dominantBaseline="middle"
                          fontSize={9}
                          fill={palette.ink}
                          aria-hidden="true"
                        >
                          {Math.round(score * 100)}
                        </text>
                      )}
                    </g>
                  );
                })}
              </g>
            );
          })}
        </svg>
      </div>
    </ChartFrame>
  );
}
