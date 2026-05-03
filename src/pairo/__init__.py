"""pairo — Pair records, smarter."""

from pairo.core import aggregate_usage, match, run
from pairo.schemas import Candidate, MatchResult, Record
from pairo.usage import TokenUsage

__version__ = "0.1.0"
__all__ = [
    "match",
    "run",
    "aggregate_usage",
    "Record",
    "Candidate",
    "MatchResult",
    "TokenUsage",
    "__version__",
]
