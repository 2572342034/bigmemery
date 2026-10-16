from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins_raw: str = Field(
        default="http://localhost:5173",
        alias="CORS_ORIGINS",
    )

    local_llm_provider: str = Field(default="ollama", alias="LOCAL_LLM_PROVIDER")
    default_model: str = Field(
        default="qwen2.5:14b-instruct-q4_k_m",
        alias="DEFAULT_MODEL",
    )
    available_models_raw: str = Field(
        default=(
            "qwen2.5:14b-instruct-q4_k_m,"
            "llama3.1:8b-instruct-q4_k_m,"
            "mistral:7b-instruct-q4_k_m,"
            "qwen2.5:7b-instruct-q4_k_m"
        ),
        alias="AVAILABLE_MODELS",
    )

    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434",
        alias="OLLAMA_BASE_URL",
    )
    ollama_embedding_model: str = Field(
        default="nomic-embed-text",
        alias="OLLAMA_EMBEDDING_MODEL",
    )
    llamacpp_base_url: str = Field(
        default="http://127.0.0.1:8080/v1",
        alias="LLAMACPP_BASE_URL",
    )
    llamacpp_api_key: str = Field(default="local-key", alias="LLAMACPP_API_KEY")

    chat_sqlite_url: str = Field(
        default=f"sqlite:///{(BASE_DIR / 'chat.db').as_posix()}",
        alias="CHAT_SQLITE_URL",
    )

    mysql_host: str = Field(default="127.0.0.1", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_user: str = Field(default="root", alias="MYSQL_USER")
    mysql_password: str = Field(default="root", alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="bigmemery_auth", alias="MYSQL_DATABASE")

    auth_token_secret: str = Field(
        default="change-this-secret-in-production",
        alias="AUTH_TOKEN_SECRET",
    )
    auth_token_expire_minutes: int = Field(default=720, alias="AUTH_TOKEN_EXPIRE_MINUTES")

    chroma_persist_directory: str = Field(
        default=str(BASE_DIR / "chroma_db"),
        alias="CHROMA_PERSIST_DIRECTORY",
    )
    knowledge_storage_directory: str = Field(
        default=str(BASE_DIR / "data" / "knowledge_files"),
        alias="KNOWLEDGE_STORAGE_DIRECTORY",
    )
    chroma_collection_name: str = Field(
        default="bigmemery_knowledge",
        alias="CHROMA_COLLECTION_NAME",
    )
    rag_top_k: int = Field(default=4, alias="RAG_TOP_K")
    rag_vector_k: int = Field(default=8, alias="RAG_VECTOR_K")
    rag_keyword_k: int = Field(default=8, alias="RAG_KEYWORD_K")
    rag_rerank_k: int = Field(default=5, alias="RAG_RERANK_K")
    rag_min_score: float = Field(default=0.18, alias="RAG_MIN_SCORE")

    default_admin_username: str = Field(default="admin", alias="DEFAULT_ADMIN_USERNAME")
    default_admin_password: str = Field(default="Admin@123456", alias="DEFAULT_ADMIN_PASSWORD")
    default_admin_display_name: str = Field(default="System Admin", alias="DEFAULT_ADMIN_DISPLAY_NAME")

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]

    @property
    def available_models(self) -> list[str]:
        return [item.strip() for item in self.available_models_raw.split(",") if item.strip()]

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            "?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

if __name__ == "__main__":
    print(settings.chat_sqlite_url)
