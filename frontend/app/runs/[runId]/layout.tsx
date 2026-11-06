import type { ReactNode } from "react";

import { RunShell } from "@/components/run-shell";

export const instant = false;

export default function RunLayout({ children }: { readonly children: ReactNode }) {
  return <RunShell>{children}</RunShell>;
}
