"use client";

import { useQuery } from "@tanstack/react-query";

import { getHealth, getReadyz, headOpenApi } from "./api";

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
