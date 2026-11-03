"""Adapter tests with fake clients. No network, no API keys, no SDK packages needed."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from llm_evals.extractors import ExtractorSetupError, get_extractor
from llm_evals.extractors._llm_common import (
    ModelOutputError,
    build_prompts,
    is_retryable_error,
    parse_json_object,
    with_retries,
)
from llm_evals.extractors.anthropic_adapter import AnthropicExtractor
from llm_evals.extractors.openai_adapter import OpenAIExtractor

INVOICE = {
    "vendor": "Northwind Paper Co",
    "invoice_number": "NW-1001",
    "invoice_date": "2026-03-04",
    "currency": "USD",
    "subtotal": 100.0,
    "tax": 8.0,
    "total": 108.0,
    "line_items": [{"description": "A4 paper", "quantity": 10, "unit_price": 10.0, "amount": 100.0}],
}


# ---------- parse_json_object ----------


def test_parse_clean_json():
    assert parse_json_object(json.dumps(INVOICE)) == INVOICE


def test_parse_fenced_json():
    text = "```json\n" + json.dumps(INVOICE, indent=2) + "\n```"
    assert parse_json_object(text) == INVOICE


def test_parse_json_with_prose_around_it():
    text = "Here is the invoice you asked for:\n" + json.dumps(INVOICE) + "\nLet me know if you need anything else."
    assert parse_json_object(text) == INVOICE


def test_parse_invalid_text_raises_a_clear_error():
    with pytest.raises(ModelOutputError) as info:
        parse_json_object("Sorry, I could not find an invoice in that email.")
    assert "no JSON object" in str(info.value)


def test_parse_broken_json_raises_a_clear_error():
    with pytest.raises(ModelOutputError) as info:
        parse_json_object('{"vendor": "Northwind", "total": }')
    assert "not valid JSON" in str(info.value)


def test_parse_empty_text_raises():
    with pytest.raises(ModelOutputError):
        parse_json_object("   ")


# ---------- retries ----------


class RateLimitError(Exception):
    status_code = 429


class AuthenticationError(Exception):
    status_code = 401


class APIStatusError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"status {status_code}")
        self.status_code = status_code


def test_with_retries_retries_a_retryable_error_then_succeeds():
    calls = {"n": 0}
    slept: list[float] = []

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RateLimitError("slow down")
        return "ok"

    assert with_retries(flaky, is_retryable_error, attempts=3, base_delay=1.0, sleep=slept.append) == "ok"
    assert calls["n"] == 3
    assert slept == [1.0, 2.0]


def test_with_retries_gives_up_after_the_last_attempt():
    slept: list[float] = []

    def always_limited():
        raise RateLimitError("slow down")

    with pytest.raises(RateLimitError):
        with_retries(always_limited, is_retryable_error, attempts=3, base_delay=0.5, sleep=slept.append)
    assert slept == [0.5, 1.0]


def test_with_retries_stops_at_once_on_a_non_retryable_error():
    calls = {"n": 0}
    slept: list[float] = []

    def bad_key():
        calls["n"] += 1
        raise AuthenticationError("invalid api key")

    with pytest.raises(AuthenticationError):
        with_retries(bad_key, is_retryable_error, attempts=3, sleep=slept.append)
    assert calls["n"] == 1
    assert slept == []


def test_is_retryable_error_rules():
    assert is_retryable_error(RateLimitError())
    assert is_retryable_error(APIStatusError(429))
    assert is_retryable_error(APIStatusError(529))
    assert not is_retryable_error(APIStatusError(401))
    assert not is_retryable_error(APIStatusError(400))
    assert not is_retryable_error(AuthenticationError())
    assert not is_retryable_error(ValueError("not an api error"))


# ---------- prompts ----------


def test_build_prompts_embeds_the_schema_and_the_email():
    system, user = build_prompts("Invoice NW-1001 from Northwind")
    assert '"line_items"' in system
    assert "YYYY-MM-DD" in system
    assert "Invoice NW-1001 from Northwind" in user


# ---------- fake clients ----------


class FakeAnthropicMessages:
    def __init__(self, reply_text: str) -> None:
        self.reply_text = reply_text
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=self.reply_text)],
            usage=SimpleNamespace(input_tokens=321, output_tokens=87),
        )


class FakeAnthropicClient:
    def __init__(self, reply_text: str) -> None:
        self.messages = FakeAnthropicMessages(reply_text)


class FakeOpenAICompletions:
    def __init__(self, reply_text: str) -> None:
        self.reply_text = reply_text
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.reply_text))],
            usage=SimpleNamespace(prompt_tokens=250, completion_tokens=60),
        )


class FakeOpenAIClient:
    def __init__(self, reply_text: str) -> None:
        self.chat = SimpleNamespace(completions=FakeOpenAICompletions(reply_text))


def test_anthropic_extractor_with_a_fake_client():
    client = FakeAnthropicClient("```json\n" + json.dumps(INVOICE) + "\n```")
    extractor = AnthropicExtractor(model="claude-test-1", client=client)

    result = extractor.extract("Invoice NW-1001 from Northwind, total 108.00 USD")

    assert result == INVOICE
    assert extractor.name == "anthropic:claude-test-1"
    call = client.messages.calls[0]
    assert call["model"] == "claude-test-1"
    assert call["temperature"] == 0
    assert call["max_tokens"] == 2048
    assert '"line_items"' in call["system"]
    assert call["messages"][0]["role"] == "user"
    assert "Invoice NW-1001" in call["messages"][0]["content"]
    assert extractor.last_usage == {"input_tokens": 321, "output_tokens": 87}


def test_openai_extractor_with_a_fake_client():
    client = FakeOpenAIClient(json.dumps(INVOICE))
    extractor = OpenAIExtractor(model="gpt-test-1", client=client)

    result = extractor.extract("Invoice NW-1001 from Northwind, total 108.00 USD")

    assert result == INVOICE
    assert extractor.name == "openai:gpt-test-1"
    call = client.chat.completions.calls[0]
    assert call["model"] == "gpt-test-1"
    assert call["temperature"] == 0
    assert call["response_format"] == {"type": "json_object"}
    assert call["messages"][0]["role"] == "system"
    assert '"line_items"' in call["messages"][0]["content"]
    assert call["messages"][1]["role"] == "user"
    assert extractor.last_usage == {"input_tokens": 250, "output_tokens": 60}


def test_model_falls_back_to_env_then_default(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "model-from-env")
    assert AnthropicExtractor(client=FakeAnthropicClient("{}")).name == "anthropic:model-from-env"
    monkeypatch.delenv("LLM_MODEL", raising=False)
    assert AnthropicExtractor(client=FakeAnthropicClient("{}")).name == "anthropic:claude-haiku-4-5"
    assert OpenAIExtractor(client=FakeOpenAIClient("{}")).name == "openai:gpt-4o-mini"


def test_anthropic_extractor_retries_then_parses(monkeypatch):
    attempts = {"n": 0}

    class FlakyMessages(FakeAnthropicMessages):
        def create(self, **kwargs):
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise RateLimitError("try later")
            return super().create(**kwargs)

    client = FakeAnthropicClient(json.dumps(INVOICE))
    client.messages = FlakyMessages(json.dumps(INVOICE))
    slept: list[float] = []
    extractor = AnthropicExtractor(model="m", client=client, sleep=slept.append)

    assert extractor.extract("text") == INVOICE
    assert attempts["n"] == 2
    assert slept == [1.0]


def test_missing_api_key_is_a_readable_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ExtractorSetupError) as info:
        get_extractor("anthropic")
    assert "ANTHROPIC_API_KEY is not set" in str(info.value)

    with pytest.raises(ExtractorSetupError) as info:
        get_extractor("openai")
    assert "OPENAI_API_KEY is not set" in str(info.value)


def test_cli_fails_fast_without_a_key(monkeypatch, capsys, tmp_path):
    from llm_evals.cli import main

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    code = main(["run", "--dataset", "data/golden.jsonl", "--extractor", "anthropic", "--limit", "1", "--out", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 2
    assert "ANTHROPIC_API_KEY is not set" in captured.err
    assert "Traceback" not in captured.err
