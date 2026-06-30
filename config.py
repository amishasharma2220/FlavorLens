"""
FlavorLens Configuration
------------------------
Central configuration file. All settings loaded from environment variables.
Never hardcode credentials. Never commit .env to Git.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    name: str = os.getenv("DB_NAME", "flavorlens")
    user: str = os.getenv("DB_USER", "")
    password: str = os.getenv("DB_PASSWORD", "")

    @property
    def url(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


@dataclass
class LLMConfig:
    anthropic_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    openai_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 1024


@dataclass
class COIConfig:
    """
    Default COI weights. These are starting assumptions, not ground truth.
    Users can override these via Streamlit sliders.
    All weights must sum to 1.0.
    """
    demand_weight: float = 0.30
    competition_weight: float = 0.20
    growth_weight: float = 0.20
    rating_stability_weight: float = 0.15
    affordability_weight: float = 0.15

    # Confidence thresholds
    min_restaurants_for_full_confidence: int = 10
    min_reviews_for_full_confidence: int = 50


@dataclass
class AppConfig:
    env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    project_name: str = "FlavorLens"
    tagline: str = "Restaurant Expansion Intelligence Platform"


# Singleton instances — import these throughout the project
db_config = DatabaseConfig()
llm_config = LLMConfig()
coi_config = COIConfig()
app_config = AppConfig()
