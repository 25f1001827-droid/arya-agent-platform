
import { apiCall, tokenManager, type ApiResponse } from './api'
import type { 
  User, 
  AuthResponse, 
  LoginForm, 
  RegisterForm 
} from '@/types'

class AuthService {
  async login(credentials: LoginForm): Promise<ApiResponse<AuthResponse>> {
    const response = await apiCall<AuthResponse>({
      method: 'POST',
      url: '/api/v1/auth/login',
      data: credentials,
    })

    if (response.data) {
      tokenManager.setTokens({
        access_token: response.data.access_token,
        refresh_token: response.data.refresh_token,
        expires_in: response.data.expires_in,
        token_type: response.data.token_type,
      })
    }

    return response
  }

  async register(userData: RegisterForm): Promise<ApiResponse<AuthResponse>> {
    const response = await apiCall<AuthResponse>({
      method: 'POST',
      url: '/api/v1/auth/register',
      data: userData,
    })

    if (response.data) {
      tokenManager.setTokens({
        access_token: response.data.access_token,
        refresh_token: response.data.refresh_token,
        expires_in: response.data.expires_in,
        token_type: response.data.token_type,
      })
    }

    return response
  }

  async logout(): Promise<void> {
    try {
      await apiCall({
        method: 'POST',
        url: '/api/v1/auth/logout',
      })
    } catch (error) {
      console.error('Logout API call failed:', error)
    } finally {
      tokenManager.clearTokens()
    }
  }

  async getCurrentUser(): Promise<ApiResponse<User>> {
    return apiCall<User>({
      method: 'GET',
      url: '/api/v1/auth/me',
    })
  }

  async updateProfile(userData: Partial<User>): Promise<ApiResponse<User>> {
    return apiCall<User>({
      method: 'PUT',
      url: '/api/v1/auth/me',
      data: userData,
    })
  }

  async requestPasswordReset(email: string): Promise<ApiResponse<{ message: string }>> {
    return apiCall<{ message: string }>({
      method: 'POST',
      url: '/api/v1/auth/password-reset',
      data: { email },
    })
  }

  async confirmPasswordReset(data: {
    email: string
    reset_token: string
    new_password: string
  }): Promise<ApiResponse<{ message: string }>> {
    return apiCall<{ message: string }>({
      method: 'POST',
      url: '/api/v1/auth/password-reset-confirm',
      data,
    })
  }

  async getUserStats(): Promise<ApiResponse<{
    user_id: number
    plan: string
    posts_used_this_month: number
    monthly_post_limit: number
    ai_credits_remaining: number
    usage_percentage: number
    account_age_days: number
    last_login?: string
  }>> {
    return apiCall({
      method: 'GET',
      url: '/api/v1/auth/stats',
    })
  }

  isAuthenticated(): boolean {
    return !!tokenManager.getAccessToken()
  }
}

export const authService = new AuthService()
