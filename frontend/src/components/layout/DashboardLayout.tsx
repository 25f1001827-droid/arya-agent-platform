
import React, { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { toast, Toaster } from 'react-hot-toast'

import { useAuthStore } from '@/state/auth'
import { usePagesStore } from '@/state/pages'
import Sidebar from './Sidebar'
import Header from './Header'
import LoadingSpinner from '@/components/ui/LoadingSpinner'

interface DashboardLayoutProps {
  children: React.ReactNode
  title: string
  subtitle?: string
  headerActions?: React.ReactNode
}

const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  children,
  title,
  subtitle,
  headerActions
}) => {
  const router = useRouter()
  const { user, isAuthenticated, isLoading, getCurrentUser } = useAuthStore()
  const { fetchPages } = usePagesStore()

  useEffect(() => {
    // Check authentication status on mount
    if (!isAuthenticated) {
      getCurrentUser()
    }
  }, [isAuthenticated, getCurrentUser])

  useEffect(() => {
    // Redirect to login if not authenticated and not loading
    if (!isLoading && !isAuthenticated) {
      router.push('/auth/login')
      return
    }

    // Fetch user's pages if authenticated
    if (isAuthenticated && user) {
      fetchPages().catch(error => {
        console.error('Failed to fetch pages:', error)
      })
    }
  }, [isAuthenticated, isLoading, user, router, fetchPages])

  // Show loading spinner while checking authentication
  if (isLoading || (!isAuthenticated && !user)) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="flex">
        {/* Sidebar */}
        <Sidebar />

        {/* Main content */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Header */}
          <Header title={title} subtitle={subtitle}>
            {headerActions}
          </Header>

          {/* Page content */}
          <main className="flex-1 p-6">
            {children}
          </main>
        </div>
      </div>

      {/* Toast notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 3000,
            iconTheme: {
              primary: '#22c55e',
              secondary: '#fff',
            },
          },
          error: {
            duration: 5000,
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
    </div>
  )
}

export default DashboardLayout
