
import { apiCall, type ApiResponse } from './api'
import type { 
  AnalyticsDashboard,
  PageAnalyticsSummary,
  PostAnalytics,
  OptimizationInsight
} from '@/types'

interface PerformanceComparison {
  current_period: PageAnalyticsSummary
  previous_period: PageAnalyticsSummary
  improvements: Record<string, number>
  declines: Record<string, number>
  recommendations: string[]
}

interface RegionalPerformanceComparison {
  us_performance?: PageAnalyticsSummary
  uk_performance?: PageAnalyticsSummary
  regional_insights: string[]
  cross_regional_recommendations: string[]
}

interface EngagementTimeline {
  facebook_page_id: number
  timeline_data: Array<{
    date: string
    avg_engagement: number
    total_reactions: number
    post_count: number
  }>
  peak_hours: number[]
  best_days: string[]
  seasonal_patterns: Record<string, any>
}

interface ContentPerformanceAnalysis {
  content_type_performance: Record<string, number>
  optimal_caption_length: number
  best_hashtag_count: number
  sentiment_impact: Record<string, number>
  image_vs_text_performance: Record<string, number>
  regional_preferences: Record<string, any>
}

class AnalyticsService {
  async getDashboard(
    pageId?: number, 
    days: number = 30
  ): Promise<ApiResponse<AnalyticsDashboard>> {
    return apiCall<AnalyticsDashboard>({
      method: 'GET',
      url: '/api/v1/analytics/dashboard',
      params: { page_id: pageId, days },
    })
  }

  async getPageSummary(
    pageId: number,
    startDate?: string,
    endDate?: string
  ): Promise<ApiResponse<PageAnalyticsSummary>> {
    return apiCall<PageAnalyticsSummary>({
      method: 'GET',
      url: `/api/v1/analytics/pages/${pageId}/summary`,
      params: { start_date: startDate, end_date: endDate },
    })
  }

  async getPostAnalytics(postId: number): Promise<ApiResponse<PostAnalytics>> {
    return apiCall<PostAnalytics>({
      method: 'GET',
      url: `/api/v1/analytics/posts/${postId}`,
    })
  }

  async collectAnalytics(pageId: number): Promise<ApiResponse<{ message: string }>> {
    return apiCall<{ message: string }>({
      method: 'POST',
      url: `/api/v1/analytics/collect/${pageId}`,
    })
  }

  async comparePerformance(
    pageId: number,
    daysCurrent: number = 30,
    daysPrevious: number = 30
  ): Promise<ApiResponse<PerformanceComparison>> {
    return apiCall<PerformanceComparison>({
      method: 'GET',
      url: '/api/v1/analytics/compare',
      params: { 
        page_id: pageId, 
        days_current: daysCurrent, 
        days_previous: daysPrevious 
      },
    })
  }

  async getRegionalComparison(
    days: number = 30
  ): Promise<ApiResponse<RegionalPerformanceComparison>> {
    return apiCall<RegionalPerformanceComparison>({
      method: 'GET',
      url: '/api/v1/analytics/regional-comparison',
      params: { days },
    })
  }

  async getEngagementTimeline(
    pageId: number,
    days: number = 30
  ): Promise<ApiResponse<EngagementTimeline>> {
    return apiCall<EngagementTimeline>({
      method: 'GET',
      url: `/api/v1/analytics/engagement-timeline/${pageId}`,
      params: { days },
    })
  }

  async getContentAnalysis(
    pageId: number,
    days: number = 90
  ): Promise<ApiResponse<ContentPerformanceAnalysis>> {
    return apiCall<ContentPerformanceAnalysis>({
      method: 'GET',
      url: `/api/v1/analytics/content-analysis/${pageId}`,
      params: { days },
    })
  }

  async getOptimizationInsights(
    pageId?: number
  ): Promise<ApiResponse<OptimizationInsight[]>> {
    return apiCall<OptimizationInsight[]>({
      method: 'GET',
      url: '/api/v1/analytics/optimization-insights',
      params: { page_id: pageId },
    })
  }
}

export const analyticsService = new AnalyticsService()
