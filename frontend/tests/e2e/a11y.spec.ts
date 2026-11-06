import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.skip(process.env.HPS_E2E !== "1", "Set HPS_E2E=1 with a running backend.");

const runId = process.env.HPS_E2E_RUN_ID;
const routes = ["/", "/settings", "/health", "/claims"];
if (runId !== undefined && runId !== "") {
  routes.push(`/runs/${runId}`, `/runs/${runId}/consensus`, `/runs/${runId}/brief`);
}

for (const route of routes) {
  test(`axe: ${route} has no violations`, async ({ page }) => {
    await page.goto(route);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });
}
