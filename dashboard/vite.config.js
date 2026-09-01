import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
    // Only src/. Without this, vitest walks node_modules and tries to run the
    // test files shipped inside dependencies.
    include: ['src/**/*.{test,spec}.{js,jsx}'],
  },
  server: {
    port: 5173,
    host: true
  },
  build: {
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-three': ['three', '@react-three/fiber', '@react-three/drei'],
          'vendor-graph': ['react-force-graph-3d'],
          'vendor-charts': ['recharts'],
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
  },
})
