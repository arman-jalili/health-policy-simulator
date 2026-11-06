"use client";

import type { ReactNode } from "react";

import { Icon } from "@/components/icons";
import { useSettings } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/http";
import { cn } from "@/lib/cn";
import type { MessageKey } from "@/lib/i18n";

export function Skeleton({ className }: { readonly className?: string }) {
  return <div aria-hidden="true" className={cn("animate-pulse rounded-xs bg-surface-muted", className)} />;
}

export function LoadingBlock({ rows = 4 }: { readonly rows?: number }) {
  const { t } = useSettings();
  return (
    <div role="status" aria-live="polite" className="space-y-2">
      <span className="sr-only">{t("common.loading")}</span>
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className={index === 0 ? "h-8 w-1/2" : "h-5 w-full"} />
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  hint,
  action,
}: {
  readonly title: string;
  readonly hint?: string | undefined;
  readonly action?: ReactNode;
}) {
  return (
    <div className="border border-dashed border-line-strong bg-surface px-4 py-8 text-center">
      <p className="text-sm font-medium text-ink">{title}</p>
      {hint !== undefined && <p className="mx-auto mt-2 max-w-prose text-sm text-ink-muted">{hint}</p>}
      {action !== undefined && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}

function fixKeyFor(error: ApiError): MessageKey | null {
  switch (error.code) {
    case "ROUND_STILL_OPEN":
      return "error.roundStillOpen";
    case "ROUND_CAP_EXCEEDED":
      return "error.roundCapExceeded";
    case "RUN_NOT_CLOSED":
      return "error.runNotClosed";
    case "ROUND_CLOSE_GUARD_VIOLATION":
      return "error.guardViolation";
    case "ARGUMENT_WITHOUT_EVIDENCE":
      return "error.argumentWithoutEvidence";
    case "CLAIM_VERDICT_REJECTED":
      return "error.claimVerdictRejected";
    case "DISCLOSURE_MISSING":
      return "error.disclosureMissing";
    case "CITATION_RESOLUTION_FAILED":
      return "error.citationResolutionFailed";
    case "INCOMPLETE_BRIEF":
      return "error.incompleteBrief";
    case "CONSENSUS_ANALYSIS_UNAVAILABLE":
      return "error.consensusUnavailable";
    default:
      return null;
  }
}

export function ErrorState({
  error,
  onRetry,
  title,
}: {
  readonly error: unknown;
  readonly onRetry?: () => void;
  readonly title?: string | undefined;
}) {
  const { t } = useSettings();
  const apiError =
    error instanceof ApiError
      ? error
      : new ApiError({
          status: 0,
          code: "UNKNOWN",
          message: error instanceof Error ? error.message : t("error.network"),
        });
  const fixKey = fixKeyFor(apiError);
  const heading =
    title ??
    (apiError.status === 403
      ? t("error.forbidden")
      : apiError.status === 503
        ? t("error.unavailable")
        : apiError.status === 409
          ? t("error.conflict")
          : apiError.status === 422
            ? t("error.validation")
            : t("common.error"));

  return (
    <div role="alert" className="border border-danger/30 bg-danger-quiet px-4 py-3">
      <div className="flex items-start gap-2">
        <span className="mt-0.5 text-danger">
          <Icon name="warning" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-danger">{heading}</p>
          <p className="mt-1 text-sm text-ink">{apiError.message}</p>
          {fixKey !== null && <p className="mt-1 text-sm text-ink-muted">{t(fixKey)}</p>}
          <p className="mt-2 font-mono text-2xs text-ink-muted">
            {t("error.code")}: {apiError.code}
            {apiError.traceId !== "" && ` · ${t("common.traceId")}: ${apiError.traceId}`}
          </p>
          {apiError.details.length > 0 && (
            <ul className="mt-2 space-y-1 text-2xs text-ink-muted">
              {apiError.details.map((detail, index) => (
                <li key={`${detail.field ?? "detail"}-${index}`}>
                  {detail.field !== null && detail.field !== undefined && (
                    <span className="font-mono">{detail.field}: </span>
                  )}
                  {detail.message}
                </li>
              ))}
            </ul>
          )}
          {onRetry !== undefined && (
            <div className="mt-3">
              <Button size="sm" onClick={onRetry}>
                {t("common.retry")}
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function DegradedBanner({
  checks,
  status,
}: {
  readonly checks: Readonly<Record<string, string>>;
  readonly status?: string | undefined;
}) {
  const { t } = useSettings();
  if (status !== "degraded") return null;
  const problems = Object.entries(checks);
  if (problems.length === 0) return null;
  return (
    <div role="status" className="border border-warn/40 bg-warn-quiet px-4 py-3">
      <div className="flex items-start gap-2">
        <span className="mt-0.5 text-warn">
          <Icon name="warning" />
        </span>
        <div>
          <p className="text-sm font-medium text-warn">{t("degraded.banner")}</p>
          <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-2xs text-ink-muted">
            {problems.map(([key, value]) => (
              <li key={key}>
                <span className="font-mono">{key}</span>: {value}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

export function ForbiddenState({ detail }: { readonly detail?: string }) {
  const { t } = useSettings();
  return (
    <div role="alert" className="border border-warn/40 bg-warn-quiet px-4 py-3 text-sm">
      <p className="font-medium text-warn">{t("error.forbidden")}</p>
      {detail !== undefined && <p className="mt-1 text-ink-muted">{detail}</p>}
    </div>
  );
}
