import asyncio
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import json
import logging
from dataclasses import dataclass
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error

from app.models.models import (
    RegionEnum, FacebookPage, PostAnalytics, 
    ContentGeneration, ScheduledPost, OptimizationInsight
)


logger = logging.getLogger(__name__)


@dataclass
class ContentFeatures:
    """Features extracted from content for optimization."""
    posting_hour: int
    posting_weekday: int
    caption_length: int
    hashtag_count: int
    has_image: bool
    sentiment_score: float
    readability_score: float
    content_type: str
    regional_relevance_score: float


@dataclass
class PerformanceMetrics:
    """Standardized performance metrics."""
    engagement_rate: float
    reach_rate: float
    click_through_rate: float
    total_reactions: int
    comments: int
    shares: int
    performance_score: float


class ContentOptimizationEngine:
    def __init__(self):
        self.feature_weights = {
            "posting_time": 0.25,
            "content_length": 0.15,
            "hashtag_count": 0.10,
            "image_presence": 0.20,
            "sentiment_score": 0.15,
            "regional_relevance": 0.15
        }

        # ML Models for different metrics
        self.engagement_model = LinearRegression()
        self.reach_model = LinearRegression()
        self.click_model = LinearRegression()
        self.scaler = StandardScaler()

        # Model performance tracking
        self.model_performance = {
            "engagement": {"accuracy": 0.0, "last_trained": None},
            "reach": {"accuracy": 0.0, "last_trained": None},
            "click": {"accuracy": 0.0, "last_trained": None}
        }

    async def analyze_content_performance(
        self,
        page_id: int,
        posts_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze content performance patterns for a page."""

        if len(posts_data) < 10:
            return {"error": "Insufficient data for analysis (minimum 10 posts required)"}

        # Extract features and performance metrics
        features_list = []
        performance_list = []

        for post_data in posts_data:
            try:
                features = self._extract_content_features(post_data)
                performance = self._extract_performance_metrics(post_data)

                features_list.append(features)
                performance_list.append(performance)
            except Exception as e:
                logger.warning(f"Failed to process post data: {e}")
                continue

        if len(features_list) < 5:
            return {"error": "Insufficient valid data for analysis"}

        # Analyze patterns
        analysis_results = {
            "total_posts_analyzed": len(features_list),
            "time_analysis": self._analyze_posting_times(features_list, performance_list),
            "content_analysis": self._analyze_content_patterns(features_list, performance_list),
            "engagement_insights": self._analyze_engagement_patterns(features_list, performance_list),
            "optimization_recommendations": []
        }

        # Generate recommendations
        recommendations = self._generate_optimization_recommendations(
            features_list, performance_list, analysis_results
        )
        analysis_results["optimization_recommendations"] = recommendations

        return analysis_results

    def _extract_content_features(self, post_data: Dict[str, Any]) -> ContentFeatures:
        """Extract features from post data for analysis."""

        scheduled_post = post_data.get("scheduled_post", {})
        content_gen = post_data.get("content_generation", {})
        analytics = post_data.get("analytics", {})

        # Extract posting time features
        posted_time = scheduled_post.get("actual_posted_time") or scheduled_post.get("scheduled_time")
        if isinstance(posted_time, str):
            posted_time = datetime.fromisoformat(posted_time.replace('Z', '+00:00'))

        posting_hour = posted_time.hour if posted_time else 12
        posting_weekday = posted_time.weekday() if posted_time else 0

        # Extract content features
        caption = content_gen.get("generated_caption", "")
        caption_length = len(caption)

        # Count hashtags
        hashtag_count = caption.count('#') if caption else 0

        # Check for image
        has_image = bool(content_gen.get("generated_image_url"))

        # Get AI scores
        sentiment_score = content_gen.get("sentiment_score", 0.0)
        readability_score = content_gen.get("readability_score", 50.0)

        # Content type
        content_type = content_gen.get("content_type", "mixed")

        # Calculate regional relevance (simplified)
        regional_relevance_score = self._calculate_regional_relevance(caption, content_gen)

        return ContentFeatures(
            posting_hour=posting_hour,
            posting_weekday=posting_weekday,
            caption_length=caption_length,
            hashtag_count=hashtag_count,
            has_image=has_image,
            sentiment_score=sentiment_score,
            readability_score=readability_score,
            content_type=content_type,
            regional_relevance_score=regional_relevance_score
        )

    def _extract_performance_metrics(self, post_data: Dict[str, Any]) -> PerformanceMetrics:
        """Extract performance metrics from post data."""

        analytics = post_data.get("analytics", {})

        # Basic metrics
        impressions = analytics.get("impressions", 0)
        reach = analytics.get("reach", 0)
        engaged_users = analytics.get("engaged_users", 0)
        clicks = analytics.get("clicks", 0)

        # Engagement metrics
        likes = analytics.get("likes", 0)
        comments = analytics.get("comments", 0)
        shares = analytics.get("shares", 0)
        reactions = analytics.get("total_reactions", likes)

        # Calculate rates
        engagement_rate = (engaged_users / reach * 100) if reach > 0 else 0.0
        reach_rate = (reach / impressions * 100) if impressions > 0 else 0.0
        click_through_rate = (clicks / impressions * 100) if impressions > 0 else 0.0

        # Calculate overall performance score
        performance_score = analytics.get("performance_score", 0.0)
        if performance_score == 0.0:
            performance_score = self._calculate_performance_score(
                engagement_rate, reach_rate, click_through_rate, reactions, comments, shares
            )

        return PerformanceMetrics(
            engagement_rate=engagement_rate,
            reach_rate=reach_rate,
            click_through_rate=click_through_rate,
            total_reactions=reactions,
            comments=comments,
            shares=shares,
            performance_score=performance_score
        )

    def _calculate_regional_relevance(self, caption: str, content_gen: Dict) -> float:
        """Calculate how relevant content is to the regional audience."""

        # Simple keyword-based relevance scoring
        us_keywords = ["dollar", "$", "america", "usa", "thanksgiving", "nfl", "superbowl"]
        uk_keywords = ["pound", "£", "britain", "uk", "tea", "premier league", "bank holiday"]

        caption_lower = caption.lower() if caption else ""

        us_score = sum(1 for keyword in us_keywords if keyword in caption_lower)
        uk_score = sum(1 for keyword in uk_keywords if keyword in caption_lower)

        # Normalize to 0-1 scale
        max_possible = max(len(us_keywords), len(uk_keywords))
        relevance_score = max(us_score, uk_score) / max_possible if max_possible > 0 else 0.5

        return min(1.0, relevance_score)

    def _calculate_performance_score(
        self,
        engagement_rate: float,
        reach_rate: float,
        ctr: float,
        reactions: int,
        comments: int,
        shares: int
    ) -> float:
        """Calculate overall performance score."""

        # Weighted combination of metrics
        weights = {
            "engagement_rate": 0.4,
            "reach_rate": 0.2,
            "ctr": 0.2,
            "social_signals": 0.2
        }

        # Normalize social signals (reactions, comments, shares)
        social_score = min(1.0, (reactions + comments * 3 + shares * 5) / 100)

        # Combine metrics
        score = (
            weights["engagement_rate"] * (engagement_rate / 10) +  # Normalize to 0-1
            weights["reach_rate"] * (reach_rate / 100) +
            weights["ctr"] * (ctr / 5) +  # Typical good CTR is 2-5%
            weights["social_signals"] * social_score
        )

        return min(1.0, score)

    def _analyze_posting_times(
        self,
        features: List[ContentFeatures],
        performance: List[PerformanceMetrics]
    ) -> Dict[str, Any]:
        """Analyze optimal posting times."""

        hour_performance = defaultdict(list)
        weekday_performance = defaultdict(list)

        for feat, perf in zip(features, performance):
            hour_performance[feat.posting_hour].append(perf.engagement_rate)
            weekday_performance[feat.posting_weekday].append(perf.engagement_rate)

        # Calculate average performance by hour
        best_hours = {}
        for hour, rates in hour_performance.items():
            best_hours[hour] = {
                "avg_engagement": np.mean(rates),
                "post_count": len(rates)
            }

        # Sort by performance
        sorted_hours = sorted(
            best_hours.items(),
            key=lambda x: x[1]["avg_engagement"],
            reverse=True
        )

        # Calculate average performance by weekday
        best_weekdays = {}
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for weekday, rates in weekday_performance.items():
            best_weekdays[weekday_names[weekday]] = {
                "avg_engagement": np.mean(rates),
                "post_count": len(rates)
            }

        return {
            "best_hours": dict(sorted_hours[:5]),  # Top 5 hours
            "best_weekdays": best_weekdays,
            "recommendations": {
                "optimal_hours": [hour for hour, _ in sorted_hours[:3]],
                "avoid_hours": [hour for hour, _ in sorted_hours[-2:]]
            }
        }

    def _analyze_content_patterns(
        self,
        features: List[ContentFeatures],
        performance: List[PerformanceMetrics]
    ) -> Dict[str, Any]:
        """Analyze content patterns that drive performance."""

        # Analyze caption length impact
        length_buckets = {
            "short": (0, 100),
            "medium": (100, 200),
            "long": (200, 300),
            "very_long": (300, 1000)
        }

        length_performance = defaultdict(list)

        for feat, perf in zip(features, performance):
            for bucket, (min_len, max_len) in length_buckets.items():
                if min_len <= feat.caption_length < max_len:
                    length_performance[bucket].append(perf.engagement_rate)
                    break

        # Analyze hashtag impact
        hashtag_performance = defaultdict(list)
        for feat, perf in zip(features, performance):
            hashtag_bucket = min(feat.hashtag_count, 10)  # Cap at 10+
            hashtag_performance[hashtag_bucket].append(perf.engagement_rate)

        # Analyze image impact
        image_performance = {"with_image": [], "without_image": []}
        for feat, perf in zip(features, performance):
            if feat.has_image:
                image_performance["with_image"].append(perf.engagement_rate)
            else:
                image_performance["without_image"].append(perf.engagement_rate)

        return {
            "caption_length_analysis": {
                bucket: {
                    "avg_engagement": np.mean(rates) if rates else 0,
                    "post_count": len(rates)
                }
                for bucket, rates in length_performance.items()
            },
            "hashtag_analysis": {
                count: {
                    "avg_engagement": np.mean(rates) if rates else 0,
                    "post_count": len(rates)
                }
                for count, rates in hashtag_performance.items()
            },
            "image_impact": {
                "with_image": {
                    "avg_engagement": np.mean(image_performance["with_image"]) if image_performance["with_image"] else 0,
                    "post_count": len(image_performance["with_image"])
                },
                "without_image": {
                    "avg_engagement": np.mean(image_performance["without_image"]) if image_performance["without_image"] else 0,
                    "post_count": len(image_performance["without_image"])
                }
            }
        }

    def _analyze_engagement_patterns(
        self,
        features: List[ContentFeatures],
        performance: List[PerformanceMetrics]
    ) -> Dict[str, Any]:
        """Analyze what drives engagement."""

        # Sentiment impact analysis
        sentiment_buckets = {
            "negative": (-1.0, -0.3),
            "neutral": (-0.3, 0.3),
            "positive": (0.3, 1.0)
        }

        sentiment_performance = defaultdict(list)

        for feat, perf in zip(features, performance):
            for bucket, (min_sent, max_sent) in sentiment_buckets.items():
                if min_sent <= feat.sentiment_score < max_sent:
                    sentiment_performance[bucket].append(perf.engagement_rate)
                    break

        # Regional relevance impact
        relevance_buckets = {
            "low": (0.0, 0.3),
            "medium": (0.3, 0.7),
            "high": (0.7, 1.0)
        }

        relevance_performance = defaultdict(list)

        for feat, perf in zip(features, performance):
            for bucket, (min_rel, max_rel) in relevance_buckets.items():
                if min_rel <= feat.regional_relevance_score < max_rel:
                    relevance_performance[bucket].append(perf.engagement_rate)
                    break

        return {
            "sentiment_impact": {
                bucket: {
                    "avg_engagement": np.mean(rates) if rates else 0,
                    "post_count": len(rates)
                }
                for bucket, rates in sentiment_performance.items()
            },
            "regional_relevance_impact": {
                bucket: {
                    "avg_engagement": np.mean(rates) if rates else 0,
                    "post_count": len(rates)
                }
                for bucket, rates in relevance_performance.items()
            }
        }

    def _generate_optimization_recommendations(
        self,
        features: List[ContentFeatures],
        performance: List[PerformanceMetrics],
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate actionable optimization recommendations."""

        recommendations = []

        # Time-based recommendations
        time_analysis = analysis.get("time_analysis", {})
        if time_analysis.get("best_hours"):
            best_hours = list(time_analysis["best_hours"].keys())[:3]
            recommendations.append({
                "type": "posting_time",
                "priority": "high",
                "recommendation": f"Post during peak hours: {', '.join(map(str, best_hours))}",
                "expected_improvement": "15-25% increase in engagement",
                "confidence": 0.8
            })

        # Content length recommendations
        content_analysis = analysis.get("content_analysis", {})
        length_analysis = content_analysis.get("caption_length_analysis", {})

        if length_analysis:
            best_length = max(
                length_analysis.items(),
                key=lambda x: x[1]["avg_engagement"]
            )[0]

            recommendations.append({
                "type": "content_length",
                "priority": "medium",
                "recommendation": f"Optimize caption length for '{best_length}' range",
                "expected_improvement": "10-15% increase in engagement",
                "confidence": 0.7
            })

        # Image recommendations
        image_impact = content_analysis.get("image_impact", {})
        if image_impact:
            with_image_eng = image_impact.get("with_image", {}).get("avg_engagement", 0)
            without_image_eng = image_impact.get("without_image", {}).get("avg_engagement", 0)

            if with_image_eng > without_image_eng * 1.2:  # 20% better
                recommendations.append({
                    "type": "visual_content",
                    "priority": "high",
                    "recommendation": "Always include images with posts",
                    "expected_improvement": f"{((with_image_eng - without_image_eng) / without_image_eng * 100):.1f}% increase in engagement",
                    "confidence": 0.9
                })

        # Hashtag recommendations
        hashtag_analysis = content_analysis.get("hashtag_analysis", {})
        if hashtag_analysis:
            optimal_hashtag_count = max(
                hashtag_analysis.items(),
                key=lambda x: x[1]["avg_engagement"]
            )[0]

            recommendations.append({
                "type": "hashtags",
                "priority": "medium",
                "recommendation": f"Use approximately {optimal_hashtag_count} hashtags per post",
                "expected_improvement": "5-10% increase in reach",
                "confidence": 0.6
            })

        # Sentiment recommendations
        engagement_patterns = analysis.get("engagement_insights", {})
        sentiment_impact = engagement_patterns.get("sentiment_impact", {})

        if sentiment_impact:
            best_sentiment = max(
                sentiment_impact.items(),
                key=lambda x: x[1]["avg_engagement"]
            )[0]

            recommendations.append({
                "type": "content_tone",
                "priority": "medium",
                "recommendation": f"Focus on {best_sentiment} tone in captions",
                "expected_improvement": "8-12% increase in engagement",
                "confidence": 0.7
            })

        return recommendations

    async def train_predictive_models(
        self,
        features_data: List[ContentFeatures],
        performance_data: List[PerformanceMetrics]
    ) -> Dict[str, float]:
        """Train ML models to predict content performance."""

        if len(features_data) < 20:
            logger.warning("Insufficient data for model training")
            return {"error": "Need at least 20 data points for training"}

        # Convert features to numerical format
        X = self._features_to_array(features_data)

        # Prepare target variables
        y_engagement = [p.engagement_rate for p in performance_data]
        y_reach = [p.reach_rate for p in performance_data]
        y_clicks = [p.click_through_rate for p in performance_data]

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Split data for training and validation
        split_idx = int(len(X_scaled) * 0.8)
        X_train, X_val = X_scaled[:split_idx], X_scaled[split_idx:]

        y_engagement_train, y_engagement_val = y_engagement[:split_idx], y_engagement[split_idx:]
        y_reach_train, y_reach_val = y_reach[:split_idx], y_reach[split_idx:]
        y_clicks_train, y_clicks_val = y_clicks[:split_idx], y_clicks[split_idx:]

        # Train models
        models_performance = {}

        try:
            # Engagement model
            self.engagement_model.fit(X_train, y_engagement_train)
            engagement_pred = self.engagement_model.predict(X_val)
            engagement_mse = mean_squared_error(y_engagement_val, engagement_pred)
            models_performance["engagement_mse"] = engagement_mse

            # Reach model
            self.reach_model.fit(X_train, y_reach_train)
            reach_pred = self.reach_model.predict(X_val)
            reach_mse = mean_squared_error(y_reach_val, reach_pred)
            models_performance["reach_mse"] = reach_mse

            # Click model
            self.click_model.fit(X_train, y_clicks_train)
            clicks_pred = self.click_model.predict(X_val)
            clicks_mse = mean_squared_error(y_clicks_val, clicks_pred)
            models_performance["clicks_mse"] = clicks_mse

            # Update model performance tracking
            now = datetime.now(timezone.utc)
            self.model_performance["engagement"]["accuracy"] = 1.0 / (1.0 + engagement_mse)
            self.model_performance["engagement"]["last_trained"] = now

            self.model_performance["reach"]["accuracy"] = 1.0 / (1.0 + reach_mse)
            self.model_performance["reach"]["last_trained"] = now

            self.model_performance["click"]["accuracy"] = 1.0 / (1.0 + clicks_mse)
            self.model_performance["click"]["last_trained"] = now

            logger.info(f"Models trained successfully. Performance: {models_performance}")

        except Exception as e:
            logger.error(f"Model training failed: {e}")
            models_performance["error"] = str(e)

        return models_performance

    def _features_to_array(self, features: List[ContentFeatures]) -> np.ndarray:
        """Convert ContentFeatures list to numpy array for ML models."""

        feature_arrays = []

        for feat in features:
            feature_vector = [
                feat.posting_hour / 24.0,  # Normalize to 0-1
                feat.posting_weekday / 6.0,  # Normalize to 0-1
                min(feat.caption_length / 300.0, 1.0),  # Normalize, cap at 300
                min(feat.hashtag_count / 10.0, 1.0),  # Normalize, cap at 10
                float(feat.has_image),  # Binary feature
                (feat.sentiment_score + 1.0) / 2.0,  # Convert -1,1 to 0,1
                feat.readability_score / 100.0,  # Normalize to 0-1
                feat.regional_relevance_score  # Already 0-1
            ]
            feature_arrays.append(feature_vector)

        return np.array(feature_arrays)

    def predict_content_performance(self, features: ContentFeatures) -> Dict[str, float]:
        """Predict performance for given content features."""

        # Convert features to array format
        X = self._features_to_array([features])
        X_scaled = self.scaler.transform(X)

        predictions = {}

        try:
            if hasattr(self.engagement_model, 'coef_'):
                predictions["engagement_rate"] = max(0, self.engagement_model.predict(X_scaled)[0])

            if hasattr(self.reach_model, 'coef_'):
                predictions["reach_rate"] = max(0, self.reach_model.predict(X_scaled)[0])

            if hasattr(self.click_model, 'coef_'):
                predictions["click_through_rate"] = max(0, self.click_model.predict(X_scaled)[0])

            # Calculate overall predicted performance score
            if predictions:
                avg_performance = sum(predictions.values()) / len(predictions)
                predictions["overall_score"] = min(1.0, avg_performance / 10.0)  # Normalize

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            predictions["error"] = str(e)

        return predictions

    def get_content_optimization_suggestions(
        self,
        features: ContentFeatures,
        target_improvement: float = 0.2
    ) -> List[Dict[str, Any]]:
        """Get specific suggestions to optimize content."""

        suggestions = []

        # Get current predicted performance
        current_prediction = self.predict_content_performance(features)
        current_score = current_prediction.get("overall_score", 0.5)

        # Test different variations
        test_features = [
            # Different posting times
            (features._replace(posting_hour=9), "Post at 9 AM"),
            (features._replace(posting_hour=12), "Post at 12 PM"),
            (features._replace(posting_hour=18), "Post at 6 PM"),

            # Different caption lengths
            (features._replace(caption_length=150), "Optimize caption to 150 characters"),
            (features._replace(caption_length=200), "Optimize caption to 200 characters"),

            # With/without image
            (features._replace(has_image=True), "Add image to post"),
            (features._replace(has_image=False), "Remove image from post"),

            # Different hashtag counts
            (features._replace(hashtag_count=3), "Use 3 hashtags"),
            (features._replace(hashtag_count=5), "Use 5 hashtags"),

            # Improve sentiment
            (features._replace(sentiment_score=0.8), "Make content more positive"),
            (features._replace(sentiment_score=-0.2), "Use more neutral tone")
        ]

        for test_feature, description in test_features:
            predicted_performance = self.predict_content_performance(test_feature)
            predicted_score = predicted_performance.get("overall_score", 0.5)

            improvement = (predicted_score - current_score) / current_score if current_score > 0 else 0

            if improvement >= target_improvement:
                suggestions.append({
                    "suggestion": description,
                    "expected_improvement": f"{improvement * 100:.1f}%",
                    "confidence": min(1.0, improvement / target_improvement),
                    "predicted_score": predicted_score
                })

        # Sort by expected improvement
        suggestions.sort(key=lambda x: float(x["expected_improvement"].rstrip('%')), reverse=True)

        return suggestions[:5]  # Return top 5 suggestions

