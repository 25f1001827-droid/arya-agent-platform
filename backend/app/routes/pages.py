import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select, update, delete, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import SecurityManager, get_current_active_user
from app.models.models import User, FacebookPage, ScheduledPost, PostAnalytics
from app.schemas.pages import (
    FacebookPageCreate, FacebookPageUpdate, FacebookPageResponse,
    FacebookPageWithStats, FacebookPageStats, PageTokenVerification, PageTokenResponse
)
from app.services.facebook_api import FacebookAPIManager

router = APIRouter()


@router.post("/", response_model=FacebookPageResponse, status_code=status.HTTP_201_CREATED)
async def create_facebook_page(
    page_data: FacebookPageCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a new Facebook page to user account."""

    # Check if page already exists
    result = await db.execute(
        select(FacebookPage).where(
            FacebookPage.facebook_page_id == page_data.facebook_page_id
        )
    )
    existing_page = result.scalar_one_or_none()

    if existing_page:
        if existing_page.owner_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This Facebook page is already connected to your account"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This Facebook page is already connected to another account"
            )

    # Verify Facebook page access
    fb_api = FacebookAPIManager()
    try:
        page_verification = await fb_api.verify_page_access(
            page_data.facebook_page_id,
            page_data.access_token
        )

        if not page_verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to verify Facebook page access"
            )

        # Get long-lived token
        long_lived_token_data = await fb_api.get_long_lived_token(page_data.access_token)
        long_lived_token = long_lived_token_data.get("access_token", page_data.access_token)

        # Use page access token if available
        page_access_token = page_verification.get("page_access_token", long_lived_token)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Facebook page verification failed: {str(e)}"
        )
    finally:
        await fb_api.close()

    # Encrypt access tokens
    encrypted_access_token = SecurityManager.encrypt_sensitive_data(long_lived_token)
    encrypted_page_token = SecurityManager.encrypt_sensitive_data(page_access_token) if page_access_token != long_lived_token else encrypted_access_token

    # Create new Facebook page record
    new_page = FacebookPage(
        facebook_page_id=page_data.facebook_page_id,
        page_name=page_verification.get("name", page_data.page_name),
        page_username=page_verification.get("username", page_data.page_username),
        page_url=str(page_data.page_url) if page_data.page_url else page_verification.get("link"),
        category=page_verification.get("category", page_data.category),
        region=page_data.region,
        timezone=page_data.timezone,
        access_token_encrypted=encrypted_access_token,
        page_access_token_encrypted=encrypted_page_token,
        token_expires_at=datetime.now(timezone.utc) + timedelta(days=60) if long_lived_token_data.get("expires_in") else None,
        is_active=True,
        auto_posting_enabled=page_data.auto_posting_enabled,
        posting_frequency_hours=page_data.posting_frequency_hours,
        followers_count=page_verification.get("followers_count", 0),
        likes_count=page_verification.get("fan_count", 0),
        content_themes=page_data.content_themes,
        owner_id=current_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    db.add(new_page)
    await db.commit()
    await db.refresh(new_page)

    # Schedule initial analytics collection
    background_tasks.add_task(collect_initial_analytics, new_page.id)

    return FacebookPageResponse.from_orm(new_page)


@router.get("/", response_model=List[FacebookPageWithStats])
async def get_user_facebook_pages(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all Facebook pages for current user."""

    # Get pages with basic stats
    result = await db.execute(
        select(FacebookPage)
        .where(and_(FacebookPage.owner_id == current_user.id, FacebookPage.is_active == True))
        .order_by(desc(FacebookPage.created_at))
    )
    pages = result.scalars().all()

    # Get stats for each page
    pages_with_stats = []
    for page in pages:
        stats = await get_page_statistics(page.id, db)
        page_with_stats = FacebookPageWithStats(
            **FacebookPageResponse.from_orm(page).dict(),
            stats=stats
        )
        pages_with_stats.append(page_with_stats)

    return pages_with_stats


@router.get("/{page_id}", response_model=FacebookPageWithStats)
async def get_facebook_page(
    page_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific Facebook page details."""

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

    # Get page statistics
    stats = await get_page_statistics(page.id, db)

    return FacebookPageWithStats(
        **FacebookPageResponse.from_orm(page).dict(),
        stats=stats
    )


@router.put("/{page_id}", response_model=FacebookPageResponse)
async def update_facebook_page(
    page_id: int,
    update_data: FacebookPageUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update Facebook page settings."""

    # Find page
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

    # Update page fields
    update_fields = {}
    for field, value in update_data.dict(exclude_unset=True).items():
        if value is not None:
            update_fields[field] = value

    if update_fields:
        update_fields["updated_at"] = datetime.now(timezone.utc)

        await db.execute(
            update(FacebookPage)
            .where(FacebookPage.id == page_id)
            .values(**update_fields)
        )
        await db.commit()
        await db.refresh(page)

    return FacebookPageResponse.from_orm(page)


@router.delete("/{page_id}")
async def delete_facebook_page(
    page_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove Facebook page from account."""

    # Find page
    result = await db.execute(
        select(FacebookPage).where(
            and_(
                FacebookPage.id == page_id,
                FacebookPage.owner_id == current_user.id
            )
        )
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facebook page not found"
        )

    # Soft delete page
    await db.execute(
        update(FacebookPage)
        .where(FacebookPage.id == page_id)
        .values(
            is_active=False,
            updated_at=datetime.now(timezone.utc)
        )
    )
    await db.commit()

    return {"message": "Facebook page removed successfully"}


@router.post("/verify-token", response_model=PageTokenResponse)
async def verify_page_token(
    token_data: PageTokenVerification,
    current_user: User = Depends(get_current_active_user)
):
    """Verify Facebook page access token."""

    fb_api = FacebookAPIManager()

    try:
        page_info = await fb_api.verify_page_access(
            token_data.facebook_page_id,
            token_data.access_token
        )

        return PageTokenResponse(
            is_valid=True,
            page_info=page_info
        )

    except Exception as e:
        return PageTokenResponse(
            is_valid=False,
            error_message=str(e)
        )
    finally:
        await fb_api.close()


@router.post("/{page_id}/sync")
async def sync_facebook_page(
    page_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Sync Facebook page data and analytics."""

    # Find page
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

    # Schedule sync task
    background_tasks.add_task(sync_page_data, page.id)

    return {"message": "Page sync initiated"}


@router.get("/{page_id}/posts")
async def get_page_posts(
    page_id: int,
    limit: int = 25,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recent posts for a Facebook page."""

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

    # Get recent scheduled posts
    posts_result = await db.execute(
        select(ScheduledPost)
        .where(ScheduledPost.facebook_page_id == page_id)
        .order_by(desc(ScheduledPost.created_at))
        .limit(limit)
    )
    posts = posts_result.scalars().all()

    return [
        {
            "id": post.id,
            "scheduled_time": post.scheduled_time,
            "actual_posted_time": post.actual_posted_time,
            "status": post.status.value,
            "facebook_post_id": post.facebook_post_id,
            "post_url": post.post_url,
            "created_at": post.created_at
        }
        for post in posts
    ]


# Helper functions
async def get_page_statistics(page_id: int, db: AsyncSession) -> FacebookPageStats:
    """Get statistics for a Facebook page."""

    # Get total posts count
    total_posts_result = await db.execute(
        select(func.count(ScheduledPost.id))
        .where(ScheduledPost.facebook_page_id == page_id)
    )
    total_posts = total_posts_result.scalar() or 0

    # Get posts this month
    current_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    posts_this_month_result = await db.execute(
        select(func.count(ScheduledPost.id))
        .where(
            and_(
                ScheduledPost.facebook_page_id == page_id,
                ScheduledPost.created_at >= current_month
            )
        )
    )
    posts_this_month = posts_this_month_result.scalar() or 0

    # Get analytics aggregates
    analytics_result = await db.execute(
        select(
            func.avg(PostAnalytics.engagement_rate),
            func.sum(PostAnalytics.reach),
            func.sum(PostAnalytics.impressions)
        )
        .where(PostAnalytics.facebook_page_id == page_id)
    )
    analytics_data = analytics_result.first()

    avg_engagement_rate = float(analytics_data[0] or 0.0)
    total_reach = int(analytics_data[1] or 0)
    total_impressions = int(analytics_data[2] or 0)

    # Determine performance trend (simplified)
    performance_trend = "stable"  # This would be calculated based on historical data

    return FacebookPageStats(
        total_posts=total_posts,
        posts_this_month=posts_this_month,
        avg_engagement_rate=avg_engagement_rate,
        total_reach=total_reach,
        total_impressions=total_impressions,
        performance_trend=performance_trend
    )


# Background tasks
async def collect_initial_analytics(page_id: int):
    """Collect initial analytics for a new page."""
    print(f"Collecting initial analytics for page {page_id}")
    # Implementation would fetch recent posts and analytics


async def sync_page_data(page_id: int):
    """Sync page data with Facebook API."""
    print(f"Syncing data for page {page_id}")
    # Implementation would update page info and collect latest analytics

