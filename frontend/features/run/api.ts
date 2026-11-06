import { request, requestVoid } from "@/lib/http";

import {
  AbstentionBodySchema,
  ArgumentResponseSchema,
  BindBodySchema,
  BindResponseSchema,
  CloseRoundBodySchema,
  CloseRoundResponseSchema,
  CoalitionBodySchema,
  CoalitionResponseSchema,
  ConflictListSchema,
  EventsResponseSchema,
  JobResponseSchema,
  OpenRoundBodySchema,
  OpenRoundResponseSchema,
  OpenRunBodySchema,
  OpenRunResponseSchema,
  PauseResumeBodySchema,
  PauseResumeResponseSchema,
  PositionBodySchema,
  PositionResponseSchema,
  ReviseBodySchema,
  RoundListSchema,
  RunResponseSchema,
  SelectionBodySchema,
  SelectionResponseSchema,
  StartBodySchema,
  StartResponseSchema,
  TurnBodySchema,
  UsageResponseSchema,
  type AbstentionBodyInput,
  type BindBody,
  type CloseRoundBody,
  type CoalitionBody,
  type OpenRunBody,
  type PauseResumeBody,
  type PositionBody,
  type ReviseBody,
  type SelectionBody,
  type StartBody,
  type TurnBody,
} from "./contracts";

export async function openRun(body: OpenRunBody, signal?: AbortSignal) {
  return request("/runs", {
    schema: OpenRunResponseSchema,
    method: "POST",
    body: OpenRunBodySchema.parse(body),
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function getRun(runId: string, signal?: AbortSignal) {
  return request(`/runs/${encodeURIComponent(runId)}`, {
    schema: RunResponseSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function getEvents(runId: string, untilRound?: number, signal?: AbortSignal) {
  const query = untilRound === undefined ? "" : `?until_round=${untilRound}`;
  return request(`/runs/${encodeURIComponent(runId)}/events${query}`, {
    schema: EventsResponseSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function getRounds(runId: string, signal?: AbortSignal) {
  return request(`/runs/${encodeURIComponent(runId)}/rounds`, {
    schema: RoundListSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function openRound(runId: string, round?: number) {
  return request(`/runs/${encodeURIComponent(runId)}/rounds`, {
    schema: OpenRoundResponseSchema,
    method: "POST",
    body: OpenRoundBodySchema.parse(round === undefined ? {} : { round }),
  });
}

export async function closeRound(runId: string, round: number, body: CloseRoundBody) {
  return request(`/runs/${encodeURIComponent(runId)}/rounds/${round}:close`, {
    schema: CloseRoundResponseSchema,
    method: "POST",
    body: CloseRoundBodySchema.parse(body),
  });
}

export async function submitPosition(runId: string, body: PositionBody) {
  return request(`/runs/${encodeURIComponent(runId)}/positions`, {
    schema: PositionResponseSchema,
    method: "POST",
    body: PositionBodySchema.parse(body),
  });
}

export async function takeTurn(runId: string, body: TurnBody) {
  return request(`/runs/${encodeURIComponent(runId)}/turns`, {
    schema: ArgumentResponseSchema,
    method: "POST",
    body: TurnBodySchema.parse(body),
  });
}

export async function recordAbstention(runId: string, body: AbstentionBodyInput) {
  return requestVoid(`/runs/${encodeURIComponent(runId)}/abstentions`, {
    method: "POST",
    body: AbstentionBodySchema.parse(body),
  });
}

export async function revisePosition(runId: string, positionId: string, body: ReviseBody) {
  return request(`/runs/${encodeURIComponent(runId)}/positions/${encodeURIComponent(positionId)}:revise`, {
    schema: PositionResponseSchema,
    method: "POST",
    body: ReviseBodySchema.parse(body),
  });
}

export async function getConflicts(runId: string, status?: string, signal?: AbortSignal) {
  const query = status === undefined ? "" : `?status=${encodeURIComponent(status)}`;
  return request(`/runs/${encodeURIComponent(runId)}/conflicts${query}`, {
    schema: ConflictListSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function formCoalition(runId: string, body: CoalitionBody) {
  return request(`/runs/${encodeURIComponent(runId)}/coalitions`, {
    schema: CoalitionResponseSchema,
    method: "POST",
    body: CoalitionBodySchema.parse(body),
  });
}

export async function selectStakeholders(runId: string, body: SelectionBody) {
  return request(`/runs/${encodeURIComponent(runId)}/stakeholders:select`, {
    schema: SelectionResponseSchema,
    method: "POST",
    body: SelectionBodySchema.parse(body),
  });
}

export async function bindStakeholders(runId: string, body: BindBody) {
  return request(`/runs/${encodeURIComponent(runId)}/stakeholders:bind`, {
    schema: BindResponseSchema,
    method: "POST",
    body: BindBodySchema.parse(body),
  });
}

export async function startRun(runId: string, body: StartBody) {
  return request(`/runs/${encodeURIComponent(runId)}:start`, {
    schema: StartResponseSchema,
    method: "POST",
    body: StartBodySchema.parse(body),
  });
}

export async function pauseRun(runId: string, body: PauseResumeBody) {
  return request(`/runs/${encodeURIComponent(runId)}:pause`, {
    schema: PauseResumeResponseSchema,
    method: "POST",
    body: PauseResumeBodySchema.parse({ ...body, action: "pause" }),
  });
}

export async function resumeRun(runId: string, body: PauseResumeBody) {
  return request(`/runs/${encodeURIComponent(runId)}:resume`, {
    schema: PauseResumeResponseSchema,
    method: "POST",
    body: PauseResumeBodySchema.parse({ ...body, action: "resume" }),
  });
}

export async function getUsage(runId: string, signal?: AbortSignal) {
  return request(`/runs/${encodeURIComponent(runId)}/usage`, {
    schema: UsageResponseSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}

export async function getJob(jobId: string, signal?: AbortSignal) {
  return request(`/jobs/${encodeURIComponent(jobId)}`, {
    schema: JobResponseSchema,
    ...(signal === undefined ? {} : { signal }),
  });
}
