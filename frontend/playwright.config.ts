import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:8765",
    headless: true,
    trace: "retain-on-failure",
  },
  projects: [{
    name: "msedge",
    use: { ...devices["Desktop Chrome"], channel: "msedge" },
  }],
  webServer: {
    command: "..\\.venv\\Scripts\\python.exe -m skin_analyzer --source file:../frontend/e2e/fixtures/no-face.png --port 8765",
    cwd: "../backend",
    url: "http://127.0.0.1:8765/api/health",
    reuseExistingServer: false,
    timeout: 120000,
  },
});
