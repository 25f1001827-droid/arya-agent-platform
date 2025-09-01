
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authService } from '@/services/auth'
import type { User, LoginForm, RegisterForm } from '@/types'

interface AuthState {
  user: User | null
  isLoading: boolean
  error: string | null
  isAuthenticated: boolean

  // Actions
  login: (credentials: LoginForm) => Promise<boolean>
  register: (userData: RegisterForm) => Promise<boolean>
  logout: () => Promise<void>
  getCurrentUser: () => Promise<void>
  updateProfile: (userData: Partial<User>) => Promise<boolean>
  clearError: () => void
  resetAuth: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isLoading: false,
      error: null,
      isAuthenticated: false,

      login: async (credentials: LoginForm): Promise<boolean> => {
        set({ isLoading: true, error: null })

        try {
          const response = await authService.login(credentials)

          if (response.error) {
            set({ error: response.error, isLoading: false })
            return false
          }

          if (response.data) {
            set({ 
              user: response.data.user,
              isAuthenticated: true,
              isLoading: false,
              error: null
            })
            return true
          }

          return false
        } catch (error) {
          set({ 
            error: 'Login failed. Please try again.',
            isLoading: false
          })
          return false
        }
      },

      register: async (userData: RegisterForm): Promise<boolean> => {
        set({ isLoading: true, error: null })

        try {
          const response = await authService.register(userData)

          if (response.error) {
            set({ error: response.error, isLoading: false })
            return false
          }

          if (response.data) {
            set({ 
              user: response.data.user,
              isAuthenticated: true,
              isLoading: false,
              error: null
            })
            return true
          }

          return false
        } catch (error) {
          set({ 
            error: 'Registration failed. Please try again.',
            isLoading: false
          })
          return false
        }
      },

      logout: async (): Promise<void> => {
        set({ isLoading: true })

        try {
          await authService.logout()
        } catch (error) {
          console.error('Logout error:', error)
        } finally {
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null
          })
        }
      },

      getCurrentUser: async (): Promise<void> => {
        if (!authService.isAuthenticated()) {
          set({ isAuthenticated: false, user: null })
          return
        }

        set({ isLoading: true })

        try {
          const response = await authService.getCurrentUser()

          if (response.error) {
            set({ 
              error: response.error,
              isAuthenticated: false,
              user: null,
              isLoading: false
            })
            return
          }

          if (response.data) {
            set({ 
              user: response.data,
              isAuthenticated: true,
              isLoading: false,
              error: null
            })
          }
        } catch (error) {
          set({
            error: 'Failed to fetch user data',
            isAuthenticated: false,
            user: null,
            isLoading: false
          })
        }
      },

      updateProfile: async (userData: Partial<User>): Promise<boolean> => {
        set({ isLoading: true, error: null })

        try {
          const response = await authService.updateProfile(userData)

          if (response.error) {
            set({ error: response.error, isLoading: false })
            return false
          }

          if (response.data) {
            set({ 
              user: response.data,
              isLoading: false,
              error: null
            })
            return true
          }

          return false
        } catch (error) {
          set({ 
            error: 'Profile update failed',
            isLoading: false
          })
          return false
        }
      },

      clearError: () => {
        set({ error: null })
      },

      resetAuth: () => {
        set({
          user: null,
          isLoading: false,
          error: null,
          isAuthenticated: false
        })
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        user: state.user,
        isAuthenticated: state.isAuthenticated
      }),
    }
  )
)
