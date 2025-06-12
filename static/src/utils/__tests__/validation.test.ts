import { describe, it, expect } from 'vitest'
import {
  validateRequired,
  validateAmount,
  validateDateRange,
  validateEmail,
  validatePassword,
  validatePhone,
  validateMaxLength,
  validateMinLength,
  FormValidator,
} from '../validation'

describe('Form Validation Helpers', () => {
  describe('validateRequired', () => {
    it('should validate required fields', () => {
      expect(validateRequired('test')).toBe(true)
      expect(validateRequired('  test  ')).toBe(true)
      expect(validateRequired('')).toBe(false)
      expect(validateRequired('   ')).toBe(false)
      expect(validateRequired(null as any)).toBe(false)
      expect(validateRequired(undefined as any)).toBe(false)
    })
  })

  describe('validateAmount', () => {
    it('should validate valid amounts', () => {
      expect(validateAmount('100.00')).toBe(true)
      expect(validateAmount('0.01')).toBe(true)
      expect(validateAmount('999999.99')).toBe(true)
      expect(validateAmount('100')).toBe(true)
      expect(validateAmount('100.1')).toBe(true)
    })

    it('should reject invalid amounts', () => {
      expect(validateAmount('')).toBe(false)
      expect(validateAmount('abc')).toBe(false)
      expect(validateAmount('-100')).toBe(false) // Negative by default
      expect(validateAmount('100.999')).toBe(false) // Too many decimals
      expect(validateAmount('0')).toBe(false) // Zero by default
    })

    it('should respect min/max constraints', () => {
      expect(validateAmount('50', { min: 0, max: 100 })).toBe(true)
      expect(validateAmount('150', { min: 0, max: 100 })).toBe(false)
      expect(validateAmount('5', { min: 10 })).toBe(false)
    })

    it('should allow negative amounts when specified', () => {
      expect(validateAmount('-100', { allowNegative: true })).toBe(true)
      expect(validateAmount('-100', { allowNegative: false })).toBe(false)
    })

    it('should allow zero when specified', () => {
      expect(validateAmount('0', { allowZero: true })).toBe(true)
      expect(validateAmount('0.00', { allowZero: true })).toBe(true)
      expect(validateAmount('0', { allowZero: false })).toBe(false)
    })
  })

  describe('validateDateRange', () => {
    const today = new Date().toISOString().split('T')[0] as string
    const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0] as string
    const tomorrow = new Date(Date.now() + 86400000).toISOString().split('T')[0] as string

    it('should validate date ranges', () => {
      expect(validateDateRange(yesterday, today)).toBe(true)
      expect(validateDateRange(today, tomorrow)).toBe(true)
      expect(validateDateRange(today, yesterday)).toBe(false)
      expect(validateDateRange(tomorrow, today)).toBe(false)
    })

    it('should allow same dates', () => {
      expect(validateDateRange(today, today)).toBe(true)
    })

    it('should handle invalid dates', () => {
      expect(validateDateRange('invalid', today)).toBe(false)
      expect(validateDateRange(today, 'invalid')).toBe(false)
      expect(validateDateRange('', '')).toBe(false)
    })
  })

  describe('validateEmail', () => {
    it('should validate correct email formats', () => {
      expect(validateEmail('test@example.com')).toBe(true)
      expect(validateEmail('user.name@example.co.uk')).toBe(true)
      expect(validateEmail('user+tag@example.com')).toBe(true)
    })

    it('should reject invalid email formats', () => {
      expect(validateEmail('invalid')).toBe(false)
      expect(validateEmail('test@')).toBe(false)
      expect(validateEmail('@example.com')).toBe(false)
      expect(validateEmail('test @example.com')).toBe(false)
      expect(validateEmail('')).toBe(false)
    })
  })

  describe('validatePassword', () => {
    it('should validate strong passwords', () => {
      expect(validatePassword('StrongP@ss123')).toBe(true)
      expect(validatePassword('MyP@ssw0rd!')).toBe(true)
    })

    it('should reject weak passwords by default', () => {
      expect(validatePassword('password')).toBe(false) // No uppercase, no number, no special
      expect(validatePassword('PASSWORD')).toBe(false) // No lowercase, no number, no special
      expect(validatePassword('Password')).toBe(false) // No number, no special
      expect(validatePassword('Password1')).toBe(false) // No special character
      expect(validatePassword('short')).toBe(false) // Too short
    })

    it('should respect custom requirements', () => {
      const options = {
        minLength: 6,
        requireUppercase: false,
        requireLowercase: false,
        requireNumbers: false,
        requireSpecialChars: false,
      }
      expect(validatePassword('simple', options)).toBe(true)
      expect(validatePassword('short', options)).toBe(false)
    })
  })

  describe('validatePhone', () => {
    it('should validate US phone numbers', () => {
      expect(validatePhone('+1234567890')).toBe(true)
      expect(validatePhone('+12345678901')).toBe(true)
      expect(validatePhone('+123456789012')).toBe(true)
      expect(validatePhone('+1234567890123')).toBe(true)
    })

    it('should reject invalid phone numbers', () => {
      expect(validatePhone('123')).toBe(false)
      expect(validatePhone('abc')).toBe(false)
      expect(validatePhone('')).toBe(false)
      expect(validatePhone('+1')).toBe(false) // Too short
      expect(validatePhone('+12345678901234567890')).toBe(false) // Too long
    })
  })

  describe('validateMaxLength', () => {
    it('should validate string length constraints', () => {
      expect(validateMaxLength('test', 10)).toBe(true)
      expect(validateMaxLength('test', 4)).toBe(true)
      expect(validateMaxLength('test', 3)).toBe(false)
      expect(validateMaxLength('', 0)).toBe(true)
    })
  })

  describe('validateMinLength', () => {
    it('should validate minimum length constraints', () => {
      expect(validateMinLength('test', 3)).toBe(true)
      expect(validateMinLength('test', 4)).toBe(true)
      expect(validateMinLength('test', 5)).toBe(false)
      expect(validateMinLength('', 0)).toBe(true)
    })
  })
})

describe('FormValidator', () => {
  it('should validate a simple form', () => {
    const validator = new FormValidator({
      username: [
        { rule: 'required', message: 'Username is required' },
        { rule: 'minLength', value: 3, message: 'Username must be at least 3 characters' },
      ],
      email: [
        { rule: 'required', message: 'Email is required' },
        { rule: 'email', message: 'Invalid email format' },
      ],
    })

    const validResult = validator.validate({
      username: 'john',
      email: 'john@example.com',
    })

    expect(validResult.isValid).toBe(true)
    expect(validResult.errors).toEqual({})

    const invalidResult = validator.validate({
      username: 'jo',
      email: 'invalid',
    })

    expect(invalidResult.isValid).toBe(false)
    expect(invalidResult.errors['username']).toContain('Username must be at least 3 characters')
    expect(invalidResult.errors['email']).toContain('Invalid email format')
  })

  it('should validate transaction form', () => {
    const validator = new FormValidator({
      amount: [
        { rule: 'required', message: 'Amount is required' },
        { rule: 'amount', message: 'Invalid amount', options: { min: 0.01 } },
      ],
      description: [
        { rule: 'required', message: 'Description is required' },
        { rule: 'maxLength', value: 255, message: 'Description too long' },
      ],
      date: [
        { rule: 'required', message: 'Date is required' },
      ],
      category: [
        {
          rule: 'custom',
          validate: (value: any, data: any) => {
            return data.transaction_type !== 'expense' || !!value
          },
          message: 'Category is required for expenses',
        },
      ],
    })

    // Valid expense with category
    const validExpense = validator.validate({
      amount: '100.00',
      description: 'Groceries',
      date: '2024-01-01',
      transaction_type: 'expense',
      category: 1,
    })
    expect(validExpense.isValid).toBe(true)

    // Invalid expense without category
    const invalidExpense = validator.validate({
      amount: '100.00',
      description: 'Groceries',
      date: '2024-01-01',
      transaction_type: 'expense',
      category: null,
    })
    expect(invalidExpense.isValid).toBe(false)
    expect(invalidExpense.errors['category']).toContain('Category is required for expenses')

    // Valid income without category
    const validIncome = validator.validate({
      amount: '1000.00',
      description: 'Salary',
      date: '2024-01-01',
      transaction_type: 'income',
      category: null,
    })
    expect(validIncome.isValid).toBe(true)
  })

  it('should handle async validation', async () => {
    const validator = new FormValidator({
      username: [
        { rule: 'required', message: 'Username is required' },
        {
          rule: 'custom',
          validate: async (value: string) => {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 10))
            return value !== 'taken'
          },
          message: 'Username is already taken',
        },
      ],
    })

    const validResult = await validator.validateAsync({
      username: 'available',
    })
    expect(validResult.isValid).toBe(true)

    const invalidResult = await validator.validateAsync({
      username: 'taken',
    })
    expect(invalidResult.isValid).toBe(false)
    expect(invalidResult.errors['username']).toContain('Username is already taken')
  })

  it('should stop on first error when specified', () => {
    const validator = new FormValidator(
      {
        email: [
          { rule: 'required', message: 'Email is required' },
          { rule: 'email', message: 'Invalid email format' },
          { rule: 'maxLength', value: 50, message: 'Email too long' },
        ],
      },
      { stopOnFirstError: true }
    )

    const result = validator.validate({ email: '' })
    expect(result.errors['email']).toHaveLength(1)
    expect(result.errors['email']).toContain('Email is required')
  })
})
