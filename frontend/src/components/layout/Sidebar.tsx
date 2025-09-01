
import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { 
  LayoutDashboard, 
  Facebook, 
  PenTool, 
  Calendar, 
  BarChart3, 
  Settings,
  LogOut,
  User,
  CreditCard
} from 'lucide-react'

import { cn } from '@/utils'
import { useAuthStore } from '@/state/auth'
import { usePagesStore } from '@/state/pages'
import type { NavItem } from '@/types'

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Facebook Pages', href: '/pages', icon: Facebook },
  { name: 'Content Studio', href: '/content', icon: PenTool },
  { name: 'Scheduler', href: '/scheduler', icon: Calendar },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Settings', href: '/settings', icon: Settings },
]

interface SidebarProps {
  className?: string
}

const Sidebar: React.FC<SidebarProps> = ({ className }) => {
  const pathname = usePathname()
  const { user, logout } = useAuthStore()
  const { pages } = usePagesStore()

  const handleLogout = async () => {
    await logout()
    window.location.href = '/auth/login'
  }

  return (
    <div className={cn('flex h-full w-64 flex-col bg-gray-900', className)}>
      {/* Logo */}
      <div className="flex h-16 shrink-0 items-center px-6">
        <div className="text-white text-xl font-bold">
          SocialAI
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col px-6 pb-4">
        <ul className="flex flex-1 flex-col gap-y-7">
          <li>
            <ul className="-mx-2 space-y-1">
              {navigation.map((item) => {
                const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
                return (
                  <li key={item.name}>
                    <Link
                      href={item.href}
                      className={cn(
                        'group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-semibold',
                        isActive
                          ? 'bg-gray-800 text-white'
                          : 'text-gray-400 hover:text-white hover:bg-gray-800'
                      )}
                    >
                      <item.icon className="h-6 w-6 shrink-0" />
                      {item.name}
                      {item.name === 'Facebook Pages' && pages.length > 0 && (
                        <span className="ml-auto bg-primary-600 text-white text-xs rounded-full px-2 py-0.5">
                          {pages.length}
                        </span>
                      )}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </li>

          {/* User section */}
          <li className="mt-auto">
            <div className="border-t border-gray-700 pt-6">
              {/* User info */}
              <div className="flex items-center px-2 py-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-600 text-white text-sm font-medium">
                  {user?.username?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-white">
                    {user?.full_name || user?.username || 'User'}
                  </p>
                  <p className="text-xs text-gray-400 capitalize">
                    {user?.plan?.toLowerCase() || 'free'} plan
                  </p>
                </div>
              </div>

              {/* User menu */}
              <ul className="space-y-1">
                <li>
                  <Link
                    href="/profile"
                    className="group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-semibold text-gray-400 hover:text-white hover:bg-gray-800"
                  >
                    <User className="h-6 w-6 shrink-0" />
                    Profile
                  </Link>
                </li>
                <li>
                  <Link
                    href="/billing"
                    className="group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-semibold text-gray-400 hover:text-white hover:bg-gray-800"
                  >
                    <CreditCard className="h-6 w-6 shrink-0" />
                    Billing
                  </Link>
                </li>
                <li>
                  <button
                    onClick={handleLogout}
                    className="w-full group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-semibold text-gray-400 hover:text-white hover:bg-gray-800"
                  >
                    <LogOut className="h-6 w-6 shrink-0" />
                    Sign out
                  </button>
                </li>
              </ul>
            </div>
          </li>
        </ul>
      </nav>
    </div>
  )
}

export default Sidebar
