
import { create } from 'zustand'
import { analyticsService } from '@/services/analytics'
import type { 
  AnalyticsDashboard, 
  PageAnalyticsSummary, 
  PostAnalytics,
  OptimizationInsight 
} from '@/types'

interface AnalyticsState {
  dashboard: AnalyticsDashboard | null
  pageSummary: PageAnalyticsSummary | null
  postAnalytics: PostAnalytics[]
  optimizationInsights: OptimizationInsight[]
  isLoading: boolean
  error: string | null

  // Filters
  selectedPageId: number | null
  dateRange: {
    start: string
    end: string
  } | null

  // Actions
  fetchDashboard: (pageId?: number, days?: number) => Promise<void>
  fetchPageSummary: (pageId: number, startDate?: string, endDate?: string) => Promise<void>
  fetchPostAnalytics: (postId: number) => Promise<void>
  collectAnalytics: (pageId: number) => Promise<boolean>
  fetchOptimizationInsights: (pageId?: number) => Promise<void>
  setSelectedPageId: (pageId: number | null) => void
  setDateRange: (range: { start: string; end: string } | null) => void
  clearError: () => void
  resetAnalytics: () => void
}

export const useAnalyticsStore = create<AnalyticsState>()((set, get) => ({
  dashboard: null,
  pageSummary: null,
  postAnalytics: [],
  optimizationInsights: [],
  isLoading: false,
  error: null,
  selectedPageId: null,
  dateRange: null,

  fetchDashboard: async (pageId?: number, days: number = 30): Promise<void> => {
    set({ isLoading: true, error: null })

    try {
      const response = await analyticsService.getDashboard(pageId, days)

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return
      }

      if (response.data) {
        set({ 
          dashboard: response.data,
          isLoading: false,
          error: null
        })
      }
    } catch (error) {
      set({ 
        error: 'Failed to fetch dashboard data',
        isLoading: false
      })
    }
  },

  fetchPageSummary: async (pageId: number, startDate?: string, endDate?: string): Promise<void> => {
    set({ isLoading: true, error: null })

    try {
      const response = await analyticsService.getPageSummary(pageId, startDate, endDate)

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return
      }

      if (response.data) {
        set({ 
          pageSummary: response.data,
          isLoading: false,
          error: null
        })
      }
    } catch (error) {
      set({ 
        error: 'Failed to fetch page summary',
        isLoading: false
      })
    }
  },

  fetchPostAnalytics: async (postId: number): Promise<void> => {
    set({ isLoading: true, error: null })

    try {
      const response = await analyticsService.getPostAnalytics(postId)

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return
      }

      if (response.data) {
        const currentAnalytics = get().postAnalytics
        const updatedAnalytics = currentAnalytics.find(p => p.id === postId)
          ? currentAnalytics.map(p => p.id === postId ? response.data! : p)
          : [...currentAnalytics, response.data]

        set({ 
          postAnalytics: updatedAnalytics,
          isLoading: false,
          error: null
        })
      }
    } catch (error) {
      set({ 
        error: 'Failed to fetch post analytics',
        isLoading: false
      })
    }
  },

  collectAnalytics: async (pageId: number): Promise<boolean> => {
    set({ isLoading: true, error: null })

    try {
      const response = await analyticsService.collectAnalytics(pageId)

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return false
      }

      set({ isLoading: false })

      // Refresh dashboard after collecting analytics
      await get().fetchDashboard(pageId)

      return true
    } catch (error) {
      set({ 
        error: 'Analytics collection failed',
        isLoading: false
      })
      return false
    }
  },

  fetchOptimizationInsights: async (pageId?: number): Promise<void> => {
    set({ isLoading: true, error: null })

    try {
      const response = await analyticsService.getOptimizationInsights(pageId)

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return
      }

      if (response.data) {
        set({ 
          optimizationInsights: response.data,
          isLoading: false,
          error: null
        })
      }
    } catch (error) {
      set({ 
        error: 'Failed to fetch optimization insights',
        isLoading: false
      })
    }
  },

  setSelectedPageId: (pageId: number | null) => {
    set({ selectedPageId: pageId })
  },

  setDateRange: (range: { start: string; end: string } | null) => {
    set({ dateRange: range })
  },

  clearError: () => {
    set({ error: null })
  },

  resetAnalytics: () => {
    set({
      dashboard: null,
      pageSummary: null,
      postAnalytics: [],
      optimizationInsights: [],
      isLoading: false,
      error: null,
      selectedPageId: null,
      dateRange: null
    })
  }
}))
