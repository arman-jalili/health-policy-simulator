import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { Providers } from "@/components/providers";
import { ExpandableText } from "@/components/ui/expandable-text";
import { SelectMenu } from "@/components/ui/select-menu";

const LONG = "Ein langer Absatz mit Belegtext. ".repeat(20);
const OPTIONS = [
  { value: "all", label: "Alle Ereignisse" },
  { value: "opened", label: "Verhandlung eröffnet" },
];

function Harness() {
  const [value, setValue] = useState("all");
  return (
    <Providers>
      <SelectMenu label="Filter" value={value} options={OPTIONS} onChange={setValue} />
    </Providers>
  );
}

describe("ExpandableText", () => {
  it("collapses long text and toggles the full text", async () => {
    const user = userEvent.setup();
    render(
      <Providers>
        <ExpandableText text={LONG} />
      </Providers>,
    );
    const toggle = screen.getByRole("button", { name: "Mehr anzeigen" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await user.click(toggle);
    expect(screen.getByRole("button", { name: "Weniger anzeigen" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });

  it("does not show a toggle for short text", () => {
    render(
      <Providers>
        <ExpandableText text="Kurz." />
      </Providers>,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});

describe("SelectMenu", () => {
  it("opens the listbox and selects an option", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole("button", { name: /Filter/ }));
    expect(screen.getByRole("listbox")).toBeInTheDocument();
    await user.click(screen.getByRole("option", { name: "Verhandlung eröffnet" }));
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Filter/ })).toHaveTextContent(
      "Verhandlung eröffnet",
    );
  });

  it("supports arrow-key selection", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole("button", { name: /Filter/ }));
    await user.keyboard("{ArrowDown}{Enter}");
    expect(screen.getByRole("button", { name: /Filter/ })).toHaveTextContent(
      "Verhandlung eröffnet",
    );
  });
});
