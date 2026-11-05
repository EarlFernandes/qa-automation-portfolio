"""Tests for the small .env loader."""

from __future__ import annotations

from pathlib import Path

from llm_evals.dotenv import find_env_file, load_env_file, parse_env_lines


def test_parse_env_lines_handles_comments_quotes_and_export() -> None:
    values = parse_env_lines(
        [
            "# a comment",
            "",
            "ANTHROPIC_API_KEY=abc123",
            'OPENAI_API_KEY="quoted value"',
            "export LLM_MODEL='claude-haiku-4-5'",
            "not a pair",
        ]
    )
    assert values == {
        "ANTHROPIC_API_KEY": "abc123",
        "OPENAI_API_KEY": "quoted value",
        "LLM_MODEL": "claude-haiku-4-5",
    }


def test_load_env_file_sets_missing_variables_only(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("FIRST_KEY=from-file\nSECOND_KEY=from-file\n", encoding="utf-8")
    monkeypatch.delenv("FIRST_KEY", raising=False)
    monkeypatch.setenv("SECOND_KEY", "from-shell")

    loaded = load_env_file(env_file)

    assert loaded == ["FIRST_KEY"]
    import os

    assert os.environ["FIRST_KEY"] == "from-file"
    assert os.environ["SECOND_KEY"] == "from-shell"


def test_find_env_file_walks_up_from_a_subfolder(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("A=1\n", encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert find_env_file(nested) == tmp_path / ".env"


def test_find_env_file_returns_none_when_absent(tmp_path: Path) -> None:
    nested = tmp_path / "only"
    nested.mkdir()
    assert find_env_file(nested) is None
