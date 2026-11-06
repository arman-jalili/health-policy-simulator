"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  assessImpact,
  composePackage,
  deriveConsensus,
  getComparison,
  getConsensus,
  getOpenConflicts,
  listPackages,
} from "./api";
import type { AssessImpactBody, ComposePackageBody } from "./contracts";

export function useConsensus(runId: string) {
  return useQuery({
    queryKey: ["run", runId, "consensus"],
    queryFn: ({ signal }) => getConsensus(runId, signal),
    enabled: runId !== "",
  });
}

export function useOpenConflicts(runId: string) {
  return useQuery({
    queryKey: ["run", runId, "conflicts-open"],
    queryFn: ({ signal }) => getOpenConflicts(runId, signal),
    enabled: runId !== "",
  });
}

export function usePackages(runId: string) {
  return useQuery({
    queryKey: ["run", runId, "packages"],
    queryFn: ({ signal }) => listPackages(runId, signal),
    enabled: runId !== "",
  });
}

export function useComparison(packageId: string) {
  return useQuery({
    queryKey: ["package", packageId, "comparison"],
    queryFn: ({ signal }) => getComparison(packageId, signal),
    enabled: packageId !== "",
  });
}

export function useDeriveConsensus(runId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (topics: readonly string[]) => deriveConsensus(runId, topics),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["run", runId, "consensus"] });
      void queryClient.invalidateQueries({ queryKey: ["run", runId, "conflicts-open"] });
    },
  });
}

export function useComposePackage(runId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ComposePackageBody) => composePackage(runId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["run", runId, "packages"] });
    },
  });
}

export function useAssessImpact(packageId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: AssessImpactBody) => assessImpact(packageId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["package", packageId, "comparison"] });
    },
  });
}
