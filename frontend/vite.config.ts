/// <reference types="vitest" />
import { defineConfig } from 'vite'
import { configDefaults } from 'vitest/config'
import react from '@vitejs/plugin-react'

const BACKEND = process.env.SKIN_BACKEND_URL ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': BACKEND,
      '/ws': { target: BACKEND.replace(/^http/, 'ws'), ws: true },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    passWithNoTests: true,
    exclude: [...configDefaults.exclude, 'e2e/**'], // Playwright specs run via `npm run e2e`
    coverage: {
      include: ['src/**/*.{ts,tsx}'], // count untested source files, not configs
      clean: false, // deleting the report folder can hang when the repo is in a synced folder (OneDrive)
    },
  },
})
