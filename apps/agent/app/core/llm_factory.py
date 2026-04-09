"""LLM provider factory for cloud and air-gapped deployments."""

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from app.core.config import AgentSettings


def create_llm(agent_settings: AgentSettings) -> BaseChatModel:
    """Create an LLM instance based on the configured provider.

    Supports:
    - openrouter: Cloud LLM via OpenAI-compatible API (default)
    - ollama: Local LLM for air-gapped environments
    """
    if agent_settings.llm_provider == "openrouter":
        base_url = agent_settings.llm_base_url or "https://openrouter.ai/api/v1"
        return ChatOpenAI(
            base_url=base_url,
            api_key=agent_settings.llm_api_key,
            model=agent_settings.llm_model,
            streaming=True,
        )
    elif agent_settings.llm_provider == "ollama":
        base_url = agent_settings.llm_base_url or "http://localhost:11434"
        return ChatOllama(
            base_url=base_url,
            model=agent_settings.llm_model,
        )
    raise ValueError(f"Unknown LLM provider: {agent_settings.llm_provider}")
