/**
 * Currency formatting utilities for Personal Finance Dashboard
 */

export class CurrencyFormatter {
  private formatter: Intl.NumberFormat
  private currency: string
  private locale: string

  // Common currency codes
  private static readonly SUPPORTED_CURRENCIES = [
    'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD',
    'CNY', 'INR', 'KRW', 'SGD', 'HKD', 'NOK', 'SEK', 'DKK',
    'PLN', 'CZK', 'HUF', 'RON', 'BGN', 'HRK', 'RUB', 'TRY',
    'BRL', 'MXN', 'ARS', 'CLP', 'COP', 'PEN', 'UYU', 'ZAR'
  ]

  constructor(currency: string, locale: string = 'en-US') {
    this.currency = currency
    this.locale = locale
    this.formatter = new Intl.NumberFormat(this.locale, {
      style: 'currency',
      currency: this.currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  }

  /**
   * Format a decimal string or number to currency display format
   */
  format(amount: string | number): string {
    const numericAmount = this.parseToNumber(amount)
    if (isNaN(numericAmount)) {
      return this.formatter.format(0)
    }
    return this.formatter.format(numericAmount)
  }

  /**
   * Parse formatted currency string back to decimal string
   */
  parse(formattedAmount: string): string {
    // Remove currency symbols and thousand separators
    const cleanedAmount = formattedAmount
      .replace(/[^0-9,.\-]/g, '')
      .replace(/,/g, '.')
      .replace(/\.(?=.*\.)/g, '') // Keep only the last dot as decimal separator

    const numericAmount = parseFloat(cleanedAmount)
    if (isNaN(numericAmount)) {
      return '0.00'
    }

    return numericAmount.toFixed(2)
  }

  /**
   * Validate if a string represents a valid currency amount
   */
  isValidAmount(amount: string): boolean {
    if (!amount || amount.trim() === '') {
      return false
    }

    // Check if it's a valid number
    const numericAmount = parseFloat(amount)
    if (isNaN(numericAmount)) {
      return false
    }

    // Check decimal places (max 2)
    const parts = amount.split('.')
    if (parts.length > 2) {
      return false
    }

    if (parts.length === 2 && parts[1] && parts[1].length > 2) {
      return false
    }

    return true
  }

  /**
   * Get the currency symbol
   */
  getSymbol(): string {
    // Format 0 and extract the symbol
    const formatted = this.formatter.format(0)
    const symbol = formatted.replace(/[0-9,.\s]/g, '').trim()
    return symbol || this.currency
  }

  /**
   * Get decimal places for the currency (usually 2, but 0 for JPY)
   */
  getDecimalPlaces(): number {
    return this.currency === 'JPY' ? 0 : 2
  }

  /**
   * Get list of supported currency codes
   */
  static getSupportedCurrencies(): string[] {
    return [...this.SUPPORTED_CURRENCIES]
  }

  /**
   * Validate if a currency code is supported
   */
  static isValidCurrencyCode(code: string): boolean {
    return this.SUPPORTED_CURRENCIES.includes(code)
  }

  /**
   * Helper to convert various inputs to number
   */
  private parseToNumber(value: string | number): number {
    if (typeof value === 'number') {
      return value
    }

    if (!value || value.trim() === '') {
      return 0
    }

    const parsed = parseFloat(value)
    return isNaN(parsed) ? 0 : parsed
  }
}
