import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pytz
import random
import logging

from app.core.config import settings
from app.models.models import RegionEnum, PostStatusEnum, FacebookPage, ScheduledPost
from app.services.facebook_api import FacebookAPIManager
from app.core.security import SecurityManager


logger = logging.getLogger(__name__)


class ContentScheduler:
    def __init__(self):
        self.fb_api = FacebookAPIManager()

        # Regional timezone mapping
        self.regional_timezones = {
            RegionEnum.US: pytz.timezone(settings.TIMEZONE_US),
            RegionEnum.UK: pytz.timezone(settings.TIMEZONE_UK)
        }

        # Optimal posting times by region (24-hour format)
        self.optimal_posting_times = {
            RegionEnum.US: {
                "weekday": [9, 12, 15, 18, 21],  # EST peak times
                "weekend": [10, 13, 16, 19, 20]
            },
            RegionEnum.UK: {
                "weekday": [8, 12, 17, 19, 21],  # GMT peak times  
                "weekend": [9, 12, 15, 18, 20]
            }
        }

        # Content frequency limits to avoid spamming
        self.posting_limits = {
            "min_interval_hours": 2,    # Minimum time between posts
            "max_daily_posts": 6,       # Maximum posts per day
            "max_weekly_posts": 30      # Maximum posts per week
        }

    def get_optimal_posting_times(
        self, 
        region: RegionEnum, 
        target_date: datetime,
        page_preferences: Optional[List[int]] = None
    ) -> List[datetime]:
        """Get optimal posting times for a specific date and region."""

        timezone = self.regional_timezones[region]
        local_date = target_date.astimezone(timezone)

        # Determine if it's weekday or weekend
        is_weekend = local_date.weekday() >= 5  # Saturday = 5, Sunday = 6
        time_key = "weekend" if is_weekend else "weekday"

        # Use page preferences if available, otherwise use regional defaults
        optimal_hours = page_preferences or self.optimal_posting_times[region][time_key]

        # Create datetime objects for each optimal hour
        optimal_times = []
        for hour in optimal_hours:
            optimal_time = local_date.replace(
                hour=hour, 
                minute=random.randint(0, 59),  # Random minute for natural variation
                second=0, 
                microsecond=0
            )

            # Convert back to UTC
            utc_time = optimal_time.astimezone(timezone.utc)
            optimal_times.append(utc_time)

        return sorted(optimal_times)

    def calculate_next_posting_slot(
        self,
        region: RegionEnum,
        existing_posts: List[datetime],
        preferred_frequency_hours: int = 6,
        page_preferences: Optional[List[int]] = None
    ) -> datetime:
        """Calculate the next available posting slot."""

        now_utc = datetime.now(timezone.utc)
        regional_tz = self.regional_timezones[region]

        # Look ahead for the next 7 days
        for days_ahead in range(7):
            target_date = now_utc + timedelta(days=days_ahead)

            # Get optimal times for this date
            optimal_times = self.get_optimal_posting_times(
                region=region,
                target_date=target_date,
                page_preferences=page_preferences
            )

            for optimal_time in optimal_times:
                # Skip past times
                if optimal_time <= now_utc:
                    continue

                # Check if this slot conflicts with existing posts
                if self._is_slot_available(optimal_time, existing_posts):
                    return optimal_time

        # Fallback: schedule for next available slot based on frequency
        if existing_posts:
            last_post_time = max(existing_posts)
            next_slot = last_post_time + timedelta(hours=preferred_frequency_hours)
        else:
            next_slot = now_utc + timedelta(hours=1)  # Start in 1 hour

        return self._adjust_to_optimal_time(next_slot, region, page_preferences)

    def _is_slot_available(
        self, 
        proposed_time: datetime, 
        existing_posts: List[datetime],
        min_gap_hours: int = 2
    ) -> bool:
        """Check if a proposed posting time conflicts with existing posts."""

        min_gap = timedelta(hours=min_gap_hours)

        for existing_time in existing_posts:
            if abs(proposed_time - existing_time) < min_gap:
                return False

        return True

    def _adjust_to_optimal_time(
        self,
        base_time: datetime,
        region: RegionEnum,
        page_preferences: Optional[List[int]] = None
    ) -> datetime:
        """Adjust a base time to the nearest optimal posting time."""

        regional_tz = self.regional_timezones[region]
        local_time = base_time.astimezone(regional_tz)

        # Get optimal times for this day
        optimal_times = self.get_optimal_posting_times(
            region=region,
            target_date=base_time,
            page_preferences=page_preferences
        )

        if not optimal_times:
            return base_time

        # Find the closest optimal time
        closest_time = min(optimal_times, key=lambda t: abs((t - base_time).total_seconds()))

        return closest_time

    def generate_posting_schedule(
        self,
        region: RegionEnum,
        start_date: datetime,
        end_date: datetime,
        posts_per_day: int = 3,
        page_preferences: Optional[Dict[str, Any]] = None
    ) -> List[datetime]:
        """Generate a complete posting schedule for a date range."""

        schedule = []
        current_date = start_date

        # Extract page preferences
        optimal_hours = page_preferences.get("optimal_posting_times") if page_preferences else None
        min_interval = page_preferences.get("min_interval_hours", 2) if page_preferences else 2

        while current_date <= end_date:
            # Get optimal times for this day
            daily_optimal_times = self.get_optimal_posting_times(
                region=region,
                target_date=current_date,
                page_preferences=optimal_hours
            )

            # Select subset based on posts_per_day
            if len(daily_optimal_times) > posts_per_day:
                # Randomly sample to avoid predictable patterns
                selected_times = random.sample(daily_optimal_times, posts_per_day)
                selected_times.sort()
            else:
                selected_times = daily_optimal_times

            # Ensure minimum interval between posts
            filtered_times = []
            last_time = None

            for time_slot in selected_times:
                if last_time is None or (time_slot - last_time).total_seconds() >= min_interval * 3600:
                    filtered_times.append(time_slot)
                    last_time = time_slot

            schedule.extend(filtered_times)
            current_date += timedelta(days=1)

        return sorted(schedule)

    def add_human_like_variance(self, scheduled_times: List[datetime]) -> List[datetime]:
        """Add human-like variance to scheduled posting times."""

        varied_times = []

        for scheduled_time in scheduled_times:
            # Add random variance: ±30 minutes
            variance_minutes = random.randint(-30, 30)
            varied_time = scheduled_time + timedelta(minutes=variance_minutes)

            # Ensure we don't go before current time
            now_utc = datetime.now(timezone.utc)
            if varied_time <= now_utc:
                varied_time = now_utc + timedelta(minutes=random.randint(5, 15))

            varied_times.append(varied_time)

        return sorted(varied_times)

    async def validate_posting_schedule(
        self,
        facebook_page: FacebookPage,
        proposed_schedule: List[datetime]
    ) -> Dict[str, Any]:
        """Validate a proposed posting schedule against constraints."""

        now_utc = datetime.now(timezone.utc)
        validation_results = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "suggested_adjustments": []
        }

        # Check if any times are in the past
        past_times = [t for t in proposed_schedule if t <= now_utc]
        if past_times:
            validation_results["errors"].append(
                f"{len(past_times)} scheduled times are in the past"
            )
            validation_results["is_valid"] = False

        # Check daily limits
        daily_counts = {}
        for scheduled_time in proposed_schedule:
            date_key = scheduled_time.date()
            daily_counts[date_key] = daily_counts.get(date_key, 0) + 1

        max_daily = self.posting_limits["max_daily_posts"]
        over_limit_days = [date for date, count in daily_counts.items() if count > max_daily]

        if over_limit_days:
            validation_results["warnings"].append(
                f"{len(over_limit_days)} days exceed daily posting limit of {max_daily}"
            )

        # Check minimum intervals
        min_interval = timedelta(hours=self.posting_limits["min_interval_hours"])
        sorted_times = sorted(proposed_schedule)

        for i in range(1, len(sorted_times)):
            if (sorted_times[i] - sorted_times[i-1]) < min_interval:
                validation_results["warnings"].append(
                    f"Posts scheduled too close together: {sorted_times[i-1]} and {sorted_times[i]}"
                )

        # Check weekly limits
        weekly_count = len([t for t in proposed_schedule if t <= now_utc + timedelta(weeks=1)])
        if weekly_count > self.posting_limits["max_weekly_posts"]:
            validation_results["warnings"].append(
                f"Weekly limit of {self.posting_limits['max_weekly_posts']} posts may be exceeded"
            )

        # Suggest optimal time adjustments
        regional_tz = self.regional_timezones[facebook_page.region]
        suboptimal_times = []

        for scheduled_time in proposed_schedule:
            local_time = scheduled_time.astimezone(regional_tz)
            hour = local_time.hour

            # Check if time is in optimal range
            is_weekday = local_time.weekday() < 5
            time_key = "weekday" if is_weekday else "weekend"
            optimal_hours = self.optimal_posting_times[facebook_page.region][time_key]

            if hour not in optimal_hours:
                suboptimal_times.append(scheduled_time)

        if suboptimal_times:
            validation_results["suggested_adjustments"].append(
                f"{len(suboptimal_times)} posts scheduled outside optimal times"
            )

        return validation_results

    def optimize_schedule_for_engagement(
        self,
        region: RegionEnum,
        base_schedule: List[datetime],
        historical_performance: Optional[Dict[int, float]] = None
    ) -> List[datetime]:
        """Optimize posting schedule based on historical engagement data."""

        if not historical_performance:
            # Use default optimal times if no historical data
            return base_schedule

        # Sort hours by performance score
        sorted_hours = sorted(
            historical_performance.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Get top performing hours
        top_hours = [hour for hour, _ in sorted_hours[:5]]

        # Adjust schedule to favor high-performing hours
        optimized_schedule = []
        regional_tz = self.regional_timezones[region]

        for scheduled_time in base_schedule:
            local_time = scheduled_time.astimezone(regional_tz)
            current_hour = local_time.hour

            # If current hour is not in top performers, try to adjust
            if current_hour not in top_hours and top_hours:
                # Find nearest top performing hour
                closest_hour = min(top_hours, key=lambda h: abs(h - current_hour))

                # Create new time with optimized hour
                optimized_local_time = local_time.replace(
                    hour=closest_hour,
                    minute=random.randint(0, 59)
                )
                optimized_utc_time = optimized_local_time.astimezone(timezone.utc)
                optimized_schedule.append(optimized_utc_time)
            else:
                optimized_schedule.append(scheduled_time)

        return sorted(optimized_schedule)

    def calculate_posting_frequency(
        self,
        page_followers: int,
        content_quality_score: float,
        engagement_history: Optional[Dict[str, float]] = None
    ) -> int:
        """Calculate optimal posting frequency based on page metrics."""

        base_frequency = 6  # 6 hours between posts

        # Adjust based on follower count
        if page_followers > 100000:
            base_frequency = 4  # More frequent for larger audiences
        elif page_followers > 50000:
            base_frequency = 5
        elif page_followers < 1000:
            base_frequency = 8  # Less frequent for smaller audiences

        # Adjust based on content quality
        if content_quality_score > 0.8:
            base_frequency = max(2, base_frequency - 1)  # Higher quality = more frequent
        elif content_quality_score < 0.5:
            base_frequency = min(12, base_frequency + 2)  # Lower quality = less frequent

        # Adjust based on engagement history
        if engagement_history:
            avg_engagement = sum(engagement_history.values()) / len(engagement_history)
            if avg_engagement > 5.0:  # High engagement rate
                base_frequency = max(3, base_frequency - 1)
            elif avg_engagement < 1.0:  # Low engagement rate
                base_frequency = min(12, base_frequency + 2)

        return base_frequency

    async def close(self):
        """Clean up resources."""
        await self.fb_api.close()

