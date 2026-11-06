"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getIngestionRun,
  getSnapshot,
  ingestDocument,
  pinSnapshot,
  publishDocument,
  startIngestionRun,
} from "./api";
import type { IngestDocumentBody, PinSnapshotBody, StartIngestionRunBody } from "./contracts";

export function useIngestionRun(runId: string) {
  return useQuery({
    queryKey: ["corpus", "ingestion-run", runId],
    queryFn: ({ signal }) => getIngestionRun(runId, signal),
    enabled: runId !== "",
    refetchInterval: (query) => (query.state.data?.status === "running" ? 2_000 : false),
  });
}

export function useSnapshotDetails(snapshotId: string) {
  return useQuery({
    queryKey: ["corpus", "snapshot", snapshotId],
    queryFn: ({ signal }) => getSnapshot(snapshotId, signal),
    enabled: snapshotId !== "",
  });
}

export function useStartIngestionRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: StartIngestionRunBody) => startIngestionRun(body),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["corpus", "ingestion-run", result.run_id] });
      void queryClient.invalidateQueries({ queryKey: ["readyz"] });
    },
  });
}

export function usePinSnapshot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PinSnapshotBody) => pinSnapshot(body),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["corpus", "snapshot", result.snapshot_id] });
    },
  });
}

export function useIngestDocument() {
  return useMutation({
    mutationFn: (body: IngestDocumentBody) => ingestDocument(body),
  });
}

export function usePublishDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => publishDocument(documentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["readyz"] });
    },
  });
}
