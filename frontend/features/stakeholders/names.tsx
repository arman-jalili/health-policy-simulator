"use client";

import { useMemo } from "react";

import { useStakeholders } from "./hooks";

export function useStakeholderNames(): ReadonlyMap<string, string> {
  const { data } = useStakeholders();
  return useMemo(() => {
    const map = new Map<string, string>();
    for (const item of data?.items ?? []) {
      map.set(item.stakeholder_id, item.identity.short_name);
    }
    return map;
  }, [data]);
}

export function StakeholderLabel({
  stakeholderId,
  full = false,
}: {
  readonly stakeholderId: string;
  readonly full?: boolean;
}) {
  const { data } = useStakeholders();
  const item = data?.items.find((entry) => entry.stakeholder_id === stakeholderId);
  const label = item === undefined ? stakeholderId : full ? item.identity.name : item.identity.short_name;
  return (
    <span title={stakeholderId} className="inline-block max-w-full truncate align-bottom">
      {label}
    </span>
  );
}
