import os
from typing import Optional

# Load environment variables from a local .env file during development if present.
# This is safe in production because env vars typically come from the environment.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # If python-dotenv is not available for some reason, silently continue.
    # The application will still rely on environment variables if set by the orchestrator.
    pass


# PUBLIC_INTERFACE
def get_mongodb_url() -> str:
    """Return MongoDB connection URI from environment variable MONGODB_URL.

    Raises:
        RuntimeError: If the mandatory MONGODB_URL is not set.

    Notes:
        Configuration is injected via environment variables. Ensure the orchestrator
        sets this value or provide it in a local .env during development.

        Example for local dev when using the provided database container:
            MONGODB_URL=mongodb://appuser:dbuser123@localhost:5000/?authSource=admin
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
    """Return MongoDB database name from MONGODB_DB or default to 'myapp'."""
    # Default aligns with tic_tac_toe_database startup.sh (DB_NAME default is 'myapp')
    return os.getenv("MONGODB_DB", "myapp")


# PUBLIC_INTERFACE
def get_openai_api_key() -> Optional[str]:
    """Return the OpenAI API key if configured, else None."""
    return os.getenv("OPENAI_API_KEY")


# PUBLIC_INTERFACE
def get_openai_model() -> str:
    """Return the OpenAI model name for chat/trash talk generation."""
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
