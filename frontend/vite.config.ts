import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Vite's default CSS minifier (lightningcss) rewrites plain
    // `@media (max-width: 860px)` into the newer range syntax
    // `@media (width<=860px)` - valid CSS, but unsupported by many
    // Android WebViews (e.g. links opened inside WhatsApp), which then
    // silently ignore the whole rule and keep the desktop two-column
    // dashboard layout on a phone-width screen, overlapping the nav and
    // page content. esbuild's CSS minifier preserves the original
    // max-width/min-width syntax, which every browser understands.
    cssMinify: "esbuild",
  },
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
