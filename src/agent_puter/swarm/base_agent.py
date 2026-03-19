"""
base_agent.py — Shared factory for all swarm agents.

Every agent in the swarm uses `make_model()` to build a LiteLLMModel
that connects to Puter.js via the OpenAI-compatible API.  This keeps
all env-var wiring in one place, exactly like the canonical agent.py.
"""
import os
from pydantic_ai_litellm import LiteLLMModel


def make_model() -> LiteLLMModel:
    """
    Build a LiteLLMModel from environment variables.

    Required env vars (same as agent.py):
        PUTER_MODEL       — e.g. "claude-sonnet-4-5"
        PUTER_AUTH_TOKEN  — Puter session token
        PUTER_API_BASE    — e.g. "https://api.puter.com/drivers/call"

    Returns a configured LiteLLMModel ready to pass to pydantic_ai.Agent.
    """
    model_name = os.getenv("PUTER_MODEL")
    api_key = os.getenv("PUTER_AUTH_TOKEN")
    api_base = os.getenv("PUTER_API_BASE")

    if not all([model_name, api_key, api_base]):
        raise EnvironmentError(
            "Missing required environment variables: "
            "PUTER_MODEL, PUTER_AUTH_TOKEN, PUTER_API_BASE"
        )

    return LiteLLMModel(
        model_name=model_name,
        api_key=api_key,
        api_base=api_base,
        custom_llm_provider="openai",
    )
