"""Blocker interface — generates candidate matches for a source record.

A blocker's job is to be cheap and high-recall: cut the target set down from
N to ~5–10 candidates per source, so the (expensive) matcher only sees a
small set. Recall matters more than precision here, the matcher will sort
out the wrong ones.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from pairo.schemas import Candidate, Record


class Blocker(ABC):
    """Subclass to add a new candidate-generation strategy."""

    @abstractmethod
    def index(self, targets: Sequence[Record]) -> None:
        """Build whatever data structure the blocker needs over the targets.

        Called once per matching run.
        """

    @abstractmethod
    def candidates(self, source: Record, k: int = 5) -> list[Candidate]:
        """Return up to `k` candidates for a single source record."""
