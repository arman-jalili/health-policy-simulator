"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createBriefVersion, getBrief, listBriefVersions, listCitations, publishBrief } from "./api";

export function useBriefVersions(runId: string) {
  return useQuery({
    queryKey: ["brief", "versions", runId],
    queryFn: ({ signal }) => listBriefVersions(runId, signal),
    enabled: runId !== "",
  });
}

export function useBrief(briefId: string) {
  return useQuery({
    queryKey: ["brief", briefId],
    queryFn: ({ signal }) => getBrief(briefId, signal),
    enabled: briefId !== "",
  });
}

export function useCitations(briefId: string, section?: string) {
  return useQuery({
    queryKey: ["brief", briefId, "citations", section ?? "all"],
    queryFn: ({ signal }) => listCitations(briefId, section, signal),
    enabled: briefId !== "",
  });
}

export function usePublishBrief(runId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => publishBrief(runId),
    onSuccess: (brief) => {
      queryClient.setQueryData(["brief", brief.brief_id], brief);
      void queryClient.invalidateQueries({ queryKey: ["brief", "versions", runId] });
    },
  });
}

export function useCreateBriefVersion(briefId: string, runId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reason: string) => createBriefVersion(briefId, reason),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["brief", "versions", runId] });
      void queryClient.invalidateQueries({ queryKey: ["brief", briefId] });
    },
  });
}
