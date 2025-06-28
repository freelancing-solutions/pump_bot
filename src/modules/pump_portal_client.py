import os
import requests
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PumpPortalClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = os.getenv("PUMP_PORTAL_BASE_URL", "https://api.pumpportal.fun")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })

    def create_token(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new token on PumpPortal"""
        try:
            response = self.session.post(f"{self.base_url}/api/create-token", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to create token: {e}")
            raise

    def get_token_info(self, token_address: str) -> Dict[str, Any]:
        """Get information about a specific token"""
        try:
            response = self.session.get(f"{self.base_url}/api/token/{token_address}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get token info: {e}")
            raise

    def get_launch_status(self, launch_id: str) -> Dict[str, Any]:
        """Get the status of a token launch"""
        try:
            response = self.session.get(f"{self.base_url}/api/launch/{launch_id}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get launch status: {e}")
            raise

    def update_token_metadata(self, token_address: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Update token metadata"""
        try:
            response = self.session.put(f"{self.base_url}/api/token/{token_address}/metadata", json=metadata)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to update token metadata: {e}")
            raise

    def get_portfolio(self) -> Dict[str, Any]:
        """Get user's token portfolio"""
        try:
            response = self.session.get(f"{self.base_url}/api/portfolio")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get portfolio: {e}")
            raise

    def close(self):
        """Close the session"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
