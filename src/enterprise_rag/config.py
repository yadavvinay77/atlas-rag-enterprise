from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RAG_", extra="ignore")

    data_dir: Path = Path("data/processed")
    ocr_languages: str = "guj+eng"
    ocr_dpi: int = 300
    enable_dense: bool = False
    embedding_model: str = "intfloat/multilingual-e5-base"
    generation_provider: str = "ollama"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: float = 35.0
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    compatible_api_key: str | None = None
    compatible_base_url: str = "http://127.0.0.1:1234/v1"
    compatible_model: str = "local-model"
    langsmith_api_key: str | None = None
    langsmith_project: str = "atlas-rag"
    min_retrieval_score: float = 0.01


settings = Settings()
