import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getRun } from "@/features/run/api";
import { useRunFeed } from "@/features/run/hooks";
import { ApiError } from "@/lib/http";

const runState = {
  run_id: "run_1",
  phase: "position_formation",
  round: 1,
  round_cap: 2,
  closed: true,
  bound_stakeholder_ids: ["stk_aerztekammer"],
  open_position_ids: ["pos_1"],
  coalition_ids: [],
};

const eventsBody = {
  items: [
    {
      sequence: 1,
      event_type: "SimulationRunOpened",
      payload: { run_id: "run_1" },
      occurred_at: "2026-11-06T06:23:11.412Z",
    },
  ],
  state: runState,
};

function okResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

function wrapper(client: QueryClient) {
  return function Wrapper({ children }: { readonly children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe("useRunFeed", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async () => okResponse(eventsBody)));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads the event log and stops on a closed run", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result, unmount } = renderHook(() => useRunFeed("run_1"), {
      wrapper: wrapper(client),
    });

    await waitFor(() => expect(result.current.events).toHaveLength(1));
    expect(result.current.state?.closed).toBe(true);
    expect(result.current.pollMode).toBe("closed");
    expect(result.current.isLoading).toBe(false);
    unmount();
  });

  it("reports a contract mismatch when the payload is invalid", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => okResponse({ items: [{ sequence: "one" }], state: {} })),
    );
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result, unmount } = renderHook(() => useRunFeed("run_1"), {
      wrapper: wrapper(client),
    });

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error).toBeInstanceOf(ApiError);
    if (result.current.error instanceof ApiError) {
      expect(result.current.error.code).toBe("CONTRACT_MISMATCH");
    }
    unmount();
  });

  it("maps an error envelope to a typed ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              code: "SIMULATION_RUN_NOT_FOUND",
              message: "no simulation run run_1",
              details: [],
              trace_id: "req_1",
            }),
            { status: 404, headers: { "content-type": "application/json" } },
          ),
      ),
    );
    await expect(getRun("run_1")).rejects.toMatchObject({
      status: 404,
      code: "SIMULATION_RUN_NOT_FOUND",
      traceId: "req_1",
    });
  });
});
