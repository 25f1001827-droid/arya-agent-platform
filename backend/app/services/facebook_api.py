import asyncio
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import json
import logging

from app.core.config import settings
from app.core.security import SecurityManager
from app.models.models import RegionEnum


logger = logging.getLogger(__name__)


class FacebookAPIManager:
    def __init__(self):
        self.base_url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}"
        self.app_id = settings.FACEBOOK_APP_ID
        self.app_secret = settings.FACEBOOK_APP_SECRET

        self.client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )

        # Rate limiting tracking
        self.rate_limits = {
            "calls_per_hour": 200,  # Facebook Graph API limit
            "calls_made": 0,
            "reset_time": datetime.now(timezone.utc) + timedelta(hours=1)
        }

    async def verify_page_access(self, page_id: str, access_token: str) -> Dict[str, Any]:
        """Verify page access and get page information."""

        try:
            response = await self.client.get(
                f"{self.base_url}/{page_id}",
                params={
                    "access_token": access_token,
                    "fields": "id,name,username,category,link,followers_count,fan_count,access_token"
                }
            )

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                raise Exception(f"Facebook API error: {error_data.get('error', {}).get('message', 'Unknown error')}")

            page_data = response.json()

            return {
                "facebook_page_id": page_data.get("id"),
                "name": page_data.get("name"),
                "username": page_data.get("username"),
                "category": page_data.get("category"),
                "link": page_data.get("link"),
                "followers_count": page_data.get("followers_count", 0),
                "fan_count": page_data.get("fan_count", 0),
                "page_access_token": page_data.get("access_token")
            }

        except httpx.RequestError as e:
            raise Exception(f"Network error connecting to Facebook: {str(e)}")
        except Exception as e:
            logger.error(f"Page verification failed: {str(e)}")
            raise

    async def get_long_lived_token(self, short_lived_token: str) -> Dict[str, Any]:
        """Convert short-lived token to long-lived token."""

        try:
            response = await self.client.get(
                f"{self.base_url}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": self.app_id,
                    "client_secret": self.app_secret,
                    "fb_exchange_token": short_lived_token
                }
            )

            if response.status_code != 200:
                raise Exception(f"Token exchange failed: {response.text}")

            token_data = response.json()

            return {
                "access_token": token_data.get("access_token"),
                "expires_in": token_data.get("expires_in"),
                "token_type": token_data.get("token_type", "bearer")
            }

        except Exception as e:
            logger.error(f"Token exchange failed: {str(e)}")
            raise

    async def post_to_page(
        self, 
        page_id: str, 
        content: Dict[str, Any], 
        access_token: str,
        schedule_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Post content to Facebook page."""

        await self._check_rate_limits()

        # Prepare post data
        post_data = {
            "access_token": access_token
        }

        # Add message/caption
        if content.get("caption"):
            post_data["message"] = content["caption"]

        # Handle scheduled posts
        if schedule_time:
            scheduled_timestamp = int(schedule_time.timestamp())
            post_data["scheduled_publish_time"] = scheduled_timestamp
            post_data["published"] = "false"

        # Handle image posts
        if content.get("image_url"):
            return await self._post_photo(page_id, post_data, content["image_url"])
        else:
            return await self._post_text(page_id, post_data)

    async def _post_photo(self, page_id: str, post_data: Dict, image_url: str) -> Dict[str, Any]:
        """Post photo to Facebook page."""

        photo_data = post_data.copy()
        photo_data["url"] = image_url

        try:
            response = await self.client.post(
                f"{self.base_url}/{page_id}/photos",
                data=photo_data
            )

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                raise Exception(f"Photo post failed: {error_data.get('error', {}).get('message', response.text)}")

            result = response.json()
            self._update_rate_limits()

            return {
                "post_id": result.get("post_id") or result.get("id"),
                "facebook_post_id": result.get("id"),
                "post_url": f"https://facebook.com/{page_id}/posts/{result.get('post_id', '').split('_')[-1]}" if result.get("post_id") else None,
                "success": True
            }

        except Exception as e:
            logger.error(f"Photo post failed for page {page_id}: {str(e)}")
            raise

    async def _post_text(self, page_id: str, post_data: Dict) -> Dict[str, Any]:
        """Post text-only content to Facebook page."""

        try:
            response = await self.client.post(
                f"{self.base_url}/{page_id}/feed",
                data=post_data
            )

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                raise Exception(f"Text post failed: {error_data.get('error', {}).get('message', response.text)}")

            result = response.json()
            self._update_rate_limits()

            return {
                "post_id": result.get("id"),
                "facebook_post_id": result.get("id"),
                "post_url": f"https://facebook.com/{page_id}/posts/{result.get('id', '').split('_')[-1]}" if result.get("id") else None,
                "success": True
            }

        except Exception as e:
            logger.error(f"Text post failed for page {page_id}: {str(e)}")
            raise

    async def get_post_insights(
        self, 
        post_id: str, 
        access_token: str,
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get insights/analytics for a specific post."""

        if not metrics:
            metrics = [
                "post_impressions",
                "post_impressions_unique", 
                "post_engaged_users",
                "post_clicks",
                "post_reactions_like_total",
                "post_reactions_love_total",
                "post_reactions_wow_total",
                "post_reactions_haha_total",
                "post_reactions_sorry_total",
                "post_reactions_anger_total",
                "post_video_views"  # For video posts
            ]

        try:
            response = await self.client.get(
                f"{self.base_url}/{post_id}/insights",
                params={
                    "metric": ",".join(metrics),
                    "access_token": access_token
                }
            )

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                raise Exception(f"Insights fetch failed: {error_data.get('error', {}).get('message', response.text)}")

            insights_data = response.json()
            self._update_rate_limits()

            # Process insights into readable format
            processed_insights = self._process_insights_data(insights_data.get("data", []))

            return processed_insights

        except Exception as e:
            logger.error(f"Failed to fetch insights for post {post_id}: {str(e)}")
            raise

    def _process_insights_data(self, raw_insights: List[Dict]) -> Dict[str, Any]:
        """Process raw Facebook insights data into standardized format."""

        processed = {
            "impressions": 0,
            "reach": 0,
            "engaged_users": 0,
            "clicks": 0,
            "likes": 0,
            "reactions_love": 0,
            "reactions_wow": 0,
            "reactions_haha": 0,
            "reactions_sad": 0,
            "reactions_angry": 0,
            "video_views": 0
        }

        # Map Facebook metrics to our standardized format
        metric_mapping = {
            "post_impressions": "impressions",
            "post_impressions_unique": "reach",
            "post_engaged_users": "engaged_users", 
            "post_clicks": "clicks",
            "post_reactions_like_total": "likes",
            "post_reactions_love_total": "reactions_love",
            "post_reactions_wow_total": "reactions_wow",
            "post_reactions_haha_total": "reactions_haha",
            "post_reactions_sorry_total": "reactions_sad",
            "post_reactions_anger_total": "reactions_angry",
            "post_video_views": "video_views"
        }

        for insight in raw_insights:
            metric_name = insight.get("name")
            if metric_name in metric_mapping:
                values = insight.get("values", [])
                if values:
                    processed[metric_mapping[metric_name]] = values[0].get("value", 0)

        # Calculate derived metrics
        if processed["reach"] > 0:
            processed["engagement_rate"] = (processed["engaged_users"] / processed["reach"]) * 100
        else:
            processed["engagement_rate"] = 0.0

        if processed["impressions"] > 0:
            processed["click_through_rate"] = (processed["clicks"] / processed["impressions"]) * 100
        else:
            processed["click_through_rate"] = 0.0

        # Calculate total reactions
        processed["total_reactions"] = (
            processed["likes"] + processed["reactions_love"] + 
            processed["reactions_wow"] + processed["reactions_haha"] + 
            processed["reactions_sad"] + processed["reactions_angry"]
        )

        return processed

    async def get_page_insights(
        self,
        page_id: str,
        access_token: str,
        period: str = "day",
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get page-level insights."""

        if not metrics:
            metrics = [
                "page_impressions",
                "page_impressions_unique",
                "page_fan_adds",
                "page_fan_removes", 
                "page_views_total",
                "page_post_engagements"
            ]

        try:
            response = await self.client.get(
                f"{self.base_url}/{page_id}/insights",
                params={
                    "metric": ",".join(metrics),
                    "period": period,
                    "access_token": access_token
                }
            )

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                raise Exception(f"Page insights failed: {error_data.get('error', {}).get('message', response.text)}")

            insights_data = response.json()
            self._update_rate_limits()

            return self._process_page_insights(insights_data.get("data", []))

        except Exception as e:
            logger.error(f"Failed to fetch page insights for {page_id}: {str(e)}")
            raise

    def _process_page_insights(self, raw_insights: List[Dict]) -> Dict[str, Any]:
        """Process page insights data."""

        processed = {
            "impressions": 0,
            "reach": 0,
            "fan_adds": 0,
            "fan_removes": 0,
            "page_views": 0,
            "post_engagements": 0
        }

        metric_mapping = {
            "page_impressions": "impressions",
            "page_impressions_unique": "reach",
            "page_fan_adds": "fan_adds",
            "page_fan_removes": "fan_removes",
            "page_views_total": "page_views",
            "page_post_engagements": "post_engagements"
        }

        for insight in raw_insights:
            metric_name = insight.get("name")
            if metric_name in metric_mapping:
                values = insight.get("values", [])
                if values and values[-1]:
                    processed[metric_mapping[metric_name]] = values[-1].get("value", 0)

        return processed

    async def _check_rate_limits(self):
        """Check and enforce rate limits."""
        current_time = datetime.now(timezone.utc)

        # Reset counters if hour has passed
        if current_time >= self.rate_limits["reset_time"]:
            self.rate_limits["calls_made"] = 0
            self.rate_limits["reset_time"] = current_time + timedelta(hours=1)

        # Check if we're at the limit
        if self.rate_limits["calls_made"] >= self.rate_limits["calls_per_hour"]:
            wait_time = (self.rate_limits["reset_time"] - current_time).total_seconds()
            logger.warning(f"Rate limit reached. Waiting {wait_time} seconds.")
            await asyncio.sleep(wait_time)

            # Reset after waiting
            self.rate_limits["calls_made"] = 0
            self.rate_limits["reset_time"] = datetime.now(timezone.utc) + timedelta(hours=1)

    def _update_rate_limits(self):
        """Update rate limit counters after successful API call."""
        self.rate_limits["calls_made"] += 1

    async def delete_post(self, post_id: str, access_token: str) -> bool:
        """Delete a Facebook post."""

        try:
            response = await self.client.delete(
                f"{self.base_url}/{post_id}",
                params={"access_token": access_token}
            )

            self._update_rate_limits()
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Failed to delete post {post_id}: {str(e)}")
            return False

    async def get_page_posts(
        self, 
        page_id: str, 
        access_token: str, 
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Get recent posts from a page."""

        try:
            response = await self.client.get(
                f"{self.base_url}/{page_id}/posts",
                params={
                    "access_token": access_token,
                    "limit": limit,
                    "fields": "id,message,created_time,permalink_url,type"
                }
            )

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                raise Exception(f"Posts fetch failed: {error_data.get('error', {}).get('message', response.text)}")

            posts_data = response.json()
            self._update_rate_limits()

            return posts_data.get("data", [])

        except Exception as e:
            logger.error(f"Failed to fetch posts for page {page_id}: {str(e)}")
            raise

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

