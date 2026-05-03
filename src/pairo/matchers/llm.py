"""LLM-backed matcher using an OpenAI-compatible Chat Completions API.

Why "OpenAI-compatible" is the default:

  Most mainstream LLM providers expose an endpoint that speaks the same
  protocol as OpenAI's `/v1/chat/completions`. By targeting this protocol,
  one matcher class transparently supports many providers — just point at
  a different `base_url` and `api_key`:

      LLMMatcher(model="gpt-4o-mini")                                # OpenAI
      LLMMatcher(model="deepseek-chat",
                 base_url="https://api.deepseek.com/v1")             # DeepSeek
      LLMMatcher(model="moonshot-v1-8k",
                 base_url="https://api.moonshot.cn/v1")              # Moonshot
      LLMMatcher(model="qwen-plus",
                 base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")  # Qwen

For provider-specific features that aren't part of the OpenAI Chat
Completions protocol (native batch-job APIs, provider-specific
prompt-cache markers, etc.), add a sibling matcher next to this file
with its own implementation. The base `Matcher` ABC is the only
contract callers depend on.

Structured output is forced via tool-use (the `submit_match` function),
so callers never need to parse free-form JSON.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Any

from pairo.matchers.base import Matcher
from pairo.schemas import Candidate, MatchResult, Record
from pairo.usage import TokenUsage, from_openai_usage

logger = logging.getLogger("pairo.matcher")

_SYSTEM_PROMPT = """\
You are an expert at deciding whether two records describe the same real-world
entity (typically a company), even when their names differ.

Each task gives you ONE source record and a small list of CANDIDATE target
records. Pick the candidate that refers to the same entity, or report no_match
if none does.

Use any contextual fields (industry, country, ticker, year, URL slug) you are
given to disambiguate. Treat surface-level name similarity as suggestive but
not decisive.

Calibrate your verdicts:
  - "high"   : you are confident (~>=0.85). Auto-accept territory.
  - "medium" : plausible but not certain (~0.5-0.85). For human review.
  - "low"    : weak evidence (~<0.5). Treat as no_match unless asked otherwise.
  - "no_match": no candidate is the same entity.

Examples that should be "high":
  - "Facebook, Inc." == "Meta Platforms" (renamed 2021).
  - "INTL Globex Inc" == "International Globex" (abbreviation).
  - "ACME CORP" == "Acme Corporation" (legal-suffix variant).

Examples that should be "no_match":
  - "Apple Inc" (Cupertino tech, ticker AAPL) vs "Apple Records" (Beatles label).
  - "Ford Motor Company" (auto, USA) vs "Ford Foundation" (philanthropy).

Examples that depend on context — typically "medium":
  - "Alphabet Inc" vs "Google" (parent vs subsidiary; high if the task is
    about brand identity, lower if about legal entity).

Always call the `submit_match` tool to deliver your verdict.
"""

_SUBMIT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "submit_match",
        "description": "Submit the matching verdict for one source record.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "target_id": {
                    "type": ["string", "null"],
                    "description": "The id of the chosen candidate, or null for no_match.",
                },
                "decision": {
                    "type": "string",
                    "enum": ["high", "medium", "low", "no_match"],
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
                "reasoning": {
                    "type": "string",
                    "description": "One or two sentences explaining the verdict.",
                },
            },
            "required": ["target_id", "decision", "confidence", "reasoning"],
        },
    },
}


def _format_record(label: str, r: Record) -> str:
    parts = [f"{label}: {r.name}", f"  id: {r.id}"]
    for k, v in r.context.items():
        if v in (None, ""):
            continue
        parts.append(f"  {k}: {v}")
    return "\n".join(parts)


def _format_user_message(source: Record, candidates: Sequence[Candidate]) -> str:
    blocks: list[str] = [_format_record("SOURCE", source), "", "CANDIDATES:"]
    for i, c in enumerate(candidates, start=1):
        blocks.append(f"\n[{i}] block_score={c.block_score:.2f} ({c.block_method})")
        blocks.append(_format_record(f"  candidate_{i}", c.record))
    blocks.append(
        "\nCall `submit_match` with the chosen candidate's id "
        "(or null for no_match)."
    )
    return "\n".join(blocks)


class LLMMatcher(Matcher):
    """Default matcher. Talks to any OpenAI-compatible Chat Completions API."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        system_prompt: str = _SYSTEM_PROMPT,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system_prompt = system_prompt
        self._client: Any = None  # lazy

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        # Imported lazily so importing pairo doesn't require the openai SDK
        # to be installed (useful for tests that mock the matcher).
        from openai import OpenAI

        kwargs: dict[str, Any] = {}
        if self.api_key is not None:
            kwargs["api_key"] = self.api_key
        if self.base_url is not None:
            kwargs["base_url"] = self.base_url
        self._client = OpenAI(**kwargs)
        return self._client

    def judge(self, source: Record, candidates: Sequence[Candidate]) -> MatchResult:
        if not candidates:
            logger.debug("no candidates for source=%s; returning no_match", source.id)
            return MatchResult(
                source_id=source.id,
                target_id=None,
                confidence=0.0,
                decision="no_match",
                reasoning="no candidates supplied",
                candidates_considered=0,
                usage=TokenUsage(),
            )

        client = self._get_client()
        logger.debug(
            "LLM call: model=%s source=%s name=%r k=%d",
            self.model, source.id, source.name, len(candidates),
        )
        resp = client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": _format_user_message(source, candidates)},
            ],
            tools=[_SUBMIT_TOOL],
            tool_choice={"type": "function", "function": {"name": "submit_match"}},
        )

        usage = from_openai_usage(getattr(resp, "usage", None)) or TokenUsage(calls=1)
        choice = resp.choices[0]
        tool_calls = getattr(choice.message, "tool_calls", None) or []
        if not tool_calls:
            logger.warning(
                "model did not call submit_match for source=%s; raw=%r",
                source.id, choice.message.content,
            )
            return MatchResult(
                source_id=source.id,
                target_id=None,
                confidence=0.0,
                decision="no_match",
                reasoning=f"model did not call submit_match; raw: {choice.message.content!r}",
                candidates_considered=len(candidates),
                usage=usage,
            )

        args = json.loads(tool_calls[0].function.arguments)
        result = MatchResult(
            source_id=source.id,
            target_id=args.get("target_id"),
            confidence=float(args.get("confidence", 0.0)),
            decision=args.get("decision", "no_match"),
            reasoning=args.get("reasoning", ""),
            candidates_considered=len(candidates),
            usage=usage,
        )
        logger.info(
            "match: source=%s name=%r -> target=%s decision=%s conf=%.2f "
            "tokens=%d (in=%d out=%d cached=%d)",
            source.id, source.name, result.target_id, result.decision,
            result.confidence, usage.total_tokens, usage.prompt_tokens,
            usage.completion_tokens, usage.cached_tokens,
        )
        return result
