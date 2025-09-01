
import React from 'react'
import { Bell, Search, Plus } from 'lucide-react'
import { useAuthStore } from '@/state/auth'
import { useContentStore } from '@/state/content'
import Button from '@/components/ui/Button'

interface HeaderProps {
  title: string
  subtitle?: string
  children?: React.ReactNode
}

const Header: React.FC<HeaderProps> = ({ title, subtitle, children }) => {
  const { user } = useAuthStore()
  const { isGenerating } = useContentStore()

  return (
    <div className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
          {subtitle && (
            <p className="mt-1 text-sm text-gray-600">{subtitle}</p>
          )}
        </div>

        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="search"
              placeholder="Search..."
              className="w-64 pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          {/* Notifications */}
          <div className="relative">
            <Button variant="ghost" size="sm" className="!p-2">
              <Bell className="h-5 w-5" />
            </Button>
            <span className="absolute -top-1 -right-1 h-3 w-3 bg-red-500 rounded-full"></span>
          </div>

          {/* Quick actions */}
          {children}

          {/* User credits indicator */}
          <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg">
            <div className="text-sm">
              <span className="text-gray-600">AI Credits:</span>
              <span className="font-semibold text-gray-900 ml-1">
                {user?.ai_credits_remaining || 0}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Loading indicator for content generation */}
      {isGenerating && (
        <div className="mt-4 bg-primary-50 border border-primary-200 rounded-lg p-3">
          <div className="flex items-center">
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary-600 border-t-transparent mr-3"></div>
            <p className="text-sm text-primary-700">
              AI is generating content...
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default Header
