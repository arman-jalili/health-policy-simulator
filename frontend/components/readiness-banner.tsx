"use client";

import Link from "next/link";

import { useSettings } from "@/components/providers";
import { Icon } from "@/components/icons";
import { DegradedBanner } from "@/components/ui/states";
import { useReadyz } from "@/features/platform/hooks";

export function ReadinessBanner() {
  const { t } = useSettings();
  const { data, error } = useReadyz();

  if (error !== null) {
    return (
      <div role="status" className="mb-4 rounded-md border border-danger/30 bg-danger-quiet px-4 py-3">
        <div className="flex items-start gap-2">
          <span className="mt-0.5 text-danger">
            <Icon name="warning" />
          </span>
          <p className="text-sm text-ink">
            {t("error.network")}{" "}
            <Link href="/health" className="font-medium">
              {t("nav.health")}
            </Link>
          </p>
        </div>
      </div>
    );
  }

  if (data === undefined) return null;

  return (
    <div className="mb-4">
      <DegradedBanner checks={data.checks} status={data.status} />
    </div>
  );
}
