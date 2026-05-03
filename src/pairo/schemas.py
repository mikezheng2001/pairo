"""Public data models. These are the contract users program against."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from pairo.usage import TokenUsage


class Record(BaseModel):
    """A row from either side of a matching task.

    `id` is the user's stable identifier (uuid, ticker, URL, ...).
    `name` is the primary string used for blocking and display.
    `context` carries arbitrary side information the matcher will see
    (industry, country, year, etc.) — anything that helps the LLM
    disambiguate.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    context: dict[str, Any] = Field(default_factory=dict)


class Candidate(BaseModel):
    """A target record proposed by the blocker for a given source record."""

    model_config = ConfigDict(extra="forbid")

    record: Record
    block_score: float = Field(ge=0.0, le=1.0)
    block_method: str


class MatchResult(BaseModel):
    """The matcher's verdict for one source record."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    target_id: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    decision: Literal["high", "medium", "low", "no_match"]
    reasoning: str
    candidates_considered: int
    usage: TokenUsage | None = None
