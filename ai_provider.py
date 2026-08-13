"""
Provider-neutral enterprise LLM adapter.

Supported modes:
1. Capgemini / enterprise OpenAI-compatible endpoint
2. Any OpenAI-compatible endpoint using the same secret contract
3. No provider -> deterministic semantic analysis remains available, while
   Ask AI clearly reports that an LLM is not configured.

No Databricks Foundation Model endpoint is required for the core POC.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

import requests
import streamlit as st


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str


def _secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default) or "").strip()
    except Exception:
        return default


def provider_name() -> str:
    configured = _secret("AI_PROVIDER", "").lower()
    if configured:
        return configured
    if _secret("CAPGEMINI_LLM_BASE_URL"):
        return "capgemini"
    if _secret("LLM_BASE_URL"):
        return "openai_compatible"
    return "none"


def is_available() -> bool:
    provider = provider_name()
    if provider == "capgemini":
        return bool(
            _secret("CAPGEMINI_LLM_BASE_URL")
            and _secret("CAPGEMINI_LLM_API_KEY")
            and _secret("CAPGEMINI_LLM_MODEL")
        )
    if provider in {"openai_compatible", "enterprise"}:
        return bool(
            _secret("LLM_BASE_URL")
            and _secret("LLM_API_KEY")
            and _secret("LLM_MODEL")
        )
    return False


def _chat_openai_compatible(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 1200,
) -> LLMResult:
    url = base_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=int(_secret("LLM_TIMEOUT_SECONDS", "60")),
    )
    response.raise_for_status()
    data = response.json()

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"LLM response did not contain choices[0].message.content: {data}"
        ) from exc

    return LLMResult(text=str(text).strip(), provider=provider_name(), model=model)


def chat(messages: list[dict], temperature: float = 0.1, max_tokens: int = 1200) -> LLMResult:
    provider = provider_name()

    if provider == "capgemini":
        return _chat_openai_compatible(
            _secret("CAPGEMINI_LLM_BASE_URL"),
            _secret("CAPGEMINI_LLM_API_KEY"),
            _secret("CAPGEMINI_LLM_MODEL"),
            messages,
            temperature,
            max_tokens,
        )

    if provider in {"openai_compatible", "enterprise"}:
        return _chat_openai_compatible(
            _secret("LLM_BASE_URL"),
            _secret("LLM_API_KEY"),
            _secret("LLM_MODEL"),
            messages,
            temperature,
            max_tokens,
        )

    raise RuntimeError(
        "No enterprise LLM provider is configured. "
        "Configure Capgemini's approved OpenAI-compatible endpoint "
        "or another approved enterprise LLM provider."
    )


def extract_json(text: str):
    cleaned = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.I)
    cleaned = re.sub(r"```$", "", cleaned.strip())
    return json.loads(cleaned)
