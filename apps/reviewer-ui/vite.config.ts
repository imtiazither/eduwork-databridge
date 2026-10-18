import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const isPages = mode === "pages";
  const apiTarget = loadEnv(mode, ".", "VITE_DEMO_").VITE_DEMO_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
    base: isPages ? "/eduwork-databridge/" : "/",
    define: {
      "import.meta.env.VITE_STATIC_DEMO": JSON.stringify(isPages ? "true" : "false"),
    },
    plugins: [react()],
    server: {
      proxy: {
        "/api": apiTarget,
        "/healthz": apiTarget,
        "/readyz": apiTarget,
      },
    },
    test: {
      include: ["src/**/*.test.{ts,tsx}"],
      environment: "jsdom",
      setupFiles: "./src/test/setup.ts",
    },
  };
});
