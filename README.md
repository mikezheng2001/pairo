# pairo

**Pair records, smarter.** LLM-powered entity resolution and record linkage
with prompt caching, batch API, and structured output built in.

```python
from pairo import match

results = match(
    source=[{"id": "1001", "name": "Acme Industries Inc.", "country": "US", "industry": "Manufacturing"}],
    target=[{"id": "p_acme",   "name": "Acme Corp", "url": "https://example.com/acme"},
            {"id": "p_globex", "name": "Globex",   "url": "https://example.com/globex"}],
    model="gpt-4o-mini",  # default; any OpenAI-compatible model works
)
# → [{"source_id": "1001", "target_id": "p_acme", "confidence": 0.95, "reason": "..."}]
```

The default backend talks to any OpenAI-compatible Chat Completions API,
so you can point it at OpenAI, DeepSeek, Moonshot, Qwen, OpenRouter,
Together, vLLM, Ollama, etc. by passing `base_url` and `api_key`.

## Why

Traditional fuzzy matching (`difflib`, `rapidfuzz`, Jaro-Winkler) compares
strings *character-by-character*. It can't handle:

| Case | Fuzzy says | Truth |
|---|---|---|
| `Facebook` ↔ `Meta Platforms` | 0.0 | same company (renamed) |
| `Alphabet Inc` ↔ `Google` | low | same (parent/child) |
| `Apple` (Cupertino) ↔ `Apple Records` (Beatles) | 1.0 | different |
| `INTL Globex` ↔ `International Globex` | medium | same (abbrev expansion) |

`pairo` adds an LLM in the loop, with a blocker stage to keep cost sane.

## Architecture

```text
   source  ┐                                     ┌─►  matched pairs
           ├─►  blocker (cheap)  ─►  candidates ─┤    + confidence
   target  ┘   embedding / fuzzy / search API    └─►  + reasoning
                                       ▼
                                 matcher (LLM)
                              OpenAI / DeepSeek / etc.
```

Two stages, both pluggable:

1. **Blocker** generates a small set of candidates per source record (top-K
   by embedding similarity, fuzzy hash, or external search). Cheap.
2. **Matcher** asks the LLM to pick the right candidate (or none),
   conditioned on contextual fields the user provides (industry, country,
   ticker, ...). Returns structured output via tool use.

## Status

**v0.1.0 — early.** API may still change before 1.0. Not yet on PyPI;
install from source: `pip install -e .` (use
`--config-settings editable_mode=compat` on Windows with non-ASCII paths).

## Citation

If you use `pairo` in academic work, please cite it. The repo ships a
[CITATION.cff](CITATION.cff), GitHub will auto-render a "Cite this
repository" button on the sidebar with both APA and BibTeX entries.

## Author

Built and maintained by **Zhiyu Zheng** ([@mikezheng2001](https://github.com/mikezheng2001)).

Issues, ideas, and PRs welcome on [GitHub](https://github.com/mikezheng2001/pairo).

## License

MIT — see [LICENSE](LICENSE).
