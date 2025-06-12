import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  // Build configuration
  build: {
    // Output directory for built assets
    outDir: 'static/dist',
    // Generate manifest for Django integration
    manifest: true,
    // Input files
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'static/src/main.ts'),
        style: resolve(__dirname, 'static/src/style.css'),
      },
    },
    // Clean output directory before build
    emptyOutDir: true,
  },

  // Development server
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Enable HMR
    hmr: {
      port: 5173,
    },
    // Watch options for better performance
    watch: {
      usePolling: true,
      interval: 1000,
    },
  },

  // Base URL for assets
  base: '/static/dist/',

  // CSS configuration
  css: {
    postcss: './postcss.config.js',
  },

  // Resolve configuration
  resolve: {
    alias: {
      '@': resolve(__dirname, 'static/src'),
    },
  },

  // Define environment variables
  define: {
    __DEV__: JSON.stringify(process.env['NODE_ENV'] === 'development'),
  },

  // Plugin configuration
  plugins: [],
})
