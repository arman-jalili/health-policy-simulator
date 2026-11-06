"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getHealth, getLlmProvider, getReadyz, headOpenApi, selectLlmProvider } from "./api";

export function useReadyz() {
  return useQuery({
    queryKey: ["readyz"],
    queryFn: ({ signal }) => getReadyz(signal),
    refetchInterval: 30_000,
  });
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => getHealth(signal),
    refetchInterval: 30_000,
  });
}

export function useOpenApiHead() {
  return useQuery({
    queryKey: ["openapi", "head"],
    queryFn: ({ signal }) => headOpenApi(signal),
    refetchInterval: 60_000,
  });
}

export function useLlmProvider() {
  return useQuery({
    queryKey: ["llm-provider"],
    queryFn: ({ signal }) => getLlmProvider(signal),
    refetchInterval: 30_000,
  });
}

export function useSelectLlmProvider() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (provider: string) => selectLlmProvider(provider),
    onSuccess: () => {
      // readiness reports the active backend, so the overview pill must refresh with it
      void queryClient.invalidateQueries({ queryKey: ["llm-provider"] });
      void queryClient.invalidateQueries({ queryKey: ["readyz"] });
    },
  });
}
