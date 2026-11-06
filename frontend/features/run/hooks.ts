"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { useReadyz } from "@/features/platform/hooks";

import {
  loadRunIndex,
  loadSeed,
  updateRunInIndex,
  type DemoSeed,
  type RunIndexEntry,
} from "@/lib/settings";
import { openEventStream } from "@/lib/sse";

import {
  bindStakeholders,
  closeRound,
  formCoalition,
  getConflicts,
  getEvents,
  getRounds,
  getRun,
  getUsage,
  openRound,
  openRun,
  pauseRun,
  recordAbstention,
  resumeRun,
  revisePosition,
  selectStakeholders,
  startRun,
  submitPosition,
  takeTurn,
} from "./api";
import type {
  AbstentionBodyInput,
  BindBody,
  CloseRoundBody,
  CoalitionBody,
  EventItem,
  OpenRunBody,
  PauseResumeBody,
  PositionBody,
  ReviseBody,
  RunResponse,
  SelectionBody,
  StartBody,
  TurnBody,
} from "./contracts";

export type PollMode = "live" | "idle" | "closed" | "error";

export interface RunFeed {
  readonly events: readonly EventItem[];
  readonly state: RunResponse | null;
  readonly error: unknown;
  readonly isLoading: boolean;
  readonly pollMode: PollMode;
  readonly refetch: () => void;
}

export function useRun(runId: string) {
  return useQuery({
    queryKey: ["run", runId],
    queryFn: ({ signal }) => getRun(runId, signal),
    enabled: runId !== "",
  });
}

export function useRounds(runId: string) {
  return useQuery({
    queryKey: ["run", runId, "rounds"],
    queryFn: ({ signal }) => getRounds(runId, signal),
    enabled: runId !== "",
  });
}

export function useConflicts(runId: string, status?: string) {
  return useQuery({
    queryKey: ["run", runId, "conflicts", status ?? "all"],
    queryFn: ({ signal }) => getConflicts(runId, status, signal),
    enabled: runId !== "",
  });
}

export interface RunDriver {
  readonly automated: boolean;
  readonly scripted: boolean;
  readonly known: boolean;
}

export function useRunDriver(runId: string): RunDriver {
  const localRuns = useLocalRuns();
  const readyz = useReadyz();
  const usage = useQuery({
    queryKey: ["run", runId, "usage"],
    queryFn: ({ signal }) => getUsage(runId, signal),
    enabled: runId !== "",
    refetchInterval: 10_000,
  });
  const entry = localRuns.find((item) => item.runId === runId);
  const invoked = usage.data?.by_stakeholder.filter((item) => item.invocations >= 1) ?? [];
  const automated =
    entry?.driver === "automated" ||
    (entry?.driver !== "manual" && invoked.length >= 9);
  const known = entry?.driver !== undefined || usage.data !== undefined;
  return {
    automated,
    scripted: readyz.data?.checks["llm"] === "scripted",
    known,
  };
}

export function useRunFeed(runId: string): RunFeed {
  const queryClient = useQueryClient();
  const [events, setEvents] = useState<readonly EventItem[]>([]);
  const [state, setState] = useState<RunResponse | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [pollMode, setPollMode] = useState<PollMode>("live");
  const [nonce, setNonce] = useState(0);
  const previousCount = useRef(0);
  const idleTicks = useRef(0);

  useEffect(() => {
    if (runId === "") return;
    let cancelled = false;
    let polling = false;
    let streamClosed = false;
    const controller = new AbortController();
    let timer: number | undefined;
    let closeStream: (() => void) | undefined;
    previousCount.current = 0;
    idleTicks.current = 0;
    setEvents([]);
    setError(null);
    setIsLoading(true);
    setPollMode("live");

    const mergeEvent = (incoming: EventItem): void => {
      setEvents((current) => {
        const bySequence = new Map(current.map((item) => [item.sequence, item]));
        bySequence.set(incoming.sequence, incoming);
        return [...bySequence.values()].sort((a, b) => a.sequence - b.sequence);
      });
    };

    const refreshState = async (): Promise<void> => {
      try {
        const latest = await getRun(runId, controller.signal);
        if (cancelled) return;
        setState(latest);
        queryClient.setQueryData(["run", runId], latest);
        if (latest.closed) {
          setPollMode("closed");
          closeStream?.();
        }
      } catch {
        // the stream remains the primary signal; the next frame retries the snapshot
      }
    };

    const schedule = (delay: number): void => {
      if (cancelled) return;
      timer = window.setTimeout(() => {
        void tick();
      }, delay);
    };

    const tick = async (): Promise<void> => {
      if (cancelled) return;
      try {
        const data = await getEvents(runId, undefined, controller.signal);
        if (cancelled) return;
        const ordered = [...data.items].sort((a, b) => a.sequence - b.sequence);
        setEvents(ordered);
        setState(data.state);
        setIsLoading(false);
        setError(null);
        queryClient.setQueryData(["run", runId], data.state);
        const grew = ordered.length > previousCount.current;
        previousCount.current = ordered.length;
        idleTicks.current = grew ? 0 : idleTicks.current + 1;
        if (data.state.closed) {
          setPollMode("closed");
          return;
        }
        const idle = idleTicks.current >= 5;
        setPollMode(idle ? "idle" : "live");
        schedule(idle ? 3000 : 750);
      } catch (caught) {
        if (cancelled) return;
        setIsLoading(false);
        setError(caught);
        setPollMode("error");
        schedule(3000);
      }
    };

    const startPolling = (): void => {
      if (cancelled || polling) return;
      polling = true;
      setPollMode("live");
      void tick();
    };

    const startStream = (lastEventId: string | undefined): void => {
      closeStream = openEventStream(`/runs/${encodeURIComponent(runId)}/negotiation/stream`, {
        ...(lastEventId === undefined ? {} : { lastEventId }),
        signal: controller.signal,
        onFrame: (frame) => {
          if (cancelled) return;
          try {
            const payload = JSON.parse(frame.data) as unknown;
            if (payload === null || typeof payload !== "object" || Array.isArray(payload)) return;
            const sequence = Number(frame.id);
            const event: EventItem = {
              sequence: Number.isFinite(sequence) && sequence > 0 ? sequence : previousCount.current + 1,
              event_type: frame.event,
              payload: payload as Record<string, unknown>,
              occurred_at: null,
            };
            previousCount.current = Math.max(previousCount.current + 1, event.sequence);
            mergeEvent(event);
            setIsLoading(false);
            setError(null);
            setPollMode("live");
            void refreshState();
          } catch {
            // malformed frame: skip it, never drop the rest of the stream
          }
        },
        onError: () => {
          if (cancelled) return;
          setPollMode("idle");
          startPolling();
        },
        onClose: () => {
          if (cancelled || streamClosed) return;
          streamClosed = true;
          startPolling();
        },
      });
    };

    const initialize = async (): Promise<void> => {
      try {
        const data = await getEvents(runId, undefined, controller.signal);
        if (cancelled) return;
        const ordered = [...data.items].sort((a, b) => a.sequence - b.sequence);
        setEvents(ordered);
        setState(data.state);
        setIsLoading(false);
        setError(null);
        queryClient.setQueryData(["run", runId], data.state);
        previousCount.current = ordered.length;
        if (data.state.closed) {
          setPollMode("closed");
          return;
        }
        const last = ordered.at(-1)?.sequence;
        startStream(last === undefined ? undefined : String(last));
      } catch (caught) {
        if (cancelled) return;
        setIsLoading(false);
        setError(caught);
        setPollMode("error");
        startPolling();
      }
    };

    void initialize();
    return () => {
      cancelled = true;
      controller.abort();
      closeStream?.();
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [runId, nonce, queryClient]);

  return {
    events,
    state,
    error,
    isLoading,
    pollMode,
    refetch: () => setNonce((value) => value + 1),
  };
}

function useInvalidateRun(runId: string, extra: readonly string[] = []) {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["run", runId] }),
      ...extra.map((key) => queryClient.invalidateQueries({ queryKey: ["run", runId, key] })),
    ]);
}

export function useOpenRun() {
  return useMutation({
    mutationFn: (body: OpenRunBody) => openRun(body),
  });
}

export function useOpenRound(runId: string) {
  const invalidate = useInvalidateRun(runId, ["rounds"]);
  return useMutation({
    mutationFn: (round?: number) => openRound(runId, round),
    onSuccess: () => void invalidate(),
  });
}

export function useCloseRound(runId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { readonly round: number; readonly body: CloseRoundBody }) =>
      closeRound(runId, input.round, input.body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["run", runId] });
      void queryClient.invalidateQueries({ queryKey: ["run", runId, "rounds"] });
      void queryClient.invalidateQueries({ queryKey: ["run", runId, "consensus"] });
      void queryClient.invalidateQueries({ queryKey: ["run", runId, "conflicts"] });
    },
  });
}

export function useSubmitPosition(runId: string) {
  const invalidate = useInvalidateRun(runId, ["conflicts"]);
  return useMutation({
    mutationFn: (body: PositionBody) => submitPosition(runId, body),
    onSuccess: () => void invalidate(),
  });
}

export function useTakeTurn(runId: string) {
  const invalidate = useInvalidateRun(runId, ["rounds", "conflicts"]);
  return useMutation({
    mutationFn: (body: TurnBody) => takeTurn(runId, body),
    onSuccess: () => void invalidate(),
  });
}

export function useRecordAbstention(runId: string) {
  const invalidate = useInvalidateRun(runId, ["rounds"]);
  return useMutation({
    mutationFn: (body: AbstentionBodyInput) => recordAbstention(runId, body),
    onSuccess: () => void invalidate(),
  });
}

export function useRevisePosition(runId: string) {
  const invalidate = useInvalidateRun(runId, ["conflicts"]);
  return useMutation({
    mutationFn: (input: { readonly positionId: string; readonly body: ReviseBody }) =>
      revisePosition(runId, input.positionId, input.body),
    onSuccess: () => void invalidate(),
  });
}

export function useFormCoalition(runId: string) {
  const invalidate = useInvalidateRun(runId);
  return useMutation({
    mutationFn: (body: CoalitionBody) => formCoalition(runId, body),
    onSuccess: () => void invalidate(),
  });
}

export function useSelectStakeholders(runId: string) {
  const invalidate = useInvalidateRun(runId);
  return useMutation({
    mutationFn: (body: SelectionBody) => selectStakeholders(runId, body),
    onSuccess: () => void invalidate(),
  });
}

export function useBindStakeholders(runId: string) {
  const invalidate = useInvalidateRun(runId);
  return useMutation({
    mutationFn: (body: BindBody) => bindStakeholders(runId, body),
    onSuccess: () => void invalidate(),
  });
}

export function useStartRun(runId: string) {
  const invalidate = useInvalidateRun(runId, ["usage"]);
  return useMutation({
    mutationFn: (body: StartBody) => startRun(runId, body),
    onSuccess: () => {
      updateRunInIndex(runId, { driver: "automated" });
      void invalidate();
    },
  });
}

export function usePauseRun(runId: string) {
  const invalidate = useInvalidateRun(runId, ["usage"]);
  return useMutation({
    mutationFn: (body: PauseResumeBody) => pauseRun(runId, body),
    onSuccess: () => void invalidate(),
  });
}

export function useResumeRun(runId: string) {
  const invalidate = useInvalidateRun(runId, ["usage"]);
  return useMutation({
    mutationFn: (body: PauseResumeBody) => resumeRun(runId, body),
    onSuccess: () => void invalidate(),
  });
}

export function useSeed(): DemoSeed | null {
  const [seed, setSeed] = useState<DemoSeed | null>(null);
  useEffect(() => {
    const sync = (): void => setSeed(loadSeed());
    sync();
    window.addEventListener("hps:seed", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("hps:seed", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  return seed;
}

export function useLocalRuns(): readonly RunIndexEntry[] {
  const [runs, setRuns] = useState<readonly RunIndexEntry[]>([]);
  useEffect(() => {
    const sync = (): void => setRuns(loadRunIndex());
    sync();
    window.addEventListener("hps:runs", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("hps:runs", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  return runs;
}
