"""Keyless tests for the OpenAI-compatible model profiles."""

from __future__ import annotations

import asyncio

import pytest

from src.agent import llm


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """Keep machine .env values and process-cached clients out of each test."""
    monkeypatch.setattr(llm, "_load_env", lambda: None)
    for var in (
        "LLM_API_KEY",
        "LLM_BASE_URL",
        "LLM_TIMEOUT_SECONDS",
        "LLM_DISABLE_THINKING",
        "LLM_EXTRA_BODY",
        "LLM_EASY_API_KEY",
        "LLM_EASY_BASE_URL",
        "LLM_EASY_MODEL",
        "LLM_EASY_MAX_TOKENS",
        "LLM_EASY_TIMEOUT_SECONDS",
        "LLM_EASY_DISABLE_THINKING",
        "LLM_EASY_EXTRA_BODY",
        "LLM_HARD_API_KEY",
        "LLM_HARD_BASE_URL",
        "LLM_HARD_MODEL",
        "LLM_HARD_MAX_TOKENS",
        "LLM_HARD_TIMEOUT_SECONDS",
        "LLM_HARD_DISABLE_THINKING",
        "LLM_HARD_EXTRA_BODY",
        "RAGAS_JUDGE_API_KEY",
        "RAGAS_JUDGE_BASE_URL",
        "RAGAS_JUDGE_MODEL",
        "RAGAS_JUDGE_MAX_TOKENS",
        "RAGAS_JUDGE_TIMEOUT_SECONDS",
        "RAGAS_JUDGE_DISABLE_THINKING",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_MODEL_FLASH",
        "DEEPSEEK_MODEL_PRO",
        "DEEPSEEK_MAX_TOKENS_FLASH",
        "DEEPSEEK_MAX_TOKENS_PRO",
        "DEEPSEEK_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(var, raising=False)
    llm._SYNC_CLIENTS.clear()
    yield
    llm._SYNC_CLIENTS.clear()


def test_default_models_preserve_deepseek_compatibility() -> None:
    assert llm._model_for("easy") == "deepseek-v4-flash"
    assert llm._model_for("hard") == "deepseek-v4-pro"


def test_key_gating_and_tier_override(monkeypatch) -> None:
    assert llm.has_api_key() is False
    monkeypatch.setenv("LLM_API_KEY", "shared")
    assert llm.has_api_key("easy") is True
    monkeypatch.setenv("LLM_HARD_API_KEY", "hard-only")
    assert llm._resolve_key("hard") == "hard-only"


def test_judge_profile_is_separate_and_pinned(monkeypatch) -> None:
    monkeypatch.setenv("LLM_EASY_API_KEY", "easy-key")
    monkeypatch.setenv("LLM_EASY_BASE_URL", "http://easy/v1")
    monkeypatch.setenv("LLM_EASY_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("LLM_EASY_MODEL", "legal-easy")
    monkeypatch.setenv("RAGAS_JUDGE_MODEL", "ragas-judge-dev")
    monkeypatch.setenv("RAGAS_JUDGE_DISABLE_THINKING", "false")
    profile = llm._judge_profile()
    assert profile.model == "ragas-judge-dev"
    assert profile.base_url == "http://easy/v1"
    assert profile.timeout == 45
    assert profile.disable_thinking is False
    assert "easy-key" not in repr(profile)


class _Recorder:
    def __init__(self) -> None:
        self.kwargs: dict = {}

    def create(self, **kwargs):
        self.kwargs = kwargs
        return "ok"


class _AsyncRecorder:
    def __init__(self) -> None:
        self.kwargs: dict = {}

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return "ok"


class _AsyncCloseRecorder(_AsyncRecorder):
    def __init__(self) -> None:
        super().__init__()
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def test_wrapper_injects_cost_controls() -> None:
    raw = _Recorder()
    client = llm._ClientWrapper(raw, "legal-easy", 256, is_async=False)
    assert client.create(messages=[]) == "ok"
    assert raw.kwargs["model"] == "legal-easy"
    assert raw.kwargs["max_tokens"] == 256
    assert raw.kwargs["max_retries"] == 0
    assert raw.kwargs["extra_body"] == {"thinking": {"type": "disabled"}}


def test_async_wrapper_closes_its_raw_client() -> None:
    raw = _AsyncCloseRecorder()
    client = llm._ClientWrapper(raw, "legal-easy", 256, is_async=True)
    asyncio.run(client.aclose())
    assert raw.closed is True
