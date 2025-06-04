/// <reference types="vite/client" />

// Global variables from Vite config
declare const __DEV__: boolean

// HTMX global
declare const htmx: any

// Chart.js types
declare module 'chart.js' {
  // Re-export Chart.js types for better IDE support
}
