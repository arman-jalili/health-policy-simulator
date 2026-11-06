import { render, screen } from "@testing-library/react";
import axe from "axe-core";
import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";

import { Providers } from "@/components/providers";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/ui/states";
import { StatusPill } from "@/components/ui/status-pill";
import { ApiError } from "@/lib/http";

function renderWithProviders(ui: ReactElement) {
  return render(<Providers>{ui}</Providers>);
}

describe("state components", () => {
  it("renders an actionable empty state", () => {
    renderWithProviders(<EmptyState title="Keine Daten" hint="Legen Sie eine Verhandlung an." />);
    expect(screen.getByText("Keine Daten")).toBeInTheDocument();
    expect(screen.getByText("Legen Sie eine Verhandlung an.")).toBeInTheDocument();
  });

  it("renders a loading region with a status role", () => {
    renderWithProviders(<LoadingBlock rows={2} />);
    expect(screen.getByRole("status")).toHaveTextContent("Wird geladen");
  });

  it("renders the error envelope, code, fix and trace id", () => {
    const error = new ApiError({
      status: 409,
      code: "ROUND_CLOSE_GUARD_VIOLATION",
      message: "round 1 cannot close; unaccounted: stk_oegk",
      traceId: "req_1",
    });
    renderWithProviders(<ErrorState error={error} />);
    expect(screen.getByRole("alert")).toHaveTextContent("ROUND_CLOSE_GUARD_VIOLATION");
    expect(screen.getByText("Nicht alle Institutionen sind berücksichtigt.")).toBeInTheDocument();
    expect(screen.getByText(/req_1/)).toBeInTheDocument();
  });

  it("has no axe violations in the state primitives", async () => {
    const { container } = renderWithProviders(
      <div>
        <StatusPill tone="ok">Bereit</StatusPill>
        <EmptyState title="Leer" hint="Nichts vorhanden." />
      </div>,
    );
    const results = await axe.run(container, {
      rules: { "color-contrast": { enabled: false } },
    });
    expect(results.violations).toEqual([]);
  });
});
