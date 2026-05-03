"""Fuzzy blocker — uses rapidfuzz token-set ratio over normalized names.

Cheap, no network, no API key. Good baseline; combine with EmbeddingBlocker
for semantic recall (renames, synonyms).
"""

from __future__ import annotations

from collections.abc import Sequence

from rapidfuzz import fuzz, process

from pairo.blockers.base import Blocker
from pairo.normalize import normalize_company_name
from pairo.schemas import Candidate, Record


class FuzzyBlocker(Blocker):
    def __init__(self, scorer: object = fuzz.token_set_ratio) -> None:
        self._scorer = scorer
        self._targets: list[Record] = []
        self._normalized: list[str] = []

    def index(self, targets: Sequence[Record]) -> None:
        self._targets = list(targets)
        self._normalized = [normalize_company_name(t.name) for t in self._targets]

    def candidates(self, source: Record, k: int = 5) -> list[Candidate]:
        if not self._targets:
            return []
        query = normalize_company_name(source.name)
        hits = process.extract(query, self._normalized, scorer=self._scorer, limit=k)
        out: list[Candidate] = []
        for _, score, idx in hits:
            out.append(
                Candidate(
                    record=self._targets[idx],
                    block_score=score / 100.0,
                    block_method="fuzzy.token_set_ratio",
                )
            )
        return out
