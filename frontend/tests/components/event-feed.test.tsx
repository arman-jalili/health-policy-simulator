import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Providers } from "@/components/providers";
import { EventFeed } from "@/features/run/components/event-feed";
import { StanceBadge } from "@/features/run/components/stance-badge";
import type { EventItem } from "@/features/run/contracts";

const events: EventItem[] = [
  {
    sequence: 1,
    event_type: "SimulationRunOpened",
    payload: { run_id: "run_1" },
    occurred_at: "2026-11-06T06:23:11.412Z",
  },
  {
    sequence: 2,
    event_type: "ArgumentSubmitted",
    payload: {
      run_id: "run_1",
      round: 1,
      argument_id: "arg_1",
      stakeholder_id: "stk_aerztekammer",
      stance: "support",
      topic: "Kassenstellen",
      target: { topic: "Kassenstellen" },
    },
    occurred_at: "2026-11-06T06:23:15.000Z",
  },
];

const names = new Map([["stk_aerztekammer", "Ärztekammer"]]);

describe("EventFeed", () => {
  it("renders known events newest first with a stakeholder name", () => {
    render(
      <Providers>
        <EventFeed events={events} names={names} />
      </Providers>,
    );
    const list = within(screen.getByTestId("event-feed-list"));
    expect(list.getByText("Argument eingebracht")).toBeInTheDocument();
    expect(list.getByText("Ärztekammer")).toBeInTheDocument();
    expect(list.getAllByText(/Kassenstellen/).length).toBeGreaterThan(0);
  });

  it("filters by event type", async () => {
    const user = userEvent.setup();
    render(
      <Providers>
        <EventFeed events={events} names={names} />
      </Providers>,
    );
    await user.selectOptions(screen.getByLabelText("Nach Ereignistyp filtern"), "SimulationRunOpened");
    const list = within(screen.getByTestId("event-feed-list"));
    expect(list.getByText("Verhandlung eröffnet")).toBeInTheDocument();
    expect(list.queryByText("Argument eingebracht")).not.toBeInTheDocument();
  });

  it("shows the raw payload in a collapsible detail", async () => {
    const user = userEvent.setup();
    render(
      <Providers>
        <EventFeed events={events} names={names} />
      </Providers>,
    );
    const summaries = screen.getAllByText("Details");
    const first = summaries[0];
    expect(first).toBeDefined();
    if (first !== undefined) await user.click(first);
    const list = within(screen.getByTestId("event-feed-list"));
    expect(list.getByText(/arg_1/)).toBeInTheDocument();
  });

  it("renders the stance badge with a symbol and a German label", () => {
    render(
      <Providers>
        <StanceBadge stance="support" />
      </Providers>,
    );
    expect(screen.getByText("Zustimmung")).toBeInTheDocument();
    expect(screen.getByText("▲")).toHaveAttribute("aria-hidden", "true");
  });
});
