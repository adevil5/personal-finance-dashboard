import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { APIClient } from '../client'
import type { Transaction, Category, Budget, PaginatedResponse } from '@/types/api'

describe('APIClient', () => {
  let client: APIClient
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    fetchMock = vi.fn()
    global.fetch = fetchMock

    // Mock CSRF token
    document.head.innerHTML = '<meta name="csrf-token" content="test-csrf-token">'

    client = new APIClient('/api/v1')
  })

  afterEach(() => {
    vi.clearAllMocks()
    document.head.innerHTML = ''
  })

  describe('constructor', () => {
    it('should initialize with base URL', () => {
      expect(client).toBeDefined()
      expect(client['baseURL']).toBe('/api/v1')
    })

    it('should get CSRF token from meta tag', () => {
      expect(client['csrfToken']).toBe('test-csrf-token')
    })

    it('should handle missing CSRF token', () => {
      document.head.innerHTML = ''
      const newClient = new APIClient('/api/v1')
      expect(newClient['csrfToken']).toBe('')
    })
  })

  describe('request method', () => {
    it('should make GET requests correctly', async () => {
      const mockResponse = { data: 'test' }
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await client['request']('/test')

      expect(fetchMock).toHaveBeenCalledWith('/api/v1/test', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': 'test-csrf-token',
        },
      })
      expect(result).toEqual(mockResponse)
    })

    it('should make POST requests with body', async () => {
      const mockBody = { name: 'test' }
      const mockResponse = { id: 1, ...mockBody }
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await client['request']('/test', {
        method: 'POST',
        body: mockBody,
      })

      expect(fetchMock).toHaveBeenCalledWith('/api/v1/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': 'test-csrf-token',
        },
        body: JSON.stringify(mockBody),
      })
      expect(result).toEqual(mockResponse)
    })

    it('should handle API errors', async () => {
      const mockError = { detail: 'Not found' }
      fetchMock.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => mockError,
      })

      await expect(client['request']('/test')).rejects.toMatchObject({
        status: 404,
        data: mockError,
      })
    })

    it('should handle network errors', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Network error'))

      await expect(client['request']('/test')).rejects.toThrow('Network error')
    })

    it('should build query strings correctly', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      })

      await client['request']('/test', {
        params: {
          page: 1,
          search: 'test query',
          amount: 100.50,
          empty: null,
          zero: 0,
        },
      })

      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/test?page=1&search=test+query&amount=100.5&zero=0',
        expect.any(Object)
      )
    })
  })

  describe('transactions API', () => {
    const mockTransaction: Transaction = {
      id: 1,
      user: 1,
      amount: '100.00',
      amount_index: '100.00',
      transaction_type: 'expense',
      category: 1,
      description: 'Test transaction',
      date: '2024-01-01',
      tags: [],
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    }

    it('should get transactions list', async () => {
      const mockResponse: PaginatedResponse<Transaction> = {
        count: 1,
        next: null,
        previous: null,
        results: [mockTransaction],
      }

      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await client.transactions.list({
        page: 1,
        transaction_type: 'expense',
      })

      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/transactions/?page=1&transaction_type=expense',
        expect.any(Object)
      )
      expect(result).toEqual(mockResponse)
    })

    it('should get single transaction', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTransaction,
      })

      const result = await client.transactions.get(1)

      expect(fetchMock).toHaveBeenCalledWith('/api/v1/transactions/1/', expect.any(Object))
      expect(result).toEqual(mockTransaction)
    })

    it('should create transaction', async () => {
      const newTransaction = {
        amount: '100.00',
        transaction_type: 'expense' as const,
        category: 1,
        description: 'New transaction',
        date: '2024-01-01',
      }

      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 2, ...newTransaction }),
      })

      const result = await client.transactions.create(newTransaction)

      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/transactions/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(newTransaction),
        })
      )
      expect(result.id).toBe(2)
    })

    it('should update transaction', async () => {
      const updates = { description: 'Updated description' }
      const updatedTransaction = { ...mockTransaction, ...updates }

      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => updatedTransaction,
      })

      const result = await client.transactions.update(1, updates)

      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/transactions/1/',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify(updates),
        })
      )
      expect(result).toEqual(updatedTransaction)
    })

    it('should delete transaction', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      })

      await client.transactions.delete(1)

      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/transactions/1/',
        expect.objectContaining({
          method: 'DELETE',
        })
      )
    })
  })

  describe('categories API', () => {
    const mockCategory: Category = {
      id: 1,
      name: 'Groceries',
      user: 1,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    }

    it('should get categories list', async () => {
      const mockResponse: PaginatedResponse<Category> = {
        count: 1,
        next: null,
        previous: null,
        results: [mockCategory],
      }

      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await client.categories.list()

      expect(fetchMock).toHaveBeenCalledWith('/api/v1/categories/', expect.any(Object))
      expect(result).toEqual(mockResponse)
    })

    it('should create category', async () => {
      const newCategory = { name: 'Shopping' }

      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 2, ...newCategory }),
      })

      const result = await client.categories.create(newCategory)

      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/categories/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(newCategory),
        })
      )
      expect(result.name).toBe('Shopping')
    })
  })

  describe('budgets API', () => {
    const mockBudget: Budget = {
      id: 1,
      user: 1,
      name: 'Monthly Groceries',
      amount: '500.00',
      category: 1,
      period_start: '2024-01-01',
      period_end: '2024-01-31',
      alert_threshold: 80,
      alert_enabled: true,
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    }

    it('should get budgets list with filters', async () => {
      const mockResponse: PaginatedResponse<Budget> = {
        count: 1,
        next: null,
        previous: null,
        results: [mockBudget],
      }

      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      const result = await client.budgets.list({
        is_active: true,
        category: 1,
      })

      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/budgets/?is_active=true&category=1',
        expect.any(Object)
      )
      expect(result).toEqual(mockResponse)
    })

    it('should get budget statistics', async () => {
      const mockStats = {
        total_budget: '1500.00',
        total_spent: '750.00',
        utilization_percentage: 50,
      }

      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStats,
      })

      const result = await client.budgets.statistics()

      expect(fetchMock).toHaveBeenCalledWith('/api/v1/budgets/statistics/', expect.any(Object))
      expect(result).toEqual(mockStats)
    })

    it('should get budget analytics', async () => {
      const mockAnalytics = {
        spending_by_category: [],
        budget_utilization: [],
      }

      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAnalytics,
      })

      const result = await client.budgets.analytics({
        period_start: '2024-01-01',
        period_end: '2024-01-31',
      })

      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/budgets/analytics/?period_start=2024-01-01&period_end=2024-01-31',
        expect.any(Object)
      )
      expect(result).toEqual(mockAnalytics)
    })
  })

  describe('analytics API', () => {
    it('should get spending trends', async () => {
      const mockTrends = {
        trends: [
          { date: '2024-01-01', amount: '100.00', transaction_count: 5 },
        ],
      }

      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrends,
      })

      const result = await client.analytics.trends({
        start_date: '2024-01-01',
        end_date: '2024-01-31',
        period: 'daily',
      })

      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/analytics/trends/?start_date=2024-01-01&end_date=2024-01-31&period=daily',
        expect.any(Object)
      )
      expect(result).toEqual(mockTrends)
    })

    it('should get dashboard metrics', async () => {
      const mockMetrics = {
        current_month: {
          total_income: '3000.00',
          total_expenses: '2000.00',
          net_savings: '1000.00',
          savings_rate: 33.33,
          top_categories: [],
          recent_transactions: [],
        },
        comparison: {
          income_change: 10,
          expenses_change: -5,
          savings_change: 15,
        },
        budget_summary: {
          total_budgets: 5,
          active_budgets: 4,
          over_budget_count: 1,
          total_budget_amount: '2500.00',
          total_spent: '2000.00',
          overall_utilization: 80,
        },
      }

      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetrics,
      })

      const result = await client.analytics.dashboard()

      expect(fetchMock).toHaveBeenCalledWith('/api/v1/analytics/dashboard/', expect.any(Object))
      expect(result).toEqual(mockMetrics)
    })
  })

  describe('error handling', () => {
    it('should handle validation errors', async () => {
      const validationError = {
        amount: ['Amount must be greater than 0'],
        description: ['This field is required'],
      }

      fetchMock.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => validationError,
      })

      try {
        await client.transactions.create({
          amount: '0',
          transaction_type: 'expense',
          description: '',
          date: '2024-01-01',
        })
        expect.fail('Should have thrown an error')
      } catch (error: any) {
        expect(error.status).toBe(400)
        expect(error.data).toEqual(validationError)
        expect(error.message).toBe('Request failed with status 400')
      }
    })

    it('should handle authentication errors', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Authentication credentials were not provided.' }),
      })

      await expect(client.transactions.list()).rejects.toMatchObject({
        status: 401,
        data: { detail: 'Authentication credentials were not provided.' },
      })
    })
  })
})
