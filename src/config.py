import os
from dotenv import load_dotenv

load_dotenv()

# --- Provider API Keys ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ZHIPUAI_API_KEY = os.getenv("ZHIPUAI_API_KEY")

# --- Neo4j ---
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# --- Chat Model Choices (display name -> LiteLLM model string) ---
MODEL_CHOICES = {
    "Gemini 2.5 Flash": "gemini/gemini-2.5-flash",
    "GPT-4o Mini": "openai/gpt-4o-mini",
    "GPT-4o": "openai/gpt-4o",
    "Claude 3.5 Haiku": "anthropic/claude-3-5-haiku-latest",
    "Claude 3.5 Sonnet": "anthropic/claude-3-5-sonnet-latest",
    "GLM-4-Flash": "zhipuai/glm-4-flash",
}

DEFAULT_CHAT_MODEL = "gemini/gemini-2.5-flash"

# --- Embedding Model Choices ---
EMBEDDING_CHOICES = {
    "Gemini Embedding": "gemini/gemini-embedding-001",
    "OpenAI text-embedding-3-small": "openai/text-embedding-3-small",
    "OpenAI text-embedding-3-large": "openai/text-embedding-3-large",
}

DEFAULT_EMBEDDING_MODEL = "gemini/gemini-embedding-001"
