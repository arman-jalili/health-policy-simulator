import type { EventItem } from "@/features/run/contracts";

export interface PositionView {
  readonly stakeholderId: string;
  readonly topic: string;
  readonly stance: string;
  readonly positionId: string;
  readonly round: number;
  readonly evidenceIds: readonly string[];
  readonly initialStance: string;
  readonly revisionDriver: string | null;
}

export interface ArgumentView {
  readonly argumentId: string;
  readonly stakeholderId: string;
  readonly topic: string;
  readonly stance: string;
  readonly round: number;
  readonly evidenceIds: readonly string[];
  readonly invocationId: string | null;
}

export interface CoalitionView {
  readonly coalitionId: string;
  readonly topic: string;
  readonly members: readonly string[];
  readonly proposalSummary: string;
  readonly round: number;
}

export type TurnStatus = "position" | "turn" | "abstention" | "pending";

function readString(payload: Record<string, unknown>, key: string): string | null {
  const value = payload[key];
  return typeof value === "string" ? value : null;
}

function readNumber(payload: Record<string, unknown>, key: string): number {
  const value = payload[key];
  return typeof value === "number" ? value : 0;
}

function readStringArray(payload: Record<string, unknown>, key: string): readonly string[] {
  const value = payload[key];
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

export function positionKey(stakeholderId: string, topic: string): string {
  return `${stakeholderId}\u0000${topic}`;
}

export function derivePositions(events: readonly EventItem[]): readonly PositionView[] {
  const map = new Map<string, PositionView>();
  for (const event of events) {
    const payload = event.payload;
    const stakeholderId = readString(payload, "stakeholder_id");
    const topic = readString(payload, "topic");
    if (stakeholderId === null || topic === null) continue;
    if (event.event_type === "InitialPositionStated") {
      const stance = readString(payload, "stance") ?? "support";
      map.set(positionKey(stakeholderId, topic), {
        stakeholderId,
        topic,
        stance,
        positionId: readString(payload, "position_id") ?? "",
        round: readNumber(payload, "round"),
        evidenceIds: readStringArray(payload, "evidence_ids"),
        initialStance: stance,
        revisionDriver: null,
      });
    } else if (event.event_type === "PositionRevised") {
      const key = positionKey(stakeholderId, topic);
      const existing = map.get(key);
      const toStance = readString(payload, "to_stance");
      if (existing === undefined || toStance === null) continue;
      map.set(key, {
        ...existing,
        stance: toStance,
        positionId: readString(payload, "position_id") ?? existing.positionId,
        round: readNumber(payload, "round"),
        revisionDriver: readString(payload, "driver"),
      });
    }
  }
  return [...map.values()].sort((a, b) => a.topic.localeCompare(b.topic));
}

export function deriveArguments(events: readonly EventItem[]): readonly ArgumentView[] {
  const items: ArgumentView[] = [];
  for (const event of events) {
    if (event.event_type !== "ArgumentSubmitted") continue;
    const payload = event.payload;
    const stakeholderId = readString(payload, "stakeholder_id");
    if (stakeholderId === null) continue;
    const target = payload["target"];
    const topic =
      typeof target === "object" && target !== null
        ? (readString(target as Record<string, unknown>, "topic") ?? "")
        : "";
    items.push({
      argumentId: readString(payload, "argument_id") ?? "",
      stakeholderId,
      topic,
      stance: readString(payload, "stance") ?? "support",
      round: readNumber(payload, "round"),
      evidenceIds: readStringArray(payload, "evidence_ids"),
      invocationId: readString(payload, "invocation_id"),
    });
  }
  return items;
}

export function deriveCoalitions(events: readonly EventItem[]): readonly CoalitionView[] {
  const items: CoalitionView[] = [];
  for (const event of events) {
    if (event.event_type !== "CoalitionFormed") continue;
    const payload = event.payload;
    const proposal = payload["proposal"];
    const summary =
      typeof proposal === "object" && proposal !== null
        ? (readString(proposal as Record<string, unknown>, "summary") ?? "")
        : "";
    items.push({
      coalitionId: readString(payload, "coalition_id") ?? "",
      topic: readString(payload, "topic") ?? "",
      members: readStringArray(payload, "members"),
      proposalSummary: summary,
      round: readNumber(payload, "round"),
    });
  }
  return items;
}

export function deriveTurnStatuses(
  events: readonly EventItem[],
  round: number,
  stakeholderIds: readonly string[],
): ReadonlyMap<string, TurnStatus> {
  const statuses = new Map<string, TurnStatus>();
  for (const id of stakeholderIds) statuses.set(id, "pending");
  for (const event of events) {
    const payload = event.payload;
    if (readNumber(payload, "round") !== round) continue;
    const stakeholderId = readString(payload, "stakeholder_id");
    if (stakeholderId === null || !statuses.has(stakeholderId)) continue;
    if (event.event_type === "ArgumentSubmitted") {
      statuses.set(stakeholderId, "turn");
    } else if (
      event.event_type === "InitialPositionStated" ||
      event.event_type === "PositionRevised"
    ) {
      if (statuses.get(stakeholderId) !== "turn") statuses.set(stakeholderId, "position");
    } else if (event.event_type === "AbstentionRecorded") {
      if (statuses.get(stakeholderId) !== "turn") statuses.set(stakeholderId, "abstention");
    }
  }
  return statuses;
}

export function unaccountedStakeholders(
  statuses: ReadonlyMap<string, TurnStatus>,
): readonly string[] {
  return [...statuses.entries()]
    .filter(([, status]) => status === "pending" || status === "position")
    .map(([id]) => id);
}

export function turnOrderForRound(
  events: readonly EventItem[],
  round: number,
  fallback: readonly string[],
): readonly string[] {
  for (const event of events) {
    if (event.event_type !== "RoundOpened") continue;
    if (readNumber(event.payload, "round") !== round) continue;
    const order = readStringArray(event.payload, "turn_order");
    if (order.length > 0) return order;
  }
  return fallback;
}

export function turnCounts(
  events: readonly EventItem[],
  round: number,
): ReadonlyMap<string, number> {
  const counts = new Map<string, number>();
  for (const event of events) {
    if (event.event_type !== "ArgumentSubmitted") continue;
    if (readNumber(event.payload, "round") !== round) continue;
    const stakeholderId = readString(event.payload, "stakeholder_id");
    if (stakeholderId === null) continue;
    counts.set(stakeholderId, (counts.get(stakeholderId) ?? 0) + 1);
  }
  return counts;
}

export function uniqueTopics(positions: readonly PositionView[]): readonly string[] {
  return [...new Set(positions.map((position) => position.topic))].sort((a, b) => a.localeCompare(b));
}
