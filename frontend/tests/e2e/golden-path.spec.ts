import { readFileSync } from "node:fs";

import { expect, test } from "@playwright/test";

const enabled = process.env.HPS_E2E === "1";

test.skip(!enabled, "Set HPS_E2E=1 with a running backend and a seeded corpus.");

function loadSeed(): unknown | null {
  try {
    return JSON.parse(readFileSync("/tmp/demo-seed.json", "utf8"));
  } catch {
    return null;
  }
}

test("golden path: open run, nine turns, close, consensus, brief", async ({ page }) => {
  const seed = loadSeed();
  test.skip(seed === null, "Missing /tmp/demo-seed.json; run LOG_LEVEL=ERROR make -s demo-seed.");

  await page.addInitScript((value) => {
    window.localStorage.setItem("hps.seed.v1", JSON.stringify(value));
  }, seed);

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Verhandlungen" })).toBeVisible();

  await page.getByRole("button", { name: "Neue Verhandlung eröffnen" }).click();
  await expect(page.getByRole("heading", { name: "Neue Verhandlung" })).toBeVisible();
  await page.getByLabel("Policy-Frage").fill(
    "Wie sichern wir Kassenstellen und Versorgung in Oesterreich?",
  );
  await page.getByRole("button", { name: "Verhandlung eröffnen" }).click();

  await expect(page).toHaveURL(/\/runs\/run_/);
  await expect(page.getByRole("heading", { name: "Konsole" })).toBeVisible();
  await page.getByRole("button", { name: "Runde öffnen" }).click();

  const runId = page.url().split("/runs/")[1] ?? "";
  const stateResponse = await page.request.get(`/api/hps/runs/${runId}`);
  expect(stateResponse.ok()).toBeTruthy();
  const state = (await stateResponse.json()) as { bound_stakeholder_ids: string[] };
  const stakeholdersResponse = await page.request.get("/api/hps/stakeholders");
  const stakeholders = (await stakeholdersResponse.json()) as {
    items: { stakeholder_id: string; identity: { short_name: string } }[];
  };
  const names = new Map(
    stakeholders.items.map((item) => [item.stakeholder_id, item.identity.short_name]),
  );

  for (const stakeholderId of state.bound_stakeholder_ids) {
    const name = names.get(stakeholderId) ?? stakeholderId;
    await page.getByRole("button", { name: "Wort ergreifen" }).click();
    await page.getByLabel("Institution").selectOption({ label: name });
    await page.getByLabel("Text des Arguments").fill(
      "Das ASVG regelt die Kassenstellen und die Finanzierung.",
    );
    await page.getByRole("button", { name: "Argument senden" }).click();
    await expect(page.getByRole("dialog")).toBeHidden();
  }

  await page.getByLabel("Konvergenz").selectOption("none");
  await page.getByRole("button", { name: "Runde schließen" }).click();
  await expect(page.getByRole("status")).toContainText("Runde geschlossen");

  await page.getByRole("link", { name: "Konsens" }).click();
  await expect(page.getByRole("heading", { name: "Konsensaufzeichnungen" })).toBeVisible();

  await page.getByRole("link", { name: "Entscheidungsbrief" }).click();
  await page.getByRole("button", { name: "Brief publizieren" }).click();
  await expect(page.getByRole("heading", { name: "Entscheidungsbrief" }).first()).toBeVisible();
});
