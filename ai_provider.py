"""
Enterprise Semantic Platform — AI Provider

Supports:

1. Azure OpenAI / Microsoft Foundry
2. Capgemini OpenAI-compatible endpoint
3. Generic OpenAI-compatible endpoint

The semantic platform itself does NOT depend on an LLM.
The LLM is an optional intelligence layer for Ask AI and
AI-assisted semantic suggestions.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import requests
import streamlit as st


# =============================================================================
# RESULT
# =============================================================================

@dataclass
class LLMResult:
    text: str
    provider: str
    model: str


# =============================================================================
# SECRETS
# =============================================================================

def _secret(
    name: str,
    default: str = "",
) -> str:

    try:
        value = st.secrets.get(
            name,
            default,
        )
    except Exception:
        value = default

    if value is None:
        return default

    return str(value).strip()


# =============================================================================
# PROVIDER
# =============================================================================

def provider_name() -> str:

    provider = _secret(
        "AI_PROVIDER",
        "",
    ).lower()

    if provider:
        return provider

    # Auto-detect Azure
    if (
        _secret("AZURE_OPENAI_ENDPOINT")
        and (
            _secret("AZURE_OPENAI_API_KEY")
            or _secret("AZURE_OPENAI_DEPLOYMENT")
        )
    ):
        return "azure"

    # Auto-detect Capgemini
    if _secret(
        "CAPGEMINI_LLM_BASE_URL"
    ):
        return "capgemini"

    # Generic provider
    if _secret(
        "LLM_BASE_URL"
    ):
        return "openai_compatible"

    return "none"


# =============================================================================
# AVAILABILITY
# =============================================================================

def is_available() -> bool:

    provider = provider_name()

    # -------------------------------------------------------------------------
    # Azure OpenAI
    # -------------------------------------------------------------------------

    if provider == "azure":

        endpoint = _secret(
            "AZURE_OPENAI_ENDPOINT"
        )

        deployment = _secret(
            "AZURE_OPENAI_DEPLOYMENT"
        )

        api_key = _secret(
            "AZURE_OPENAI_API_KEY"
        )

        # API-key authentication
        if (
            endpoint
            and deployment
            and api_key
        ):
            return True

        # Entra/service-token support can be added separately.
        return False

    # -------------------------------------------------------------------------
    # Capgemini
    # -------------------------------------------------------------------------

    if provider == "capgemini":

        return bool(
            _secret(
                "CAPGEMINI_LLM_BASE_URL"
            )
            and _secret(
                "CAPGEMINI_LLM_API_KEY"
            )
            and _secret(
                "CAPGEMINI_LLM_MODEL"
            )
        )

    # -------------------------------------------------------------------------
    # Generic OpenAI-compatible
    # -------------------------------------------------------------------------

    if provider in {
        "openai_compatible",
        "enterprise",
    }:

        return bool(
            _secret(
                "LLM_BASE_URL"
            )
            and _secret(
                "LLM_API_KEY"
            )
            and _secret(
                "LLM_MODEL"
            )
        )

    return False


# =============================================================================
# ENDPOINT HELPERS
# =============================================================================

def _azure_base_url() -> str:

    endpoint = _secret(
        "AZURE_OPENAI_ENDPOINT"
    ).rstrip("/")

    if not endpoint:
        raise RuntimeError(
            "AZURE_OPENAI_ENDPOINT is missing."
        )

    # Current Azure OpenAI v1 API.
    #
    # Example:
    #
    # https://my-resource.openai.azure.com/openai/v1/
    #
    if endpoint.endswith(
        "/openai/v1"
    ):
        return endpoint + "/"

    if endpoint.endswith(
        "/openai/v1/"
    ):
        return endpoint

    if endpoint.endswith(
        "/openai"
    ):
        return endpoint + "/v1/"

    return (
        endpoint
        + "/openai/v1/"
    )


# =============================================================================
# AZURE OPENAI
# =============================================================================

def _chat_azure(
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 1200,
) -> LLMResult:

    endpoint = _azure_base_url()

    api_key = _secret(
        "AZURE_OPENAI_API_KEY"
    )

    deployment = _secret(
        "AZURE_OPENAI_DEPLOYMENT"
    )

    if not api_key:
        raise RuntimeError(
            "AZURE_OPENAI_API_KEY is missing."
        )

    if not deployment:
        raise RuntimeError(
            "AZURE_OPENAI_DEPLOYMENT is missing."
        )

    response = requests.post(
        endpoint + "chat/completions",
        headers={
            "Content-Type": "application/json",
            "api-key": api_key,
        },
        json={
            "model": deployment,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=int(
            _secret(
                "LLM_TIMEOUT_SECONDS",
                "60",
            )
        ),
    )

    if response.status_code >= 400:

        raise RuntimeError(
            "Azure OpenAI request failed "
            f"HTTP {response.status_code}: "
            f"{response.text[:1000]}"
        )

    data = response.json()

    try:

        text = (
            data[
                "choices"
            ][0][
                "message"
            ][
                "content"
            ]
        )

    except (
        KeyError,
        IndexError,
        TypeError,
    ) as exc:

        raise RuntimeError(
            "Azure OpenAI response did not contain "
            "choices[0].message.content. "
            f"Response: {data}"
        ) from exc

    return LLMResult(
        text=str(text).strip(),
        provider="azure",
        model=deployment,
    )


# =============================================================================
# GENERIC OPENAI-COMPATIBLE
# =============================================================================

def _chat_openai_compatible(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 1200,
    provider: str = "openai_compatible",
) -> LLMResult:

    url = base_url.rstrip("/")

    if not url.endswith(
        "/chat/completions"
    ):

        url += "/chat/completions"

    response = requests.post(
        url,
        headers={
            "Authorization": (
                f"Bearer {api_key}"
            ),
            "Content-Type": (
                "application/json"
            ),
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=int(
            _secret(
                "LLM_TIMEOUT_SECONDS",
                "60",
            )
        ),
    )

    if response.status_code >= 400:

        raise RuntimeError(
            f"{provider} request failed "
            f"HTTP {response.status_code}: "
            f"{response.text[:1000]}"
        )

    data = response.json()

    try:

        text = (
            data[
                "choices"
            ][0][
                "message"
            ][
                "content"
            ]
        )

    except (
        KeyError,
        IndexError,
        TypeError,
    ) as exc:

        raise RuntimeError(
            f"{provider} response did not contain "
            "choices[0].message.content. "
            f"Response: {data}"
        ) from exc

    return LLMResult(
        text=str(text).strip(),
        provider=provider,
        model=model,
    )


# =============================================================================
# PUBLIC CHAT FUNCTION
# =============================================================================

def chat(
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 1200,
) -> LLMResult:

    provider = provider_name()

    # -------------------------------------------------------------------------
    # Azure
    # -------------------------------------------------------------------------

    if provider == "azure":

        return _chat_azure(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # -------------------------------------------------------------------------
    # Capgemini
    # -------------------------------------------------------------------------

    if provider == "capgemini":

        return _chat_openai_compatible(
            base_url=_secret(
                "CAPGEMINI_LLM_BASE_URL"
            ),
            api_key=_secret(
                "CAPGEMINI_LLM_API_KEY"
            ),
            model=_secret(
                "CAPGEMINI_LLM_MODEL"
            ),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            provider="capgemini",
        )

    # -------------------------------------------------------------------------
    # Generic enterprise OpenAI-compatible
    # -------------------------------------------------------------------------

    if provider in {
        "openai_compatible",
        "enterprise",
    }:

        return _chat_openai_compatible(
            base_url=_secret(
                "LLM_BASE_URL"
            ),
            api_key=_secret(
                "LLM_API_KEY"
            ),
            model=_secret(
                "LLM_MODEL"
            ),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            provider=provider,
        )

    raise RuntimeError(
        "No supported enterprise LLM provider is configured."
    )


# =============================================================================
# JSON EXTRACTION
# =============================================================================

def extract_json(text: str):

    cleaned = str(
        text
    ).strip()

    # Remove Markdown JSON fences.
    cleaned = re.sub(
        r"^```(?:json)?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    cleaned = re.sub(
        r"```$",
        "",
        cleaned,
    ).strip()

    return json.loads(
        cleaned
    )
