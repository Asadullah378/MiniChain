import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/status': 'http://localhost:8000',
      '/blocks': 'http://localhost:8000',
      '/mempool': 'http://localhost:8000',
      '/submit': 'http://localhost:8000',
      '/debug': 'http://localhost:8000',
    },
  },
});
