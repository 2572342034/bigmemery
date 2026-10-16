from functools import lru_cache
import json
from urllib.error import URLError
from urllib.request import urlopen

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import ChatOpenAI

from app.core.config import settings


class LLMService:
    def __init__(self) -> None:
        self._chat_cache: dict[tuple[str, str], BaseChatModel] = {}
        self._embedding_cache: dict[str, OllamaEmbeddings] = {}

    def get_supported_models(self) -> list[str]:
        configured = settings.available_models
        if settings.local_llm_provider.lower() != "ollama":
            return configured

        installed = self._get_installed_ollama_models()
        if not installed:
            return configured

        preferred = [model for model in configured if model in installed]
        return preferred or installed

    def get_default_model(self) -> str:
        models = self.get_supported_models()
        if settings.default_model in models:
            return settings.default_model
        return models[0]

    def get_chat_model(self, model_name: str | None = None) -> BaseChatModel:
        resolved_model = model_name or self.get_default_model()
        provider = settings.local_llm_provider.lower()
        cache_key = (provider, resolved_model)
        if cache_key not in self._chat_cache:
            self._chat_cache[cache_key] = self._create_model(provider, resolved_model)
        return self._chat_cache[cache_key]

    def get_embeddings(self) -> OllamaEmbeddings:
        cache_key = settings.ollama_embedding_model
        if cache_key not in self._embedding_cache:
            self._embedding_cache[cache_key] = OllamaEmbeddings(
                model=settings.ollama_embedding_model,
                base_url=settings.ollama_base_url,
            )
        return self._embedding_cache[cache_key]

    def _create_model(self, provider: str, model_name: str) -> BaseChatModel:
        if provider == "ollama":
            return ChatOllama(
                model=model_name,
                base_url=settings.ollama_base_url,
                temperature=0.4,
            )
        if provider == "llamacpp":
            return ChatOpenAI(
                model=model_name,
                base_url=settings.llamacpp_base_url,
                api_key=settings.llamacpp_api_key,
                temperature=0.4,
            )
        raise ValueError(f"Unsupported local LLM provider: {provider}")

    def _get_installed_ollama_models(self) -> list[str]:
        try:
            with urlopen(f"{settings.ollama_base_url}/api/tags", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, TimeoutError, ValueError):
            return []

        models = payload.get("models", [])
        return [item["name"] for item in models if item.get("name")]


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService()


llm_service = get_llm_service()
