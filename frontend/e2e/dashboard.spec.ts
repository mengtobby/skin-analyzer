import { expect, test, type Page } from "@playwright/test";

const telemetryTimeout = 15000;

async function openDashboard(page: Page) {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Skin Analyzer", exact: true })).toBeVisible();
  await expect(page.getByLabel("Pipeline status").getByText("connected", { exact: true }))
    .toBeVisible({ timeout: telemetryTimeout });
}

function frameCounter(page: Page) {
  return page.getByRole("region", { name: "Live analysis" }).getByText(/^Frame \d+$/);
}

test("health returns the REST envelope and an open file source", async ({ request }) => {
  await expect(async () => {
    const response = await request.get("/api/health");
    expect(response.status()).toBe(200);
    const envelope = await response.json();
    expect(Object.keys(envelope).sort()).toEqual(["data", "error", "success"]);
    expect(envelope).toMatchObject({
      success: true, error: null, data: { status: "ok", camera_open: true },
    });
  }).toPass({ timeout: telemetryTimeout });
});

test("dashboard connects and its live frame counter advances", async ({ page }) => {
  await openDashboard(page);
  const counter = frameCounter(page);
  await expect(counter).toBeVisible({ timeout: telemetryTimeout });
  const initial = Number((await counter.innerText()).slice("Frame ".length));
  await expect.poll(async () => Number((await counter.innerText()).slice("Frame ".length)), {
    timeout: telemetryTimeout,
  }).toBeGreaterThan(initial);
});

test("no-face frame shows guidance without lesion findings", async ({ page }) => {
  await openDashboard(page);
  await expect(page.getByRole("status").filter({ hasText: "No face detected" }))
    .toBeVisible({ timeout: telemetryTimeout });
  const insights = page.getByRole("region", { name: "Insights", exact: true });
  await expect(insights.getByText(/^No findings yet\./)).toBeVisible();
  await expect(insights.getByRole("article")).toHaveCount(0);
  const counts = page.getByRole("region", { name: "Skin telemetry" }).getByRole("listitem");
  await expect(counts).toHaveCount(9);
  for (const row of await counts.all()) {
    await expect(row).toHaveText(/^\D+0$/);
  }
});

test("recommendations provide the baseline routine and cosmetic disclaimer", async ({ page }) => {
  await openDashboard(page);
  const recommendations = page.getByRole("region", { name: "Recommendations" });
  for (const category of ["cleanser", "moisturizer", "sunscreen"]) {
    await expect(recommendations.getByRole("article").filter({
      hasText: new RegExp(`${category} /`),
    }).first()).toBeVisible({ timeout: telemetryTimeout });
  }
  await expect(recommendations.getByText("Gentle routine maintenance and daily barrier care.").first())
    .toBeVisible();
  await expect(page.getByText(/Cosmetic guidance only.*not a medical diagnosis/))
    .toBeVisible({ timeout: telemetryTimeout });
});

test("overlay controls toggle and tracking reset keeps the stream healthy", async ({ page }) => {
  await openDashboard(page);
  for (const name of ["Zones", "Masks", "Boxes", "Labels"]) {
    const toggle = page.getByRole("checkbox", { name, exact: true });
    await expect(toggle).toBeChecked();
    await toggle.uncheck();
    await expect(toggle).not.toBeChecked();
    await toggle.check();
    await expect(toggle).toBeChecked();
  }
  const counter = frameCounter(page);
  await expect(counter).toBeVisible({ timeout: telemetryTimeout });
  const initial = Number((await counter.innerText()).slice("Frame ".length));
  await page.getByRole("button", { name: "Reset tracking" }).click();
  await expect.poll(async () => Number((await counter.innerText()).slice("Frame ".length)), {
    timeout: telemetryTimeout,
  }).toBeGreaterThan(initial);
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("reset rejects a foreign Origin", async ({ page }) => {
  const response = await page.request.post("/api/reset", {
    headers: { Origin: "http://evil.example" },
  });
  expect(response.status()).toBe(403);
  expect(await response.json()).toMatchObject({ success: false, data: null });
});
