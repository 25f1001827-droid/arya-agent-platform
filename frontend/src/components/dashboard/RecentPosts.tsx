
import React from 'react'
import Image from 'next/image'
import { formatRelativeDate, formatNumber } from '@/utils'
import { Eye, Heart, MessageCircle, Share2, ExternalLink } from 'lucide-react'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import type { PostAnalytics } from '@/types'

interface RecentPostsProps {
  posts: PostAnalytics[]
  isLoading?: boolean
}

const RecentPosts: React.FC<RecentPostsProps> = ({ posts, isLoading }) => {
  if (isLoading) {
    return (
      <Card title="Recent Posts">
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse">
              <div className="flex space-x-4">
                <div className="w-16 h-16 bg-gray-200 rounded-lg"></div>
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                  <div className="flex space-x-4">
                    <div className="h-3 bg-gray-200 rounded w-16"></div>
                    <div className="h-3 bg-gray-200 rounded w-16"></div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    )
  }

  if (!posts.length) {
    return (
      <Card title="Recent Posts">
        <div className="text-center py-8">
          <p className="text-gray-500">No recent posts found</p>
        </div>
      </Card>
    )
  }

  const getPerformanceBadge = (score: number) => {
    if (score >= 8) return <Badge variant="success">Excellent</Badge>
    if (score >= 6) return <Badge variant="info">Good</Badge>
    if (score >= 4) return <Badge variant="warning">Average</Badge>
    return <Badge variant="error">Poor</Badge>
  }

  return (
    <Card title="Recent Posts" subtitle={`${posts.length} posts`}>
      <div className="space-y-6">
        {posts.map((post) => (
          <div key={post.id} className="flex space-x-4 p-4 hover:bg-gray-50 rounded-lg transition-colors">
            {/* Post preview image placeholder */}
            <div className="w-16 h-16 bg-gradient-to-br from-primary-100 to-primary-200 rounded-lg flex items-center justify-center">
              <span className="text-xs font-medium text-primary-600">
                {new Date(post.created_at).getDate()}
              </span>
            </div>

            <div className="flex-1 min-w-0">
              {/* Post info */}
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium text-gray-900 truncate">
                  Post #{post.id}
                </p>
                {getPerformanceBadge(post.performance_score)}
              </div>

              <p className="text-sm text-gray-600 mb-3">
                Posted {formatRelativeDate(post.created_at)}
              </p>

              {/* Metrics */}
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                <div className="flex items-center">
                  <Eye className="h-4 w-4 mr-1" />
                  <span>{formatNumber(post.impressions)}</span>
                </div>
                <div className="flex items-center">
                  <Heart className="h-4 w-4 mr-1" />
                  <span>{formatNumber(post.likes)}</span>
                </div>
                <div className="flex items-center">
                  <MessageCircle className="h-4 w-4 mr-1" />
                  <span>{formatNumber(post.comments)}</span>
                </div>
                <div className="flex items-center">
                  <Share2 className="h-4 w-4 mr-1" />
                  <span>{formatNumber(post.shares)}</span>
                </div>
              </div>

              {/* Engagement rate */}
              <div className="mt-2 flex items-center justify-between">
                <div className="flex items-center">
                  <span className="text-xs text-gray-500">Engagement:</span>
                  <span className="text-xs font-medium text-gray-900 ml-1">
                    {post.engagement_rate.toFixed(1)}%
                  </span>
                </div>
                <button className="text-primary-600 hover:text-primary-700 p-1">
                  <ExternalLink className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {posts.length >= 5 && (
        <div className="mt-6 pt-4 border-t border-gray-200">
          <button className="w-full text-center text-sm text-primary-600 hover:text-primary-700 font-medium">
            View all posts
          </button>
        </div>
      )}
    </Card>
  )
}

export default RecentPosts
