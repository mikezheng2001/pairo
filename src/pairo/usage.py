"""Token-usage accounting for matcher backends that report it.

Pulled out into its own module so non-LLM matchers (or test doubles) don't
need to know about it. The LLM matcher fills `MatchResult.usage` per call;
`core.run` aggregates across the whole pipeline and emits a final tally to
the `pairo` logger.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TokenUsage(BaseModel):
    """Per-call or aggregated token counts.

    `cached_tokens` is a subset of `prompt_tokens` — providers that support
    automatic prompt caching (OpenAI, Anthropic via compat layers, DeepSeek)
    report which input tokens hit the cache. Non-cached providers leave it
    at zero.
    """

    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    cached_tokens: int = Field(default=0, ge=0)
    calls: int = Field(default=0, ge=0)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def cache_hit_rate(self) -> float:
        if self.prompt_tokens == 0:
            return 0.0
        return self.cached_tokens / self.prompt_tokens

    def __add__(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            cached_tokens=self.cached_tokens + other.cached_tokens,
            calls=self.calls + other.calls,
        )

    def __iadd__(self, other: TokenUsage) -> TokenUsage:
        # Pydantic models are immutable-by-default in practice; rebind via __add__.
        return self.__add__(other)


def from_openai_usage(usage: Any) -> TokenUsage | None:
    """Convert an `openai.types.CompletionUsage`-shaped object to TokenUsage.

    Tolerant of providers that omit fields or return plain dicts. Returns
    None when the response had no `usage` block (some streaming paths, or
    misbehaving compat servers).
    """
    if usage is None:
        return None
    get = (lambda k: usage.get(k, 0)) if isinstance(usage, dict) else (
        lambda k: getattr(usage, k, 0)
    )
    cached = 0
    details = get("prompt_tokens_details")
    if details is not None:
        if isinstance(details, dict):
            cached = details.get("cached_tokens", 0) or 0
        else:
            cached = getattr(details, "cached_tokens", 0) or 0
    return TokenUsage(
        prompt_tokens=int(get("prompt_tokens") or 0),
        completion_tokens=int(get("completion_tokens") or 0),
        cached_tokens=int(cached),
        calls=1,
    )
