/**
 * Form validation utilities for Personal Finance Dashboard
 */

export interface ValidationResult {
  isValid: boolean
  errors: Record<string, string[]>
}

export interface AmountValidationOptions {
  min?: number
  max?: number
  allowNegative?: boolean
  allowZero?: boolean
}

export interface PasswordValidationOptions {
  minLength?: number
  requireUppercase?: boolean
  requireLowercase?: boolean
  requireNumbers?: boolean
  requireSpecialChars?: boolean
}

export interface ValidationRule {
  rule: 'required' | 'email' | 'amount' | 'minLength' | 'maxLength' | 'password' | 'phone' | 'custom'
  message: string
  value?: any
  options?: any
  validate?: (value: any, data?: any) => boolean | Promise<boolean>
}

export interface ValidationSchema {
  [field: string]: ValidationRule[]
}

/**
 * Validate required field
 */
export function validateRequired(value: any): boolean {
  if (value === null || value === undefined) {
    return false
  }

  if (typeof value === 'string') {
    return value.trim().length > 0
  }

  return true
}

/**
 * Validate currency amount
 */
export function validateAmount(
  value: string,
  options: AmountValidationOptions = {}
): boolean {
  const {
    min,
    max = Number.MAX_SAFE_INTEGER,
    allowNegative = false,
    allowZero = false,
  } = options

  if (!value || value.trim() === '') {
    return false
  }

  const numValue = parseFloat(value)
  if (isNaN(numValue)) {
    return false
  }

  // Check decimal places - handle negative numbers
  const absoluteValue = value.replace(/^-/, '')
  const parts = absoluteValue.split('.')
  if (parts.length > 2 || (parts.length === 2 && parts[1] && parts[1].length > 2)) {
    return false
  }

  // Check zero
  if (numValue === 0 && !allowZero) {
    return false
  }

  // Check negative
  if (numValue < 0 && !allowNegative) {
    return false
  }

  // Check range
  if (min !== undefined && numValue < min) {
    return false
  }

  if (numValue > max) {
    return false
  }

  return true
}

/**
 * Validate date range
 */
export function validateDateRange(startDate: string, endDate: string): boolean {
  if (!startDate || !endDate) {
    return false
  }

  const start = new Date(startDate)
  const end = new Date(endDate)

  if (isNaN(start.getTime()) || isNaN(end.getTime())) {
    return false
  }

  return start <= end
}

/**
 * Validate email format
 */
export function validateEmail(email: string): boolean {
  if (!email) {
    return false
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

/**
 * Validate password strength
 */
export function validatePassword(
  password: string,
  options: PasswordValidationOptions = {}
): boolean {
  const {
    minLength = 8,
    requireUppercase = true,
    requireLowercase = true,
    requireNumbers = true,
    requireSpecialChars = true,
  } = options

  if (!password || password.length < minLength) {
    return false
  }

  if (requireUppercase && !/[A-Z]/.test(password)) {
    return false
  }

  if (requireLowercase && !/[a-z]/.test(password)) {
    return false
  }

  if (requireNumbers && !/\d/.test(password)) {
    return false
  }

  if (requireSpecialChars && !/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    return false
  }

  return true
}

/**
 * Validate phone number (basic international format)
 */
export function validatePhone(phone: string): boolean {
  if (!phone) {
    return false
  }

  // Basic international phone validation (+ followed by 10-15 digits)
  const phoneRegex = /^\+\d{10,15}$/
  return phoneRegex.test(phone)
}

/**
 * Validate maximum length
 */
export function validateMaxLength(value: string, maxLength: number): boolean {
  return value.length <= maxLength
}

/**
 * Validate minimum length
 */
export function validateMinLength(value: string, minLength: number): boolean {
  return value.length >= minLength
}

/**
 * Form validator class
 */
export class FormValidator {
  constructor(
    private schema: ValidationSchema,
    private options: { stopOnFirstError?: boolean } = {}
  ) {}

  /**
   * Validate form data synchronously
   */
  validate(data: Record<string, any>): ValidationResult {
    const errors: Record<string, string[]> = {}
    let isValid = true

    for (const [field, rules] of Object.entries(this.schema)) {
      const fieldErrors: string[] = []
      const value = data[field]

      for (const rule of rules) {
        if (this.options.stopOnFirstError && fieldErrors.length > 0) {
          break
        }

        const isRuleValid = this.validateRule(rule, value, data)
        if (!isRuleValid) {
          fieldErrors.push(rule.message)
          isValid = false
        }
      }

      if (fieldErrors.length > 0) {
        errors[field] = fieldErrors
      }
    }

    return { isValid, errors }
  }

  /**
   * Validate form data asynchronously
   */
  async validateAsync(data: Record<string, any>): Promise<ValidationResult> {
    const errors: Record<string, string[]> = {}
    let isValid = true

    for (const [field, rules] of Object.entries(this.schema)) {
      const fieldErrors: string[] = []
      const value = data[field]

      for (const rule of rules) {
        if (this.options.stopOnFirstError && fieldErrors.length > 0) {
          break
        }

        const isRuleValid = await this.validateRuleAsync(rule, value, data)
        if (!isRuleValid) {
          fieldErrors.push(rule.message)
          isValid = false
        }
      }

      if (fieldErrors.length > 0) {
        errors[field] = fieldErrors
      }
    }

    return { isValid, errors }
  }

  /**
   * Validate a single rule
   */
  private validateRule(rule: ValidationRule, value: any, data: any): boolean {
    switch (rule.rule) {
      case 'required':
        return validateRequired(value)

      case 'email':
        return validateEmail(value)

      case 'amount':
        return validateAmount(value, rule.options)

      case 'minLength':
        return validateMinLength(value || '', rule.value)

      case 'maxLength':
        return validateMaxLength(value || '', rule.value)

      case 'password':
        return validatePassword(value, rule.options)

      case 'phone':
        return validatePhone(value)

      case 'custom':
        if (rule.validate) {
          const result = rule.validate(value, data)
          return result === true || result === false ? result : true
        }
        return true

      default:
        return true
    }
  }

  /**
   * Validate a single rule asynchronously
   */
  private async validateRuleAsync(
    rule: ValidationRule,
    value: any,
    data: any
  ): Promise<boolean> {
    if (rule.rule === 'custom' && rule.validate) {
      const result = await rule.validate(value, data)
      return result
    }

    return this.validateRule(rule, value, data)
  }
}
