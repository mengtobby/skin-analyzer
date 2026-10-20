import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import type { FrameHeader, Health, Report } from "../src/protocol/types";

const fixture = (name: string) => readFileSync(new URL(`./fixtures/${name}`, import.meta.url));
const header: FrameHeader = JSON.parse(fixture("stream-header.json").toString());
const report: Report = JSON.parse(fixture("stream-report.json").toString());
const jpeg = fixture("stream-face.jpg");
const telemetryTimeout = 15000;

test("guided analysis explores blemishes and treatments on a synthetic stream", async ({ page }) => {
  await page.routeWebSocket(/\/ws\/stream/, socket => {
    const health: Health = {
      status: "ok", source: "synthetic", camera_open: true, frame_size: [1280, 720],
      detector: "mock", preprocessor: "mock", onnx_providers: [], landmarker: "mock", error: null,
    };
    socket.send(JSON.stringify({ type: "status", data: health }));
    let frameId = 0;
    const frames = setInterval(() => {
      const json = Buffer.from(JSON.stringify({ ...header, frame_id: ++frameId, timestamp: Date.now() / 1000 }));
      const length = Buffer.alloc(4);
      length.writeUInt32LE(json.length);
      socket.send(Buffer.concat([length, json, jpeg]));
    }, 100);
    const reports = setInterval(() => {
      socket.send(JSON.stringify({ type: "report", data: { ...report, generated_at: Date.now() / 1000 } }));
    }, 1000);
    socket.onClose(() => { clearInterval(frames); clearInterval(reports); });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Start analyzing" }).click();
  const currentStep = page.getByRole("navigation", { name: "Analysis progress" }).locator('[aria-current="step"]');
  await expect(currentStep).toContainText("Camera");
  const analyze = page.getByRole("button", { name: "Analyze my skin" });
  await expect(analyze).toBeEnabled({ timeout: telemetryTimeout });
  await analyze.click();
  await expect(page.getByRole("heading", { name: "Your results", exact: true })).toBeVisible({ timeout: telemetryTimeout });
  await expect(page.getByRole("button", { name: /, details$/ })).toHaveCount(4);
  await page.getByRole("button", { name: "Pustule 1, chin, details", exact: true }).click();
  const detail = page.getByLabel("Selected area details");
  await expect(detail.getByRole("heading", { name: "Pustule", exact: true })).toBeVisible();
  await expect(detail.getByRole("heading", { name: "What it is" })).toBeVisible();
  await expect(detail.getByText("A raised spot with a pale centre and surrounding redness. Avoid picking to help limit irritation.")).toBeVisible();
  await expect(detail.getByRole("heading", { name: "Why it happens" })).toBeVisible();
  const acneInsight = report.insights.find(insight => insight.condition === "inflammatory_acne");
  expect(acneInsight?.mechanisms.length).toBeGreaterThan(0);
  await expect(detail.getByText(acneInsight!.mechanisms[0], { exact: true })).toBeVisible();
  for (const group of ["Papules", "Pustules", "Red marks", "Dark marks"]) {
    await expect(page.getByRole("region", { name: "All areas" }).getByRole("heading", { name: `${group} (1)`, exact: true })).toBeVisible();
  }
  for (const [name, value] of [["Redness", 46], ["Texture", 28], ["Oiliness", 12], ["Pigmentation", 34]] as const) {
    await expect(page.getByRole("heading", { name, exact: true }).locator("..")).toContainText(`${value} / 100`);
  }

  await page.getByRole("button", { name: "See treatments" }).click();
  await expect(page.getByRole("heading", { name: "Recommended treatments", exact: true })).toBeVisible();
  expect(report.ingredients.length).toBeGreaterThan(0);
  await expect(page.getByRole("heading", { name: report.ingredients[0].name, exact: true })).toBeVisible();
  await expect(page.getByRole("progressbar", { name: `${report.ingredients[0].name} recommendation match`, exact: true })).toBeVisible();
  for (const name of ["Morning", "Evening"]) {
    const routine = page.getByRole("region", { name: `${name} routine` });
    await expect(routine).toBeVisible();
    await expect(routine.getByRole("heading", { level: 4 }).first()).toBeVisible();
  }
  await expect(page.getByLabel("Disclaimer")).toHaveText(report.disclaimer);
  await page.getByRole("button", { name: "Start a new analysis" }).click();
  await expect(page.getByRole("heading", { name: /take a look/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start analyzing" })).toBeVisible();
  await expect(currentStep).toContainText("Start");
});
