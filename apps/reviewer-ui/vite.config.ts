import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const isPages = mode === "pages";

  return {
    base: isPages ? "/eduwork-databridge/" : "/",
    define: {
      "import.meta.env.VITE_STATIC_DEMO": JSON.stringify(isPages ? "true" : "false"),
    },
    plugins: [react()],
    server: {
      proxy: {
        "/api": "http://127.0.0.1:8000",
        "/healthz": "http://127.0.0.1:8000",
        "/readyz": "http://127.0.0.1:8000",
      },
    },
    test: {
      environment: "jsdom",
      setupFiles: "./src/test/setup.ts",
    },
  };
});
