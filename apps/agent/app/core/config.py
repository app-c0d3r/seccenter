"""Agent configuration via pydantic-settings."""

from pydantic_settings import BaseSettings


class AgentSettings(BaseSettings):
    """LLM configuration loaded from environment variables."""

    llm_provider: str = "openrouter"
    llm_model: str = "anthropic/claude-sonnet-4-20250514"
    llm_api_key: str = ""
    llm_base_url: str = ""

    model_config = {"env_prefix": "LLM_"}


settings = AgentSettings()
