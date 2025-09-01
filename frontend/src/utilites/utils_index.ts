
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format, formatDistanceToNow, isToday, isYesterday } from 'date-fns'

// Utility function to merge Tailwind CSS classes
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Format numbers with appropriate suffixes
export function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toLocaleString()
}

// Format percentage
export function formatPercentage(value: number, decimals: number = 1): string {
  return `${value.toFixed(decimals)}%`
}

// Format currency
export function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
  }).format(amount)
}

// Format date relative to now
export function formatRelativeDate(date: string | Date): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date

  if (isToday(dateObj)) {
    return 'Today'
  }

  if (isYesterday(dateObj)) {
    return 'Yesterday'
  }

  return formatDistanceToNow(dateObj, { addSuffix: true })
}

// Format absolute date
export function formatAbsoluteDate(date: string | Date, formatStr: string = 'MMM dd, yyyy'): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date
  return format(dateObj, formatStr)
}

// Format time
export function formatTime(date: string | Date, includeSeconds: boolean = false): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date
  const formatStr = includeSeconds ? 'HH:mm:ss' : 'HH:mm'
  return format(dateObj, formatStr)
}

// Format date and time
export function formatDateTime(date: string | Date): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date
  return format(dateObj, 'MMM dd, yyyy • HH:mm')
}

// Truncate text
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

// Get initials from name
export function getInitials(name: string): string {
  return name
    .split(' ')
    .map((word) => word[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

// Validate email
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

// Generate random ID
export function generateId(): string {
  return Math.random().toString(36).substr(2, 9)
}

// Debounce function
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | undefined

  return (...args: Parameters<T>) => {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

// Deep clone object
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') return obj
  if (obj instanceof Date) return new Date(obj.getTime()) as T
  if (Array.isArray(obj)) return obj.map(item => deepClone(item)) as T

  const clonedObj = {} as T
  for (const key in obj) {
    if (obj.hasOwnProperty(key)) {
      clonedObj[key] = deepClone(obj[key])
    }
  }
  return clonedObj
}

// Local storage helpers
export const storage = {
  get: <T>(key: string): T | null => {
    if (typeof window === 'undefined') return null
    try {
      const item = localStorage.getItem(key)
      return item ? JSON.parse(item) : null
    } catch {
      return null
    }
  },

  set: <T>(key: string, value: T): void => {
    if (typeof window === 'undefined') return
    try {
      localStorage.setItem(key, JSON.stringify(value))
    } catch (error) {
      console.error('Failed to save to localStorage:', error)
    }
  },

  remove: (key: string): void => {
    if (typeof window === 'undefined') return
    localStorage.removeItem(key)
  },

  clear: (): void => {
    if (typeof window === 'undefined') return
    localStorage.clear()
  }
}

// Session storage helpers
export const sessionStorage = {
  get: <T>(key: string): T | null => {
    if (typeof window === 'undefined') return null
    try {
      const item = window.sessionStorage.getItem(key)
      return item ? JSON.parse(item) : null
    } catch {
      return null
    }
  },

  set: <T>(key: string, value: T): void => {
    if (typeof window === 'undefined') return
    try {
      window.sessionStorage.setItem(key, JSON.stringify(value))
    } catch (error) {
      console.error('Failed to save to sessionStorage:', error)
    }
  },

  remove: (key: string): void => {
    if (typeof window === 'undefined') return
    window.sessionStorage.removeItem(key)
  }
}

// Handle async operations with error handling
export async function handleAsyncOperation<T>(
  operation: () => Promise<T>,
  errorMessage?: string
): Promise<{ data: T | null; error: string | null }> {
  try {
    const data = await operation()
    return { data, error: null }
  } catch (error) {
    console.error(errorMessage || 'Async operation failed:', error)
    return { 
      data: null, 
      error: error instanceof Error ? error.message : 'Unknown error occurred'
    }
  }
}

// Regional utilities
export const regionUtils = {
  getTimezone: (region: 'US' | 'UK'): string => {
    return region === 'US' ? 'America/New_York' : 'Europe/London'
  },

  getCurrency: (region: 'US' | 'UK'): string => {
    return region === 'US' ? 'USD' : 'GBP'
  },

  getCurrencySymbol: (region: 'US' | 'UK'): string => {
    return region === 'US' ? '$' : '£'
  },

  getDateFormat: (region: 'US' | 'UK'): string => {
    return region === 'US' ? 'MM/dd/yyyy' : 'dd/MM/yyyy'
  }
}

// Performance utilities
export const performanceUtils = {
  calculateEngagementRate: (engaged_users: number, reach: number): number => {
    return reach > 0 ? (engaged_users / reach) * 100 : 0
  },

  calculateClickThroughRate: (clicks: number, impressions: number): number => {
    return impressions > 0 ? (clicks / impressions) * 100 : 0
  },

  getPerformanceLabel: (score: number): { label: string; color: string } => {
    if (score >= 8) return { label: 'Excellent', color: 'text-green-600' }
    if (score >= 6) return { label: 'Good', color: 'text-blue-600' }
    if (score >= 4) return { label: 'Average', color: 'text-yellow-600' }
    if (score >= 2) return { label: 'Below Average', color: 'text-orange-600' }
    return { label: 'Poor', color: 'text-red-600' }
  },

  getTrendDirection: (current: number, previous: number): 'up' | 'down' | 'stable' => {
    const threshold = 0.05 // 5% threshold
    const change = (current - previous) / previous

    if (change > threshold) return 'up'
    if (change < -threshold) return 'down'
    return 'stable'
  }
}

