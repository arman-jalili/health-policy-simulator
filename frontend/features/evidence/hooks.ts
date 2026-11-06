"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getPassage, getAuthorityRules } from "@/features/corpus/api";

import {
  assemblePack,
  getEvidencePack,
  getPackScores,
  reweightPack,
  searchCandidates,
} from "./api";
import type { AssemblePackBody, ReweightPackBody, SearchCandidatesBody } from "./contracts";

export function useEvidencePack(packId: string) {
  return useQuery({
    queryKey: ["evidence", "pack", packId],
    queryFn: ({ signal }) => getEvidencePack(packId, signal),
    enabled: packId !== "",
  });
}

export function usePackScores(packId: string) {
  return useQuery({
    queryKey: ["evidence", "scores", packId],
    queryFn: ({ signal }) => getPackScores(packId, signal),
    enabled: packId !== "",
  });
}

export function usePassage(passageId: string) {
  return useQuery({
    queryKey: ["passage", passageId],
    queryFn: ({ signal }) => getPassage(passageId, signal),
    enabled: passageId !== "",
  });
}

export function useAuthorityRules(claimType?: string) {
  return useQuery({
    queryKey: ["corpus", "authority-rules", claimType ?? "all"],
    queryFn: ({ signal }) => getAuthorityRules(claimType, signal),
  });
}

export function useSearchCandidates() {
  return useMutation({
    mutationFn: (body: SearchCandidatesBody) => searchCandidates(body),
  });
}

export function useAssemblePack() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: AssemblePackBody) => assemblePack(body),
    onSuccess: (pack) => {
      queryClient.setQueryData(["evidence", "pack", pack.pack_id], pack);
    },
  });
}

export function useReweightPack(packId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ReweightPackBody) => reweightPack(packId, body),
    onSuccess: (pack) => {
      queryClient.setQueryData(["evidence", "pack", pack.pack_id], pack);
      void queryClient.invalidateQueries({ queryKey: ["evidence", "scores", packId] });
    },
  });
}
