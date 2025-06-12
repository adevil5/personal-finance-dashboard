import './style.css'

/**
 * Main TypeScript entry point for Personal Finance Dashboard
 */

// Import HTMX for enhanced interactivity
import 'htmx.org'

// Chart.js for data visualization
// Note: Chart.js will be imported when needed for specific components

// Import our utilities
import { APIClient } from '@/api'
import { CurrencyFormatter, FormValidator, validateAmount } from '@/utils'

// Chart.js components will be registered when needed

// Global app configuration
interface AppConfig {
  debug: boolean
  apiBaseUrl: string
  csrfToken: string
  currency: string
  locale: string
}

// Initialize application
class PersonalFinanceApp {
  private config: AppConfig
  private apiClient: APIClient
  private currencyFormatter: CurrencyFormatter

  constructor() {
    this.config = {
      debug: __DEV__,
      apiBaseUrl: '/api/v1',
      csrfToken: this.getCSRFToken(),
      currency: this.getUserCurrency(),
      locale: this.getUserLocale(),
    }

    // Initialize API client
    this.apiClient = new APIClient(this.config.apiBaseUrl)

    // Initialize currency formatter
    this.currencyFormatter = new CurrencyFormatter(this.config.currency, this.config.locale)

    this.init()
  }

  private init(): void {
    console.log('Personal Finance Dashboard initialized')

    // Initialize components
    this.initializeCharts()
    this.initializeHTMX()
    this.initializeFormHandlers()
    this.initializeTheme()
  }

  private getCSRFToken(): string {
    const token = document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]')?.content
    return token || ''
  }

  private getUserCurrency(): string {
    // Get from data attribute or default to USD
    return document.documentElement.dataset['currency'] || 'USD'
  }

  private getUserLocale(): string {
    // Get from data attribute or default to navigator language
    return document.documentElement.dataset['locale'] || navigator.language || 'en-US'
  }

  private initializeCharts(): void {
    // Initialize Chart.js instances for dashboard
    const chartElements = document.querySelectorAll<HTMLCanvasElement>('[data-chart]')

    chartElements.forEach(element => {
      const chartType = element.dataset['chart']
      const chartData = element.dataset['chartData']

      if (chartType && chartData) {
        try {
          const data = JSON.parse(chartData)
          this.createChart(element, chartType, data)
        } catch (error) {
          console.error('Failed to parse chart data:', error)
        }
      }
    })
  }

  private createChart(canvas: HTMLCanvasElement, type: string, data: any): any | null {
    try {
      // Chart.js will be imported dynamically when needed
      console.log(`Creating chart of type ${type} for canvas`, canvas, data)
      return null // Placeholder for now
    } catch (error) {
      console.error('Failed to create chart:', error)
      return null
    }
  }

  private initializeHTMX(): void {
    // HTMX configuration and event handlers
    document.addEventListener('htmx:afterRequest', (event: any) => {
      const xhr = event.detail.xhr
      if (xhr.status >= 400) {
        console.error('HTMX request failed:', xhr.status, xhr.statusText)
      }
    })

    document.addEventListener('htmx:beforeRequest', (event: any) => {
      // Add CSRF token to HTMX requests
      if (this.config.csrfToken) {
        event.detail.xhr.setRequestHeader('X-CSRFToken', this.config.csrfToken)
      }
    })
  }

  private initializeFormHandlers(): void {
    // Enhanced form handling
    const forms = document.querySelectorAll<HTMLFormElement>('[data-enhanced-form]')

    forms.forEach(form => {
      form.addEventListener('submit', this.handleFormSubmit.bind(this))

      // Initialize form validation for transaction forms
      if (form.dataset['formType'] === 'transaction') {
        this.initializeTransactionFormValidation(form)
      }
    })

    // Initialize amount fields with currency formatting
    this.initializeAmountFields()
  }

  private initializeTransactionFormValidation(form: HTMLFormElement): void {
    const validator = new FormValidator({
      amount: [
        { rule: 'required', message: 'Amount is required' },
        { rule: 'amount', message: 'Please enter a valid amount' },
      ],
      description: [
        { rule: 'required', message: 'Description is required' },
        { rule: 'maxLength', value: 255, message: 'Description is too long' },
      ],
      date: [
        { rule: 'required', message: 'Date is required' },
      ],
    })

    form.addEventListener('submit', async (e) => {
      e.preventDefault()

      const formData = new FormData(form)
      const data = Object.fromEntries(formData.entries())

      const result = validator.validate(data)

      if (!result.isValid) {
        this.displayFormErrors(form, result.errors)
        return
      }

      // Form is valid, proceed with submission
      this.submitTransactionForm(form, data)
    })
  }

  private initializeAmountFields(): void {
    const amountFields = document.querySelectorAll<HTMLInputElement>('[data-currency-input]')

    amountFields.forEach(field => {
      // Format on blur
      field.addEventListener('blur', () => {
        const value = field.value
        if (value && validateAmount(value)) {
          field.value = this.currencyFormatter.format(value).replace(/[^0-9.-]/g, '')
        }
      })

      // Display formatted value next to input
      const display = document.createElement('span')
      display.className = 'currency-display ml-2 text-gray-600'
      field.parentElement?.appendChild(display)

      field.addEventListener('input', () => {
        const value = field.value
        if (value && validateAmount(value)) {
          display.textContent = this.currencyFormatter.format(value)
        } else {
          display.textContent = ''
        }
      })
    })
  }

  private displayFormErrors(form: HTMLFormElement, errors: Record<string, string[]>): void {
    // Clear previous errors
    form.querySelectorAll('.error-message').forEach(el => el.remove())

    // Display new errors
    Object.entries(errors).forEach(([field, messages]) => {
      const input = form.querySelector(`[name="${field}"]`)
      if (input && messages.length > 0) {
        const errorEl = document.createElement('div')
        errorEl.className = 'error-message text-red-600 text-sm mt-1'
        errorEl.textContent = messages[0] || ''
        input.parentElement?.appendChild(errorEl)
      }
    })
  }

  private async submitTransactionForm(form: HTMLFormElement, data: any): Promise<void> {
    try {
      const formData: any = {
        amount: data.amount,
        transaction_type: data.transaction_type,
        description: data.description,
        date: data.date,
      }

      if (data.category) {
        formData.category = parseInt(data.category as string)
      }

      if (data.merchant) {
        formData.merchant = data.merchant
      }

      if (data.notes) {
        formData.notes = data.notes
      }

      const transaction = await this.apiClient.transactions.create(formData)

      // Success - redirect or update UI
      window.location.href = `/expenses/transactions/${transaction.id}/`
    } catch (error: any) {
      if (error.status === 400 && error.data) {
        this.displayFormErrors(form, error.data)
      } else {
        console.error('Failed to create transaction:', error)
      }
    }
  }

  private handleFormSubmit(event: Event): void {
    const form = event.target as HTMLFormElement
    const submitButton = form.querySelector<HTMLButtonElement>('[type="submit"]')

    if (submitButton) {
      submitButton.disabled = true
      submitButton.textContent = 'Processing...'

      // Re-enable after a delay if not handled by HTMX
      setTimeout(() => {
        submitButton.disabled = false
        submitButton.textContent = submitButton.dataset['originalText'] || 'Submit'
      }, 5000)
    }
  }

  private initializeTheme(): void {
    // Theme switching functionality
    const themeToggle = document.querySelector<HTMLButtonElement>('[data-theme-toggle]')

    if (themeToggle) {
      themeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme')
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark'

        document.documentElement.setAttribute('data-theme', newTheme)
        localStorage.setItem('theme', newTheme)
      })
    }

    // Apply saved theme
    const savedTheme = localStorage.getItem('theme')
    if (savedTheme) {
      document.documentElement.setAttribute('data-theme', savedTheme)
    }
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const app = new PersonalFinanceApp()

  // Make utilities available globally for debugging/integration
  window.PFD = {
    app,
    api: app['apiClient'],
    currencyFormatter: app['currencyFormatter'],
  }
})

// Export for global access if needed
declare global {
  interface Window {
    PFD: {
      app: PersonalFinanceApp
      api: APIClient
      currencyFormatter: CurrencyFormatter
    }
  }
}
