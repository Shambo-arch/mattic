import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: process.env.STOREFRONT_E2E === "true",
    hmr: process.env.STOREFRONT_E2E ? false : undefined,
    proxy: {
      "/api": {
        target: process.env.STOREFRONT_BACKEND_URL || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/media": {
        target: process.env.STOREFRONT_BACKEND_URL || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: { react: ["react", "react-dom", "react-router-dom"] },
      },
    },
  },
});
