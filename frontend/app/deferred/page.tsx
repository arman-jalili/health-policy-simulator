"use client";

import Link from "next/link";

import { useSettings } from "@/components/providers";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { DEFERRED_ENTRIES } from "@/lib/deferred";

export default function DeferredPage() {
  const { t, locale } = useSettings();
  return (
    <div className="space-y-4">
      <PageHeader title={t("deferred.title")} subtitle={t("deferred.intro")} />
      <ul className="space-y-3">
        {DEFERRED_ENTRIES.map((entry) => (
          <li key={entry.id}>
            <Card>
              <CardHeader
                title={`${entry.id} · ${locale === "en" ? entry.title.en : entry.title.de}`}
              />
              <CardBody className="grid gap-3 text-sm md:grid-cols-3">
                <section>
                  <h3 className="text-2xs font-semibold uppercase tracking-wide text-ink-muted">
                    {t("deferred.truth")}
                  </h3>
                  <p className="mt-1">{locale === "en" ? entry.truth.en : entry.truth.de}</p>
                </section>
                <section>
                  <h3 className="text-2xs font-semibold uppercase tracking-wide text-ink-muted">
                    {t("deferred.workaround")}
                  </h3>
                  <p className="mt-1">{locale === "en" ? entry.workaround.en : entry.workaround.de}</p>
                </section>
                <section>
                  <h3 className="text-2xs font-semibold uppercase tracking-wide text-ink-muted">
                    {t("deferred.removal")}
                  </h3>
                  <p className="mt-1">{locale === "en" ? entry.removal.en : entry.removal.de}</p>
                </section>
              </CardBody>
            </Card>
          </li>
        ))}
      </ul>
      <Link href="/" className="text-sm">
        {t("nav.overview")}
      </Link>
    </div>
  );
}
