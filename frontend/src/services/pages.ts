
import { apiCall, type ApiResponse } from './api'
import type { 
  FacebookPage, 
  FacebookPageForm,
  FacebookPageStats 
} from '@/types'

interface FacebookPageWithStats extends FacebookPage {
  stats: FacebookPageStats
}

class PagesService {
  async getPages(): Promise<ApiResponse<FacebookPageWithStats[]>> {
    return apiCall<FacebookPageWithStats[]>({
      method: 'GET',
      url: '/api/v1/pages/',
    })
  }

  async getPage(pageId: number): Promise<ApiResponse<FacebookPageWithStats>> {
    return apiCall<FacebookPageWithStats>({
      method: 'GET',
      url: `/api/v1/pages/${pageId}`,
    })
  }

  async createPage(pageData: FacebookPageForm): Promise<ApiResponse<FacebookPage>> {
    return apiCall<FacebookPage>({
      method: 'POST',
      url: '/api/v1/pages/',
      data: pageData,
    })
  }

  async updatePage(
    pageId: number, 
    updates: Partial<FacebookPageForm>
  ): Promise<ApiResponse<FacebookPage>> {
    return apiCall<FacebookPage>({
      method: 'PUT',
      url: `/api/v1/pages/${pageId}`,
      data: updates,
    })
  }

  async deletePage(pageId: number): Promise<ApiResponse<{ message: string }>> {
    return apiCall<{ message: string }>({
      method: 'DELETE',
      url: `/api/v1/pages/${pageId}`,
    })
  }

  async verifyToken(data: {
    facebook_page_id: string
    access_token: string
  }): Promise<ApiResponse<{
    is_valid: boolean
    page_info?: Record<string, any>
    error_message?: string
  }>> {
    return apiCall({
      method: 'POST',
      url: '/api/v1/pages/verify-token',
      data,
    })
  }

  async syncPage(pageId: number): Promise<ApiResponse<{ message: string }>> {
    return apiCall<{ message: string }>({
      method: 'POST',
      url: `/api/v1/pages/${pageId}/sync`,
    })
  }

  async getPagePosts(pageId: number, limit: number = 25): Promise<ApiResponse<Array<{
    id: number
    scheduled_time: string
    actual_posted_time?: string
    status: string
    facebook_post_id?: string
    post_url?: string
    created_at: string
  }>>> {
    return apiCall({
      method: 'GET',
      url: `/api/v1/pages/${pageId}/posts`,
      params: { limit },
    })
  }
}

export const pagesService = new PagesService()
