from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator
from app.models.models import RegionEnum


class FacebookPageBase(BaseModel):
    page_name: str = Field(..., min_length=1, max_length=255)
    page_username: Optional[str] = Field(None, max_length=100)
    page_url: Optional[HttpUrl] = None
    category: Optional[str] = Field(None, max_length=100)
    region: RegionEnum
    timezone: str = Field(..., min_length=1)


class FacebookPageCreate(FacebookPageBase):
    facebook_page_id: str = Field(..., min_length=1, max_length=100)
    access_token: str = Field(..., min_length=10)
    auto_posting_enabled: bool = True
    posting_frequency_hours: int = Field(6, ge=1, le=24)
    content_themes: Optional[List[str]] = Field(None, max_items=10)

    @validator('posting_frequency_hours')
    def validate_frequency(cls, v):
        if v < 1 or v > 24:
            raise ValueError('Posting frequency must be between 1 and 24 hours')
        return v


class FacebookPageUpdate(BaseModel):
    page_name: Optional[str] = Field(None, min_length=1, max_length=255)
    page_username: Optional[str] = Field(None, max_length=100)
    page_url: Optional[HttpUrl] = None
    category: Optional[str] = Field(None, max_length=100)
    auto_posting_enabled: Optional[bool] = None
    posting_frequency_hours: Optional[int] = Field(None, ge=1, le=24)
    content_themes: Optional[List[str]] = Field(None, max_items=10)
    optimal_posting_times: Optional[List[int]] = Field(None, max_items=24)


class FacebookPageResponse(FacebookPageBase):
    id: int
    facebook_page_id: str
    is_active: bool
    auto_posting_enabled: bool
    posting_frequency_hours: int
    followers_count: int
    likes_count: int
    last_post_date: Optional[datetime]
    optimal_posting_times: Optional[List[int]]
    content_themes: Optional[List[str]]
    created_at: datetime
    updated_at: datetime
    owner_id: int

    class Config:
        from_attributes = True


class FacebookPageStats(BaseModel):
    total_posts: int
    posts_this_month: int
    avg_engagement_rate: float
    total_reach: int
    total_impressions: int
    performance_trend: str  # "improving", "stable", "declining"


class FacebookPageWithStats(FacebookPageResponse):
    stats: FacebookPageStats


class PageTokenVerification(BaseModel):
    facebook_page_id: str
    access_token: str


class PageTokenResponse(BaseModel):
    is_valid: bool
    page_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

