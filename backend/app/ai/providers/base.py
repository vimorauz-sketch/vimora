from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class AIResult:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    latency_ms: int


class AIProviderError(Exception):
    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class ProviderAdapter(Protocol):
    key: str

    def complete(self, *, model: str, system: str, user: str, max_tokens: int, temperature: float, timeout: float) -> AIResult: ...
