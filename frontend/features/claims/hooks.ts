"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createReferenceFigure,
  flagClaim,
  getClaim,
  getContradictions,
  listReferenceFigures,
  reviewClaim,
  verifyClaim,
} from "./api";
import type { ReferenceFigureBody, VerifyClaimBody } from "./contracts";

export function useVerifyClaim() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: VerifyClaimBody) => verifyClaim(body),
    onSuccess: (verdict) => {
      queryClient.setQueryData(["claim", verdict.claim_id], verdict);
      void queryClient.invalidateQueries({ queryKey: ["claims", "contradictions"] });
    },
  });
}

export function useClaim(claimId: string) {
  return useQuery({
    queryKey: ["claim", claimId],
    queryFn: ({ signal }) => getClaim(claimId, signal),
    enabled: claimId !== "",
  });
}

export function useFlagClaim(claimId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reason: string) => flagClaim(claimId, reason),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["claim", claimId] });
    },
  });
}

export function useReviewClaim(claimId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { readonly verdict: string; readonly basis: string }) =>
      reviewClaim(claimId, input.verdict, input.basis),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["claim", claimId] });
    },
  });
}

export function useContradictions() {
  return useQuery({
    queryKey: ["claims", "contradictions"],
    queryFn: ({ signal }) => getContradictions(signal),
  });
}

export function useReferenceFigures() {
  return useQuery({
    queryKey: ["claims", "figures"],
    queryFn: ({ signal }) => listReferenceFigures(signal),
  });
}

export function useCreateReferenceFigure() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ReferenceFigureBody) => createReferenceFigure(body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["claims", "figures"] });
    },
  });
}
