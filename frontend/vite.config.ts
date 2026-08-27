import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  // Same proxy for `vite preview` (a production-mode build served
  // locally), so Playwright E2E tests can hit a real backend without a
  // separate reverse-proxy setup - see .github/workflows/ci.yml.
  preview: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
