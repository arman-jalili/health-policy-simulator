"use client";

import { useMemo, useState } from "react";

import { useSettings } from "@/components/providers";
import { CopyButton } from "@/components/ui/copy-button";
import { Select, controlClass } from "@/components/ui/field";
import { EmptyState } from "@/components/ui/states";
import { StanceBadge } from "@/features/run/components/stance-badge";
import type { EventItem } from "@/features/run/contracts";
import { formatRelative, truncateMiddle } from "@/lib/format";
import { enumLabel, humanize } from "@/lib/i18n";

const PAGE = 120;

function text(payload: Record<string, unknown>, key: string): string | null {
  const value = payload[key];
  return typeof value === "string" ? value : null;
}

function summary(
  payload: Record<string, unknown>,
  eventType: string,
  locale: "de-AT" | "en",
): string | null {
  const topic = text(payload, "topic");
  const stance = text(payload, "stance");
  const position = text(payload, "position_id");
  const argument = text(payload, "argument_id");
  if (stance !== null && topic !== null) return `${topic} · ${enumLabel("stance", stance, locale)}`;
  if (topic !== null) return topic;
  if (argument !== null) return argument;
  if (position !== null) return position;
  if (eventType === "SimulationRunClosed") {
    const condition = text(payload, "condition");
    return condition === null ? null : `condition: ${condition}`;
  }
  return null;
}

export function EventFeed({
  events,
  names,
}: {
  readonly events: readonly EventItem[];
  readonly names: ReadonlyMap<string, string>;
}) {
  const { t, locale } = useSettings();
  const [eventType, setEventType] = useState("all");
  const [stakeholderId, setStakeholderId] = useState("all");
  const [limit, setLimit] = useState(PAGE);

  const types = useMemo(() => {
    const unique = new Set(events.map((event) => event.event_type));
    return [...unique].sort((a, b) => a.localeCompare(b));
  }, [events]);

  const stakeholders = useMemo(() => {
    const unique = new Set<string>();
    for (const event of events) {
      const value = event.payload["stakeholder_id"];
      if (typeof value === "string") unique.add(value);
    }
    return [...unique];
  }, [events]);

  const filtered = useMemo(() => {
    const items = events.filter((event) => {
      if (eventType !== "all" && event.event_type !== eventType) return false;
      if (stakeholderId !== "all" && event.payload["stakeholder_id"] !== stakeholderId) return false;
      return true;
    });
    return items.slice().sort((a, b) => b.sequence - a.sequence);
  }, [events, eventType, stakeholderId]);

  const visible = filtered.slice(0, limit);
  const latest = visible[0];

  return (
    <section aria-labelledby="feed-heading" className="rounded-md border border-line bg-surface">
      <div className="border-b border-line px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="feed-heading" className="text-base font-semibold">
            {t("console.feed")}
          </h2>
          <span className="text-2xs text-ink-muted">
            {latest === undefined
              ? t("console.feedEmpty")
              : formatRelative(latest.occurred_at ?? null, locale)}
          </span>
        </div>
        <div className="mt-2 flex flex-wrap items-end gap-2">
          <div>
            <label htmlFor="feed-type" className="sr-only">
              {t("console.filter")}
            </label>
            <Select
              id="feed-type"
              value={eventType}
              onChange={(event) => {
                setEventType(event.target.value);
                setLimit(PAGE);
              }}
              className="h-8"
            >
              <option value="all">{t("console.allEvents")}</option>
              {types.map((type) => (
                <option key={type} value={type}>
                  {enumLabel("eventType", type, locale) === humanize(type)
                    ? type
                    : enumLabel("eventType", type, locale)}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <label htmlFor="feed-stakeholder" className="sr-only">
              {t("console.filterStakeholder")}
            </label>
            <Select
              id="feed-stakeholder"
              value={stakeholderId}
              onChange={(event) => {
                setStakeholderId(event.target.value);
                setLimit(PAGE);
              }}
              className="h-8"
            >
              <option value="all">{t("console.allStakeholders")}</option>
              {stakeholders.map((id) => (
                <option key={id} value={id}>
                  {names.get(id) ?? id}
                </option>
              ))}
            </Select>
          </div>
          <span aria-live="polite" className="sr-only">
            {t("console.feedAnnounce", { count: filtered.length })}
          </span>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="p-4">
          <EmptyState title={t("console.feedEmpty")} />
        </div>
      ) : (
        <ol data-testid="event-feed-list" className="divide-y divide-line" style={{ contain: "content" }}>
          {visible.map((event) => {
            const holder = event.payload["stakeholder_id"];
            const holderName = typeof holder === "string" ? (names.get(holder) ?? holder) : null;
            const stance = text(event.payload, "stance");
            const eventSummary = summary(event.payload, event.event_type, locale);
            return (
              <li key={event.sequence} className="px-4 py-2.5" style={{ contentVisibility: "auto" }}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium">
                      {enumLabel("eventType", event.event_type, locale) === humanize(event.event_type)
                        ? event.event_type
                        : enumLabel("eventType", event.event_type, locale)}
                    </p>
                    <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-2xs text-ink-muted">
                      <span className="font-mono">#{event.sequence}</span>
                      {holderName !== null && <span>{holderName}</span>}
                      {typeof event.payload["round"] === "number" && (
                        <span>{t("console.eventRound", { round: event.payload["round"] })}</span>
                      )}
                      {eventSummary !== null && <span>{eventSummary}</span>}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {stance !== null && <StanceBadge stance={stance} />}
                    <span className="text-2xs text-ink-subtle">
                      {formatRelative(event.occurred_at ?? null, locale)}
                    </span>
                  </div>
                </div>
                <details className="mt-1.5">
                  <summary className="cursor-pointer text-2xs text-ink-subtle">
                    {t("common.details")}
                  </summary>
                  <div className="mt-1 rounded-xs border border-line bg-surface-muted p-2">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <span className="font-mono text-2xs text-ink-muted">
                        {truncateMiddle(event.event_type, 30, 0)}
                      </span>
                      <CopyButton value={JSON.stringify(event.payload, null, 2)} />
                    </div>
                    <pre className="max-h-48 overflow-auto font-mono text-2xs text-ink">
                      {JSON.stringify(event.payload, null, 2)}
                    </pre>
                  </div>
                </details>
              </li>
            );
          })}
        </ol>
      )}
      {filtered.length > visible.length && (
        <div className="border-t border-line px-4 py-2 text-center">
          <button
            type="button"
            className={`${controlClass} h-8 w-auto px-3 text-2xs`}
            onClick={() => setLimit((value) => value + PAGE)}
          >
            {t("console.showMore")} ({filtered.length - visible.length})
          </button>
        </div>
      )}
    </section>
  );
}
