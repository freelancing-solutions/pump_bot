import requests
import json
from src.config import Config  # Assuming you add n8n webhook URLs to Config


class SocialMediaManager:
    def __init__(self, settings: Config):
        self.n8n_webhook_urls = {
            "twitter_post": settings.N_EIGHT_N.N8N_TWITTER_WEBHOOK_URL,
            "telegram_alert": settings.N_EIGHT_N.N8N_TELEGRAM_WEBHOOK_URL,
            "discord_update": settings.N_EIGHT_N.N8N_DISCORD_WEBHOOK_URL,
            # Add more specific webhooks if needed, e.g., for pre-launch marketing
            "twitter_pre_launch_day7": settings.N_EIGHT_N.N8N_TWITTER_PRE_LAUNCH_DAY7_WEBHOOK_URL,
            "twitter_pre_launch_day1": settings.N_EIGHT_N.N8N_TWITTER_PRE_LAUNCH_DAY1_WEBHOOK_URL,
            "telegram_pre_launch_day3": settings.N_EIGHT_N.N8N_TELEGRAM_PRE_LAUNCH_DAY3_WEBHOOK_URL,
        }

    def _send_webhook(self, url_key, payload):
        webhook_url = self.n8n_webhook_urls.get(url_key)
        if not webhook_url:
            print(f"Error: Webhook URL not configured for '{url_key}'")
            return False

        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            print(f"Successfully sent webhook for '{url_key}'. Response: {response.text}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error sending webhook for '{url_key}': {e}")
            return False

    def post_twitter_update(self, text, image_url=None):
        payload = {"text": text, "image_url": image_url}
        return self._send_webhook("twitter_post", payload)

    def send_telegram_alert(self, message):
        payload = {"message": message}
        return self._send_webhook("telegram_alert", payload)

    def post_discord_update(self, message):
        payload = {"message": message}
        return self._send_webhook("discord_update", payload)

    # Example for pre-launch
    def post_pre_launch_tweet(self, day_identifier, text, image_url=None):
        url_key = f"twitter_pre_launch_day{day_identifier}"
        payload = {"text": text, "image_url": image_url, "day": day_identifier}
        return self._send_webhook(url_key, payload)

# In your config.py (or .env):
# N8N_TWITTER_WEBHOOK_URL="https://your_n8n_domain/webhook/twitter-post"
# N8N_TELEGRAM_WEBHOOK_URL="https://your_n8n_domain/webhook/telegram-alert"
# N8N_DISCORD_WEBHOOK_URL="https://your_n8n_domain/webhook/discord-update"
# N8N_TWITTER_PRE_LAUNCH_DAY7_WEBHOOK_URL="https://your_n8n_domain/webhook/twitter-day7-teaser"
# ... and so on for each scheduled post type.