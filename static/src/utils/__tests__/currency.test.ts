import { describe, it, expect, beforeEach } from 'vitest'
import { CurrencyFormatter } from '../currency'

describe('CurrencyFormatter', () => {
  let formatter: CurrencyFormatter

  describe('USD formatting', () => {
    beforeEach(() => {
      formatter = new CurrencyFormatter('USD', 'en-US')
    })

    it('should format positive amounts correctly', () => {
      expect(formatter.format('100.00')).toBe('$100.00')
      expect(formatter.format('1000.50')).toBe('$1,000.50')
      expect(formatter.format('1234567.89')).toBe('$1,234,567.89')
    })

    it('should format negative amounts correctly', () => {
      expect(formatter.format('-100.00')).toBe('-$100.00')
      expect(formatter.format('-1000.50')).toBe('-$1,000.50')
    })

    it('should handle zero correctly', () => {
      expect(formatter.format('0')).toBe('$0.00')
      expect(formatter.format('0.00')).toBe('$0.00')
    })

    it('should handle decimal precision', () => {
      expect(formatter.format('100')).toBe('$100.00')
      expect(formatter.format('100.1')).toBe('$100.10')
      expect(formatter.format('100.999')).toBe('$101.00') // Rounds up
    })

    it('should handle invalid input gracefully', () => {
      expect(formatter.format('')).toBe('$0.00')
      expect(formatter.format('invalid')).toBe('$0.00')
      expect(formatter.format('abc123')).toBe('$0.00')
    })

    it('should handle very large numbers', () => {
      expect(formatter.format('999999999999.99')).toBe('$999,999,999,999.99')
    })
  })

  describe('EUR formatting', () => {
    beforeEach(() => {
      formatter = new CurrencyFormatter('EUR', 'de-DE')
    })

    it('should format EUR amounts with correct symbol and separators', () => {
      // EUR formatting can vary by environment, check key components
      const formatted100 = formatter.format('100.00')
      const formatted1000 = formatter.format('1000.50')
      const formatted1234567 = formatter.format('1234567.89')

      // Check that amounts contain expected parts
      expect(formatted100).toContain('100')
      expect(formatted100).toContain('00')
      expect(formatted100).toContain('€')

      expect(formatted1000).toContain('000')
      expect(formatted1000).toContain('50')
      expect(formatted1000).toContain('€')

      expect(formatted1234567).toContain('234')
      expect(formatted1234567).toContain('567')
      expect(formatted1234567).toContain('89')
      expect(formatted1234567).toContain('€')
    })
  })

  describe('GBP formatting', () => {
    beforeEach(() => {
      formatter = new CurrencyFormatter('GBP', 'en-GB')
    })

    it('should format GBP amounts correctly', () => {
      expect(formatter.format('100.00')).toBe('£100.00')
      expect(formatter.format('1000.50')).toBe('£1,000.50')
    })
  })

  describe('Custom locale support', () => {
    it('should support different locales for the same currency', () => {
      const usFormatter = new CurrencyFormatter('USD', 'en-US')
      const frFormatter = new CurrencyFormatter('USD', 'fr-FR')

      expect(usFormatter.format('1234.56')).toBe('$1,234.56')

      // French formatting can use different space characters
      const frFormatted = frFormatter.format('1234.56')
      expect(frFormatted).toContain('234')
      expect(frFormatted).toContain('56')
      expect(frFormatted).toContain('$')
    })
  })

  describe('Utility methods', () => {
    beforeEach(() => {
      formatter = new CurrencyFormatter('USD', 'en-US')
    })

    it('should parse formatted currency back to number', () => {
      expect(formatter.parse('$1,234.56')).toBe('1234.56')
      expect(formatter.parse('-$1,234.56')).toBe('-1234.56')
      expect(formatter.parse('$0.00')).toBe('0.00')
    })

    it('should validate currency amounts', () => {
      expect(formatter.isValidAmount('100.00')).toBe(true)
      expect(formatter.isValidAmount('-100.00')).toBe(true)
      expect(formatter.isValidAmount('0')).toBe(true)
      expect(formatter.isValidAmount('abc')).toBe(false)
      expect(formatter.isValidAmount('')).toBe(false)
      expect(formatter.isValidAmount('100.999')).toBe(false) // More than 2 decimals
    })

    it('should get currency symbol', () => {
      expect(formatter.getSymbol()).toBe('$')

      const eurFormatter = new CurrencyFormatter('EUR', 'en-US')
      expect(eurFormatter.getSymbol()).toBe('€')
    })

    it('should get decimal places', () => {
      expect(formatter.getDecimalPlaces()).toBe(2)
    })
  })

  describe('Static utility methods', () => {
    it('should provide list of supported currencies', () => {
      const currencies = CurrencyFormatter.getSupportedCurrencies()
      expect(currencies).toContain('USD')
      expect(currencies).toContain('EUR')
      expect(currencies).toContain('GBP')
      expect(currencies).toContain('JPY')
      expect(currencies.length).toBeGreaterThan(10)
    })

    it('should validate currency codes', () => {
      expect(CurrencyFormatter.isValidCurrencyCode('USD')).toBe(true)
      expect(CurrencyFormatter.isValidCurrencyCode('EUR')).toBe(true)
      expect(CurrencyFormatter.isValidCurrencyCode('XXX')).toBe(false)
      expect(CurrencyFormatter.isValidCurrencyCode('US')).toBe(false)
      expect(CurrencyFormatter.isValidCurrencyCode('USDD')).toBe(false)
    })
  })
})
