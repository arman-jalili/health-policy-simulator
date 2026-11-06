"use client";

import { scaleBand, scaleLinear } from "d3-scale";

import { useSettings } from "@/components/providers";
import { ChartFrame } from "@/components/ui/chart-frame";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import type { EventItem } from "@/features/run/contracts";
import { readChartPalette } from "@/lib/chart/encoding";
import { useChartWidth } from "@/lib/chart/use-width";
import { enumLabel, humanize } from "@/lib/i18n";

const LEFT = 130;
const TOP = 18;
const ROW = 28;

const MARKERS: Record<string, { shape: "square" | "circle" | "diamond" | "cross" | "triangle"; tone: "info" | "ok" | "warn" | "muted" | "danger" }> = {
  InitialPositionStated: { shape: "square", tone: "info" },
  PositionRevised: { shape: "diamond", tone: "warn" },
  PositionRevisionRejected: { shape: "triangle", tone: "danger" },
  ArgumentSubmitted: { shape: "circle", tone: "ok" },
  AbstentionRecorded: { shape: "cross", tone: "muted" },
};

function Marker({
  shape,
  color,
  x,
  y,
  label,
}: {
  readonly shape: string;
  readonly color: string;
  readonly x: number;
  readonly y: number;
  readonly label: string;
}) {
  const size = 5;
  if (shape === "square") {
    return <rect x={x - size} y={y - size} width={size * 2} height={size * 2} fill={color} rx={1}><title>{label}</title></rect>;
  }
  if (shape === "diamond") {
    return <path d={`M${x} ${y - size - 1}L${x + size + 1} ${y}L${x} ${y + size + 1}L${x - size - 1} ${y}Z`} fill={color}><title>{label}</title></path>;
  }
  if (shape === "triangle") {
    return <path d={`M${x} ${y - size - 1}L${x + size + 1} ${y + size}L${x - size - 1} ${y + size}Z`} fill={color}><title>{label}</title></path>;
  }
  if (shape === "cross") {
    return (
      <g stroke={color} strokeWidth={2}>
        <line x1={x - size} y1={y - size} x2={x + size} y2={y + size}><title>{label}</title></line>
        <line x1={x - size} y1={y + size} x2={x + size} y2={y - size} />
      </g>
    );
  }
  return <circle cx={x} cy={y} r={size} fill={color}><title>{label}</title></circle>;
}

export function RoundTimeline({
  events,
  round,
  stakeholderIds,
  stakeholderNames,
  blocked,
}: {
  readonly events: readonly EventItem[];
  readonly round: number;
  readonly stakeholderIds: readonly string[];
  readonly stakeholderNames: ReadonlyMap<string, string>;
  readonly blocked: readonly string[];
}) {
  const { t, locale } = useSettings();
  const palette = readChartPalette();
  const { ref, width: measured } = useChartWidth(760);
  const width = Math.max(420, measured);
  const height = TOP + stakeholderIds.length * ROW + 12;
  const inRound = events.filter((event) => {
    const value = event.payload["round"];
    return typeof value === "number" ? value === round : false;
  });
  const sequences = inRound.map((event) => event.sequence);
  const min = sequences.length === 0 ? 0 : Math.min(...sequences);
  const max = sequences.length === 0 ? 1 : Math.max(...sequences);
  const x = scaleLinear()
    .domain([min, max === min ? min + 1 : max])
    .range([LEFT, width - 20]);
  const y = scaleBand<string>()
    .domain(stakeholderIds)
    .range([TOP, TOP + stakeholderIds.length * ROW]);
  const toneColor: Record<string, string> = {
    info: palette.info,
    ok: palette.ok,
    warn: palette.warn,
    muted: palette.muted,
    danger: palette.danger,
  };
  const blockedSet = new Set(blocked);

  return (
    <ChartFrame
      title={t("console.timeline")}
      description={t("console.turnOrder")}
      table={
        <Table caption={t("console.timeline")}>
          <THead>
            <TR>
              <TH className="text-right">#</TH>
              <TH>{t("console.feed")}</TH>
              <TH>{t("common.stakeholder")}</TH>
              <TH className="text-right">{t("common.round")}</TH>
            </TR>
          </THead>
          <TBody>
            {inRound.map((event) => (
              <TR key={event.sequence}>
                <TD className="text-right tabular">{event.sequence}</TD>
                <TD>{enumLabel("eventType", event.event_type, locale)}</TD>
                <TD>
                  {typeof event.payload["stakeholder_id"] === "string"
                    ? (stakeholderNames.get(event.payload["stakeholder_id"]) ?? event.payload["stakeholder_id"])
                    : humanize(event.event_type)}
                </TD>
                <TD className="text-right tabular">{round}</TD>
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
          aria-label={t("console.timeline")}
        >
          <title>{t("console.timeline")}</title>
          <desc>{t("console.turnOrder")}</desc>
          {stakeholderIds.map((id) => {
            const rowY = y(id) ?? 0;
            return (
              <g key={id}>
                {blockedSet.has(id) && (
                  <rect
                    x={LEFT}
                    y={rowY}
                    width={width - LEFT - 20}
                    height={ROW}
                    fill={palette.warn}
                    fillOpacity={0.1}
                  />
                )}
                <text
                  x={LEFT - 8}
                  y={rowY + ROW / 2}
                  textAnchor="end"
                  dominantBaseline="middle"
                  fontSize={10}
                  fill={palette.ink}
                >
                  {(stakeholderNames.get(id) ?? id).slice(0, 20)}
                </text>
                <line
                  x1={LEFT}
                  x2={width - 20}
                  y1={rowY + ROW / 2}
                  y2={rowY + ROW / 2}
                  stroke={palette.line}
                  strokeDasharray="2 3"
                />
              </g>
            );
          })}
          {inRound.map((event) => {
            const stakeholderId = event.payload["stakeholder_id"];
            if (typeof stakeholderId !== "string" || !y.domain().includes(stakeholderId)) return null;
            const marker = MARKERS[event.event_type];
            if (marker === undefined) return null;
            const rowY = (y(stakeholderId) ?? 0) + ROW / 2;
            return (
              <Marker
                key={event.sequence}
                shape={marker.shape}
                color={toneColor[marker.tone] ?? palette.muted}
                x={x(event.sequence)}
                y={rowY}
                label={`${enumLabel("eventType", event.event_type, locale)} · ${stakeholderNames.get(stakeholderId) ?? stakeholderId}`}
              />
            );
          })}
        </svg>
      </div>
    </ChartFrame>
  );
}
