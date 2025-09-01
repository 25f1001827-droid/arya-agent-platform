
// Core types for the application
export interface User {
  id: number
  email: string
  username: string
  full_name?: string
  is_active: boolean
  is_verified: boolean
  plan: 'FREE' | 'BASIC' | 'PRO' | 'ENTERPRISE'
  monthly_post_limit: number
  posts_used_this_month: number
  ai_credits_remaining: number
  preferred_region?: 'US' | 'UK'
  timezone?: string
  created_at: string
  last_login?: string
}

export interface FacebookPage {
  id: number
  facebook_page_id: string
  page_name: string
  page_username?: string
  page_url?: string
  category?: string
  region: 'US' | 'UK'
  timezone: string
  is_active: boolean
  auto_posting_enabled: boolean
  posting_frequency_hours: number
  followers_count: number
  likes_count: number
  last_post_date?: string
  optimal_posting_times?: number[]
  content_themes?: string[]
  created_at: string
  updated_at: string
  owner_id: number
  stats?: FacebookPageStats
}

export interface FacebookPageStats {
  total_posts: number
  posts_this_month: number
  avg_engagement_rate: number
  total_reach: number
  total_impressions: number
  performance_trend: 'improving' | 'stable' | 'declining'
}

export interface ContentGeneration {
  id: number
  ai_prompt: string
  content_type: 'IMAGE' | 'TEXT' | 'VIDEO' | 'MIXED'
  generated_caption?: string
  generated_image_url?: string
  generated_hashtags?: string[]
  ai_model_used: string
  generation_cost?: number
  sentiment_score?: number
  readability_score?: number
  predicted_engagement?: number
  performance_score: number
  is_approved: boolean
  approval_date?: string
  facebook_page_id: number
  user_id: number
  created_at: string
  updated_at: string
}

export interface ScheduledPost {
  id: number
  scheduled_time: string
  actual_posted_time?: string
  status: 'DRAFT' | 'SCHEDULED' | 'POSTED' | 'FAILED' | 'CANCELLED'
  facebook_post_id?: string
  post_url?: string
  error_message?: string
  retry_count: number
  max_retries: number
  posting_priority: number
  is_optimal_time: boolean
  user_id: number
  facebook_page_id: number
  content_generation_id?: number
  created_at: string
  updated_at: string
  content?: ContentGeneration
}

export interface PostAnalytics {
  id: number
  facebook_page_id: number
  scheduled_post_id?: number
  impressions: number
  reach: number
  engaged_users: number
  clicks: number
  likes: number
  comments: number
  shares: number
  reactions_love: number
  reactions_wow: number
  reactions_haha: number
  reactions_sad: number
  reactions_angry: number
  engagement_rate: number
  click_through_rate: number
  cost_per_engagement?: number
  performance_score: number
  relative_performance?: string
  last_updated: string
  created_at: string
}

export interface OptimizationInsight {
  id: number
  facebook_page_id: number
  insight_type: string
  insight_data: Record<string, any>
  confidence_score: number
  recommendation: string
  expected_improvement?: number
  is_implemented: boolean
  implementation_date?: string
  actual_improvement?: number
  created_at: string
  expires_at?: string
}

// API Response types
export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface ApiError {
  detail: string
  status?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pages: number
  has_next: boolean
  has_prev: boolean
}

// Form types
export interface LoginForm {
  email: string
  password: string
}

export interface RegisterForm {
  email: string
  username: string
  password: string
  full_name?: string
  preferred_region?: 'US' | 'UK'
  timezone?: string
}

export interface FacebookPageForm {
  facebook_page_id: string
  access_token: string
  page_name: string
  page_username?: string
  page_url?: string
  category?: string
  region: 'US' | 'UK'
  timezone: string
  auto_posting_enabled: boolean
  posting_frequency_hours: number
  content_themes?: string[]
}

export interface ContentGenerationForm {
  facebook_page_id: number
  ai_prompt: string
  content_type: 'IMAGE' | 'TEXT' | 'VIDEO' | 'MIXED'
  target_audience?: string
  tone: string
  include_hashtags: boolean
  include_image: boolean
  custom_instructions?: string
}

// Dashboard types
export interface DashboardStats {
  total_pages: number
  total_posts: number
  total_impressions: number
  total_reach: number
  avg_engagement_rate: number
  ai_credits_used: number
  ai_credits_remaining: number
  posts_this_month: number
  monthly_limit: number
}

export interface AnalyticsDashboard {
  summary: PageAnalyticsSummary
  recent_posts: PostAnalytics[]
  optimization_insights: OptimizationInsight[]
  performance_trends: Record<string, number[]>
  upcoming_optimizations: Array<Record<string, any>>
}

export interface PageAnalyticsSummary {
  facebook_page_id: number
  date_range: { start: string; end: string }
  total_posts: number
  total_impressions: number
  total_reach: number
  total_engaged_users: number
  total_clicks: number
  avg_engagement_rate: number
  avg_click_through_rate: number
  best_performing_post?: Record<string, any>
  worst_performing_post?: Record<string, any>
  posting_frequency: number
  growth_metrics: Record<string, number>
}

// Component prop types
export interface ButtonProps {
  children: React.ReactNode
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  disabled?: boolean
  onClick?: () => void
  type?: 'button' | 'submit' | 'reset'
  className?: string
}

export interface InputProps {
  label?: string
  placeholder?: string
  type?: string
  required?: boolean
  disabled?: boolean
  error?: string
  className?: string
}

export interface CardProps {
  children: React.ReactNode
  title?: string
  subtitle?: string
  className?: string
}

// Navigation types
export interface NavItem {
  name: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  current?: boolean
  badge?: string | number
}

// Chart data types
export interface ChartDataPoint {
  name: string
  value: number
  date?: string
}

export interface TimeSeriesDataPoint {
  date: string
  impressions: number
  reach: number
  engagement_rate: number
  clicks: number
}
