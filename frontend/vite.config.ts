import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.VITE_API_TARGET || "http://localhost:8000";
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/auth": target,
        "/tenders": target,
        "/submissions": target,
        "/documents": target,
        "/audit": target,
        "/admin": target,
        "/users": target,
        "/health": target,
      },
    },
    build: { outDir: "dist" },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: "./src/__tests__/setup.ts",
    },
  };
});