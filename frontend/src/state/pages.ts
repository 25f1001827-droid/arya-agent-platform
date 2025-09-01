
import { create } from 'zustand'
import { pagesService } from '@/services/pages'
import type { FacebookPage, FacebookPageForm, FacebookPageStats } from '@/types'

interface FacebookPageWithStats extends FacebookPage {
  stats?: FacebookPageStats
}

interface PagesState {
  pages: FacebookPageWithStats[]
  currentPage: FacebookPageWithStats | null
  isLoading: boolean
  error: string | null

  // Actions
  fetchPages: () => Promise<void>
  fetchPage: (pageId: number) => Promise<void>
  createPage: (pageData: FacebookPageForm) => Promise<boolean>
  updatePage: (pageId: number, updates: Partial<FacebookPageForm>) => Promise<boolean>
  deletePage: (pageId: number) => Promise<boolean>
  verifyToken: (data: { facebook_page_id: string; access_token: string }) => Promise<boolean>
  syncPage: (pageId: number) => Promise<boolean>
  setCurrentPage: (page: FacebookPageWithStats | null) => void
  clearError: () => void
  resetPages: () => void
}

export const usePagesStore = create<PagesState>()((set, get) => ({
  pages: [],
  currentPage: null,
  isLoading: false,
  error: null,

  fetchPages: async (): Promise<void> => {
    set({ isLoading: true, error: null })

    try {
      const response = await pagesService.getPages()

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return
      }

      if (response.data) {
        set({ 
          pages: response.data,
          isLoading: false,
          error: null
        })
      }
    } catch (error) {
      set({ 
        error: 'Failed to fetch pages',
        isLoading: false
      })
    }
  },

  fetchPage: async (pageId: number): Promise<void> => {
    set({ isLoading: true, error: null })

    try {
      const response = await pagesService.getPage(pageId)

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return
      }

      if (response.data) {
        set({ 
          currentPage: response.data,
          isLoading: false,
          error: null
        })
      }
    } catch (error) {
      set({ 
        error: 'Failed to fetch page details',
        isLoading: false
      })
    }
  },

  createPage: async (pageData: FacebookPageForm): Promise<boolean> => {
    set({ isLoading: true, error: null })

    try {
      const response = await pagesService.createPage(pageData)

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return false
      }

      if (response.data) {
        const currentPages = get().pages
        set({ 
          pages: [...currentPages, response.data],
          isLoading: false,
          error: null
        })
        return true
      }

      return false
    } catch (error) {
      set({ 
        error: 'Failed to create page',
        isLoading: false
      })
      return false
    }
  },

  updatePage: async (pageId: number, updates: Partial<FacebookPageForm>): Promise<boolean> => {
    set({ isLoading: true, error: null })

    try {
      const response = await pagesService.updatePage(pageId, updates)

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return false
      }

      if (response.data) {
        const currentPages = get().pages
        const updatedPages = currentPages.map(page => 
          page.id === pageId ? { ...page, ...response.data } : page
        )

        set({ 
          pages: updatedPages,
          currentPage: get().currentPage?.id === pageId 
            ? { ...get().currentPage!, ...response.data } 
            : get().currentPage,
          isLoading: false,
          error: null
        })
        return true
      }

      return false
    } catch (error) {
      set({ 
        error: 'Failed to update page',
        isLoading: false
      })
      return false
    }
  },

  deletePage: async (pageId: number): Promise<boolean> => {
    set({ isLoading: true, error: null })

    try {
      const response = await pagesService.deletePage(pageId)

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return false
      }

      const currentPages = get().pages
      const filteredPages = currentPages.filter(page => page.id !== pageId)

      set({ 
        pages: filteredPages,
        currentPage: get().currentPage?.id === pageId ? null : get().currentPage,
        isLoading: false,
        error: null
      })
      return true
    } catch (error) {
      set({ 
        error: 'Failed to delete page',
        isLoading: false
      })
      return false
    }
  },

  verifyToken: async (data: { facebook_page_id: string; access_token: string }): Promise<boolean> => {
    set({ isLoading: true, error: null })

    try {
      const response = await pagesService.verifyToken(data)

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return false
      }

      set({ isLoading: false })
      return response.data?.is_valid ?? false
    } catch (error) {
      set({ 
        error: 'Token verification failed',
        isLoading: false
      })
      return false
    }
  },

  syncPage: async (pageId: number): Promise<boolean> => {
    set({ isLoading: true, error: null })

    try {
      const response = await pagesService.syncPage(pageId)

      if (response.error) {
        set({ error: response.error, isLoading: false })
        return false
      }

      set({ isLoading: false })

      // Refresh page data after sync
      await get().fetchPage(pageId)

      return true
    } catch (error) {
      set({ 
        error: 'Page sync failed',
        isLoading: false
      })
      return false
    }
  },

  setCurrentPage: (page: FacebookPageWithStats | null) => {
    set({ currentPage: page })
  },

  clearError: () => {
    set({ error: null })
  },

  resetPages: () => {
    set({
      pages: [],
      currentPage: null,
      isLoading: false,
      error: null
    })
  }
}))
