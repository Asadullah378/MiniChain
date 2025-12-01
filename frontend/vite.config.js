import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/status': 'http://localhost:8080',
      '/blocks': 'http://localhost:8080',
      '/mempool': 'http://localhost:8080',
      '/submit': 'http://localhost:8080',
      '/debug': 'http://localhost:8080',
    },
  },
});
