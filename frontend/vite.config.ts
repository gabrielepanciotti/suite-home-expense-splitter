import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// HomeExpenseSplitter dashboard — Life registry frontend port 3343 (backend :10009).
// Backend proxy target: inside Docker the frontend container reaches the backend by
// its service hostname (VITE_BACKEND_PROXY_TARGET, set by deploy/docker-compose.yml);
// outside Docker it falls back to localhost on the registry backend port.
const backendTarget =
  process.env.VITE_BACKEND_PROXY_TARGET ?? "http://localhost:10009";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    port: 3343,
    strictPort: true,
    proxy: {
      "/api": { target: backendTarget, changeOrigin: true },
      "/health": { target: backendTarget, changeOrigin: true },
    },
  },
});
