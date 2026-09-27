import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Same relative-path approach nginx uses in production: the frontend
    // code never sees an absolute backend URL, in dev or in the built image.
    proxy: {
      '/api': {
        target: process.env.VITE_DEV_API_PROXY_TARGET ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    // Run tests in a browser-like environment so React components can render.
    environment: 'jsdom',
    // Loads @testing-library/jest-dom matchers (toBeInTheDocument, etc.)
    // before every test file without needing an explicit import in each file.
    setupFiles: ['src/test/setup.ts'],
    // Expose describe / it / expect as globals — matches Jest's API surface,
    // which is what @testing-library documentation examples use.
    globals: true,
  },
})

