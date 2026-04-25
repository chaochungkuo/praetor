import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  root: "frontend",
  build: {
    outDir: "../dist",
    emptyOutDir: true
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:9741",
      "/auth": "http://127.0.0.1:9741",
      "/missions": "http://127.0.0.1:9741",
      "/onboarding": "http://127.0.0.1:9741"
    }
  }
});

