"""HTTP adapters for AI providers. API keys stay server-side and are never logged."""

from __future__ import annotations

import time

import httpx

from app.ai.providers.base import AIProviderError, AIResult


def _post(url: str, headers: dict, body: dict, timeout: float) -> tuple[dict, int]:
    start = time.monotonic()
    try:
        r = httpx.post(url, headers=headers, json=body, timeout=timeout)
    except httpx.TimeoutException:
        raise AIProviderError("AI provider timed out", retryable=True) from None
    except httpx.HTTPError as exc:
        raise AIProviderError(f"AI provider unreachable: {type(exc).__name__}", retryable=True) from None
    latency = int((time.monotonic() - start) * 1000)
    if r.status_code in (429, 500, 502, 503, 504, 529):
        raise AIProviderError(f"AI provider temporarily unavailable (HTTP {r.status_code})", retryable=True)
    if r.status_code >= 400:
        try:
            detail = r.json().get("error", {})
            msg = detail.get("message") if isinstance(detail, dict) else str(detail)
        except ValueError:
            msg = r.text[:200]
        raise AIProviderError(f"AI provider rejected the request (HTTP {r.status_code}): {str(msg)[:300]}")
    try:
        return r.json(), latency
    except ValueError:
        raise AIProviderError("AI provider returned invalid JSON", retryable=True) from None


class AnthropicAdapter:
    key = "anthropic"

    def __init__(self, api_key: str, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = (base_url or "https://api.anthropic.com").rstrip("/")

    def complete(self, *, model: str, system: str, user: str, max_tokens: int, temperature: float, timeout: float) -> AIResult:
        data, latency = _post(
            f"{self.base_url}/v1/messages",
            {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            {"model": model, "max_tokens": max_tokens, "temperature": temperature, "system": system, "messages": [{"role": "user", "content": user}]},
            timeout,
        )
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        usage = data.get("usage", {})
        return AIResult(text=text, input_tokens=int(usage.get("input_tokens", 0)), output_tokens=int(usage.get("output_tokens", 0)), model=data.get("model", model), latency_ms=latency)


class OpenAICompatibleAdapter:
    """OpenAI Chat Completions API and compatible servers (set base_url for compatible ones)."""

    def __init__(self, api_key: str, base_url: str | None = None, key: str = "openai"):
        self.api_key = api_key
        self.key = key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    def complete(self, *, model: str, system: str, user: str, max_tokens: int, temperature: float, timeout: float) -> AIResult:
        body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if self.key == "openai":
            body["max_completion_tokens"] = max_tokens
        else:
            body["max_tokens"] = max_tokens
            body["temperature"] = temperature
        data, latency = _post(f"{self.base_url}/chat/completions", {"Authorization": f"Bearer {self.api_key}"}, body, timeout)
        choices = data.get("choices") or [{}]
        text = (choices[0].get("message") or {}).get("content") or ""
        usage = data.get("usage", {})
        return AIResult(text=text, input_tokens=int(usage.get("prompt_tokens", 0)), output_tokens=int(usage.get("completion_tokens", 0)), model=data.get("model", model), latency_ms=latency)


def build_adapter(key: str, api_key: str, base_url: str | None):
    if key == "anthropic":
        return AnthropicAdapter(api_key, base_url)
    if key in ("openai", "openai_compatible"):
        return OpenAICompatibleAdapter(api_key, base_url, key=key)
    raise AIProviderError(f"Unsupported AI provider: {key}")
