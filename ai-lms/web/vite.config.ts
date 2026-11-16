import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { mockApi } from "./mock/server";

// Dev server only. In production Caddy serves the built files and proxies /api.
//   npm run dev        proxies /api to AILMS_BACKEND_URL (default: the Compose web service)
//   npm run dev:mock   answers /api from fixtures, no backend needed
export default defineConfig(({ mode }) => ({
  plugins: [react(), ...(mode === "mock" ? [mockApi()] : [])],
  server: {
    port: 5173,
    proxy:
      mode === "mock"
        ? undefined
        : {
            "/api": {
              target: process.env.AILMS_BACKEND_URL ?? "http://localhost:8080",
              changeOrigin: false,
            },
          },
  },
  build: {
    // Nothing is inlined as a data: URL, so the content security policy can stay same-origin only.
    assetsInlineLimit: 0,
    sourcemap: false,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
}));
