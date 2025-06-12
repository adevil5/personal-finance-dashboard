/**
 * API type definitions for Personal Finance Dashboard
 */

// Base types
export interface User {
  id: number
  username: string
  email: string
  phone?: string
  timezone: string
  currency: string
  created_at: string
  updated_at: string
}

export interface Category {
  id: number
  name: string
  user: number
  created_at: string
  updated_at: string
}

export interface Transaction {
  id: number
  user: number
  amount: string // Decimal string for precision
  amount_index: string
  transaction_type: 'income' | 'expense' | 'transfer'
  category: number | null
  category_detail?: Category
  description: string
  merchant?: string
  notes?: string
  date: string // ISO date string
  receipt?: string // File path
  tags: string[]
  created_at: string
  updated_at: string
  formatted_amount?: string
}

export interface Budget {
  id: number
  user: number
  name: string
  amount: string
  category: number | null
  category_detail?: Category
  period_start: string
  period_end: string
  alert_threshold: number
  alert_enabled: boolean
  is_active: boolean
  created_at: string
  updated_at: string
  // Calculated fields
  spent_amount?: string
  remaining_amount?: string
  utilization_percentage?: number
  is_over_budget?: boolean
}

// API Response types
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface APIError {
  detail?: string
  [field: string]: string | string[] | undefined
}

export interface ValidationError {
  [field: string]: string[]
}

// Analytics types
export interface SpendingTrend {
  date: string
  amount: string
  transaction_count: number
}

export interface CategoryBreakdown {
  category: string
  category_id: number | null
  total: string
  percentage: number
  transaction_count: number
}

export interface DashboardMetrics {
  current_month: {
    total_income: string
    total_expenses: string
    net_savings: string
    savings_rate: number
    top_categories: CategoryBreakdown[]
    recent_transactions: Transaction[]
  }
  comparison: {
    income_change: number
    expenses_change: number
    savings_change: number
  }
  budget_summary: {
    total_budgets: number
    active_budgets: number
    over_budget_count: number
    total_budget_amount: string
    total_spent: string
    overall_utilization: number
  }
}

// Form data types
export interface TransactionFormData {
  amount: string
  transaction_type: 'income' | 'expense' | 'transfer'
  category?: number
  description: string
  merchant?: string
  notes?: string
  date: string
  receipt?: File
  tags?: string[]
}

export interface BudgetFormData {
  name: string
  amount: string
  category?: number
  period_start: string
  period_end: string
  alert_threshold?: number
  alert_enabled?: boolean
}

// Filter types
export interface TransactionFilters {
  transaction_type?: 'income' | 'expense' | 'transfer'
  category?: number
  date_after?: string
  date_before?: string
  amount_min?: string
  amount_max?: string
  search?: string
  ordering?: string
  page?: number
  page_size?: number
}

export interface BudgetFilters {
  category?: number
  period_start_after?: string
  period_start_before?: string
  period_end_after?: string
  period_end_before?: string
  is_active?: boolean
  is_over_budget?: boolean
  ordering?: string
  page?: number
  page_size?: number
}
