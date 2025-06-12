# API Reference

Complete reference for the Personal Finance Dashboard REST API. All endpoints require authentication and follow RESTful conventions.

## Table of Contents

1. [Authentication](#authentication)
2. [Core API Endpoints](#core-api-endpoints)
3. [Analytics Endpoints](#analytics-endpoints)
4. [Budget Endpoints](#budget-endpoints)
5. [Response Formats](#response-formats)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [Examples](#examples)

## Authentication

The API uses Django REST Framework Token Authentication.

### Get Authentication Token

```bash
POST /api/auth/token/
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user_id": 123,
  "username": "your_username"
}
```

### Using the Token

Include the token in the Authorization header for all API requests:

```bash
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

## Core API Endpoints

### Transactions

#### List Transactions
```
GET /api/v1/transactions/
```

**Query Parameters:**
- `transaction_type` - Filter by type (`income`, `expense`, `transfer`)
- `category` - Filter by category ID
- `date_after` - Transactions after date (YYYY-MM-DD)
- `date_before` - Transactions before date (YYYY-MM-DD)
- `amount_min` - Minimum amount filter
- `amount_max` - Maximum amount filter
- `search` - Search in notes and merchant fields
- `ordering` - Sort by field (`date`, `-date`, `amount`, `-amount`)
- `page` - Page number for pagination
- `page_size` - Results per page (default: 20, max: 100)

**Example Request:**
```bash
curl -H "Authorization: Token your-token" \
  "http://localhost:8000/api/v1/transactions/?transaction_type=expense&date_after=2024-01-01&ordering=-date"
```

**Response:**
```json
{
  "count": 150,
  "next": "http://localhost:8000/api/v1/transactions/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "amount": "45.67",
      "formatted_amount": "USD 45.67",
      "merchant": "Coffee Shop",
      "notes": "Morning coffee",
      "transaction_type": "expense",
      "date": "2024-01-15",
      "category": {
        "id": 5,
        "name": "Food & Dining",
        "color": "#FF6B6B"
      },
      "category_id": 5,
      "receipt": "http://localhost:8000/media/receipts/user_1/receipt_123.jpg",
      "created_at": "2024-01-15T09:30:00Z",
      "updated_at": "2024-01-15T09:30:00Z"
    }
  ]
}
```

#### Create Transaction
```
POST /api/v1/transactions/
Content-Type: application/json
```

**Request Body:**
```json
{
  "amount": "45.67",
  "merchant": "Coffee Shop",
  "notes": "Morning coffee",
  "transaction_type": "expense",
  "date": "2024-01-15",
  "category_id": 5
}
```

**File Upload (Multipart):**
```bash
curl -X POST \
  -H "Authorization: Token your-token" \
  -F "amount=45.67" \
  -F "merchant=Coffee Shop" \
  -F "transaction_type=expense" \
  -F "category_id=5" \
  -F "receipt=@/path/to/receipt.jpg" \
  http://localhost:8000/api/v1/transactions/
```

#### Get Transaction
```
GET /api/v1/transactions/{id}/
```

#### Update Transaction
```
PUT /api/v1/transactions/{id}/
PATCH /api/v1/transactions/{id}/
```

#### Delete Transaction
```
DELETE /api/v1/transactions/{id}/
```

### Categories

#### List Categories
```
GET /api/v1/categories/
```

**Response:**
```json
{
  "count": 12,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Food & Dining",
      "color": "#FF6B6B",
      "icon": "utensils",
      "parent": null,
      "children": [
        {
          "id": 2,
          "name": "Restaurants",
          "color": "#FF6B6B",
          "icon": "restaurant",
          "parent": 1
        }
      ],
      "transaction_count": 45,
      "total_spent": "1234.56"
    }
  ]
}
```

#### Create Category
```
POST /api/v1/categories/
Content-Type: application/json

{
  "name": "New Category",
  "color": "#4ECDC4",
  "icon": "shopping-cart",
  "parent": null
}
```

## Analytics Endpoints

### Dashboard Metrics
```
GET /api/analytics/dashboard/
```

**Query Parameters:**
- `month` - Specific month (YYYY-MM, defaults to current month)

**Response:**
```json
{
  "current_month": {
    "income": "5000.00",
    "expenses": "3200.00",
    "net_savings": "1800.00",
    "savings_rate": 36.0,
    "transaction_count": 87
  },
  "previous_month": {
    "income": "4800.00",
    "expenses": "3100.00",
    "net_savings": "1700.00",
    "savings_rate": 35.4,
    "transaction_count": 82
  },
  "month_over_month": {
    "income_change": 4.17,
    "expenses_change": 3.23,
    "savings_change": 5.88,
    "savings_rate_change": 0.6
  },
  "top_categories": [
    {
      "category_name": "Food & Dining",
      "amount": "650.00",
      "percentage": 20.31
    },
    {
      "category_name": "Transportation",
      "amount": "450.00",
      "percentage": 14.06
    }
  ],
  "recent_transactions": [
    {
      "id": 123,
      "amount": "45.67",
      "merchant": "Coffee Shop",
      "category": "Food & Dining",
      "date": "2024-01-15",
      "transaction_type": "expense"
    }
  ],
  "budget_summary": {
    "total_budgets": 8,
    "over_budget_count": 2,
    "average_utilization": 78.5
  }
}
```

### Spending Trends
```
GET /api/analytics/trends/
```

**Query Parameters:**
- `start_date` - Start date (YYYY-MM-DD)
- `end_date` - End date (YYYY-MM-DD)
- `period` - Grouping period (`daily`, `weekly`, `monthly`)

**Response:**
```json
{
  "period": "monthly",
  "data": [
    {
      "period": "2024-01",
      "total": "3200.00",
      "transaction_count": 45
    },
    {
      "period": "2024-02",
      "total": "2800.00",
      "transaction_count": 38
    }
  ]
}
```

### Category Breakdown
```
GET /api/analytics/categories/
```

**Query Parameters:**
- `start_date` - Start date (YYYY-MM-DD)
- `end_date` - End date (YYYY-MM-DD)

**Response:**
```json
{
  "total_expenses": "3200.00",
  "categories": [
    {
      "category_name": "Food & Dining",
      "amount": "650.00",
      "percentage": 20.31,
      "transaction_count": 12
    },
    {
      "category_name": "Transportation",
      "amount": "450.00",
      "percentage": 14.06,
      "transaction_count": 8
    }
  ]
}
```

### Period Comparison
```
GET /api/analytics/comparison/
```

**Query Parameters:**
- `start_date` - Current period start (YYYY-MM-DD)
- `end_date` - Current period end (YYYY-MM-DD)

**Response:**
```json
{
  "current_period": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "total_income": "5000.00",
    "total_expenses": "3200.00",
    "net_savings": "1800.00",
    "transaction_count": 87
  },
  "previous_period": {
    "start_date": "2023-12-01",
    "end_date": "2023-12-31",
    "total_income": "4800.00",
    "total_expenses": "3100.00",
    "net_savings": "1700.00",
    "transaction_count": 82
  },
  "changes": {
    "income_change": 4.17,
    "expenses_change": 3.23,
    "savings_change": 5.88,
    "transaction_count_change": 6.10
  }
}
```

### Top Categories
```
GET /api/analytics/top-categories/
```

**Query Parameters:**
- `start_date` - Start date (YYYY-MM-DD)
- `end_date` - End date (YYYY-MM-DD)
- `limit` - Number of top categories (1-20, default: 5)

### Day of Week Analysis
```
GET /api/analytics/day-of-week/
```

**Query Parameters:**
- `start_date` - Start date (YYYY-MM-DD)
- `end_date` - End date (YYYY-MM-DD)

**Response:**
```json
{
  "data": [
    {
      "day_of_week": "Monday",
      "total": "145.67",
      "average": "18.21",
      "transaction_count": 8
    },
    {
      "day_of_week": "Tuesday",
      "total": "234.50",
      "average": "29.31",
      "transaction_count": 8
    }
  ]
}
```

## Budget Endpoints

### List Budgets
```
GET /api/v1/budgets/
```

**Query Parameters:**
- `is_active` - Filter active budgets (`true`/`false`)
- `category` - Filter by category ID
- `period_start_after` - Budgets starting after date
- `period_end_before` - Budgets ending before date

**Response:**
```json
{
  "count": 8,
  "results": [
    {
      "id": 1,
      "name": "Food Budget",
      "amount": "600.00",
      "spent_amount": "450.00",
      "remaining_amount": "150.00",
      "utilization_percentage": 75.0,
      "is_over_budget": false,
      "period_start": "2024-01-01",
      "period_end": "2024-01-31",
      "category": {
        "id": 5,
        "name": "Food & Dining"
      },
      "warning_threshold": 80.0,
      "critical_threshold": 100.0,
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### Create Budget
```
POST /api/v1/budgets/
Content-Type: application/json

{
  "name": "Transportation Budget",
  "amount": "400.00",
  "period_start": "2024-01-01",
  "period_end": "2024-01-31",
  "category_id": 3,
  "warning_threshold": 80.0,
  "critical_threshold": 100.0
}
```

### Budget Statistics
```
GET /api/v1/budgets/statistics/
```

**Response:**
```json
{
  "total_budgets": 8,
  "active_budgets": 6,
  "total_budgeted": "4800.00",
  "total_spent": "3650.00",
  "average_utilization": 76.04,
  "over_budget_count": 1,
  "under_budget_count": 5,
  "performance_distribution": {
    "excellent": 2,
    "good": 3,
    "warning": 2,
    "over_budget": 1
  }
}
```

### Current Budgets
```
GET /api/v1/budgets/current/
```

Returns budgets active for the current date.

### Budget Analytics
```
GET /api/v1/budgets/{id}/analytics/
```

**Query Parameters:**
- `compare_previous` - Include previous period comparison (`true`/`false`)
- `category_breakdown` - Include category breakdown (`true`/`false`)

### Budget Performance
```
GET /api/v1/budgets/performance/
```

**Query Parameters:**
- `good_threshold` - Performance threshold for "good" (default: 80.0)

### Budget Trends
```
GET /api/v1/budgets/trends/
```

**Query Parameters:**
- `months` - Number of months to analyze (1-24, default: 6)
- `category_id` - Filter by category

## Response Formats

### Pagination

All list endpoints use cursor-based pagination:

```json
{
  "count": 150,
  "next": "http://localhost:8000/api/v1/transactions/?page=2",
  "previous": null,
  "results": [...]
}
```

### Timestamps

All timestamps are in ISO 8601 format with UTC timezone:
```json
{
  "created_at": "2024-01-15T09:30:00Z",
  "updated_at": "2024-01-15T09:30:00Z"
}
```

### Decimal Fields

Financial amounts are returned as strings to preserve precision:
```json
{
  "amount": "123.45",
  "total_spent": "1234.56"
}
```

## Error Handling

### Error Response Format

```json
{
  "detail": "Error message",
  "field_errors": {
    "amount": ["This field is required."],
    "category_id": ["Invalid category ID."]
  },
  "non_field_errors": ["Custom validation error."],
  "error_code": "INVALID_REQUEST"
}
```

### HTTP Status Codes

- `200` - Success
- `201` - Created
- `204` - No Content (successful deletion)
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `405` - Method Not Allowed
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error

### Common Error Codes

- `AUTHENTICATION_FAILED` - Invalid credentials
- `TOKEN_EXPIRED` - Authentication token expired
- `VALIDATION_ERROR` - Request validation failed
- `PERMISSION_DENIED` - Insufficient permissions
- `NOT_FOUND` - Resource not found
- `RATE_LIMITED` - Too many requests

## Rate Limiting

API endpoints are rate limited to prevent abuse:

- **Authenticated users**: 1000 requests per hour
- **Anonymous users**: 100 requests per hour
- **File uploads**: 50 requests per hour

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## Examples

### Complete Transaction Workflow

1. **Get categories for the form:**
```bash
curl -H "Authorization: Token your-token" \
  http://localhost:8000/api/v1/categories/
```

2. **Create a transaction:**
```bash
curl -X POST \
  -H "Authorization: Token your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "25.50",
    "merchant": "Local Grocery",
    "notes": "Weekly groceries",
    "transaction_type": "expense",
    "date": "2024-01-15",
    "category_id": 1
  }' \
  http://localhost:8000/api/v1/transactions/
```

3. **Upload receipt for the transaction:**
```bash
curl -X PATCH \
  -H "Authorization: Token your-token" \
  -F "receipt=@grocery_receipt.jpg" \
  http://localhost:8000/api/v1/transactions/123/
```

4. **Get updated dashboard metrics:**
```bash
curl -H "Authorization: Token your-token" \
  http://localhost:8000/api/analytics/dashboard/
```

### Budget Management Workflow

1. **Create a monthly budget:**
```bash
curl -X POST \
  -H "Authorization: Token your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "January Food Budget",
    "amount": "500.00",
    "period_start": "2024-01-01",
    "period_end": "2024-01-31",
    "category_id": 1,
    "warning_threshold": 80.0
  }' \
  http://localhost:8000/api/v1/budgets/
```

2. **Check budget performance:**
```bash
curl -H "Authorization: Token your-token" \
  http://localhost:8000/api/v1/budgets/1/analytics/?compare_previous=true
```

### Analytics and Reporting

1. **Get spending trends for the last 6 months:**
```bash
curl -H "Authorization: Token your-token" \
  "http://localhost:8000/api/analytics/trends/?start_date=2023-07-01&end_date=2024-01-31&period=monthly"
```

2. **Export transaction data (custom endpoint):**
```bash
curl -H "Authorization: Token your-token" \
  "http://localhost:8000/api/v1/transactions/export/?format=csv&start_date=2024-01-01"
```

---

## SDK and Client Libraries

### JavaScript/TypeScript

The project includes a complete TypeScript API client in `static/src/api/client.ts`:

```typescript
import { APIClient } from '@/api/client';

const client = new APIClient();

// Create transaction
const transaction = await client.transactions.create({
  amount: '25.50',
  merchant: 'Coffee Shop',
  transaction_type: 'expense',
  category_id: 5
});

// Get dashboard metrics
const dashboard = await client.analytics.dashboard();
```

### Python

For server-to-server communication or scripts:

```python
import requests

class PFDClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {'Authorization': f'Token {token}'}

    def get_transactions(self, **params):
        response = requests.get(
            f'{self.base_url}/api/v1/transactions/',
            headers=self.headers,
            params=params
        )
        return response.json()

# Usage
client = PFDClient('http://localhost:8000', 'your-token')
transactions = client.get_transactions(transaction_type='expense')
```

---

This API reference provides comprehensive documentation for integrating with the Personal Finance Dashboard API. For additional support or custom integration needs, refer to the development documentation or contact the development team.
