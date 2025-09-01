from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from app.models.models import RegionEnum


class AnalyticsRequest(BaseModel):
    facebook_page_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    metrics: Optional[List[str]] = Field(None, max_items=20)

    @validator('end_date')
    def validate_date_range(cls, v, values):
        if 'start_date' in values and values['start_date'] and v:
            if v <= values['start_date']:
                raise ValueError('End date must be after start date')
            if (v - values['start_date']).days > 90:
                raise ValueError('Date range cannot exceed 90 days')
        return v


class PostAnalyticsResponse(BaseModel):
    id: int
    facebook_page_id: int
    scheduled_post_id: Optional[int]
    impressions: int
    reach: int
    engaged_users: int
    clicks: int
    likes: int
    comments: int
    shares: int
    reactions_love: int
    reactions_wow: int
    reactions_haha: int
    reactions_sad: int
    reactions_angry: int
    engagement_rate: float
    click_through_rate: float
    cost_per_engagement: Optional[float]
    performance_score: float
    relative_performance: Optional[str]
    last_updated: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class PageAnalyticsSummary(BaseModel):
    facebook_page_id: int
    date_range: Dict[str, date]
    total_posts: int
    total_impressions: int
    total_reach: int
    total_engaged_users: int
    total_clicks: int
    avg_engagement_rate: float
    avg_click_through_rate: float
    best_performing_post: Optional[Dict[str, Any]]
    worst_performing_post: Optional[Dict[str, Any]]
    posting_frequency: float
    growth_metrics: Dict[str, float]


class PerformanceComparison(BaseModel):
    current_period: PageAnalyticsSummary
    previous_period: PageAnalyticsSummary
    improvements: Dict[str, float]
    declines: Dict[str, float]
    recommendations: List[str]


class OptimizationInsightResponse(BaseModel):
    id: int
    facebook_page_id: int
    insight_type: str
    insight_data: Dict[str, Any]
    confidence_score: float
    recommendation: str
    expected_improvement: Optional[float]
    is_implemented: bool
    implementation_date: Optional[datetime]
    actual_improvement: Optional[float]
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class RegionalPerformanceComparison(BaseModel):
    us_performance: Optional[PageAnalyticsSummary]
    uk_performance: Optional[PageAnalyticsSummary]
    regional_insights: List[str]
    cross_regional_recommendations: List[str]


class AnalyticsDashboard(BaseModel):
    summary: PageAnalyticsSummary
    recent_posts: List[PostAnalyticsResponse]
    optimization_insights: List[OptimizationInsightResponse]
    performance_trends: Dict[str, List[float]]
    upcoming_optimizations: List[Dict[str, Any]]


class EngagementTimeline(BaseModel):
    facebook_page_id: int
    timeline_data: List[Dict[str, Any]]  # Date and engagement metrics
    peak_hours: List[int]
    best_days: List[str]
    seasonal_patterns: Dict[str, Any]


class ContentPerformanceAnalysis(BaseModel):
    content_type_performance: Dict[str, float]
    optimal_caption_length: int
    best_hashtag_count: int
    sentiment_impact: Dict[str, float]
    image_vs_text_performance: Dict[str, float]
    regional_preferences: Dict[str, Any]

