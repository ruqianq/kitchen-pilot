from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = (
        "postgresql+asyncpg://kitchen:kitchen@localhost:5432/kitchen_pilot"
    )

    # LLM
    litellm_base_url: str = "http://localhost:4000"
    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: str = ""
    default_model: str = "gpt-4o-mini"
    fallback_models: list[str] = [
        "ollama_chat/qwen3:8b",
        "ollama_chat/gemma3:latest",
    ]

    # Security
    fernet_key: str = ""

    # Google OAuth
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_url: str = "http://localhost:8000/auth/google/callback"

    # Nutrition
    usda_api_key: str = ""

    # Search (optional)
    brave_api_key: str = ""
    tavily_api_key: str = ""

    # Google Calendar MCP sidecar
    gcal_mcp_url: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
