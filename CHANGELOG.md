# Changelog

All notable changes to `pairo` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-05-02

### Added

- `TokenUsage` schema and `from_openai_usage` helper to capture per-call
  prompt/completion/cached-token counts from the OpenAI-compatible response.
- `MatchResult.usage` field carrying per-call token usage.
- `aggregate_usage(results)` helper for batch totals.
- `pairo.core` and `pairo.matcher` loggers: per-call match decisions, periodic
  cumulative-token progress lines, final tally on run completion.
- `run(..., on_result=...)` callback hook so callers can stream results to
  CSV / dashboards without losing progress on Ctrl-C or crash.
- `run(..., log_every=N)` to control how often cumulative-token lines are emitted.
- Tests for usage aggregation and the on_result callback path.
- `CITATION.cff` for academic citation; GitHub auto-renders a "Cite this repository" button.

### Changed

- `match()` now exposes `log_every` and `on_result`, forwarded to `run()`.
- `pairo.__all__` re-exports `run`, `aggregate_usage`, `TokenUsage`.

## [0.0.1] — initial scaffold

### Added

- Package layout, README, LICENSE.
- Public API stubs: `Record`, `Candidate`, `MatchResult` schemas.
- `Blocker` base class + `FuzzyBlocker` (rapidfuzz token_set_ratio).
- `Matcher` base class + `LLMMatcher` (OpenAI-compatible Chat Completions,
  forced structured output via the `submit_match` tool).
- `match()` convenience function with sensible defaults.
