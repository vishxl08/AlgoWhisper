from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    telegram_token: str = ""

    redis_url: str = "redis://localhost:6379/0"

    chroma_persist_dir: str = "./data/chroma"
    chroma_collection: str = "leetcode_mentor"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    sqlite_db_path: str = "./data/progress.db"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_base_url: str = "http://127.0.0.1:8000"

    daily_digest_hour: int = 9
    daily_digest_minute: int = 0

    data_dir: Path = Path("./data")
    raw_data_dir: Path = Path("./data/raw")

    chunk_size: int = 512
    chunk_overlap: int = 64
    retrieval_top_k: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
