import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end smoke tests that exercise the built frontend through a real
 * browser. These run against `vite preview` (a static build) in CI, so the
 * backend must be reachable separately (the CI workflow starts it with
 * uvicorn before this suite runs) — see .github/workflows/ci.yml's
 * `e2e-tests` job.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["html", { open: "never" }], ["list"]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // Allow pointing at a pre-installed Chromium build (e.g. a sandboxed
        // CI/dev environment that blocks Playwright's own CDN download) via
        // PLAYWRIGHT_CHROMIUM_EXECUTABLE. Falls back to Playwright's
        // normally-managed browser otherwise.
        launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
          ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE }
          : {},
      },
    },
  ],
});
