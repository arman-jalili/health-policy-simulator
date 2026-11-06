"use client";

import Link from "next/link";

import { useSettings } from "@/components/providers";

export default function NotFound() {
  const { t } = useSettings();
  return (
    <section className="mx-auto max-w-xl py-16 text-center">
      <h1 className="text-xl">{t("error.notFound")}</h1>
      <p className="mt-3 text-sm text-ink-muted">{t("run.notFound")}</p>
      <Link
        href="/"
        className="mt-6 inline-flex h-10 items-center rounded-md border border-line px-4 text-sm no-underline"
      >
        {t("nav.overview")}
      </Link>
    </section>
  );
}
