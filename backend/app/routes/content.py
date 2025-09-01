import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select, update, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.models import (
    User, FacebookPage, ContentGeneration, ScheduledPost, 
    PostStatusEnum, ContentTypeEnum
)
from app.schemas.content import (
    ContentGenerationRequest, ContentGenerationResponse, ContentApproval,
    BulkContentGeneration, ContentOptimizationRequest, ContentOptimizationResponse
)
from app.services.ai_content import AIContentGenerator
from app.services.scheduler import ContentScheduler
from app.services.optimization import ContentOptimizationEngine

router = APIRouter()


@router.post("/generate", response_model=ContentGenerationResponse, status_code=status.HTTP_201_CREATED)
async def generate_content(
    content_request: ContentGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate AI-powered content for a Facebook page."""

    # Check if user has available AI credits
    if current_user.ai_credits_remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient AI credits. Please upgrade your plan."
        )

    # Verify page ownership
    result = await db.execute(
        select(FacebookPage).where(
            and_(
                FacebookPage.id == content_request.facebook_page_id,
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

    # Generate content using AI
    ai_generator = AIContentGenerator()
    try:
        # Determine if image is needed
        include_image = content_request.include_image and content_request.content_type in [
            ContentTypeEnum.IMAGE, ContentTypeEnum.MIXED
        ]

        if include_image:
            generated_content = await ai_generator.generate_complete_post(
                topic=content_request.ai_prompt,
                region=page.region,
                content_type=content_request.content_type,
                target_audience=content_request.target_audience
            )
        else:
            generated_content = await ai_generator.generate_caption(
                region=page.region,
                topic=content_request.ai_prompt,
                content_type=content_request.content_type,
                target_audience=content_request.target_audience,
                tone=content_request.tone,
                include_hashtags=content_request.include_hashtags
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content generation failed: {str(e)}"
        )
    finally:
        await ai_generator.close()

    # Create content generation record
    content_gen = ContentGeneration(
        ai_prompt=content_request.ai_prompt,
        content_type=content_request.content_type,
        generated_caption=generated_content.get("caption"),
        generated_image_url=generated_content.get("image_url"),
        generated_hashtags=generated_content.get("hashtags", []),
        ai_model_used=generated_content.get("ai_model_used", "gemini-pro"),
        generation_cost=generated_content.get("generation_cost", 0.001),
        sentiment_score=generated_content.get("sentiment_score", 0.0),
        readability_score=generated_content.get("readability_score", 50.0),
        predicted_engagement=generated_content.get("overall_quality_score", 0.5),
        performance_score=0.0,  # Will be updated after posting
        is_approved=False,
        user_id=current_user.id,
        facebook_page_id=content_request.facebook_page_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    db.add(content_gen)

    # Deduct AI credits
    current_user.ai_credits_remaining -= int(generated_content.get("generation_cost", 1) * 1000)

    await db.commit()
    await db.refresh(content_gen)

    return ContentGenerationResponse.from_orm(content_gen)


@router.post("/bulk-generate", response_model=List[ContentGenerationResponse])
async def bulk_generate_content(
    bulk_request: BulkContentGeneration,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate multiple pieces of content at once."""

    # Check AI credits for bulk generation
    estimated_cost = len(bulk_request.topics) * 2  # Estimate 2 credits per content
    if current_user.ai_credits_remaining < estimated_cost:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient AI credits for bulk generation"
        )

    # Verify page ownership
    result = await db.execute(
        select(FacebookPage).where(
            and_(
                FacebookPage.id == bulk_request.facebook_page_id,
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

    # Schedule bulk generation as background task
    background_tasks.add_task(
        process_bulk_generation,
        bulk_request,
        page,
        current_user.id
    )

    return {"message": f"Bulk generation of {len(bulk_request.topics)} contents initiated"}


@router.get("/", response_model=List[ContentGenerationResponse])
async def get_user_content(
    page_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's generated content."""

    query = select(ContentGeneration).where(ContentGeneration.user_id == current_user.id)

    if page_id:
        # Verify page ownership
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
        query = query.where(ContentGeneration.facebook_page_id == page_id)

    query = query.order_by(desc(ContentGeneration.created_at)).offset(offset).limit(limit)

    result = await db.execute(query)
    content_items = result.scalars().all()

    return [ContentGenerationResponse.from_orm(item) for item in content_items]


@router.get("/{content_id}", response_model=ContentGenerationResponse)
async def get_content_item(
    content_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific content generation item."""

    result = await db.execute(
        select(ContentGeneration).where(
            and_(
                ContentGeneration.id == content_id,
                ContentGeneration.user_id == current_user.id
            )
        )
    )
    content_item = result.scalar_one_or_none()

    if not content_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )

    return ContentGenerationResponse.from_orm(content_item)


@router.post("/{content_id}/approve", response_model=ContentGenerationResponse)
async def approve_content(
    content_id: int,
    approval_data: ContentApproval,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Approve or reject generated content."""

    # Find content item
    result = await db.execute(
        select(ContentGeneration).where(
            and_(
                ContentGeneration.id == content_id,
                ContentGeneration.user_id == current_user.id
            )
        )
    )
    content_item = result.scalar_one_or_none()

    if not content_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )

    # Update approval status
    content_item.is_approved = approval_data.is_approved
    content_item.approval_date = datetime.now(timezone.utc)
    content_item.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(content_item)

    # If approved, schedule for posting
    if approval_data.is_approved:
        background_tasks.add_task(schedule_approved_content, content_item.id)

    return ContentGenerationResponse.from_orm(content_item)


@router.post("/{content_id}/schedule")
async def schedule_content(
    content_id: int,
    schedule_time: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Schedule approved content for posting."""

    # Find content item
    result = await db.execute(
        select(ContentGeneration).where(
            and_(
                ContentGeneration.id == content_id,
                ContentGeneration.user_id == current_user.id,
                ContentGeneration.is_approved == True
            )
        )
    )
    content_item = result.scalar_one_or_none()

    if not content_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approved content not found"
        )

    # Get page info
    page_result = await db.execute(
        select(FacebookPage).where(FacebookPage.id == content_item.facebook_page_id)
    )
    page = page_result.scalar_one()

    # Calculate optimal posting time if not provided
    if not schedule_time:
        scheduler = ContentScheduler()

        # Get existing scheduled posts
        existing_posts_result = await db.execute(
            select(ScheduledPost.scheduled_time)
            .where(
                and_(
                    ScheduledPost.facebook_page_id == page.id,
                    ScheduledPost.status.in_([PostStatusEnum.SCHEDULED, PostStatusEnum.POSTED])
                )
            )
        )
        existing_times = [row[0] for row in existing_posts_result.fetchall()]

        # Calculate next optimal slot
        schedule_time = scheduler.calculate_next_posting_slot(
            region=page.region,
            existing_posts=existing_times,
            preferred_frequency_hours=page.posting_frequency_hours,
            page_preferences=page.optimal_posting_times
        )

        await scheduler.close()

    # Create scheduled post
    scheduled_post = ScheduledPost(
        scheduled_time=schedule_time,
        status=PostStatusEnum.SCHEDULED,
        user_id=current_user.id,
        facebook_page_id=page.id,
        content_generation_id=content_item.id,
        posting_priority=5,
        is_optimal_time=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    db.add(scheduled_post)
    await db.commit()
    await db.refresh(scheduled_post)

    return {
        "message": "Content scheduled successfully",
        "scheduled_post_id": scheduled_post.id,
        "scheduled_time": scheduled_post.scheduled_time
    }


@router.post("/{content_id}/optimize", response_model=ContentOptimizationResponse)
async def optimize_content(
    content_id: int,
    optimization_request: ContentOptimizationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get optimization suggestions for content."""

    # Find content item
    result = await db.execute(
        select(ContentGeneration).where(
            and_(
                ContentGeneration.id == content_id,
                ContentGeneration.user_id == current_user.id
            )
        )
    )
    content_item = result.scalar_one_or_none()

    if not content_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )

    # Use optimization engine
    optimizer = ContentOptimizationEngine()

    # Create features from content
    from app.services.optimization import ContentFeatures
    features = ContentFeatures(
        posting_hour=12,  # Default, would be extracted from scheduling data
        posting_weekday=1,  # Default
        caption_length=len(content_item.generated_caption or ""),
        hashtag_count=len(content_item.generated_hashtags or []),
        has_image=bool(content_item.generated_image_url),
        sentiment_score=content_item.sentiment_score or 0.0,
        readability_score=content_item.readability_score or 50.0,
        content_type=content_item.content_type.value,
        regional_relevance_score=0.5  # Would be calculated
    )

    # Get optimization suggestions
    suggestions = optimizer.get_content_optimization_suggestions(
        features, optimization_request.target_improvement
    )

    # Predict current performance
    predictions = optimizer.predict_content_performance(features)

    return ContentOptimizationResponse(
        original_content=ContentGenerationResponse.from_orm(content_item),
        suggestions=suggestions,
        expected_improvements=predictions,
        confidence_score=sum(s.get("confidence", 0) for s in suggestions) / len(suggestions) if suggestions else 0.0
    )


@router.delete("/{content_id}")
async def delete_content(
    content_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete generated content."""

    # Find content item
    result = await db.execute(
        select(ContentGeneration).where(
            and_(
                ContentGeneration.id == content_id,
                ContentGeneration.user_id == current_user.id
            )
        )
    )
    content_item = result.scalar_one_or_none()

    if not content_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )

    # Check if content is scheduled
    scheduled_result = await db.execute(
        select(ScheduledPost).where(
            and_(
                ScheduledPost.content_generation_id == content_id,
                ScheduledPost.status == PostStatusEnum.SCHEDULED
            )
        )
    )
    if scheduled_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete scheduled content. Cancel scheduling first."
        )

    # Delete content
    await db.delete(content_item)
    await db.commit()

    return {"message": "Content deleted successfully"}


# Background tasks
async def process_bulk_generation(
    bulk_request: BulkContentGeneration,
    page: FacebookPage,
    user_id: int
):
    """Process bulk content generation in background."""

    ai_generator = AIContentGenerator()
    try:
        for topic in bulk_request.topics:
            try:
                if bulk_request.include_images:
                    generated_content = await ai_generator.generate_complete_post(
                        topic=topic,
                        region=page.region,
                        content_type=bulk_request.content_type,
                        target_audience=None
                    )
                else:
                    generated_content = await ai_generator.generate_caption(
                        region=page.region,
                        topic=topic,
                        content_type=bulk_request.content_type,
                        tone=bulk_request.tone,
                        include_hashtags=bulk_request.include_hashtags
                    )

                # Save to database (simplified - would need proper DB session handling)
                print(f"Generated content for topic: {topic}")

            except Exception as e:
                print(f"Failed to generate content for topic {topic}: {e}")

    finally:
        await ai_generator.close()


async def schedule_approved_content(content_id: int):
    """Schedule approved content for optimal posting."""
    print(f"Scheduling approved content {content_id}")
    # Implementation would calculate optimal time and create ScheduledPost

