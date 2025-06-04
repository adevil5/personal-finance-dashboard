import './style.css'

/**
 * Main TypeScript entry point for Personal Finance Dashboard
 */

// Import HTMX for enhanced interactivity
import 'htmx.org'

// Chart.js for data visualization
import {
  Chart,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'

// Register Chart.js components
Chart.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
)

// Global app configuration
interface AppConfig {
  debug: boolean
  apiBaseUrl: string
  csrfToken: string
}

// Initialize application
class PersonalFinanceApp {
  private config: AppConfig

  constructor() {
    this.config = {
      debug: __DEV__,
      apiBaseUrl: '/api/v1',
      csrfToken: this.getCSRFToken(),
    }

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

  private initializeCharts(): void {
    // Initialize Chart.js instances for dashboard
    const chartElements = document.querySelectorAll<HTMLCanvasElement>('[data-chart]')

    chartElements.forEach(element => {
      const chartType = element.dataset.chart
      const chartData = element.dataset.chartData

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

  private createChart(canvas: HTMLCanvasElement, type: string, data: any): Chart | null {
    try {
      return new Chart(canvas, {
        type: type as any,
        data,
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'top',
            },
            title: {
              display: true,
              text: canvas.dataset.chartTitle || 'Chart',
            },
          },
        },
      })
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
    })
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
        submitButton.textContent = submitButton.dataset.originalText || 'Submit'
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
  new PersonalFinanceApp()
})

// Export for global access if needed
declare global {
  interface Window {
    PFD: PersonalFinanceApp
  }
}
