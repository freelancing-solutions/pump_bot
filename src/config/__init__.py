from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class TwitterSettings(BaseSettings):
    TWITTER_API_KEY: str = Field(..., alias="TWITTER_API_KEY")
    TWITTER_API_SECRET: str = Field(..., alias="TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN: str = Field(..., alias="TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_TOKEN_SECRET: str = Field(..., alias="TWITTER_ACCESS_TOKEN_SECRET")

class NeightNSettings(BaseSettings):
    N8N_TWITTER_WEBHOOK_URL: str =Field(..., alias="N8N_TWITTER_WEBHOOK_URL")
    N8N_TELEGRAM_WEBHOOK_URL: str = Field(..., alias="N8N_TELEGRAM_WEBHOOK_URL")
    N8N_DISCORD_WEBHOOK_URL: str = Field(..., alias="N8N_DISCORD_WEBHOOK_URL")
    N8N_TWITTER_PRE_LAUNCH_DAY7_WEBHOOK_URL: str = Field(..., alias="N8N_TWITTER_PRE_LAUNCH_DAY7_WEBHOOK_URL")
    N8N_TWITTER_PRE_LAUNCH_DAY1_WEBHOOK_URL: str = Field(..., alias="N8N_TWITTER_PRE_LAUNCH_DAY1_WEBHOOK_URL")
    N8N_TELEGRAM_PRE_LAUNCH_DAY3_WEBHOOK_URL: str = Field(..., alias="N8N_TELEGRAM_PRE_LAUNCH_DAY3_WEBHOOK_URL")






class Config(BaseSettings):
    SOLANA_RPC_URL: str = Field(..., alias="SOLANA_RPC_URL")
    PUMP_API_KEY: str = Field(..., alias="PUMP_API_KEY")
    OPENROUTER_API_KEY: str = Field(..., alias="OPENROUTER_API_KEY")
    DEEPSEEK_API_KEY: str = Field(..., alias="DEEPSEEK_API_KEY")
    DB_PATH: str = Field(..., alis="DB_PATH")
    TELEGRAM_BOT_TOKEN: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    DISCORD_BOT_TOKEN: str = Field(..., alias="DISCORD_BOT_TOKEN")

    TWITTER: TwitterSettings = Field(default_factory=TwitterSettings)
    N_EIGHT_N: NeightNSettings = Field(default_factory=NeightNSettings)

    SECRET_KEY: str = Field(..., alias="SECRET_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def config_instance() -> Config:
    return Config()
