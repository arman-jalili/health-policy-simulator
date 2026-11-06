"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  checkText,
  discloseProvenance,
  getAllowlist,
  getProvenance,
  listViolations,
} from "./api";
import type { DiscloseProvenanceBody, GuardCheckBody } from "./contracts";

export function useViolations(filter: {
  readonly runId?: string;
  readonly violationClass?: string;
  readonly limit?: number;
}) {
  return useQuery({
    queryKey: [
      "governance",
      "violations",
      filter.runId ?? "all",
      filter.violationClass ?? "all",
      filter.limit ?? 50,
    ],
    queryFn: ({ signal }) => listViolations(filter, signal),
  });
}

export function useAllowlist() {
  return useQuery({
    queryKey: ["governance", "allowlist"],
    queryFn: ({ signal }) => getAllowlist(signal),
  });
}

export function useCheckText() {
  return useMutation({
    mutationFn: (body: GuardCheckBody) => checkText(body),
  });
}

export function useProvenance(positionId: string, version?: number) {
  return useQuery({
    queryKey: ["governance", "provenance", positionId, version ?? "latest"],
    queryFn: ({ signal }) => getProvenance(positionId, version, signal),
    enabled: positionId !== "",
    retry: false,
  });
}

export function useDiscloseProvenance(positionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: DiscloseProvenanceBody) => discloseProvenance(positionId, body),
    onSuccess: (provenance) => {
      queryClient.setQueryData(
        ["governance", "provenance", positionId, "latest"],
        provenance,
      );
      void queryClient.invalidateQueries({ queryKey: ["governance", "provenance", positionId] });
    },
  });
}
