"""String normalization for company names.

Drops common legal-form suffixes that add noise to fuzzy comparisons:
"Apple Inc" and "Apple Corporation" should compare equal under this
normalizer. The matcher (LLM) sees the *original* name; this is only for
the blocker's internal scoring.
"""

from __future__ import annotations

import re

# Order matters: longer multi-word forms first so they're stripped before
# their substrings (e.g. "L L C" before "LLC").
_LEGAL_SUFFIXES: frozenset[str] = frozenset(
    {
        "inc",
        "incorporated",
        "corp",
        "corporation",
        "co",
        "company",
        "cos",
        "companies",
        "ltd",
        "limited",
        "plc",
        "llc",
        "lp",
        "llp",
        "lc",
        "gp",
        "pc",
        "pa",
        "pbc",
        "pvt",
        "pte",
        "pty",
        "nv",
        "bv",
        "ag",
        "gmbh",
        "sas",
        "sarl",
        "ab",
        "as",
        "oy",
        "oyj",
        "sdn",
        "bhd",
        "spa",
        "kk",
        "holding",
        "holdings",
        "group",
        "grp",
        "hldg",
        "hldgs",
        "holdco",
        "intl",
        "international",
        "trust",
    }
)

_PUNCT_RE = re.compile(r"[.,()&'\"]+")
_WS_RE = re.compile(r"\s+")


def normalize_company_name(name: str) -> str:
    """Return a lowercased, suffix-stripped form for fuzzy comparison.

    Examples:
        >>> normalize_company_name("Apple Inc.")
        'apple'
        >>> normalize_company_name("Berkshire Hathaway Holdings, Inc.")
        'berkshire hathaway'
        >>> normalize_company_name("INTL Globex Inc")
        'globex'
    """
    s = name.lower()
    s = _PUNCT_RE.sub(" ", s)
    tokens = [t for t in _WS_RE.split(s) if t and t not in _LEGAL_SUFFIXES]
    return " ".join(tokens).strip()
