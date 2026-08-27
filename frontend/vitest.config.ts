import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/setupTests.ts",
    // Playwright's E2E specs live under e2e/ and use test.describe() from
    // @playwright/test, not Vitest - exclude them here so `vitest run`
    // only picks up the component tests under src/.
    exclude: ["e2e/**", "node_modules/**"],
  },
});
