import { defineConfig, devices } from "@playwright/test";
import { fileURLToPath } from "node:url";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:5186",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 } } },
    { name: "mobile", use: { ...devices["Pixel 7"], viewport: { width: 390, height: 844 } } },
  ],
  webServer: {
    command: "python3 scripts/demo.py --workspace browser-check --reset --yes --skip-install --no-browser --api-port 8186 --ui-port 5186",
    cwd: fileURLToPath(new URL("../../", import.meta.url)),
    url: "http://127.0.0.1:5186/api/v1/version",
    reuseExistingServer: false,
    timeout: 180_000,
    gracefulShutdown: { signal: "SIGTERM", timeout: 15_000 },
    stdout: "pipe",
    stderr: "pipe",
  },
});
