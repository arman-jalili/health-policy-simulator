"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  citePowerSource,
  listHistory,
  listStakeholders,
  recordHistoricalPosition,
  registerStakeholder,
} from "./api";
import type {
  CitePowerSourceBody,
  HistoricalPositionBody,
  RegisterStakeholderBody,
} from "./contracts";

export function useStakeholders() {
  return useQuery({
    queryKey: ["stakeholders"],
    queryFn: ({ signal }) => listStakeholders(signal),
  });
}

export function useHistory(stakeholderId: string, usableOnly: boolean) {
  return useQuery({
    queryKey: ["history", stakeholderId, usableOnly],
    queryFn: ({ signal }) => listHistory(stakeholderId, usableOnly, signal),
    enabled: stakeholderId !== "",
  });
}

export function useRecordHistory(stakeholderId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: HistoricalPositionBody) => recordHistoricalPosition(stakeholderId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["history", stakeholderId] });
    },
  });
}

export function useCitePower(stakeholderId: string) {
  return useMutation({
    mutationFn: (body: CitePowerSourceBody) => citePowerSource(stakeholderId, body),
  });
}

export function useRegisterStakeholder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: RegisterStakeholderBody) => registerStakeholder(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["stakeholders"] });
    },
  });
}
