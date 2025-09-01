import asyncio
from datetime import datetime, timezone, date, timedelta
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy import select, and_, desc, func, between, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.models import (
    User, FacebookPage, PostAnalytics, ScheduledPost, 
    ContentGeneration, OptimizationInsight, RegionEnum
)
from app.schemas.analytics import (
    AnalyticsRequest, PostAnalyticsResponse, PageAnalyticsSummary,
    PerformanceComparison, OptimizationInsightResponse, RegionalPerformanceComparison,
    AnalyticsDashboard, EngagementTimeline, ContentPerformanceAnalysis
)
from app.services.facebook_api import FacebookAPIManager
from app.services.optimization import ContentOptimizationEngine

router = APIRouter()


@router.get("/dashboard", response_model=AnalyticsDashboard)
async def get_analytics_dashboard(
    page_id: Optional[int] = None,
    days: int = Query(30, ge=7, le=90),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive analytics dashboard."""

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # If specific page requested, verify ownership
    if page_id:
        page_result = await db.execute(
            select(FacebookPage).where(
                and_(
                    FacebookPage.id == page_id,
                    FacebookPage.owner_id == current_user.id,
                    FacebookPage.is_active == True
                )
            )
        )
        if not page_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Facebook page not found"
            )
        page_filter = PostAnalytics.facebook_page_id == page_id
    else:
        # Get all user's pages
        pages_result = await db.execute(
            select(FacebookPage.id).where(
                and_(
                    FacebookPage.owner_id == current_user.id,
                    FacebookPage.is_active == True
                )
            )
        )
        page_ids = [row[0] for row in pages_result.fetchall()]
        if not page_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Facebook pages found"
            )
        page_filter = PostAnalytics.facebook_page_id.in_(page_ids)

    # Get summary analytics
    summary = await get_analytics_summary(
        db, page_filter, start_date, end_date, page_id
    )

    # Get recent posts with analytics
    recent_posts = await get_recent_posts_analytics(db, page_filter, limit=10)

    # Get optimization insights
    insights = await get_optimization_insights(db, page_id, current_user.id)

    # Get performance trends (daily aggregates)
    trends = await get_performance_trends(db, page_filter, start_date, end_date)

    # Get upcoming optimizations
    upcoming = await get_upcoming_optimizations(db, page_id, current_user.id)

    return AnalyticsDashboard(
        summary=summary,
        recent_posts=recent_posts,
        optimization_insights=insights,
        performance_trends=trends,
        upcoming_optimizations=upcoming
    )


@router.get("/pages/{page_id}/summary", response_model=PageAnalyticsSummary)
async def get_page_analytics_summary(
    page_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get analytics summary for a specific page."""

    # Verify page ownership
    result = await db.execute(
        select(FacebookPage).where(
            and_(
                FacebookPage.id == page_id,
                FacebookPage.owner_id == current_user.id,
                FacebookPage.is_active == True
            )
        )
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facebook page not found"
        )

    # Set default date range if not provided
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    page_filter = PostAnalytics.facebook_page_id == page_id

    return await get_analytics_summary(db, page_filter, start_date, end_date, page_id)


@router.get("/posts/{post_id}", response_model=PostAnalyticsResponse)
async def get_post_analytics(
    post_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get analytics for a specific post."""

    # Get post analytics with page ownership verification
    result = await db.execute(
        select(PostAnalytics, FacebookPage)
        .join(FacebookPage, PostAnalytics.facebook_page_id == FacebookPage.id)
        .where(
            and_(
                PostAnalytics.id == post_id,
                FacebookPage.owner_id == current_user.id
            )
        )
    )
    analytics_data = result.first()

    if not analytics_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post analytics not found"
        )

    analytics = analytics_data[0]
    return PostAnalyticsResponse.from_orm(analytics)


@router.post("/collect/{page_id}")
async def collect_page_analytics(
    page_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger analytics collection for a page."""

    # Verify page ownership
    result = await db.execute(
        select(FacebookPage).where(
            and_(
                FacebookPage.id == page_id,
                FacebookPage.owner_id == current_user.id,
                FacebookPage.is_active == True
            )
        )
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facebook page not found"
        )

    # Schedule analytics collection
    background_tasks.add_task(collect_analytics_task, page.id)

    return {"message": "Analytics collection initiated"}


@router.get("/compare", response_model=PerformanceComparison)
async def compare_performance(
    page_id: int,
    days_current: int = Query(30, ge=7, le=90),
    days_previous: int = Query(30, ge=7, le=90),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Compare performance between two time periods."""

    # Verify page ownership
    result = await db.execute(
        select(FacebookPage).where(
            and_(
                FacebookPage.id == page_id,
                FacebookPage.owner_id == current_user.id,
                FacebookPage.is_active == True
            )
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facebook page not found"
        )

    # Define time periods
    end_date = date.today()
    current_start = end_date - timedelta(days=days_current)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days_previous)

    page_filter = PostAnalytics.facebook_page_id == page_id

    # Get analytics for both periods
    current_period = await get_analytics_summary(
        db, page_filter, current_start, end_date, page_id
    )

    previous_period = await get_analytics_summary(
        db, page_filter, previous_start, previous_end, page_id
    )

    # Calculate improvements and declines
    improvements = {}
    declines = {}

    metrics = [
        'total_impressions', 'total_reach', 'total_engaged_users',
        'avg_engagement_rate', 'avg_click_through_rate'
    ]

    for metric in metrics:
        current_val = getattr(current_period, metric, 0)
        previous_val = getattr(previous_period, metric, 0)

        if previous_val > 0:
            change_pct = ((current_val - previous_val) / previous_val) * 100
            if change_pct > 5:  # 5% threshold
                improvements[metric] = change_pct
            elif change_pct < -5:
                declines[metric] = abs(change_pct)

    # Generate recommendations based on comparison
    recommendations = generate_performance_recommendations(improvements, declines)

    return PerformanceComparison(
        current_period=current_period,
        previous_period=previous_period,
        improvements=improvements,
        declines=declines,
        recommendations=recommendations
    )


@router.get("/regional-comparison", response_model=RegionalPerformanceComparison)
async def get_regional_performance_comparison(
    days: int = Query(30, ge=7, le=90),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Compare performance between US and UK pages."""

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Get US pages
    us_pages_result = await db.execute(
        select(FacebookPage.id).where(
            and_(
                FacebookPage.owner_id == current_user.id,
                FacebookPage.region == RegionEnum.US,
                FacebookPage.is_active == True
            )
        )
    )
    us_page_ids = [row[0] for row in us_pages_result.fetchall()]

    # Get UK pages
    uk_pages_result = await db.execute(
        select(FacebookPage.id).where(
            and_(
                FacebookPage.owner_id == current_user.id,
                FacebookPage.region == RegionEnum.UK,
                FacebookPage.is_active == True
            )
        )
    )
    uk_page_ids = [row[0] for row in uk_pages_result.fetchall()]

    # Get analytics for each region
    us_performance = None
    uk_performance = None

    if us_page_ids:
        us_filter = PostAnalytics.facebook_page_id.in_(us_page_ids)
        us_performance = await get_analytics_summary(
            db, us_filter, start_date, end_date, None
        )

    if uk_page_ids:
        uk_filter = PostAnalytics.facebook_page_id.in_(uk_page_ids)
        uk_performance = await get_analytics_summary(
            db, uk_filter, start_date, end_date, None
        )

    # Generate regional insights
    regional_insights = []
    cross_regional_recommendations = []

    if us_performance and uk_performance:
        # Compare engagement rates
        if us_performance.avg_engagement_rate > uk_performance.avg_engagement_rate * 1.2:
            regional_insights.append("US pages show significantly higher engagement rates")
            cross_regional_recommendations.append("Apply US content strategies to UK pages")
        elif uk_performance.avg_engagement_rate > us_performance.avg_engagement_rate * 1.2:
            regional_insights.append("UK pages show significantly higher engagement rates")
            cross_regional_recommendations.append("Apply UK content strategies to US pages")

        # Compare posting patterns
        regional_insights.append("Regional posting time optimization recommended")
        cross_regional_recommendations.append("Customize content themes for each region")

    return RegionalPerformanceComparison(
        us_performance=us_performance,
        uk_performance=uk_performance,
        regional_insights=regional_insights,
        cross_regional_recommendations=cross_regional_recommendations
    )


@router.get("/engagement-timeline/{page_id}", response_model=EngagementTimeline)
async def get_engagement_timeline(
    page_id: int,
    days: int = Query(30, ge=7, le=90),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get engagement timeline analysis for a page."""

    # Verify page ownership
    result = await db.execute(
        select(FacebookPage).where(
            and_(
                FacebookPage.id == page_id,
                FacebookPage.owner_id == current_user.id,
                FacebookPage.is_active == True
            )
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facebook page not found"
        )

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Get daily engagement data
    timeline_result = await db.execute(
        select(
            func.date(ScheduledPost.actual_posted_time).label('post_date'),
            func.avg(PostAnalytics.engagement_rate).label('avg_engagement'),
            func.sum(PostAnalytics.total_reactions).label('total_reactions'),
            func.count(PostAnalytics.id).label('post_count')
        )
        .join(PostAnalytics, ScheduledPost.id == PostAnalytics.scheduled_post_id)
        .where(
            and_(
                ScheduledPost.facebook_page_id == page_id,
                func.date(ScheduledPost.actual_posted_time).between(start_date, end_date)
            )
        )
        .group_by(func.date(ScheduledPost.actual_posted_time))
        .order_by(func.date(ScheduledPost.actual_posted_time))
    )

    timeline_data = []
    for row in timeline_result.fetchall():
        timeline_data.append({
            'date': row.post_date.isoformat(),
            'avg_engagement': float(row.avg_engagement or 0),
            'total_reactions': int(row.total_reactions or 0),
            'post_count': int(row.post_count or 0)
        })

    # Analyze peak hours
    peak_hours_result = await db.execute(
        select(
            func.extract('hour', ScheduledPost.actual_posted_time).label('hour'),
            func.avg(PostAnalytics.engagement_rate).label('avg_engagement')
        )
        .join(PostAnalytics, ScheduledPost.id == PostAnalytics.scheduled_post_id)
        .where(
            and_(
                ScheduledPost.facebook_page_id == page_id,
                func.date(ScheduledPost.actual_posted_time).between(start_date, end_date)
            )
        )
        .group_by(func.extract('hour', ScheduledPost.actual_posted_time))
        .order_by(func.avg(PostAnalytics.engagement_rate).desc())
        .limit(5)
    )

    peak_hours = [int(row.hour) for row in peak_hours_result.fetchall()]

    # Analyze best days
    best_days_result = await db.execute(
        select(
            func.extract('dow', ScheduledPost.actual_posted_time).label('day_of_week'),
            func.avg(PostAnalytics.engagement_rate).label('avg_engagement')
        )
        .join(PostAnalytics, ScheduledPost.id == PostAnalytics.scheduled_post_id)
        .where(
            and_(
                ScheduledPost.facebook_page_id == page_id,
                func.date(ScheduledPost.actual_posted_time).between(start_date, end_date)
            )
        )
        .group_by(func.extract('dow', ScheduledPost.actual_posted_time))
        .order_by(func.avg(PostAnalytics.engagement_rate).desc())
    )

    day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    best_days = [day_names[int(row.day_of_week)] for row in best_days_result.fetchall()]

    return EngagementTimeline(
        facebook_page_id=page_id,
        timeline_data=timeline_data,
        peak_hours=peak_hours,
        best_days=best_days,
        seasonal_patterns={}  # Would be calculated with more historical data
    )


@router.get("/content-analysis/{page_id}", response_model=ContentPerformanceAnalysis)
async def get_content_performance_analysis(
    page_id: int,
    days: int = Query(90, ge=30, le=365),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed content performance analysis."""

    # Verify page ownership
    result = await db.execute(
        select(FacebookPage).where(
            and_(
                FacebookPage.id == page_id,
                FacebookPage.owner_id == current_user.id,
                FacebookPage.is_active == True
            )
        )
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facebook page not found"
        )

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Use optimization engine for analysis
    optimizer = ContentOptimizationEngine()

    # Get post data for analysis
    posts_result = await db.execute(
        select(ContentGeneration, ScheduledPost, PostAnalytics)
        .join(ScheduledPost, ContentGeneration.id == ScheduledPost.content_generation_id)
        .join(PostAnalytics, ScheduledPost.id == PostAnalytics.scheduled_post_id)
        .where(
            and_(
                ContentGeneration.facebook_page_id == page_id,
                func.date(ScheduledPost.actual_posted_time).between(start_date, end_date)
            )
        )
    )

    posts_data = []
    for row in posts_result.fetchall():
        content_gen, scheduled_post, analytics = row
        posts_data.append({
            'content_generation': content_gen,
            'scheduled_post': scheduled_post,
            'analytics': analytics
        })

    # Analyze content patterns
    if len(posts_data) >= 10:
        analysis = await optimizer.analyze_content_performance(page_id, posts_data)

        return ContentPerformanceAnalysis(
            content_type_performance=analysis.get('content_analysis', {}).get('content_type_performance', {}),
            optimal_caption_length=150,  # Would be calculated from analysis
            best_hashtag_count=3,  # Would be calculated from analysis
            sentiment_impact=analysis.get('engagement_insights', {}).get('sentiment_impact', {}),
            image_vs_text_performance=analysis.get('content_analysis', {}).get('image_impact', {}),
            regional_preferences={
                'preferred_topics': page.content_themes or [],
                'optimal_posting_times': page.optimal_posting_times or [],
                'region': page.region.value
            }
        )
    else:
        return ContentPerformanceAnalysis(
            content_type_performance={},
            optimal_caption_length=150,
            best_hashtag_count=3,
            sentiment_impact={},
            image_vs_text_performance={},
            regional_preferences={
                'preferred_topics': page.content_themes or [],
                'optimal_posting_times': page.optimal_posting_times or [],
                'region': page.region.value,
                'note': 'Insufficient data for analysis (minimum 10 posts required)'
            }
        )


# Helper functions
async def get_analytics_summary(
    db: AsyncSession,
    page_filter,
    start_date: date,
    end_date: date,
    page_id: Optional[int]
) -> PageAnalyticsSummary:
    """Get analytics summary for given criteria."""

    # Get aggregate analytics
    analytics_result = await db.execute(
        select(
            func.count(PostAnalytics.id).label('total_posts'),
            func.sum(PostAnalytics.impressions).label('total_impressions'),
            func.sum(PostAnalytics.reach).label('total_reach'),
            func.sum(PostAnalytics.engaged_users).label('total_engaged_users'),
            func.sum(PostAnalytics.clicks).label('total_clicks'),
            func.avg(PostAnalytics.engagement_rate).label('avg_engagement_rate'),
            func.avg(PostAnalytics.click_through_rate).label('avg_ctr')
        )
        .join(ScheduledPost, PostAnalytics.scheduled_post_id == ScheduledPost.id)
        .where(
            and_(
                page_filter,
                func.date(ScheduledPost.actual_posted_time).between(start_date, end_date)
            )
        )
    )

    analytics = analytics_result.first()

    # Get best and worst performing posts
    best_post_result = await db.execute(
        select(PostAnalytics)
        .join(ScheduledPost, PostAnalytics.scheduled_post_id == ScheduledPost.id)
        .where(
            and_(
                page_filter,
                func.date(ScheduledPost.actual_posted_time).between(start_date, end_date)
            )
        )
        .order_by(desc(PostAnalytics.engagement_rate))
        .limit(1)
    )
    best_post = best_post_result.scalar_one_or_none()

    worst_post_result = await db.execute(
        select(PostAnalytics)
        .join(ScheduledPost, PostAnalytics.scheduled_post_id == ScheduledPost.id)
        .where(
            and_(
                page_filter,
                func.date(ScheduledPost.actual_posted_time).between(start_date, end_date)
            )
        )
        .order_by(PostAnalytics.engagement_rate)
        .limit(1)
    )
    worst_post = worst_post_result.scalar_one_or_none()

    # Calculate posting frequency
    days_in_period = (end_date - start_date).days
    posting_frequency = (analytics.total_posts or 0) / days_in_period if days_in_period > 0 else 0

    return PageAnalyticsSummary(
        facebook_page_id=page_id or 0,
        date_range={'start': start_date, 'end': end_date},
        total_posts=analytics.total_posts or 0,
        total_impressions=analytics.total_impressions or 0,
        total_reach=analytics.total_reach or 0,
        total_engaged_users=analytics.total_engaged_users or 0,
        total_clicks=analytics.total_clicks or 0,
        avg_engagement_rate=float(analytics.avg_engagement_rate or 0),
        avg_click_through_rate=float(analytics.avg_ctr or 0),
        best_performing_post={"engagement_rate": best_post.engagement_rate} if best_post else None,
        worst_performing_post={"engagement_rate": worst_post.engagement_rate} if worst_post else None,
        posting_frequency=posting_frequency,
        growth_metrics={}  # Would be calculated with historical comparison
    )


async def get_recent_posts_analytics(
    db: AsyncSession,
    page_filter,
    limit: int = 10
) -> List[PostAnalyticsResponse]:
    """Get recent posts with analytics."""

    result = await db.execute(
        select(PostAnalytics)
        .join(ScheduledPost, PostAnalytics.scheduled_post_id == ScheduledPost.id)
        .where(page_filter)
        .order_by(desc(PostAnalytics.created_at))
        .limit(limit)
    )

    analytics = result.scalars().all()
    return [PostAnalyticsResponse.from_orm(a) for a in analytics]


async def get_optimization_insights(
    db: AsyncSession,
    page_id: Optional[int],
    user_id: int
) -> List[OptimizationInsightResponse]:
    """Get optimization insights."""

    query = select(OptimizationInsight)

    if page_id:
        query = query.where(OptimizationInsight.facebook_page_id == page_id)
    else:
        # Get all user's pages
        user_pages = await db.execute(
            select(FacebookPage.id).where(FacebookPage.owner_id == user_id)
        )
        page_ids = [row[0] for row in user_pages.fetchall()]
        query = query.where(OptimizationInsight.facebook_page_id.in_(page_ids))

    query = query.where(OptimizationInsight.expires_at > datetime.now(timezone.utc))
    query = query.order_by(desc(OptimizationInsight.confidence_score))
    query = query.limit(5)

    result = await db.execute(query)
    insights = result.scalars().all()

    return [OptimizationInsightResponse.from_orm(insight) for insight in insights]


async def get_performance_trends(
    db: AsyncSession,
    page_filter,
    start_date: date,
    end_date: date
) -> Dict[str, List[float]]:
    """Get performance trends over time."""

    # Get daily engagement trends
    trends_result = await db.execute(
        select(
            func.date(ScheduledPost.actual_posted_time).label('date'),
            func.avg(PostAnalytics.engagement_rate).label('engagement_rate'),
            func.sum(PostAnalytics.reach).label('reach'),
            func.sum(PostAnalytics.impressions).label('impressions')
        )
        .join(ScheduledPost, PostAnalytics.scheduled_post_id == ScheduledPost.id)
        .where(
            and_(
                page_filter,
                func.date(ScheduledPost.actual_posted_time).between(start_date, end_date)
            )
        )
        .group_by(func.date(ScheduledPost.actual_posted_time))
        .order_by(func.date(ScheduledPost.actual_posted_time))
    )

    engagement_trend = []
    reach_trend = []
    impressions_trend = []

    for row in trends_result.fetchall():
        engagement_trend.append(float(row.engagement_rate or 0))
        reach_trend.append(float(row.reach or 0))
        impressions_trend.append(float(row.impressions or 0))

    return {
        'engagement_rate': engagement_trend,
        'reach': reach_trend,
        'impressions': impressions_trend
    }


async def get_upcoming_optimizations(
    db: AsyncSession,
    page_id: Optional[int],
    user_id: int
) -> List[Dict[str, Any]]:
    """Get upcoming optimization suggestions."""

    # This would typically involve ML predictions and scheduled optimizations
    return [
        {
            'type': 'posting_time',
            'description': 'Optimal posting time adjustment recommended',
            'scheduled_date': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            'expected_improvement': '15% engagement increase'
        }
    ]


def generate_performance_recommendations(
    improvements: Dict[str, float],
    declines: Dict[str, float]
) -> List[str]:
    """Generate recommendations based on performance changes."""

    recommendations = []

    if 'avg_engagement_rate' in declines:
        recommendations.append("Consider refreshing content strategy to improve engagement")

    if 'total_reach' in improvements:
        recommendations.append("Current content is performing well - consider increasing posting frequency")

    if 'avg_click_through_rate' in declines:
        recommendations.append("Review call-to-action strategies and link placement")

    if not improvements and declines:
        recommendations.append("Overall performance is declining - comprehensive strategy review recommended")

    return recommendations or ["Performance is stable - continue current strategies"]


# Background tasks
async def collect_analytics_task(page_id: int):
    """Collect analytics for a page."""
    print(f"Collecting analytics for page {page_id}")
    # Implementation would fetch latest analytics from Facebook API

