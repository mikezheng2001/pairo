"""Minimal end-to-end example.

Uses clearly fictional companies (Acme, Globex, Stark, etc.) to demonstrate
the three patterns pairo is designed to handle:

  1. Straightforward match with a name variant (Acme Industries -> Acme Corp).
  2. A rename, where the old and new name both appear in the target index
     (Globex -> formerly Globodyne).
  3. Disambiguation between same-named but unrelated entities
     (Stark Industries the manufacturer vs Stark Records the label).

Requires:
  - `pairo` installed (`pip install -e .` from the repo root)
  - `OPENAI_API_KEY` env var set to a valid key (or pass `api_key=...`)
  - or any OpenAI-compatible endpoint via `base_url=...`

Run:
  python examples/01_basic.py
"""

from pairo import match

# Source: firm records from one dataset (with rich metadata).
SOURCE = [
    {
        "id": "1001",
        "name": "Acme Industries Inc.",
        "country": "USA",
        "industry": "Manufacturing",
        "ticker": "ACM",
    },
    {
        "id": "1002",
        "name": "Globex Corporation",
        "country": "USA",
        "industry": "Conglomerate",
        "ticker": "GLBX",
    },
    {
        "id": "1003",
        "name": "Stark Industries",
        "country": "USA",
        "industry": "Defense & Aerospace",
        "ticker": "STRK",
    },
]

# Target: candidate records from a second dataset (e.g., a brand index).
TARGET = [
    {"id": "p_acme", "name": "Acme Corp", "url": "https://example.com/wiki/Acme_Corp"},
    {"id": "p_globodyne", "name": "Globodyne",
     "url": "https://example.com/wiki/Globodyne",
     "note": "Renamed to Globex in 2010"},
    {"id": "p_globex", "name": "Globex",
     "url": "https://example.com/wiki/Globex"},
    {"id": "p_stark", "name": "Stark Industries",
     "url": "https://example.com/wiki/Stark_Industries",
     "note": "Defense and aerospace manufacturer"},
    {"id": "p_stark_records", "name": "Stark Records",
     "url": "https://example.com/wiki/Stark_Records",
     "note": "Independent record label (unrelated to Stark Industries)"},
    {"id": "p_wayne", "name": "Wayne Enterprises",
     "url": "https://example.com/wiki/Wayne_Enterprises"},
]

if __name__ == "__main__":
    results = match(SOURCE, TARGET, model="gpt-4o-mini", k=5)
    for r in results:
        print(
            f"{r.source_id:>8} -> {r.target_id!s:<20} "
            f"[{r.decision:8}] conf={r.confidence:.2f}  {r.reasoning}"
        )
