"""High-level orchestration: blocker + matcher.

Most users only need `match()`. Power users construct their own Blocker /
Matcher and call `run()` with explicit instances.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from tqdm import tqdm

from pairo.blockers import Blocker, FuzzyBlocker
from pairo.matchers import LLMMatcher, Matcher
from pairo.schemas import Candidate, MatchResult, Record
from pairo.usage import TokenUsage

logger = logging.getLogger("pairo.core")

ResultCallback = Callable[[MatchResult], None]


def _coerce(rows: Iterable[Record | dict[str, Any]]) -> list[Record]:
    """Accept either Record instances or plain dicts; normalize to list[Record]."""
    out: list[Record] = []
    for r in rows:
        if isinstance(r, Record):
            out.append(r)
            continue
        if "id" not in r or "name" not in r:
            raise ValueError(f"row missing required keys 'id' and 'name': {r!r}")
        context = {k: v for k, v in r.items() if k not in {"id", "name"}}
        out.append(Record(id=str(r["id"]), name=str(r["name"]), context=context))
    return out


def run(
    sources: Sequence[Record],
    targets: Sequence[Record],
    *,
    blocker: Blocker,
    matcher: Matcher,
    k: int = 5,
    min_block_score: float = 0.0,
    progress: bool = True,
    log_every: int = 50,
    on_result: ResultCallback | None = None,
) -> list[MatchResult]:
    """Run the two-stage pipeline.

    For each source, the blocker proposes up to `k` candidates. Sources whose
    best block score is below `min_block_score` skip the LLM entirely and
    receive a `no_match` verdict — this is the main cost-control knob for
    very imbalanced tasks (most rows in one dataset have no real match in the other).

    Progress, per-source decisions, and cumulative token usage are emitted
    via the `pairo.core` / `pairo.matcher` loggers (configure with
    `logging.basicConfig(level=logging.INFO)`). `log_every` controls how
    often a cumulative-token line is logged. `on_result` is called after
    each result is produced — useful for incremental CSV writers so a
    crash doesn't lose hours of work.
    """
    logger.info(
        "starting match run: sources=%d targets=%d k=%d min_block_score=%.2f",
        len(sources), len(targets), k, min_block_score,
    )
    blocker.index(targets)
    logger.debug("blocker indexed %d targets", len(targets))

    results: list[MatchResult] = []
    cumulative = TokenUsage()
    skipped = 0
    iterator: Iterable[Record] = (
        tqdm(sources, desc="matching") if progress else sources
    )
    for i, src in enumerate(iterator, start=1):
        cands: list[Candidate] = blocker.candidates(src, k=k)
        if not cands or cands[0].block_score < min_block_score:
            skipped += 1
            top = cands[0].block_score if cands else 0.0
            logger.debug(
                "skip-llm source=%s name=%r top_block_score=%.2f",
                src.id, src.name, top,
            )
            result = MatchResult(
                source_id=src.id,
                target_id=None,
                confidence=0.0,
                decision="no_match",
                reasoning="no candidate above min_block_score",
                candidates_considered=len(cands),
                usage=TokenUsage(),
            )
        else:
            result = matcher.judge(src, cands)
            if result.usage is not None:
                cumulative = cumulative + result.usage

        results.append(result)
        if on_result is not None:
            on_result(result)

        if log_every > 0 and i % log_every == 0:
            logger.info(
                "progress: %d/%d (skipped=%d) cumulative tokens "
                "in=%d out=%d cached=%d total=%d (cache_hit=%.1f%%)",
                i, len(sources), skipped,
                cumulative.prompt_tokens, cumulative.completion_tokens,
                cumulative.cached_tokens, cumulative.total_tokens,
                cumulative.cache_hit_rate * 100,
            )

    logger.info(
        "run complete: %d results (skipped=%d, llm_calls=%d) tokens "
        "in=%d out=%d cached=%d total=%d (cache_hit=%.1f%%)",
        len(results), skipped, cumulative.calls,
        cumulative.prompt_tokens, cumulative.completion_tokens,
        cumulative.cached_tokens, cumulative.total_tokens,
        cumulative.cache_hit_rate * 100,
    )
    return results


def aggregate_usage(results: Iterable[MatchResult]) -> TokenUsage:
    """Sum token usage across a batch of results. None entries are skipped."""
    total = TokenUsage()
    for r in results:
        if r.usage is not None:
            total = total + r.usage
    return total


def match(
    source: Iterable[Record | dict[str, Any]],
    target: Iterable[Record | dict[str, Any]],
    *,
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
    base_url: str | None = None,
    k: int = 5,
    min_block_score: float = 0.5,
    progress: bool = True,
    log_every: int = 50,
    on_result: ResultCallback | None = None,
) -> list[MatchResult]:
    """Match `source` records to `target` records using the default pipeline.

    Defaults: FuzzyBlocker for candidates, LLMMatcher (OpenAI-compatible) to
    judge. To swap either component, use `run()` with explicit instances.

    Args:
        source: rows to match. Each row needs `id` and `name`; any other keys
            become `context` passed to the matcher.
        target: rows to match against. Same shape as `source`.
        model: model name passed to LLMMatcher.
        api_key, base_url: forwarded to LLMMatcher; default is the OpenAI SDK's
            usual env-var resolution.
        k: candidates per source from the blocker.
        min_block_score: skip LLM judging when blocker confidence is below this
            threshold (saves cost on hopeless source rows).
        progress: show a tqdm bar.
        log_every: log a cumulative-token line every N sources (0 to disable).
        on_result: called with each MatchResult as it is produced — useful for
            incremental CSV writers / checkpointing.
    """
    sources = _coerce(source)
    targets = _coerce(target)
    blocker = FuzzyBlocker()
    matcher = LLMMatcher(model=model, api_key=api_key, base_url=base_url)
    return run(
        sources,
        targets,
        blocker=blocker,
        matcher=matcher,
        k=k,
        min_block_score=min_block_score,
        progress=progress,
        log_every=log_every,
        on_result=on_result,
    )
