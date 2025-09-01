import asyncio
import json
import httpx
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from PIL import Image
import io
import base64

from app.core.config import settings
from app.models.models import RegionEnum, ContentTypeEnum


class AIContentGenerator:
    def __init__(self):
        self.gemini_client = httpx.AsyncClient(
            base_url="https://generativelanguage.googleapis.com/v1beta",
            headers={
                "Content-Type": "application/json",
            },
            timeout=60.0
        )

        self.openai_client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=120.0
        )

        # Regional context and preferences
        self.regional_context = {
            RegionEnum.US: {
                "currency": "USD",
                "currency_symbol": "$",
                "date_format": "MM/DD/YYYY",
                "language_style": "American English",
                "cultural_refs": ["NFL", "NBA", "Thanksgiving", "4th of July", "Black Friday"],
                "slang_terms": ["awesome", "amazing", "cool", "super", "folks"],
                "hashtag_style": ["#USA", "#America", "#TeamUSA"]
            },
            RegionEnum.UK: {
                "currency": "GBP",
                "currency_symbol": "£",
                "date_format": "DD/MM/YYYY",
                "language_style": "British English",
                "cultural_refs": ["Premier League", "Bank Holiday", "Tea time", "The Queen", "Brexit"],
                "slang_terms": ["brilliant", "lovely", "proper", "cheers", "mate"],
                "hashtag_style": ["#UK", "#Britain", "#TeamGB"]
            }
        }

    async def generate_caption(
        self, 
        region: RegionEnum, 
        topic: str, 
        content_type: ContentTypeEnum = ContentTypeEnum.IMAGE,
        target_audience: Optional[str] = None,
        tone: str = "engaging",
        include_hashtags: bool = True
    ) -> Dict[str, any]:
        """Generate region-specific Facebook post captions."""

        regional_context = self.regional_context[region]

        # Build context-aware prompt
        prompt = self._build_caption_prompt(
            topic=topic,
            region=region,
            regional_context=regional_context,
            content_type=content_type,
            target_audience=target_audience,
            tone=tone,
            include_hashtags=include_hashtags
        )

        try:
            response = await self._call_gemini_api(prompt)

            # Parse and validate response
            caption_data = self._parse_caption_response(response, include_hashtags)

            # Regional post-processing
            caption_data = self._apply_regional_adaptations(caption_data, region)

            return {
                "caption": caption_data["caption"],
                "hashtags": caption_data.get("hashtags", []),
                "sentiment_score": await self._analyze_sentiment(caption_data["caption"]),
                "readability_score": self._calculate_readability(caption_data["caption"]),
                "ai_model_used": "gemini-pro",
                "generation_cost": 0.001  # Cost in USD
            }

        except Exception as e:
            raise Exception(f"Caption generation failed: {str(e)}")

    def _build_caption_prompt(
        self, 
        topic: str, 
        region: RegionEnum, 
        regional_context: Dict,
        content_type: ContentTypeEnum,
        target_audience: Optional[str],
        tone: str,
        include_hashtags: bool
    ) -> str:
        """Build comprehensive prompt for caption generation."""

        audience_text = f"targeting {target_audience}" if target_audience else "for general audience"
        hashtag_instruction = "Include 3-5 relevant hashtags at the end." if include_hashtags else "Do not include hashtags."

        prompt = f"""
        Create an engaging Facebook post caption about {topic} for {region} audience {audience_text}.

        Requirements:
        - Write in {regional_context["language_style"]}
        - Use {tone} tone
        - Content type: {content_type.value}
        - Length: 150-250 characters for high engagement
        - Include a call-to-action
        - Use cultural references from: {", ".join(regional_context["cultural_refs"][:3])}
        - Incorporate language style: {", ".join(regional_context["slang_terms"][:3])}
        - {hashtag_instruction}

        Cultural Context:
        - Currency: {regional_context["currency_symbol"]}
        - Popular terms: {", ".join(regional_context["slang_terms"])}

        Output format (JSON):
        {{
            "caption": "Your engaging caption here",
            "hashtags": ["hashtag1", "hashtag2", "hashtag3"],
            "cta": "call to action used"
        }}

        Make it authentic, relatable, and optimized for {region} social media engagement.
        """

        return prompt.strip()

    async def _call_gemini_api(self, prompt: str) -> Dict:
        """Make API call to Gemini for content generation."""

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.8,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 200,
                "stopSequences": []
            }
        }

        response = await self.gemini_client.post(
            f"/models/gemini-pro:generateContent?key={settings.GEMINI_API_KEY}",
            json=payload
        )

        if response.status_code != 200:
            raise Exception(f"Gemini API error: {response.status_code} - {response.text}")

        return response.json()

    def _parse_caption_response(self, response: Dict, include_hashtags: bool) -> Dict:
        """Parse and validate Gemini response."""

        try:
            content = response["candidates"][0]["content"]["parts"][0]["text"]

            # Try to parse as JSON first
            try:
                parsed_content = json.loads(content)
                return parsed_content
            except json.JSONDecodeError:
                # Fallback: treat as plain text
                return {
                    "caption": content.strip(),
                    "hashtags": [] if not include_hashtags else self._extract_hashtags(content),
                    "cta": ""
                }

        except (KeyError, IndexError) as e:
            raise Exception(f"Invalid response format: {e}")

    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text."""
        import re
        hashtags = re.findall(r'#\w+', text)
        return hashtags[:5]  # Limit to 5 hashtags

    def _apply_regional_adaptations(self, caption_data: Dict, region: RegionEnum) -> Dict:
        """Apply region-specific adaptations to generated content."""

        caption = caption_data["caption"]
        regional_context = self.regional_context[region]

        # Currency symbol conversion
        if region == RegionEnum.UK:
            caption = caption.replace("$", "£")

        # Language adaptations
        if region == RegionEnum.UK:
            # American to British English conversions
            caption = caption.replace("favorite", "favourite")
            caption = caption.replace("color", "colour")
            caption = caption.replace("center", "centre")
            caption = caption.replace("awesome", "brilliant")

        # Add regional hashtags if none exist
        if not caption_data.get("hashtags"):
            caption_data["hashtags"] = regional_context["hashtag_style"][:2]

        caption_data["caption"] = caption
        return caption_data

    async def generate_image(
        self,
        description: str,
        region: RegionEnum,
        style: str = "photorealistic",
        aspect_ratio: str = "1024x1024"
    ) -> Dict[str, any]:
        """Generate images using DALL-E 3 with regional context."""

        regional_context = self.regional_context[region]

        # Enhance prompt with regional context
        enhanced_prompt = self._enhance_image_prompt(description, regional_context, style)

        try:
            response = await self._call_dalle_api(enhanced_prompt, aspect_ratio)

            return {
                "image_url": response["data"][0]["url"],
                "revised_prompt": response["data"][0].get("revised_prompt", enhanced_prompt),
                "ai_model_used": "dall-e-3",
                "generation_cost": 0.040,  # DALL-E 3 cost per image
                "size": aspect_ratio
            }

        except Exception as e:
            raise Exception(f"Image generation failed: {str(e)}")

    def _enhance_image_prompt(self, description: str, regional_context: Dict, style: str) -> str:
        """Enhance image prompt with regional and cultural context."""

        cultural_elements = ", ".join(regional_context["cultural_refs"][:2])

        enhanced_prompt = f"""
        {description}, {style} style, high quality, social media friendly, 
        featuring {regional_context["language_style"]} cultural context, 
        incorporating elements like {cultural_elements}, 
        vibrant colors, professional photography, 
        optimized for Facebook engagement
        """

        return enhanced_prompt.strip()

    async def _call_dalle_api(self, prompt: str, size: str) -> Dict:
        """Make API call to DALL-E for image generation."""

        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "size": size,
            "quality": "standard",
            "n": 1
        }

        response = await self.openai_client.post(
            "/images/generations",
            json=payload
        )

        if response.status_code != 200:
            raise Exception(f"DALL-E API error: {response.status_code} - {response.text}")

        return response.json()

    async def _analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of generated content (-1 to 1)."""
        # Simple sentiment analysis using Gemini
        prompt = f"""
        Analyze the sentiment of this text and return only a number between -1 and 1:
        -1 = very negative
        0 = neutral  
        1 = very positive

        Text: "{text}"

        Return only the numerical score:
        """

        try:
            response = await self._call_gemini_api(prompt)
            content = response["candidates"][0]["content"]["parts"][0]["text"].strip()
            return float(content)
        except:
            return 0.0  # Default neutral sentiment

    def _calculate_readability(self, text: str) -> float:
        """Calculate readability score (0-100, higher = more readable)."""
        # Simplified readability calculation
        words = len(text.split())
        sentences = text.count('.') + text.count('!') + text.count('?')

        if sentences == 0:
            sentences = 1

        # Simple formula based on words per sentence
        avg_words_per_sentence = words / sentences

        # Score from 0-100 (lower words per sentence = higher readability)
        readability = max(0, 100 - (avg_words_per_sentence * 2))

        return min(100, readability)

    async def generate_complete_post(
        self,
        topic: str,
        region: RegionEnum,
        content_type: ContentTypeEnum = ContentTypeEnum.MIXED,
        target_audience: Optional[str] = None
    ) -> Dict[str, any]:
        """Generate complete post with both image and caption."""

        results = {}

        try:
            # Generate caption
            caption_result = await self.generate_caption(
                region=region,
                topic=topic,
                content_type=content_type,
                target_audience=target_audience
            )
            results.update(caption_result)

            # Generate image if required
            if content_type in [ContentTypeEnum.IMAGE, ContentTypeEnum.MIXED]:
                image_result = await self.generate_image(
                    description=topic,
                    region=region
                )
                results.update(image_result)

            # Calculate overall quality score
            results["overall_quality_score"] = self._calculate_quality_score(results)

            return results

        except Exception as e:
            raise Exception(f"Complete post generation failed: {str(e)}")

    def _calculate_quality_score(self, results: Dict) -> float:
        """Calculate overall quality score for generated content."""

        scores = []

        # Sentiment score (convert to 0-1 scale)
        if "sentiment_score" in results:
            sentiment_normalized = (results["sentiment_score"] + 1) / 2
            scores.append(sentiment_normalized * 0.3)  # 30% weight

        # Readability score
        if "readability_score" in results:
            readability_normalized = results["readability_score"] / 100
            scores.append(readability_normalized * 0.4)  # 40% weight

        # Caption length score (optimal 150-250 chars)
        if "caption" in results:
            caption_length = len(results["caption"])
            if 150 <= caption_length <= 250:
                length_score = 1.0
            elif caption_length < 150:
                length_score = caption_length / 150
            else:
                length_score = max(0.5, 250 / caption_length)
            scores.append(length_score * 0.3)  # 30% weight

        return sum(scores) if scores else 0.5

    async def close(self):
        """Close HTTP clients."""
        await self.gemini_client.aclose()
        await self.openai_client.aclose()

