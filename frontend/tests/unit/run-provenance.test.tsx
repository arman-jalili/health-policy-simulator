import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Providers } from "@/components/providers";
import {
  RunDriverBadge,
  RunProvenanceBanner,
} from "@/features/run/components/run-provenance";

function renderWithProviders(ui: React.ReactElement) {
  return render(<Providers>{ui}</Providers>);
}

describe("run provenance", () => {
  it("labels an automated run with the synthetic-support caveat", () => {
    renderWithProviders(<RunProvenanceBanner automated scripted />);

    expect(screen.getByRole("status")).toHaveTextContent("Automatisierter Lauf (Platzhalter)");
    expect(screen.getByRole("status")).toHaveTextContent("keine Aussage über die Institutionen");
    expect(screen.getByRole("status")).toHaveTextContent("Scripted-Provider");
  });

  it("renders no banner for a manual run", () => {
    renderWithProviders(<RunProvenanceBanner automated={false} scripted={false} />);

    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows the manual and automated driver badges", () => {
    const { rerender } = renderWithProviders(
      <RunDriverBadge automated={false} known />,
    );
    expect(screen.getByText("Manuell")).toBeInTheDocument();

    rerender(
      <Providers>
        <RunDriverBadge automated known />
      </Providers>,
    );
    expect(screen.getByText("Automatisiert")).toBeInTheDocument();
  });
});
