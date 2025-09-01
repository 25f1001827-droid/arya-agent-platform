from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Float, ForeignKey, Enum, Index, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property
import enum

from app.core.database import Base


# Enums
class RegionEnum(str, enum.Enum):
    US = "US"
    UK = "UK"


class ContentTypeEnum(str, enum.Enum):
    IMAGE = "image"
    TEXT = "text"
    VIDEO = "video"
    MIXED = "mixed"


class PostStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PlanTypeEnum(str, enum.Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# Models
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))

    # Status and permissions
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Plan and limits
    plan: Mapped[PlanTypeEnum] = mapped_column(Enum(PlanTypeEnum), default=PlanTypeEnum.FREE)
    monthly_post_limit: Mapped[int] = mapped_column(Integer, default=100)
    posts_used_this_month: Mapped[int] = mapped_column(Integer, default=0)
    ai_credits_remaining: Mapped[int] = mapped_column(Integer, default=1000)

    # Regional preferences
    preferred_region: Mapped[Optional[RegionEnum]] = mapped_column(Enum(RegionEnum))
    timezone: Mapped[Optional[str]] = mapped_column(String(50))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    facebook_pages: Mapped[List["FacebookPage"]] = relationship("FacebookPage", back_populates="owner", cascade="all, delete-orphan")
    content_generations: Mapped[List["ContentGeneration"]] = relationship("ContentGeneration", back_populates="user")
    scheduled_posts: Mapped[List["ScheduledPost"]] = relationship("ScheduledPost", back_populates="user")


class FacebookPage(Base):
    __tablename__ = "facebook_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    facebook_page_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Page details
    page_name: Mapped[str] = mapped_column(String(255), nullable=False)
    page_username: Mapped[Optional[str]] = mapped_column(String(100))
    page_url: Mapped[Optional[str]] = mapped_column(String(500))
    category: Mapped[Optional[str]] = mapped_column(String(100))

    # Regional settings
    region: Mapped[RegionEnum] = mapped_column(Enum(RegionEnum), nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False)

    # Access tokens (encrypted)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    page_access_token_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Status and settings
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_posting_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    posting_frequency_hours: Mapped[int] = mapped_column(Integer, default=6)  # Post every 6 hours

    # Page statistics
    followers_count: Mapped[int] = mapped_column(Integer, default=0)
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    last_post_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Optimization settings
    optimal_posting_times: Mapped[Optional[List[int]]] = mapped_column(JSON)  # Hours in day [9, 12, 15, 18]
    content_themes: Mapped[Optional[List[str]]] = mapped_column(JSON)  # ["health", "fitness", "lifestyle"]

    # Foreign keys
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="facebook_pages")
    content_generations: Mapped[List["ContentGeneration"]] = relationship("ContentGeneration", back_populates="facebook_page")
    scheduled_posts: Mapped[List["ScheduledPost"]] = relationship("ScheduledPost", back_populates="facebook_page")
    post_analytics: Mapped[List["PostAnalytics"]] = relationship("PostAnalytics", back_populates="facebook_page")


class ContentGeneration(Base):
    __tablename__ = "content_generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Content details
    content_type: Mapped[ContentTypeEnum] = mapped_column(Enum(ContentTypeEnum), nullable=False)
    ai_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    generated_caption: Mapped[Optional[str]] = mapped_column(Text)
    generated_image_url: Mapped[Optional[str]] = mapped_column(String(1000))
    generated_hashtags: Mapped[Optional[List[str]]] = mapped_column(JSON)

    # AI model information
    ai_model_used: Mapped[str] = mapped_column(String(100))  # "gemini-pro", "dall-e-3"
    generation_cost: Mapped[Optional[float]] = mapped_column(Float)  # Cost in credits

    # Content optimization
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float)  # -1 to 1
    readability_score: Mapped[Optional[float]] = mapped_column(Float)  # 0 to 100
    predicted_engagement: Mapped[Optional[float]] = mapped_column(Float)  # 0 to 1

    # Performance tracking
    performance_score: Mapped[float] = mapped_column(Float, default=0.0)  # Updated after posting
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Foreign keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    facebook_page_id: Mapped[int] = mapped_column(Integer, ForeignKey("facebook_pages.id"), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="content_generations")
    facebook_page: Mapped["FacebookPage"] = relationship("FacebookPage", back_populates="content_generations")
    scheduled_post: Mapped[Optional["ScheduledPost"]] = relationship("ScheduledPost", back_populates="content_generation", uselist=False)


class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Posting details
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    actual_posted_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[PostStatusEnum] = mapped_column(Enum(PostStatusEnum), default=PostStatusEnum.SCHEDULED, index=True)

    # Facebook post information
    facebook_post_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    post_url: Mapped[Optional[str]] = mapped_column(String(1000))

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # Optimization
    posting_priority: Mapped[int] = mapped_column(Integer, default=5)  # 1-10 priority
    is_optimal_time: Mapped[bool] = mapped_column(Boolean, default=False)  # If posted at optimal time

    # Foreign keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    facebook_page_id: Mapped[int] = mapped_column(Integer, ForeignKey("facebook_pages.id"), nullable=False)
    content_generation_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("content_generations.id"))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="scheduled_posts")
    facebook_page: Mapped["FacebookPage"] = relationship("FacebookPage", back_populates="scheduled_posts")
    content_generation: Mapped[Optional["ContentGeneration"]] = relationship("ContentGeneration", back_populates="scheduled_post")
    analytics: Mapped[Optional["PostAnalytics"]] = relationship("PostAnalytics", back_populates="scheduled_post", uselist=False)


class PostAnalytics(Base):
    __tablename__ = "post_analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Basic metrics
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    reach: Mapped[int] = mapped_column(Integer, default=0)
    engaged_users: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)

    # Engagement metrics
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    reactions_love: Mapped[int] = mapped_column(Integer, default=0)
    reactions_wow: Mapped[int] = mapped_column(Integer, default=0)
    reactions_haha: Mapped[int] = mapped_column(Integer, default=0)
    reactions_sad: Mapped[int] = mapped_column(Integer, default=0)
    reactions_angry: Mapped[int] = mapped_column(Integer, default=0)

    # Calculated metrics
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    click_through_rate: Mapped[float] = mapped_column(Float, default=0.0)
    cost_per_engagement: Mapped[Optional[float]] = mapped_column(Float)

    # Performance scoring
    performance_score: Mapped[float] = mapped_column(Float, default=0.0)
    relative_performance: Mapped[Optional[str]] = mapped_column(String(50))  # "above_average", "below_average"

    # Data collection info
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    data_collection_errors: Mapped[int] = mapped_column(Integer, default=0)

    # Foreign keys
    facebook_page_id: Mapped[int] = mapped_column(Integer, ForeignKey("facebook_pages.id"), nullable=False)
    scheduled_post_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("scheduled_posts.id"))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    facebook_page: Mapped["FacebookPage"] = relationship("FacebookPage", back_populates="post_analytics")
    scheduled_post: Mapped[Optional["ScheduledPost"]] = relationship("ScheduledPost", back_populates="analytics")

    # Calculated properties
    @hybrid_property
    def total_reactions(self) -> int:
        return (self.likes + self.reactions_love + self.reactions_wow + 
                self.reactions_haha + self.reactions_sad + self.reactions_angry)

    @hybrid_property
    def total_engagement(self) -> int:
        return self.total_reactions + self.comments + self.shares


class OptimizationInsight(Base):
    __tablename__ = "optimization_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Insight details
    insight_type: Mapped[str] = mapped_column(String(100), nullable=False)  # "best_time", "content_type", "hashtags"
    insight_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0 to 1

    # Recommendations
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    expected_improvement: Mapped[Optional[float]] = mapped_column(Float)  # Expected % improvement

    # Implementation tracking
    is_implemented: Mapped[bool] = mapped_column(Boolean, default=False)
    implementation_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    actual_improvement: Mapped[Optional[float]] = mapped_column(Float)

    # Foreign keys
    facebook_page_id: Mapped[int] = mapped_column(Integer, ForeignKey("facebook_pages.id"), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))  # When insight becomes stale

    # Relationships
    facebook_page: Mapped["FacebookPage"] = relationship("FacebookPage")


class APIUsage(Base):
    __tablename__ = "api_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Usage details
    api_name: Mapped[str] = mapped_column(String(100), nullable=False)  # "gemini", "dall-e", "facebook"
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)

    # Request/Response info
    request_size: Mapped[Optional[int]] = mapped_column(Integer)  # bytes
    response_size: Mapped[Optional[int]] = mapped_column(Integer)  # bytes
    response_time: Mapped[Optional[float]] = mapped_column(Float)  # seconds
    status_code: Mapped[Optional[int]] = mapped_column(Integer)

    # Cost tracking
    cost_in_credits: Mapped[Optional[float]] = mapped_column(Float)
    cost_in_usd: Mapped[Optional[float]] = mapped_column(Float)

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user: Mapped["User"] = relationship("User")


# Indexes for better query performance
Index("idx_user_email", User.email)
Index("idx_user_username", User.username)
Index("idx_facebook_page_region", FacebookPage.region)
Index("idx_facebook_page_owner", FacebookPage.owner_id)
Index("idx_scheduled_post_time", ScheduledPost.scheduled_time)
Index("idx_scheduled_post_status", ScheduledPost.status)
Index("idx_content_generation_page", ContentGeneration.facebook_page_id)
Index("idx_post_analytics_page", PostAnalytics.facebook_page_id)
Index("idx_api_usage_user", APIUsage.user_id, APIUsage.created_at)

# Unique constraints
UniqueConstraint("facebook_page_id", name="uq_facebook_page_id")
UniqueConstraint("user_id", "email", name="uq_user_email")
