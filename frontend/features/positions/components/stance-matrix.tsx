"use client";

import { scaleBand } from "d3-scale";

import { useSettings } from "@/components/providers";
import { ChartFrame } from "@/components/ui/chart-frame";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import type { PositionView } from "@/features/positions/derive";
import { positionKey } from "@/features/positions/derive";
import { readChartPalette, stanceColor, stanceSymbol } from "@/lib/chart/encoding";
import { useChartWidth } from "@/lib/chart/use-width";
import { enumLabel } from "@/lib/i18n";

const LEFT = 132;
const TOP = 74;
const ROW = 30;

export function StanceMatrix({
  positions,
  stakeholderIds,
  stakeholderNames,
  topics,
}: {
  readonly positions: readonly PositionView[];
  readonly stakeholderIds: readonly string[];
  readonly stakeholderNames: ReadonlyMap<string, string>;
  readonly topics: readonly string[];
}) {
  const { t, locale } = useSettings();
  const palette = readChartPalette();
  const { ref, width: measured } = useChartWidth(760);
  const width = Math.max(420, measured);
  const byKey = new Map(positions.map((position) => [positionKey(position.stakeholderId, position.topic), position]));
  const columnWidth = topics.length === 0 ? 0 : Math.max(28, (width - LEFT - 12) / topics.length);
  const height = TOP + stakeholderIds.length * ROW + 8;
  const columns = scaleBand<string>()
    .domain(topics)
    .range([LEFT, LEFT + columnWidth * topics.length]);
  const rows = scaleBand<string>().domain(stakeholderIds).range([TOP, TOP + stakeholderIds.length * ROW]);

  return (
    <ChartFrame
      title={t("positions.board")}
      description={t("positions.boardHint")}
      table={
        <Table caption={t("positions.board")}>
          <THead>
            <TR>
              <TH>{t("common.topic")}</TH>
              <TH>{t("common.stakeholder")}</TH>
              <TH>{t("common.stance")}</TH>
            </TR>
          </THead>
          <TBody>
            {positions.map((position) => (
              <TR key={`${position.stakeholderId}-${position.topic}`}>
                <TD>{position.topic}</TD>
                <TD>{stakeholderNames.get(position.stakeholderId) ?? position.stakeholderId}</TD>
                <TD>{enumLabel("stance", position.stance, locale)}</TD>
              </TR>
            ))}
            {positions.length === 0 && (
              <TR>
                <TD colSpan={3}>{t("positions.noPositions")}</TD>
              </TR>
            )}
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
          aria-label={t("positions.board")}
        >
          <title>{t("positions.board")}</title>
          <desc>{t("positions.boardHint")}</desc>
          {topics.map((topic) => {
            const x = (columns(topic) ?? 0) + columnWidth / 2;
            return (
              <text
                key={topic}
                x={x}
                y={TOP - 10}
                textAnchor="start"
                fontSize={11}
                fill={palette.ink}
                transform={`rotate(-35 ${x} ${TOP - 10})`}
              >
                {topic.length > 16 ? `${topic.slice(0, 15)}…` : topic}
              </text>
            );
          })}
          {stakeholderIds.map((stakeholderId) => {
            const y = rows(stakeholderId) ?? 0;
            return (
              <g key={stakeholderId}>
                <text
                  x={LEFT - 8}
                  y={y + ROW / 2}
                  textAnchor="end"
                  dominantBaseline="middle"
                  fontSize={11}
                  fill={palette.ink}
                >
                  {(stakeholderNames.get(stakeholderId) ?? stakeholderId).slice(0, 20)}
                </text>
                {topics.map((topic) => {
                  const position = byKey.get(positionKey(stakeholderId, topic));
                  const x = columns(topic) ?? 0;
                  const color = position === undefined ? palette.line : stanceColor(position.stance, palette);
                  return (
                    <g key={topic}>
                      <rect
                        x={x + 2}
                        y={y + 2}
                        width={Math.max(6, columnWidth - 4)}
                        height={ROW - 4}
                        rx={2}
                        fill={position === undefined ? palette.surface : color}
                        fillOpacity={position === undefined ? 1 : 0.16}
                        stroke={position === undefined ? palette.line : color}
                        strokeWidth={position === undefined ? 1 : 1.25}
                      >
                        <title>
                          {position === undefined
                            ? `${stakeholderNames.get(stakeholderId) ?? stakeholderId} · ${topic}: ${t("console.statusSilent")}`
                            : `${stakeholderNames.get(stakeholderId) ?? stakeholderId} · ${topic}: ${enumLabel("stance", position.stance, locale)} (${position.positionId})`}
                        </title>
                      </rect>
                      {position !== undefined && (
                        <text
                          x={x + columnWidth / 2}
                          y={y + ROW / 2}
                          textAnchor="middle"
                          dominantBaseline="middle"
                          fontSize={13}
                          fill={color}
                          aria-hidden="true"
                        >
                          {stanceSymbol(position.stance)}
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
      <ul className="mt-2 flex flex-wrap gap-3 text-2xs text-ink-muted">
        {["support", "oppose", "qualify", "conditional_accept", "abstain"].map((stance) => (
          <li key={stance} className="flex items-center gap-1">
            <span aria-hidden="true" style={{ color: stanceColor(stance, palette) }}>
              {stanceSymbol(stance)}
            </span>
            {enumLabel("stance", stance, locale)}
          </li>
        ))}
      </ul>
    </ChartFrame>
  );
}
