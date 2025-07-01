import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import time
from typing import Optional, Dict, List, Union
import logging

from src.config import Config

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIClient:
    def __init__(self, settings: Config):
        # DeepSeek Client Initialization
        self.settings = settings
        self.deepseek_api_key = self.settings.DEEPSEEK_API_KEY
        self.deepseek_model = self.settings.DEEPSEEK_MODEL
        self.openai_api_key = self.settings.OPENAPI_KEY

        if not self.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY must be set in .env")

        # Creating Deepseek Client
        self.deepseek_client = OpenAI(
            api_key=self.deepseek_api_key,
            base_url="https://api.deepseek.com/v1"
        )

        # OpenAI (DALL-E 3) Client Initialization
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not set. DALL-E 3 image generation disabled.")
            self.openai_client = None
        else:
            self.openai_client = OpenAI(api_key=self.openai_api_key)

        # TODO  - we can add OpenRouter Client here

    def _call_deepseek(self, system_prompt: str, user_prompt: str, temperature: float = 0.7,
                       max_tokens: int = 1000, retries: int = 3) -> str:
        """Generic method to call DeepSeek API with retry logic."""
        for attempt in range(retries):
            try:
                response = self.deepseek_client.chat.completions.create(
                    model=self.deepseek_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"DeepSeek API attempt {attempt + 1} failed: {e}")
                if attempt == retries - 1:
                    return ""
                time.sleep(2 ** attempt)  # Exponential backoff
        return ""

    def _parse_json_response(self, response_text: str, fallback: Dict) -> Dict:
        """Parse JSON response with fallback handling."""
        try:
            if response_text.startswith("```json") and response_text.endswith("```"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```") and response_text.endswith("```"):
                response_text = response_text[3:-3].strip()
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}\nRaw response: {response_text[:200]}...")
            return fallback

    def analyze_social_trends(self, social_media_data: str) -> Dict:
        """Analyzes social media data for meme coin trends."""
        system_prompt = (
            "You are an expert social media trend analyst specializing in cryptocurrency meme coins. "
            "Identify emerging narratives, trending themes, and sentiment from social media data. "
            "Focus on novelty, virality potential, and community engagement. "
            "Output structured JSON with trending themes, keywords, sentiment, and viral narratives."
        )
        user_prompt = f"Analyze for meme coin trends:\n\n{social_media_data}\n\n" \
                      "JSON format: 'trending_themes' (list), 'keywords' (list), " \
                      "'sentiment_summary' (string), 'potential_narratives' (list)."

        response_text = self._call_deepseek(system_prompt, user_prompt, temperature=0.5, max_tokens=1500)
        return self._parse_json_response(response_text, {
            "trending_themes": [],
            "keywords": [],
            "sentiment_summary": "Could not parse sentiment analysis.",
            "potential_narratives": []
        })

    def evaluate_pump_fun_data(self, historical_pump_data: str, trending_themes: List[str]) -> Dict:
        """Evaluates historical Pump.fun data against current trends."""
        system_prompt = (
            "You are a blockchain data analyst specializing in Pump.fun launches. "
            "Analyze historical data with current trends to identify success patterns, "
            "risk factors, and launch recommendations. Score theme viability 0-1."
        )
        user_prompt = f"Historical Data:\n{historical_pump_data}\n\n" \
                      f"Trending Themes: {', '.join(trending_themes)}\n\n" \
                      "JSON format: 'successful_patterns', 'risk_factors', " \
                      "'launch_recommendations' (initial_liquidity_range_sol, optimal_launch_time_utc, target_market_cap_graduation), " \
                      "'theme_viability_scores' (theme: score dict)."

        response_text = self._call_deepseek(system_prompt, user_prompt, temperature=0.6, max_tokens=1500)
        return self._parse_json_response(response_text, {
            "successful_patterns": [],
            "risk_factors": [],
            "launch_recommendations": {},
            "theme_viability_scores": {}
        })

    def generate_coin_idea(self, trending_theme: str, keywords: List[str], sentiment: str) -> Dict:
        """Generates creative meme coin concept."""
        system_prompt = (
            "You are a brilliant meme coin ideation specialist. Create viral-ready concepts with: "
            "creative name (max 3 words), memorable symbol (3-5 caps), engaging description (1-2 sentences), "
            "AI image concept, and social media hooks. Be witty and embrace internet culture."
        )
        user_prompt = f"Theme: {trending_theme}\nKeywords: {', '.join(keywords)}\nSentiment: {sentiment}\n\n" \
                      "JSON format: 'coin_name', 'coin_symbol', 'coin_description', 'image_concept', 'social_media_hooks' (list)."

        response_text = self._call_deepseek(system_prompt, user_prompt, temperature=0.9, max_tokens=500)
        return self._parse_json_response(response_text, {})

    def generate_social_media_posts(self, coin_details: Dict, pump_fun_url: str) -> Dict:
        """Generates platform-specific social media posts."""
        coin_name = coin_details.get("coin_name", "New Meme Coin")
        coin_symbol = coin_details.get("coin_symbol", "$MEME")
        coin_description = coin_details.get("coin_description", "The next big thing.")
        social_hooks = ", ".join(coin_details.get("social_media_hooks", []))

        system_prompt = (
            "You are a viral social media marketing expert for meme coins. "
            "Create platform-specific launch announcements with emojis, hashtags, CTAs. "
            "Pump.fun URL must be prominent."
        )
        user_prompt = f"Name: {coin_name}\nSymbol: {coin_symbol}\nDescription: {coin_description}\n" \
                      f"URL: {pump_fun_url}\nHooks: {social_hooks}\n\n" \
                      "Generate Twitter (280 chars), Telegram, Discord posts. " \
                      "JSON: 'twitter_text', 'telegram_text', 'discord_text'."

        response_text = self._call_deepseek(system_prompt, user_prompt, temperature=0.8, max_tokens=700)
        return self._parse_json_response(response_text, {
            "twitter_text": f"🚀 {coin_name} ({coin_symbol}) launched! {pump_fun_url}",
            "telegram_text": f"🚨 NEW LAUNCH! 🚨\n\n**{coin_name} ({coin_symbol})** LIVE!\n\n{pump_fun_url}",
            "discord_text": f"🎉 @everyone **{coin_name} ({coin_symbol})** dropped! 🥳\n\n{pump_fun_url}"
        })

    def generate_image_prompt(self, image_concept: str) -> str:
        """Generates detailed DALL-E 3 prompt from concept."""
        system_prompt = (
            "Expert DALL-E 3 prompt crafter. Expand meme coin concepts into detailed prompts "
            "with visual elements, artistic style, lighting, coin appearance, background interaction."
        )
        user_prompt = f"Create detailed DALL-E 3 prompt for: '{image_concept}'. " \
                      f"Include coin material/texture, background interaction, lighting, artistic style."

        response_text = self._call_deepseek(system_prompt, user_prompt, temperature=0.8, max_tokens=300)
        return response_text.replace("dall-e 3 image prompt:", "").strip()

    def generate_image_from_prompt(self, prompt: str, size: str = "1024x1024", quality: str = "standard") -> Optional[
        str]:
        """Generates image using DALL-E 3."""
        if not self.openai_client:
            logger.error("DALL-E 3 client not initialized.")
            return None
        if not prompt:
            logger.error("No prompt provided.")
            return None

        logger.info(f"Generating image with prompt: {prompt[:100]}...")
        try:
            response = self.openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                n=1,
                size=size,
                quality=quality,
                response_format="url"
            )
            if response.data:
                image_url = response.data[0].url
                logger.info(f"Image generated: {image_url}")
                return image_url
            return None
        except Exception as e:
            logger.error(f"DALL-E 3 error: {e}")
            return None

    @staticmethod
    def download_image(image_url: str, save_path: str = "generated_image.png") -> bool:
        """Downloads image from URL."""
        if not image_url:
            logger.error("No image URL provided.")
            return False

        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            with open(save_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"Image saved to {save_path}")
            return True
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False

    def analyze_market_sentiment(self, market_data: str) -> Dict:
        """Analyzes broader crypto market sentiment."""
        system_prompt = (
            "Analyze crypto market data for overall sentiment, risk levels, "
            "and optimal timing for meme coin launches. Consider market cycles, "
            "volume patterns, and institutional behavior."
        )
        user_prompt = f"Market data:\n{market_data}\n\n" \
                      "JSON: 'overall_sentiment', 'risk_level' (1-10), 'launch_timing_rec', 'key_indicators'."

        response_text = self._call_deepseek(system_prompt, user_prompt, temperature=0.4, max_tokens=800)
        return self._parse_json_response(response_text, {
            "overall_sentiment": "neutral",
            "risk_level": 5,
            "launch_timing_rec": "monitor further",
            "key_indicators": []
        })

    def generate_tokenomics(self, coin_details: Dict, market_analysis: Dict) -> Dict:
        """Generates tokenomics recommendations."""
        system_prompt = (
            "Design tokenomics for meme coin launch considering market conditions, "
            "theme viability, and Pump.fun mechanics. Include supply, distribution, "
            "pricing strategy, and liquidity recommendations."
        )
        user_prompt = f"Coin: {json.dumps(coin_details)}\nMarket: {json.dumps(market_analysis)}\n\n" \
                      "JSON: 'total_supply', 'initial_price_sol', 'liquidity_allocation_pct', " \
                      "'creator_allocation_pct', 'marketing_allocation_pct', 'pricing_strategy'."

        response_text = self._call_deepseek(system_prompt, user_prompt, temperature=0.6, max_tokens=1000)
        return self._parse_json_response(response_text, {
            "total_supply": 1000000000,
            "initial_price_sol": 0.0001,
            "liquidity_allocation_pct": 90,
            "creator_allocation_pct": 5,
            "marketing_allocation_pct": 5,
            "pricing_strategy": "gradual_increase"
        })

    def create_complete_coin_package(self, social_data: str, pump_data: str = "") -> Dict:
        """Creates complete meme coin package from social data."""
        logger.info("Creating complete coin package...")

        # Step 1: Analyze trends
        trends = self.analyze_social_trends(social_data)
        if not trends.get("trending_themes"):
            logger.warning("No trends identified")
            return {}

        # Step 2: Evaluate themes if pump data available
        evaluation = {}
        if pump_data:
            evaluation = self.evaluate_pump_fun_data(pump_data, trends["trending_themes"])

        # Step 3: Generate coin idea from top theme
        top_theme = trends["trending_themes"][0]
        coin_idea = self.generate_coin_idea(
            top_theme,
            trends["keywords"][:5],
            trends["sentiment_summary"]
        )

        if not coin_idea:
            logger.error("Failed to generate coin idea")
            return {}

        # Step 4: Generate image
        image_url = None
        if coin_idea.get("image_concept"):
            prompt = self.generate_image_prompt(coin_idea["image_concept"])
            if prompt:
                image_url = self.generate_image_from_prompt(prompt, quality="hd")

        # Step 5: Create social posts
        mock_url = "https://pump.fun/coin/placeholder"
        social_posts = self.generate_social_media_posts(coin_idea, mock_url)

        return {
            "trends_analysis": trends,
            "pump_evaluation": evaluation,
            "coin_concept": coin_idea,
            "image_url": image_url,
            "social_media_posts": social_posts,
            "success_probability": evaluation.get("theme_viability_scores", {}).get(top_theme, 0.5)
        }

    def validate_coin_concept(self, coin_details: Dict) -> Dict:
        """Validates coin concept for potential issues."""
        system_prompt = (
            "Review meme coin concept for potential trademark, copyright, "
            "offensive content, or regulatory issues. Suggest improvements."
        )
        user_prompt = f"Validate concept: {json.dumps(coin_details)}\n\n" \
                      "JSON: 'validation_score' (0-1), 'issues_found', 'suggestions', 'risk_level'."

        response_text = self._call_deepseek(system_prompt, user_prompt, temperature=0.3, max_tokens=600)
        return self._parse_json_response(response_text, {
            "validation_score": 0.5,
            "issues_found": [],
            "suggestions": [],
            "risk_level": "medium"
        })


# Example usage and testing
if __name__ == "__main__":
    try:
        ai_client = AIClient()

        # Test complete workflow
        test_social_data = """
        Everyone's talking about AI agents now. $GOAT pumped 1000x, 
        people want the next AI narrative. Gaming + AI is trending. 
        #AIAgents #GameFi #NextBigThing bullish sentiment everywhere.
        """

        logger.info("Testing complete coin package creation...")
        package = ai_client.create_complete_coin_package(test_social_data)

        if package:
            print("\n" + "=" * 50)
            print("COMPLETE COIN PACKAGE GENERATED")
            print("=" * 50)
            print(f"Coin: {package.get('coin_concept', {}).get('coin_name', 'N/A')}")
            print(f"Symbol: {package.get('coin_concept', {}).get('coin_symbol', 'N/A')}")
            print(f"Success Probability: {package.get('success_probability', 0):.2%}")
            if package.get('image_url'):
                print(f"Image URL: {package['image_url']}")
            print("=" * 50)
        else:
            logger.error("Failed to create package")

    except Exception as e:
        logger.error(f"Error in main: {e}")