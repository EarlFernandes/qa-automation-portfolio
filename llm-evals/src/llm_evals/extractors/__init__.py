"""Extractors turn email text into an `Invoice` dict.

`get_extractor(name, model)` is the single place that maps a CLI name to a class.
The regex extractor is the offline default. The model adapters need an API key and
raise ExtractorSetupError with a plain message when they cannot start.
"""

from __future__ import annotations

from llm_evals.extractors._llm_common import ExtractorSetupError, ModelOutputError
from llm_evals.extractors.base import Extractor

EXTRACTOR_NAMES = ("regex", "openai", "anthropic")


def get_extractor(name: str, model: str | None = None) -> Extractor:
    if name == "regex":
        from llm_evals.extractors.mock import RegexExtractor

        return RegexExtractor()
    if name == "openai":
        from llm_evals.extractors.openai_adapter import OpenAIExtractor

        return OpenAIExtractor(model=model)
    if name == "anthropic":
        from llm_evals.extractors.anthropic_adapter import AnthropicExtractor

        return AnthropicExtractor(model=model)
    raise ValueError(f"unknown extractor '{name}'. Choose one of: {', '.join(EXTRACTOR_NAMES)}.")


__all__ = ["EXTRACTOR_NAMES", "Extractor", "ExtractorSetupError", "ModelOutputError", "get_extractor"]
