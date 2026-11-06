"use client";

import Link from "next/link";
import { useEffect } from "react";

import { useSettings } from "@/components/providers";

export default function ErrorBoundary({
  error,
  reset,
}: {
  readonly error: Error & { digest?: string };
  readonly reset: () => void;
}) {
  const { t } = useSettings();

  useEffect(() => {
    if (process.env.NODE_ENV !== "production") {
      console.error(error);
    }
  }, [error]);

  return (
    <section className="mx-auto max-w-xl py-16">
      <h1 className="text-xl">{t("common.error")}</h1>
      <p className="mt-3 text-sm text-ink-muted">{t("error.network")}</p>
      {error.digest !== undefined && (
        <p className="mt-2 font-mono text-2xs text-ink-subtle">{error.digest}</p>
      )}
      <div className="mt-6 flex gap-3">
        <button
          type="button"
          onClick={reset}
          className="h-10 rounded-md bg-accent px-4 text-sm font-medium text-on-accent"
        >
          {t("common.retry")}
        </button>
        <Link
          href="/"
          className="inline-flex h-10 items-center rounded-md border border-line px-4 text-sm no-underline"
        >
          {t("nav.overview")}
        </Link>
      </div>
    </section>
  );
}
