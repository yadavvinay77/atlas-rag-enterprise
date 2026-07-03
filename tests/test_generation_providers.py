from enterprise_rag.generation_providers import generation_provider_catalog


def test_generation_provider_catalog_includes_cloud_and_offline_routes() -> None:
    providers = {provider.provider for provider in generation_provider_catalog()}

    assert {"extractive", "ollama", "openai", "compatible"} <= providers
