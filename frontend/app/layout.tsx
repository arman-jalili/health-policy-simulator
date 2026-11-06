import type { Metadata } from "next";
import { Roboto, Roboto_Condensed, Roboto_Mono } from "next/font/google";
import { Suspense, type ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { Providers } from "@/components/providers";

import "@/styles/globals.css";

const roboto = Roboto({
  variable: "--font-roboto",
  subsets: ["latin"],
  weight: ["300", "400", "500", "700"],
  display: "swap",
});

const robotoCondensed = Roboto_Condensed({
  variable: "--font-roboto-condensed",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
});

const robotoMono = Roboto_Mono({
  variable: "--font-roboto-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
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
      data-theme="portal"
      data-density="comfortable"
      data-motion="full"
      suppressHydrationWarning
      className={`${roboto.variable} ${robotoCondensed.variable} ${robotoMono.variable} h-full antialiased`}
    >
      <body className="min-h-full">
        <Providers>
          <Suspense fallback={<div className="min-h-dvh bg-surface" />}>
            <AppShell>{children}</AppShell>
          </Suspense>
        </Providers>
      </body>
    </html>
  );
}
