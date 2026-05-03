from pairo.blockers import FuzzyBlocker
from pairo.schemas import Record


TARGETS = [
    Record(id="acme", name="Acme Corporation"),
    Record(id="globex", name="Globex Corp"),
    Record(id="apple", name="Apple Inc"),
    Record(id="apple_records", name="Apple Records"),
    Record(id="meta", name="Meta Platforms, Inc."),
]


def test_fuzzy_returns_top_k():
    b = FuzzyBlocker()
    b.index(TARGETS)
    cands = b.candidates(Record(id="q", name="Acme Corp."), k=3)
    assert len(cands) == 3
    assert cands[0].record.id == "acme"
    assert all(0.0 <= c.block_score <= 1.0 for c in cands)


def test_fuzzy_disambiguates_apple_only_by_string_score():
    """Both Apples have similar surface forms — blocker can't tell them apart;
    that's the matcher's job. We just verify both make it into the candidate
    set so the matcher gets to see them."""
    b = FuzzyBlocker()
    b.index(TARGETS)
    cands = b.candidates(Record(id="q", name="Apple Inc"), k=5)
    ids = {c.record.id for c in cands}
    assert "apple" in ids
    assert "apple_records" in ids


def test_fuzzy_with_no_targets_returns_empty():
    b = FuzzyBlocker()
    b.index([])
    assert b.candidates(Record(id="q", name="anything"), k=5) == []
