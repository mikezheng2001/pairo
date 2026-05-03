"""End-to-end pipeline test using a fake matcher (no LLM call)."""

from collections.abc import Sequence

from pairo.blockers import FuzzyBlocker
from pairo.core import _coerce, aggregate_usage, run
from pairo.matchers import Matcher
from pairo.schemas import Candidate, MatchResult, Record
from pairo.usage import TokenUsage


class _AcceptTopMatcher(Matcher):
    """Test double: always accept the top candidate with high confidence."""

    def __init__(self, fake_tokens: int = 0) -> None:
        self.fake_tokens = fake_tokens

    def judge(self, source: Record, candidates: Sequence[Candidate]) -> MatchResult:
        if not candidates:
            return MatchResult(
                source_id=source.id,
                target_id=None,
                confidence=0.0,
                decision="no_match",
                reasoning="empty",
                candidates_considered=0,
                usage=TokenUsage(),
            )
        top = candidates[0]
        usage = TokenUsage(
            prompt_tokens=self.fake_tokens,
            completion_tokens=self.fake_tokens // 4,
            calls=1,
        ) if self.fake_tokens else None
        return MatchResult(
            source_id=source.id,
            target_id=top.record.id,
            confidence=0.95,
            decision="high",
            reasoning="fake matcher accepts top candidate",
            candidates_considered=len(candidates),
            usage=usage,
        )


def test_coerce_dicts_to_records():
    rows = [{"id": "1", "name": "X", "country": "US"}]
    rec = _coerce(rows)[0]
    assert rec.id == "1"
    assert rec.name == "X"
    assert rec.context == {"country": "US"}


def test_run_pipeline_end_to_end():
    sources = [Record(id="s1", name="Acme Corp.")]
    targets = [
        Record(id="t1", name="Acme Corporation"),
        Record(id="t2", name="Globex Corp"),
    ]
    results = run(
        sources,
        targets,
        blocker=FuzzyBlocker(),
        matcher=_AcceptTopMatcher(),
        k=2,
        progress=False,
    )
    assert len(results) == 1
    assert results[0].target_id == "t1"
    assert results[0].decision == "high"


def test_aggregate_usage_sums_per_call_tokens():
    sources = [Record(id=f"s{i}", name="Acme Corp.") for i in range(3)]
    targets = [Record(id="t1", name="Acme Corporation")]
    results = run(
        sources,
        targets,
        blocker=FuzzyBlocker(),
        matcher=_AcceptTopMatcher(fake_tokens=400),
        k=1,
        progress=False,
    )
    total = aggregate_usage(results)
    assert total.prompt_tokens == 1200
    assert total.completion_tokens == 300
    assert total.calls == 3


def test_on_result_callback_fires_per_source():
    seen: list[str] = []
    sources = [Record(id="s1", name="Acme"), Record(id="s2", name="Apple")]
    targets = [Record(id="t1", name="Acme Corporation"), Record(id="t2", name="Apple Inc")]
    run(
        sources,
        targets,
        blocker=FuzzyBlocker(),
        matcher=_AcceptTopMatcher(),
        k=1,
        progress=False,
        on_result=lambda r: seen.append(r.source_id),
    )
    assert seen == ["s1", "s2"]


def test_min_block_score_skips_llm():
    sources = [Record(id="s1", name="something completely unrelated zzzzz")]
    targets = [Record(id="t1", name="Acme Corporation")]
    results = run(
        sources,
        targets,
        blocker=FuzzyBlocker(),
        matcher=_AcceptTopMatcher(),
        k=1,
        min_block_score=0.99,  # impossibly high
        progress=False,
    )
    assert results[0].decision == "no_match"
    assert results[0].target_id is None
