from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator
from app.models.models import ContentTypeEnum, RegionEnum


class ContentGenerationBase(BaseModel):
    ai_prompt: str = Field(..., min_length=10, max_length=500)
    content_type: ContentTypeEnum = ContentTypeEnum.MIXED
    target_audience: Optional[str] = Field(None, max_length=100)


class ContentGenerationRequest(ContentGenerationBase):
    facebook_page_id: int
    tone: str = Field("engaging", max_length=50)
    include_hashtags: bool = True
    include_image: bool = True
    custom_instructions: Optional[str] = Field(None, max_length=200)

    @validator('tone')
    def validate_tone(cls, v):
        allowed_tones = ['engaging', 'professional', 'casual', 'humorous', 'inspirational', 'educational']
        if v.lower() not in allowed_tones:
            raise ValueError(f'Tone must be one of: {", ".join(allowed_tones)}')
        return v.lower()


class ContentGenerationResponse(ContentGenerationBase):
    id: int
    facebook_page_id: int
    generated_caption: Optional[str]
    generated_image_url: Optional[str]
    generated_hashtags: Optional[List[str]]
    ai_model_used: str
    generation_cost: Optional[float]
    sentiment_score: Optional[float]
    readability_score: Optional[float]
    predicted_engagement: Optional[float]
    performance_score: float
    is_approved: bool
    approval_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContentApproval(BaseModel):
    content_generation_id: int
    is_approved: bool
    feedback: Optional[str] = Field(None, max_length=500)


class BulkContentGeneration(BaseModel):
    facebook_page_id: int
    topics: List[str] = Field(..., min_items=1, max_items=10)
    content_type: ContentTypeEnum = ContentTypeEnum.MIXED
    tone: str = "engaging"
    include_hashtags: bool = True
    include_images: bool = True

    @validator('topics')
    def validate_topics(cls, v):
        for topic in v:
            if len(topic.strip()) < 5:
                raise ValueError('Each topic must be at least 5 characters long')
        return [topic.strip() for topic in v]


class ContentOptimizationRequest(BaseModel):
    content_generation_id: int
    optimization_goals: List[str] = Field(default=["engagement"], max_items=5)
    target_improvement: float = Field(0.2, ge=0.1, le=1.0)

    @validator('optimization_goals')
    def validate_goals(cls, v):
        allowed_goals = ['engagement', 'reach', 'clicks', 'shares', 'comments']
        for goal in v:
            if goal not in allowed_goals:
                raise ValueError(f'Goal must be one of: {", ".join(allowed_goals)}')
        return v


class ContentOptimizationResponse(BaseModel):
    original_content: ContentGenerationResponse
    suggestions: List[Dict[str, Any]]
    expected_improvements: Dict[str, float]
    confidence_score: float

