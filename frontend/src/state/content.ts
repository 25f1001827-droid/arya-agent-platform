
import { create } from 'zustand'
import { contentService } from '@/services/content'
import type { ContentGeneration, ContentGenerationForm, ScheduledPost } from '@/types'

interface ContentState {
  contentItems: ContentGeneration[]
  scheduledPosts: ScheduledPost[]
  currentContent: ContentGeneration | null
  isLoading: boolean
  isGenerating: boolean
  error: string | null

  // Filters
  selectedPageId: number | null
  contentFilter: 'all' | 'approved' | 'pending' | 'rejected'

  // Actions
  generateContent: (data: ContentGenerationForm) => Promise<boolean>
  bulkGenerate: (data: {
    facebook_page_id: number
    topics: string[]
    content_type: 'IMAGE' | 'TEXT' | 'VIDEO' | 'MIXED'
    tone: string
    include_hashtags: boolean
    include_images: boolean
  }) => Promise<boolean>
  fetchContent: (pageId?: number, limit?: number, offset?: number) => Promise<void>
  fetchContentItem: (contentId: number) => Promise<void>
  approveContent: (contentId: number, approved: boolean, feedback?: string) => Promise<boolean>
  scheduleContent: (contentId: number, scheduleTime?: string) => Promise<boolean>
  deleteContent: (contentId: number) => Promise<boolean>
  fetchScheduledPosts: (pageId?: number, status?: string) => Promise<void>
  setSelectedPageId: (pageId: number | null) => void
  setContentFilter: (filter: 'all' | 'approved' | 'pending' | 'rejected') => void
  setCurrentContent: (content: ContentGeneration | null) => void
  clearError: () => void
  resetContent: () => void
}

export const useContentStore = create<ContentState>()((set, get) => ({
  contentItems: [],
  scheduledPosts: [],
  currentContent: null,
  isLoading: false,
  isGenerating: false,
  error: null,
  selectedPageId: null,
  contentFilter: 'all',

  generateContent: async (data: ContentGenerationForm): Promise<boolean> => {
    set({ isGenerating: true, error: null })

    try {
      const response = await contentService.generateContent(data)

      if (response.error) {
        set({ error: response.error, isGenerating: false })
        return false
      }

      if (response.data) {
        const currentItems = get().contentItems
        set({ 
          contentItems: [response.data, ...currentItems],
          currentContent: response.data,
          isGenerating: false,
          error: null
        })
        return true
      }

      return false
    } catch (error) {
      set({ 
        error: 'Content generation failed',
        isGenerating: false
      })
      return false
    }
  },

  bulkGenerate: async (data): Promise<boolean> => {
    set({ isGenerating: true, error: null })

    try {
      const response = await contentService.bulkGenerate(data)

      if (response.error) {
        set({ error: response.error, isGenerating: false })
        return false
      }

      set({ isGenerating: false })

      // Refresh content list after bulk generation
      await get().fetchContent(data.facebook_page_id)

      return true
    } catch (error) {
      set({ 
        error: 'Bulk generation failed',
        isGenerating: false
      })
      return false
    }
  },

  fetchContent: async (pageId?: number, limit: number = 50, offset: number = 0): Promise<void> => {
    set({ isLoading: true, error: null })

    try {
      const response = await contentService.getContent(pageId, limit, offset)

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return
      }

      if (response.data) {
        set({ 
          contentItems: offset === 0 ? response.data : [...get().contentItems, ...response.data],
          isLoading: false,
          error: null
        })
      }
    } catch (error) {
      set({ 
        error: 'Failed to fetch content',
        isLoading: false
      })
    }
  },

  fetchContentItem: async (contentId: number): Promise<void> => {
    set({ isLoading: true, error: null })

    try {
      const response = await contentService.getContentItem(contentId)

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return
      }

      if (response.data) {
        set({ 
          currentContent: response.data,
          isLoading: false,
          error: null
        })
      }
    } catch (error) {
      set({ 
        error: 'Failed to fetch content item',
        isLoading: false
      })
    }
  },

  approveContent: async (contentId: number, approved: boolean, feedback?: string): Promise<boolean> => {
    set({ isLoading: true, error: null })

    try {
      const response = await contentService.approveContent(contentId, {
        is_approved: approved,
        feedback
      })

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return false
      }

      if (response.data) {
        const currentItems = get().contentItems
        const updatedItems = currentItems.map(item =>
          item.id === contentId ? response.data! : item
        )

        set({ 
          contentItems: updatedItems,
          currentContent: get().currentContent?.id === contentId 
            ? response.data 
            : get().currentContent,
          isLoading: false,
          error: null
        })
        return true
      }

      return false
    } catch (error) {
      set({ 
        error: 'Content approval failed',
        isLoading: false
      })
      return false
    }
  },

  scheduleContent: async (contentId: number, scheduleTime?: string): Promise<boolean> => {
    set({ isLoading: true, error: null })

    try {
      const response = await contentService.scheduleContent(contentId, scheduleTime)

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return false
      }

      set({ isLoading: false })

      // Refresh scheduled posts
      await get().fetchScheduledPosts()

      return true
    } catch (error) {
      set({ 
        error: 'Content scheduling failed',
        isLoading: false
      })
      return false
    }
  },

  deleteContent: async (contentId: number): Promise<boolean> => {
    set({ isLoading: true, error: null })

    try {
      const response = await contentService.deleteContent(contentId)

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return false
      }

      const currentItems = get().contentItems
      const filteredItems = currentItems.filter(item => item.id !== contentId)

      set({ 
        contentItems: filteredItems,
        currentContent: get().currentContent?.id === contentId ? null : get().currentContent,
        isLoading: false,
        error: null
      })
      return true
    } catch (error) {
      set({ 
        error: 'Content deletion failed',
        isLoading: false
      })
      return false
    }
  },

  fetchScheduledPosts: async (pageId?: number, status?: string): Promise<void> => {
    set({ isLoading: true, error: null })

    try {
      const response = await contentService.getScheduledPosts(pageId, status)

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return
      }

      if (response.data) {
        set({ 
          scheduledPosts: response.data,
          isLoading: false,
          error: null
        })
      }
    } catch (error) {
      set({ 
        error: 'Failed to fetch scheduled posts',
        isLoading: false
      })
    }
  },

  setSelectedPageId: (pageId: number | null) => {
    set({ selectedPageId: pageId })
  },

  setContentFilter: (filter: 'all' | 'approved' | 'pending' | 'rejected') => {
    set({ contentFilter: filter })
  },

  setCurrentContent: (content: ContentGeneration | null) => {
    set({ currentContent: content })
  },

  clearError: () => {
    set({ error: null })
  },

  resetContent: () => {
    set({
      contentItems: [],
      scheduledPosts: [],
      currentContent: null,
      isLoading: false,
      isGenerating: false,
      error: null,
      selectedPageId: null,
      contentFilter: 'all'
    })
  }
}))
