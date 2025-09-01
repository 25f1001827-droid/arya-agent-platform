
import { apiCall, type ApiResponse } from './api'
import type { 
  ContentGeneration, 
  ContentGenerationForm,
  ScheduledPost 
} from '@/types'

interface BulkContentRequest {
  facebook_page_id: number
  topics: string[]
  content_type: 'IMAGE' | 'TEXT' | 'VIDEO' | 'MIXED'
  tone: string
  include_hashtags: boolean
  include_images: boolean
}

interface ContentOptimizationRequest {
  content_generation_id: number
  optimization_goals: string[]
  target_improvement: number
}

interface OptimizationSuggestion {
  suggestion: string
  expected_improvement: string
  confidence: number
  predicted_score: number
}

class ContentService {
  async generateContent(data: ContentGenerationForm): Promise<ApiResponse<ContentGeneration>> {
    return apiCall<ContentGeneration>({
      method: 'POST',
      url: '/api/v1/content/generate',
      data,
    })
  }

  async bulkGenerate(data: BulkContentRequest): Promise<ApiResponse<{ message: string }>> {
    return apiCall<{ message: string }>({
      method: 'POST',
      url: '/api/v1/content/bulk-generate',
      data,
    })
  }

  async getContent(
    pageId?: number, 
    limit: number = 50, 
    offset: number = 0
  ): Promise<ApiResponse<ContentGeneration[]>> {
    return apiCall<ContentGeneration[]>({
      method: 'GET',
      url: '/api/v1/content/',
      params: { page_id: pageId, limit, offset },
    })
  }

  async getContentItem(contentId: number): Promise<ApiResponse<ContentGeneration>> {
    return apiCall<ContentGeneration>({
      method: 'GET',
      url: `/api/v1/content/${contentId}`,
    })
  }

  async approveContent(
    contentId: number, 
    data: { is_approved: boolean; feedback?: string }
  ): Promise<ApiResponse<ContentGeneration>> {
    return apiCall<ContentGeneration>({
      method: 'POST',
      url: `/api/v1/content/${contentId}/approve`,
      data: { content_generation_id: contentId, ...data },
    })
  }

  async scheduleContent(
    contentId: number, 
    scheduleTime?: string
  ): Promise<ApiResponse<{
    message: string
    scheduled_post_id: number
    scheduled_time: string
  }>> {
    return apiCall({
      method: 'POST',
      url: `/api/v1/content/${contentId}/schedule`,
      data: { schedule_time: scheduleTime },
    })
  }

  async optimizeContent(
    contentId: number,
    request: ContentOptimizationRequest
  ): Promise<ApiResponse<{
    original_content: ContentGeneration
    suggestions: OptimizationSuggestion[]
    expected_improvements: Record<string, number>
    confidence_score: number
  }>> {
    return apiCall({
      method: 'POST',
      url: `/api/v1/content/${contentId}/optimize`,
      data: request,
    })
  }

  async deleteContent(contentId: number): Promise<ApiResponse<{ message: string }>> {
    return apiCall<{ message: string }>({
      method: 'DELETE',
      url: `/api/v1/content/${contentId}`,
    })
  }

  async getScheduledPosts(
    pageId?: number,
    status?: string,
    limit: number = 50
  ): Promise<ApiResponse<ScheduledPost[]>> {
    return apiCall<ScheduledPost[]>({
      method: 'GET',
      url: '/api/v1/content/scheduled',
      params: { page_id: pageId, status, limit },
    })
  }
}

export const contentService = new ContentService()
