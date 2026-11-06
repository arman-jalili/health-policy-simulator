/**
 * Client-declared attribution identifier for a manual negotiation turn.
 * The backend checks presence, not membership (see DEFERRED D-004 / backend W8).
 * Never claim that this identifier was issued by the service.
 */
export function demoInvocationId(
  runId: string,
  round: number,
  stakeholderId: string,
  turnIndex: number,
): string {
  const clean = (value: string): string => value.replace(/[^A-Za-z0-9_-]/g, "-");
  return `inv_${clean(runId)}_${round}_${clean(stakeholderId)}_${turnIndex}`;
}
