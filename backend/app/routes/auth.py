import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import SecurityManager, get_current_user, get_current_active_user
from app.models.models import User
from app.schemas.auth import (
    UserCreate, UserLogin, UserResponse, UserUpdate,
    TokenResponse, TokenRefresh, PasswordReset, PasswordResetConfirm
)

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""

    # Check if user already exists
    result = await db.execute(
        select(User).where(
            (User.email == user_data.email) | (User.username == user_data.username)
        )
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        if existing_user.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

    # Create new user
    hashed_password = SecurityManager.hash_password(user_data.password)

    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        preferred_region=user_data.preferred_region,
        timezone=user_data.timezone,
        is_active=True,
        is_verified=False,
        created_at=datetime.now(timezone.utc)
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Create tokens
    token_data = {"user_id": new_user.id, "email": new_user.email}
    access_token = SecurityManager.create_access_token(token_data)
    refresh_token = SecurityManager.create_refresh_token(token_data)

    # Schedule welcome email (background task)
    background_tasks.add_task(send_welcome_email, new_user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=60 * 24 * 7,  # 7 days in minutes
        user=UserResponse.from_orm(new_user)
    )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Login user and return access tokens."""

    # Find user by email
    result = await db.execute(
        select(User).where(
            and_(User.email == login_data.email, User.is_active == True)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not SecurityManager.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    # Create tokens
    token_data = {"user_id": user.id, "email": user.email}
    access_token = SecurityManager.create_access_token(token_data)
    refresh_token = SecurityManager.create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=60 * 24 * 7,  # 7 days in minutes
        user=UserResponse.from_orm(user)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""

    # Verify refresh token
    payload = SecurityManager.verify_token(token_data.refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload"
        )

    # Get user from database
    result = await db.execute(
        select(User).where(and_(User.id == user_id, User.is_active == True))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Create new tokens
    new_token_data = {"user_id": user.id, "email": user.email}
    access_token = SecurityManager.create_access_token(new_token_data)
    new_refresh_token = SecurityManager.create_refresh_token(new_token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=60 * 24 * 7,  # 7 days in minutes
        user=UserResponse.from_orm(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information."""
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user information."""

    # Update user fields
    update_fields = {}
    for field, value in update_data.dict(exclude_unset=True).items():
        if value is not None:
            update_fields[field] = value

    if update_fields:
        update_fields["updated_at"] = datetime.now(timezone.utc)

        await db.execute(
            update(User)
            .where(User.id == current_user.id)
            .values(**update_fields)
        )
        await db.commit()

        # Refresh user data
        await db.refresh(current_user)

    return UserResponse.from_orm(current_user)


@router.post("/password-reset")
async def request_password_reset(
    reset_data: PasswordReset,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset."""

    # Find user by email
    result = await db.execute(
        select(User).where(User.email == reset_data.email)
    )
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if user and user.is_active:
        # Generate reset token
        reset_token_data = {
            "user_id": user.id,
            "email": user.email,
            "purpose": "password_reset"
        }
        reset_token = SecurityManager.create_access_token(
            reset_token_data, 
            expires_delta=timedelta(hours=1)
        )

        # Send reset email (background task)
        background_tasks.add_task(
            send_password_reset_email,
            user.email,
            reset_token
        )

    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password-reset-confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """Confirm password reset with new password."""

    # Verify reset token
    payload = SecurityManager.verify_token(reset_data.reset_token)
    if not payload or payload.get("purpose") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    user_id = payload.get("user_id")
    email = payload.get("email")

    # Verify email matches
    if email != reset_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email mismatch"
        )

    # Find user
    result = await db.execute(
        select(User).where(and_(User.id == user_id, User.email == email))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )

    # Update password
    new_hashed_password = SecurityManager.hash_password(reset_data.new_password)

    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            hashed_password=new_hashed_password,
            updated_at=datetime.now(timezone.utc)
        )
    )
    await db.commit()

    return {"message": "Password has been reset successfully"}


@router.post("/logout")
async def logout_user(
    current_user: User = Depends(get_current_active_user)
):
    """Logout user (client should discard tokens)."""
    return {"message": "Successfully logged out"}


@router.delete("/account")
async def delete_account(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete user account (soft delete)."""

    # Soft delete user
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(
            is_active=False,
            updated_at=datetime.now(timezone.utc)
        )
    )
    await db.commit()

    return {"message": "Account has been deactivated"}


# Background tasks
async def send_welcome_email(email: str):
    """Send welcome email to new user."""
    # Implementation would integrate with email service
    print(f"Sending welcome email to {email}")
    # In production, use services like SendGrid, AWS SES, etc.


async def send_password_reset_email(email: str, reset_token: str):
    """Send password reset email."""
    # Implementation would integrate with email service
    reset_url = f"https://yourapp.com/reset-password?token={reset_token}&email={email}"
    print(f"Sending password reset email to {email}: {reset_url}")
    # In production, use services like SendGrid, AWS SES, etc.


# User statistics endpoint
@router.get("/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user usage statistics."""

    # This would typically involve complex queries across multiple tables
    # For now, return basic stats
    stats = {
        "user_id": current_user.id,
        "plan": current_user.plan.value,
        "posts_used_this_month": current_user.posts_used_this_month,
        "monthly_post_limit": current_user.monthly_post_limit,
        "ai_credits_remaining": current_user.ai_credits_remaining,
        "usage_percentage": (current_user.posts_used_this_month / current_user.monthly_post_limit) * 100 if current_user.monthly_post_limit > 0 else 0,
        "account_age_days": (datetime.now(timezone.utc) - current_user.created_at).days,
        "last_login": current_user.last_login
    }

    return stats

