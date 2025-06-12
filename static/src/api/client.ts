/**
 * Type-safe API client for Personal Finance Dashboard
 */

import type {
  Transaction,
  TransactionFormData,
  TransactionFilters,
  Category,
  Budget,
  BudgetFormData,
  BudgetFilters,
  PaginatedResponse,
  DashboardMetrics,
  SpendingTrend,
  CategoryBreakdown,
} from '@/types/api'

export class APIClientError extends Error {
  constructor(
    public status: number,
    public data: any,
    message?: string
  ) {
    super(message || `Request failed with status ${status}`)
    this.name = 'APIClientError'
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  headers?: Record<string, string>
  body?: any
  params?: Record<string, any>
}

export class APIClient {
  private baseURL: string
  private csrfToken: string

  constructor(baseURL: string = '/api/v1') {
    this.baseURL = baseURL
    this.csrfToken = this.getCSRFToken()
  }

  private getCSRFToken(): string {
    const token = document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]')?.content
    return token || ''
  }

  private buildQueryString(params: Record<string, any>): string {
    const searchParams = new URLSearchParams()

    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') {
        searchParams.append(key, String(value))
      }
    })

    const queryString = searchParams.toString()
    return queryString ? `?${queryString}` : ''
  }

  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { method = 'GET', headers = {}, body, params } = options

    const url = `${this.baseURL}${endpoint}${params ? this.buildQueryString(params) : ''}`

    const config: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.csrfToken,
        ...headers,
      },
    }

    if (body && method !== 'GET') {
      config.body = JSON.stringify(body)
    }

    try {
      const response = await fetch(url, config)

      const data = await response.json()

      if (!response.ok) {
        throw new APIClientError(response.status, data)
      }

      return data
    } catch (error) {
      if (error instanceof APIClientError) {
        throw error
      }
      throw new Error(`Network error: ${error}`)
    }
  }

  // Transaction endpoints
  transactions = {
    list: (filters?: TransactionFilters) =>
      this.request<PaginatedResponse<Transaction>>('/transactions/', filters ? { params: filters } : {}),

    get: (id: number) =>
      this.request<Transaction>(`/transactions/${id}/`),

    create: (data: TransactionFormData) =>
      this.request<Transaction>('/transactions/', { method: 'POST', body: data }),

    update: (id: number, data: Partial<TransactionFormData>) =>
      this.request<Transaction>(`/transactions/${id}/`, { method: 'PATCH', body: data }),

    delete: (id: number) =>
      this.request<void>(`/transactions/${id}/`, { method: 'DELETE' }),

    bulkCreate: (data: TransactionFormData[]) =>
      this.request<Transaction[]>('/transactions/bulk/', { method: 'POST', body: data }),

    export: (format: 'csv' | 'excel', filters?: TransactionFilters) =>
      this.request<Blob>(`/transactions/export/`, {
        params: { format, ...(filters || {}) },
        headers: { 'Accept': format === 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }
      }),
  }

  // Category endpoints
  categories = {
    list: () =>
      this.request<PaginatedResponse<Category>>('/categories/'),

    get: (id: number) =>
      this.request<Category>(`/categories/${id}/`),

    create: (data: { name: string }) =>
      this.request<Category>('/categories/', { method: 'POST', body: data }),

    update: (id: number, data: { name: string }) =>
      this.request<Category>(`/categories/${id}/`, { method: 'PATCH', body: data }),

    delete: (id: number) =>
      this.request<void>(`/categories/${id}/`, { method: 'DELETE' }),
  }

  // Budget endpoints
  budgets = {
    list: (filters?: BudgetFilters) =>
      this.request<PaginatedResponse<Budget>>('/budgets/', filters ? { params: filters } : {}),

    get: (id: number) =>
      this.request<Budget>(`/budgets/${id}/`),

    create: (data: BudgetFormData) =>
      this.request<Budget>('/budgets/', { method: 'POST', body: data }),

    update: (id: number, data: Partial<BudgetFormData>) =>
      this.request<Budget>(`/budgets/${id}/`, { method: 'PATCH', body: data }),

    delete: (id: number) =>
      this.request<void>(`/budgets/${id}/`, { method: 'DELETE' }),

    statistics: () =>
      this.request<any>('/budgets/statistics/'),

    current: () =>
      this.request<PaginatedResponse<Budget>>('/budgets/current/'),

    analytics: (params?: { period_start?: string; period_end?: string; compare_previous?: boolean; category_breakdown?: boolean }) =>
      this.request<any>('/budgets/analytics/', params ? { params } : {}),

    performance: (params?: { threshold?: number }) =>
      this.request<any>('/budgets/performance/', params ? { params } : {}),

    trends: (params?: { months?: number; category_id?: number }) =>
      this.request<any>('/budgets/trends/', params ? { params } : {}),
  }

  // Analytics endpoints
  analytics = {
    trends: (params: { start_date?: string; end_date?: string; period?: 'daily' | 'weekly' | 'monthly' }) =>
      this.request<{ trends: SpendingTrend[] }>('/analytics/trends/', { params }),

    categories: (params?: { start_date?: string; end_date?: string }) =>
      this.request<{ categories: CategoryBreakdown[] }>('/analytics/categories/', params ? { params } : {}),

    comparison: (params?: { start_date?: string; end_date?: string; previous_start?: string; previous_end?: string }) =>
      this.request<any>('/analytics/comparison/', params ? { params } : {}),

    topCategories: (params?: { start_date?: string; end_date?: string; limit?: number }) =>
      this.request<{ categories: CategoryBreakdown[] }>('/analytics/top-categories/', params ? { params } : {}),

    dayOfWeek: (params?: { start_date?: string; end_date?: string }) =>
      this.request<any>('/analytics/day-of-week/', params ? { params } : {}),

    dashboard: (params?: { month?: string; year?: number }) =>
      this.request<DashboardMetrics>('/analytics/dashboard/', params ? { params } : {}),
  }

  // User endpoints
  user = {
    profile: () =>
      this.request<any>('/users/profile/'),

    updateProfile: (data: any) =>
      this.request<any>('/users/profile/', { method: 'PATCH', body: data }),

    changePassword: (data: { old_password: string; new_password: string }) =>
      this.request<any>('/users/change-password/', { method: 'POST', body: data }),
  }
}
