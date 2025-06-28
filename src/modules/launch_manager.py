import os
import requests
import json
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from .pump_portal_client import PumpPortalClient
from .solana_client import SolanaClient

load_dotenv()

logger = logging.getLogger(__name__)


class LaunchManager:
    def __init__(self, pump_portal_client: PumpPortalClient, solana_client: SolanaClient):
        self.pump_portal_client = pump_portal_client
        self.solana_client = solana_client
        self.n8n_base_url = os.getenv("N8N_BASE_URL")
        self.n8n_launch_webhook_path = os.getenv("N8N_LAUNCH_WEBHOOK_PATH", "/webhook/launch-new-meme-coin")
        self.n8n_api_key = os.getenv("N8N_API_KEY")

        if not self.n8n_base_url:
            raise ValueError("N8N_BASE_URL must be set in .env")

    def _trigger_n8n_launch_workflow(self, payload: Dict[str, Any]) -> bool:
        """Triggers the n8n workflow for launching a new coin and posting to social media."""
        webhook_url = f"{self.n8n_base_url}{self.n8n_launch_webhook_path}"
        headers = {'Content-Type': 'application/json'}

        if self.n8n_api_key:
            headers['Authorization'] = f"Bearer {self.n8n_api_key}"

        try:
            logger.info(f"Triggering n8n launch workflow at: {webhook_url}")
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            logger.info(f"N8n launch workflow triggered successfully. Status: {response.status_code}")
            return True
        except requests.exceptions.Timeout:
            logger.error(f"N8n webhook request timed out for {webhook_url}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error triggering n8n launch workflow: {e}")
            return False

    def _validate_coin_data(self, coin_data: Dict[str, Any]) -> None:
        """Validates required coin data fields."""
        required_fields = ['name', 'symbol', 'description', 'image_url', 'creator_wallet_address']
        for field in required_fields:
            if not coin_data.get(field):
                raise ValueError(f"Missing required field: {field}")

    def _validate_social_content(self, social_content: Dict[str, Any]) -> None:
        """Validates required social media content fields."""
        required_fields = ['twitter_text', 'telegram_text', 'discord_text']
        for field in required_fields:
            if not social_content.get(field):
                raise ValueError(f"Missing required social content field: {field}")

    def _create_pump_fun_token(self, coin_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates token on Pump.fun via PumpPortal API."""
        payload = {
            "name": coin_data['name'],
            "symbol": coin_data['symbol'],
            "description": coin_data['description'],
            "imageUrl": coin_data['image_url'],
            "wallet": coin_data['creator_wallet_address'],
            "telegram": coin_data.get('telegram_link', ''),
            "twitter": coin_data.get('twitter_link', ''),
            "website": coin_data.get('website_link', ''),
            "discord": coin_data.get('discord_link', '')
        }

        try:
            result = self.pump_portal_client.create_token(payload)
            if not result.get('success'):
                raise ValueError(f"Token creation failed: {result.get('error', 'Unknown error')}")

            return result
        except Exception as e:
            raise ValueError(f"PumpPortal API error: {str(e)}")

    def _prepare_social_content(self, coin_data: Dict[str, Any], social_content: Dict[str, Any],
                                token_address: str, pump_fun_url: str) -> Dict[str, Any]:
        """Prepares social media content with token details."""
        return {
            "coin_name": coin_data['name'],
            "coin_symbol": coin_data['symbol'],
            "coin_description": coin_data['description'],
            "image_url": coin_data['image_url'],
            "token_mint_address": token_address,
            "pump_fun_url": pump_fun_url,
            "twitter_text": social_content['twitter_text'].replace("YOUR_TOKEN_ADDRESS_HERE", pump_fun_url),
            "twitter_image_url": social_content.get('twitter_image_url'),
            "telegram_text": social_content['telegram_text'].replace("YOUR_TOKEN_ADDRESS_HERE", pump_fun_url),
            "discord_text": social_content['discord_text'].replace("YOUR_TOKEN_ADDRESS_HERE", pump_fun_url)
        }

    def launch_new_token(self, coin_data: Dict[str, Any], social_media_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrates the launch of a new token on Pump.fun and its initial social media blast.

        Args:
            coin_data: Token details including name, symbol, description, image_url, creator_wallet_address
            social_media_content: Content for social platforms (twitter_text, telegram_text, discord_text)

        Returns:
            Dictionary containing launch status, mint address, and social blast status
        """
        try:
            # Validate inputs
            self._validate_coin_data(coin_data)
            self._validate_social_content(social_media_content)

            logger.info(f"Launching token: {coin_data['name']} (${coin_data['symbol']})")

            # Create token on Pump.fun
            pump_result = self._create_pump_fun_token(coin_data)
            token_address = pump_result.get('mintAddress') or pump_result.get('tokenAddress')
            pump_fun_url = pump_result.get('url') or f"https://pump.fun/{token_address}"

            logger.info(f"Token created successfully! Address: {token_address}")

            # Prepare and trigger social media workflow
            n8n_payload = self._prepare_social_content(coin_data, social_media_content, token_address, pump_fun_url)
            social_success = self._trigger_n8n_launch_workflow(n8n_payload)

            return {
                "status": "success",
                "message": "Token launched and social media blast initiated",
                "mint_address": token_address,
                "pump_fun_url": pump_fun_url,
                "social_blast_initiated": social_success
            }

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error during token launch: {e}")
            return {"status": "error", "message": f"Launch failed: {str(e)}"}

    def get_launch_status(self, mint_address: str) -> Dict[str, Any]:
        """Gets the current status of a launched token."""
        try:
            # Check token status via PumpPortal
            status = self.pump_portal_client.get_token_status(mint_address)
            return {"status": "success", "data": status}
        except Exception as e:
            return {"status": "error", "message": f"Failed to get token status: {str(e)}"}

    def verify_wallet_balance(self, wallet_address: str, required_sol: float = 0.02) -> bool:
        """Verifies wallet has sufficient SOL for token creation."""
        try:
            balance = self.solana_client.get_sol_balance(wallet_address)
            return balance >= required_sol
        except Exception as e:
            logger.error(f"Error checking wallet balance: {e}")
            return False