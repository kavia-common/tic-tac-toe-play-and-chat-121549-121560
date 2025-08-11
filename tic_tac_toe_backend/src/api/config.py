import os
from typing import Optional


# PUBLIC_INTERFACE
def get_mongodb_url() -> str:
    """Return MongoDB connection URI from environment variable MONGODB_URL.

    Raises:
        RuntimeError: If the mandatory MONGODB_URL is not set.

    Notes:
        Configuration is injected via environment variables. Ensure the orchestrator
        sets this value or provide it in a local .env during development.
    """
    url = os.getenv("MONGODB_URL")
    if not url:
        raise RuntimeError(
            "MONGODB_URL environment variable is required but not set. "
            "Please configure it in your environment or .env file."
        )
    return url


# PUBLIC_INTERFACE
def get_mongodb_db_name() -> str:
    """Return MongoDB database name from MONGODB_DB or default to 'tic_tac_toe'."""
    return os.getenv("MONGODB_DB", "tic_tac_toe")


# PUBLIC_INTERFACE
def get_openai_api_key() -> Optional[str]:
    """Return the OpenAI API key if configured, else None."""
    return os.getenv("OPENAI_API_KEY")


# PUBLIC_INTERFACE
def get_openai_model() -> str:
    """Return the OpenAI model name for chat/trash talk generation."""
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
