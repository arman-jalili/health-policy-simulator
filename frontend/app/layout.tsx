import type { Metadata } from "next";
import { Source_Code_Pro, Source_Sans_3, Source_Serif_4 } from "next/font/google";
import { Suspense, type ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { Providers } from "@/components/providers";

import "@/styles/globals.css";

const sourceSans = Source_Sans_3({
  variable: "--font-source-sans",
  subsets: ["latin"],
  display: "swap",
});

const sourceSerif = Source_Serif_4({
  variable: "--font-source-serif",
  subsets: ["latin"],
  display: "swap",
});

const sourceCode = Source_Code_Pro({
  variable: "--font-source-code",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "HealthPolicy Simulator",
    template: "%s — HealthPolicy Simulator",
  },
  description:
    "Institutionelle Verhandlungssimulation für die österreichische Gesundheitspolitik mit Evidenz, Konsens und Entscheidungsbrief.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { readonly children: ReactNode }) {
  return (
    <html
      lang="de-AT"
      data-theme="paper"
      data-density="comfortable"
      data-motion="full"
      suppressHydrationWarning
      className={`${sourceSans.variable} ${sourceSerif.variable} ${sourceCode.variable} h-full antialiased`}
    >
      <body className="min-h-full">
        <Providers>
          <Suspense fallback={<div className="min-h-dvh bg-surface-muted" />}>
            <AppShell>{children}</AppShell>
          </Suspense>
        </Providers>
      </body>
    </html>
  );
}
