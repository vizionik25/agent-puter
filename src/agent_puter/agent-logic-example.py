from pydantic_ai import Agent
from dotenv import load_dotenv
from pydantic_ai_litellm import LiteLLMModel
import os
import asyncio

load_dotenv()

async def main():
    """This is the main function that will be called by the Puter agent."""

model = LiteLLMModel(
    model_name=os.getenv("PUTER_MODEL"),
    api_key=os.getenv("PUTER_AUTH_TOKEN"),
    api_base=os.getenv("PUTER_API_BASE"),
    custom_llm_provider="openai"
)

agent = Agent(
    model=model,
    instructions='Be helpful!'
)

@agent.tool_plain
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: Sunny, 72°F"

@agent.tool_plain  
def calculator(expression: str) -> str:
    """Evaluate a math expression."""
    return str(eval(expression))

# Native A2A server - Pydantic AI handles it automatically
app = agent.to_a2a()