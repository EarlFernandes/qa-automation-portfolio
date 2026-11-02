"""Extractors turn email text into an `Invoice` dict.

`get_extractor(name)` is the single place that maps a CLI name to a class.
The regex extractor is the offline default. The model adapters need an API key.
"""

from __future__ import annotations

from llm_evals.extractors.base import Extractor


def get_extractor(name: str) -> Extractor:
    if name == "regex":
        from llm_evals.extractors.mock import RegexExtractor

        return RegexExtractor()
    if name == "openai":
        from llm_evals.extractors.openai_adapter import OpenAIExtractor

        return OpenAIExtractor()
    if name == "anthropic":
        from llm_evals.extractors.anthropic_adapter import AnthropicExtractor

        return AnthropicExtractor()
    raise ValueError(f"unknown extractor '{name}'. Choose regex, openai or anthropic.")


__all__ = ["Extractor", "get_extractor"]
