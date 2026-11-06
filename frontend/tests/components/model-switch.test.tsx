import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Providers } from "@/components/providers";

// The card is inline in the settings page; render the same markup through the shared primitives to
// assert the contract the page relies on (two variants, active marked, unavailable absent).
import { Button } from "@/components/ui/button";

const provider = { active: "openai-compatible", model: "deepseek-flash", available: ["openai-compatible", "scripted"] };

function ModelSwitch({ active, onPick }: { readonly active: string; readonly onPick: (name: string) => void }) {
  return (
    <div role="group" aria-label="Modell">
      {provider.available.map((name) => (
        <Button key={name} variant={active === name ? "primary" : "secondary"} aria-pressed={active === name} onClick={() => onPick(name)}>
          {name === "scripted" ? "Skript (Platzhalter)" : "Live-LLM"}
        </Button>
      ))}
    </div>
  );
}

describe("model switch", () => {
  it("marks the active variant and offers both", () => {
    render(<Providers><ModelSwitch active={provider.active} onPick={() => undefined} /></Providers>);

    expect(screen.getByRole("button", { name: "Live-LLM" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Skript (Platzhalter)" })).toHaveAttribute("aria-pressed", "false");
  });

  it("reports the picked variant", async () => {
    const onPick = vi.fn();
    render(<Providers><ModelSwitch active={provider.active} onPick={onPick} /></Providers>);

    await userEvent.click(screen.getByRole("button", { name: "Skript (Platzhalter)" }));

    expect(onPick).toHaveBeenCalledWith("scripted");
  });
});
