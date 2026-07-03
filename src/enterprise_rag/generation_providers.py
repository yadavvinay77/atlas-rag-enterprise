from typing import Literal

import httpx
from pydantic import BaseModel

from .config import settings

ProviderId = Literal["extractive", "ollama", "openai", "compatible"]


class GenerationProviderInfo(BaseModel):
    provider: ProviderId
    label: str
    status: str
    default_model: str
    models: list[str] = []
    best_for: str
    setup: str


def _openai_compatible_available(base_url: str) -> bool:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/models", timeout=2)
        return response.status_code < 500
    except Exception:
        return False


def _openai_models() -> list[str]:
    if not settings.openai_api_key:
        return []
    try:
        response = httpx.get(
            f"{settings.openai_base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            timeout=6,
        )
        response.raise_for_status()
        ids = [
            item["id"]
            for item in response.json().get("data", [])
            if isinstance(item, dict) and item.get("id")
        ]
        chat_models = [
            model
            for model in ids
            if model.startswith(("gpt-", "o3", "o4"))
            and "instruct" not in model
        ]
        preferred_order = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"]
        return sorted(
            chat_models,
            key=lambda model: (
                preferred_order.index(model)
                if model in preferred_order
                else len(preferred_order),
                model,
            ),
        )
    except Exception:
        return []


def _ollama_models() -> list[str]:
    try:
        response = httpx.get(
            f"{settings.ollama_url.rstrip('/')}/api/tags",
            timeout=2,
        )
        response.raise_for_status()
        models = [
            item["name"]
            for item in response.json().get("models", [])
            if isinstance(item, dict) and item.get("name")
            and "completion" in item.get("capabilities", [])
        ]
        return sorted(models, key=lambda model: (model.endswith("-cloud"), model))
    except Exception:
        return []


def generation_provider_catalog() -> list[GenerationProviderInfo]:
    ollama_models = _ollama_models()
    compatible_running = _openai_compatible_available(settings.compatible_base_url)
    accessible_openai_models = _openai_models()
    openai_models = accessible_openai_models or list(
        dict.fromkeys([settings.openai_model, "gpt-4o-mini", "gpt-4.1-mini"])
    )
    openai_default = (
        settings.openai_model
        if settings.openai_model in openai_models
        else openai_models[0]
    )
    return [
        GenerationProviderInfo(
            provider="extractive",
            label="Extractive only",
            status="active",
            default_model="top-cited-passage",
            models=["top-cited-passage"],
            best_for="Fastest offline fallback; returns retrieved evidence directly without an LLM.",
            setup="None.",
        ),
        GenerationProviderInfo(
            provider="ollama",
            label="Ollama offline",
            status="active" if ollama_models else "available-not-running",
            default_model=settings.ollama_model,
            models=ollama_models or [settings.ollama_model, "qwen2.5:7b", "mistral:7b"],
            best_for="Private local/offline models such as Llama, Qwen, Mistral, Gemma.",
            setup="Install Ollama, pull a model, and keep Ollama running.",
        ),
        GenerationProviderInfo(
            provider="openai",
            label="OpenAI",
            status="active" if settings.openai_api_key else "available-needs-api-key",
            default_model=openai_default,
            models=openai_models,
            best_for="High-quality cloud answers over your retrieved local evidence.",
            setup="Set RAG_OPENAI_API_KEY in .env. Optional: set RAG_OPENAI_MODEL.",
        ),
        GenerationProviderInfo(
            provider="compatible",
            label="OpenAI-compatible local",
            status="active" if compatible_running else "available-not-running",
            default_model=settings.compatible_model,
            models=[settings.compatible_model],
            best_for="LM Studio, vLLM, llama.cpp server, text-generation-webui, or any /v1/chat/completions endpoint.",
            setup="Set RAG_COMPATIBLE_BASE_URL and RAG_COMPATIBLE_MODEL. API key is optional.",
        ),
    ]


def provider_status(provider: str) -> str:
    for item in generation_provider_catalog():
        if item.provider == provider:
            return item.status
    return "unknown"


def provider_info(provider: str) -> GenerationProviderInfo | None:
    return next(
        (item for item in generation_provider_catalog() if item.provider == provider),
        None,
    )
