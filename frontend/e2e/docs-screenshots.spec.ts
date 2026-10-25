// Regenerates the README screenshots in docs/images from the synthetic stream fixtures.
// Skipped in normal runs; generate with:  $env:DOCS_SCREENSHOTS = "1"; npm run e2e -- docs-screenshots
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test, type Page } from "@playwright/test";
import type { FrameHeader, Health, Report } from "../src/protocol/types";

const fixture = (name: string) => readFileSync(new URL(`./fixtures/${name}`, import.meta.url));
const header: FrameHeader = JSON.parse(fixture("stream-header.json").toString());
const report: Report = JSON.parse(fixture("stream-report.json").toString());
const jpeg = fixture("stream-face.jpg");
const out = (name: string) => fileURLToPath(new URL(`../../docs/images/${name}.png`, import.meta.url));
const timeout = 15000;

test.skip(!process.env.DOCS_SCREENSHOTS, "set DOCS_SCREENSHOTS=1 to regenerate README screenshots");

async function mockStream(page: Page) {
  await page.routeWebSocket(/\/ws\/stream/, (socket) => {
    const health: Health = {
      status: "ok", source: "camera:0", camera_open: true, frame_size: [1280, 720],
      detector: "classical-cielab", preprocessor: "cpu", onnx_providers: [],
      landmarker: "mediapipe-face-landmarker", error: null,
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
  await page.route("**/api/settings/cameras", (route) => route.fulfill({ json: { success: true, error: null,
    data: { cameras: [{ index: 0, width: 1280, height: 720, active: true }, { index: 1, width: 1920, height: 1080, active: false }] } } }));
  await page.route("**/api/settings", (route) => route.fulfill({ json: { success: true, error: null,
    data: { source: { kind: "camera", spec: "camera:0", camera_index: 0 } } } }));
}

// Let progress-bar and marker transitions settle so screenshots are stable.
const settle = (page: Page) => page.waitForTimeout(700);

async function toResults(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Start analyzing" }).click();
  const analyze = page.getByRole("button", { name: "Analyze my skin" });
  await expect(analyze).toBeEnabled({ timeout });
  return analyze;
}

test("desktop screenshots", async ({ page }) => {
  test.setTimeout(90000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockStream(page);
  await page.goto("/");
  await settle(page);
  await page.screenshot({ path: out("start") });
  const analyze = await toResults(page);
  await settle(page);
  await page.screenshot({ path: out("camera") });
  await analyze.click();
  await expect(page.getByRole("heading", { name: "Your results", exact: true })).toBeVisible({ timeout });
  await page.getByRole("button", { name: /^Pustule 1, chin/ }).first().click();
  await settle(page);
  await page.screenshot({ path: out("results") });
  await page.getByRole("button", { name: "See treatments" }).click();
  await expect(page.getByRole("heading", { name: "Recommended treatments", exact: true })).toBeVisible();
  await settle(page);
  await page.screenshot({ path: out("treatments") });
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await expect(page.getByRole("radio", { name: /Camera 1/ })).toBeVisible({ timeout });
  await settle(page);
  await page.screenshot({ path: out("settings") });
});

test("mobile screenshot", async ({ page }) => {
  test.setTimeout(90000);
  await page.setViewportSize({ width: 390, height: 844 });
  await mockStream(page);
  const analyze = await toResults(page);
  await analyze.click();
  await expect(page.getByRole("heading", { name: "Your results", exact: true })).toBeVisible({ timeout });
  await settle(page);
  await page.screenshot({ path: out("results-mobile") });
});
