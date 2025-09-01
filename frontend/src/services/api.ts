
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { storage } from '@/utils'
import type { AuthResponse, ApiError } from '@/types'

// API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Token management
const TOKEN_KEY = 'auth_tokens'
const REFRESH_TOKEN_KEY = 'refresh_token'

interface TokenData {
  access_token: string
  refresh_token: string
  expires_in: number
  token_type: string
}

class TokenManager {
  private tokens: TokenData | null = null
  private refreshPromise: Promise<void> | null = null

  constructor() {
    this.loadTokens()
  }

  private loadTokens() {
    this.tokens = storage.get<TokenData>(TOKEN_KEY)
  }

  getAccessToken(): string | null {
    return this.tokens?.access_token || null
  }

  getRefreshToken(): string | null {
    return this.tokens?.refresh_token || null
  }

  setTokens(tokenData: TokenData) {
    this.tokens = tokenData
    storage.set(TOKEN_KEY, tokenData)
  }

  clearTokens() {
    this.tokens = null
    storage.remove(TOKEN_KEY)
    storage.remove(REFRESH_TOKEN_KEY)
  }

  async refreshTokens(): Promise<boolean> {
    if (this.refreshPromise) {
      await this.refreshPromise
      return !!this.tokens
    }

    const refreshToken = this.getRefreshToken()
    if (!refreshToken) {
      this.clearTokens()
      return false
    }

    this.refreshPromise = this.performTokenRefresh(refreshToken)

    try {
      await this.refreshPromise
      return !!this.tokens
    } catch (error) {
      console.error('Token refresh failed:', error)
      this.clearTokens()
      return false
    } finally {
      this.refreshPromise = null
    }
  }

  private async performTokenRefresh(refreshToken: string): Promise<void> {
    const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
      refresh_token: refreshToken
    })

    const tokenData: TokenData = {
      access_token: response.data.access_token,
      refresh_token: response.data.refresh_token,
      expires_in: response.data.expires_in,
      token_type: response.data.token_type
    }

    this.setTokens(tokenData)
  }
}

// Create token manager instance
const tokenManager = new TokenManager()

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = tokenManager.getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const refreshSuccessful = await tokenManager.refreshTokens()

      if (refreshSuccessful) {
        const token = tokenManager.getAccessToken()
        originalRequest.headers.Authorization = `Bearer ${token}`
        return api(originalRequest)
      } else {
        // Redirect to login or handle logout
        if (typeof window !== 'undefined') {
          window.location.href = '/auth/login'
        }
      }
    }

    return Promise.reject(error)
  }
)

// API response wrapper
export interface ApiResponse<T = any> {
  data: T | null
  error: string | null
  status: number
}

// Generic API call function
async function apiCall<T = any>(
  config: AxiosRequestConfig
): Promise<ApiResponse<T>> {
  try {
    const response: AxiosResponse<T> = await api(config)
    return {
      data: response.data,
      error: null,
      status: response.status,
    }
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const apiError: ApiError = {
        detail: error.response?.data?.detail || error.message,
        status: error.response?.status,
      }
      return {
        data: null,
        error: apiError.detail,
        status: error.response?.status || 500,
      }
    }
    return {
      data: null,
      error: 'An unexpected error occurred',
      status: 500,
    }
  }
}

// Export API methods
export { api, tokenManager, apiCall }
export type { ApiResponse }
