import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      "@/app": path.resolve(__dirname, "src/app"),
      "@/styles": path.resolve(__dirname, "src/styles"),
    },
  },
  css: {
    postcss: path.resolve(__dirname, "postcss.config.cjs"),
  },
  test: {
    environment: "jsdom",
    setupFiles: path.resolve(__dirname, "vitest.setup.ts"),
    globals: true,
    css: true,
    reporters: ["default"],
    coverage: {
      provider: "istanbul",
    },
  },
});
