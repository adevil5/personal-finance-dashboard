# TypeScript Components - Personal Finance Dashboard

This directory contains the TypeScript components for the Personal Finance Dashboard, implementing currency formatting, form validation, and API client functionality.

## Overview

The TypeScript implementation provides:

- **Currency Formatter**: Multi-currency formatting with locale support
- **Form Validation**: Comprehensive client-side validation helpers
- **API Client**: Type-safe HTTP client for backend communication
- **Integration**: Seamless integration with existing Django/HTMX frontend

## Components

### 1. Currency Formatter (`utils/currency.ts`)

Handles currency formatting for multiple currencies and locales.

**Features:**
- Support for 30+ currencies (USD, EUR, GBP, etc.)
- Locale-specific formatting (US, EU, UK formats)
- Currency validation and parsing
- Symbol extraction and decimal place handling

**Usage:**
```typescript
import { CurrencyFormatter } from '@/utils'

const formatter = new CurrencyFormatter('USD', 'en-US')
formatter.format('1234.56') // "$1,234.56"
formatter.isValidAmount('100.00') // true
formatter.getSymbol() // "$"
```

### 2. Form Validation (`utils/validation.ts`)

Comprehensive form validation with custom rules and async support.

**Features:**
- Built-in validators (required, email, password, phone, amount)
- Custom validation rules with async support
- Form-level validation with error aggregation
- Type-safe validation schemas

**Usage:**
```typescript
import { FormValidator } from '@/utils'

const validator = new FormValidator({
  amount: [
    { rule: 'required', message: 'Amount is required' },
    { rule: 'amount', message: 'Invalid amount' }
  ],
  email: [
    { rule: 'required', message: 'Email is required' },
    { rule: 'email', message: 'Invalid email format' }
  ]
})

const result = validator.validate(formData)
if (!result.isValid) {
  console.log(result.errors) // Field-specific error messages
}
```

### 3. API Client (`api/client.ts`)

Type-safe HTTP client for backend API communication.

**Features:**
- Full TypeScript type safety with API response types
- Automatic CSRF token handling
- Error handling with proper status codes
- Support for all CRUD operations
- Query parameter building and filtering

**Usage:**
```typescript
import { APIClient } from '@/api'

const client = new APIClient('/api/v1')

// Get transactions with filters
const transactions = await client.transactions.list({
  transaction_type: 'expense',
  date_after: '2024-01-01'
})

// Create new transaction
const newTransaction = await client.transactions.create({
  amount: '100.00',
  transaction_type: 'expense',
  description: 'Groceries',
  date: '2024-01-01'
})
```

### 4. Type Definitions (`types/api.ts`)

Complete TypeScript interfaces for all API entities.

**Includes:**
- Transaction, Category, Budget interfaces
- Form data types with validation constraints
- API response types (paginated, error responses)
- Filter types for list endpoints
- Analytics and dashboard metric types

## Integration with Main Application

The `main.ts` file demonstrates integration with the existing Django/HTMX frontend:

- **Global Utilities**: API client and currency formatter available as `window.PFD`
- **Form Enhancement**: Automatic validation for transaction forms
- **Currency Fields**: Real-time formatting for amount inputs
- **Error Handling**: Seamless error display with Django form patterns

## Testing

All components include comprehensive test suites:

- **59 test cases** covering all functionality
- **Vitest** test runner with jsdom environment
- **Mock utilities** for API calls and DOM interactions
- **TDD approach** with tests written before implementation

Run tests:
```bash
npm test              # Run all tests
npm run test:ui       # Run with UI
npm run test:coverage # Generate coverage report
```

## Development

**Type Checking:**
```bash
npm run typecheck     # TypeScript type checking
```

**Linting:**
```bash
npm run lint          # ESLint checking
npm run lint:fix      # Auto-fix linting issues
```

**Formatting:**
```bash
npm run format        # Prettier formatting
npm run format:check  # Check formatting
```

**Building:**
```bash
npm run build         # Production build
npm run dev           # Development server
```

## Architecture Notes

- **Strict TypeScript**: All strict flags enabled for maximum type safety
- **ES Modules**: Modern module system with top-level await support
- **Vite Integration**: Fast build system with HMR for development
- **Path Aliases**: `@/*` mapped to `static/src/*` for clean imports
- **Environment-aware**: Development vs production configurations

## Future Enhancements

Potential areas for expansion:
- Chart.js integration with TypeScript components
- Advanced form wizards with multi-step validation
- Real-time data synchronization with WebSocket support
- Offline-first capabilities with service workers
- Advanced analytics dashboard components
