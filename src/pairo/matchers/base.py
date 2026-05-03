"""Matcher interface — picks the right candidate (or none) for a source."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from pairo.schemas import Candidate, MatchResult, Record


class Matcher(ABC):
    """Subclass to add a new judging strategy (different LLM, ensemble, etc.)."""

    @abstractmethod
    def judge(self, source: Record, candidates: Sequence[Candidate]) -> MatchResult:
        """Return a verdict for one source given its candidates.

        If no candidate is a true match, return MatchResult with
        target_id=None and decision="no_match".
        """
