import '@testing-library/jest-dom'
import { vi, expect } from 'vitest'

// Mock window.htmx for tests
;(window as any).htmx = {
  ajax: vi.fn(),
  trigger: vi.fn(),
  on: vi.fn(),
  off: vi.fn(),
  find: vi.fn(),
  findAll: vi.fn(),
  closest: vi.fn(),
  values: vi.fn(),
  addClass: vi.fn(),
  removeClass: vi.fn(),
  toggleClass: vi.fn(),
  takeClass: vi.fn(),
  config: {
    historyEnabled: true,
    refreshOnHistoryMiss: false,
  },
}

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString()
    },
    removeItem: (key: string) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    },
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

// Mock fetch for API tests
global.fetch = vi.fn()

// Add custom matchers if needed
expect.extend({
  toBeValidCurrency(received: string) {
    const currencyRegex = /^[A-Z]{3}$/
    const pass = currencyRegex.test(received)
    return {
      pass,
      message: () =>
        pass
          ? `expected ${received} not to be a valid currency code`
          : `expected ${received} to be a valid 3-letter currency code`,
    }
  },
})
