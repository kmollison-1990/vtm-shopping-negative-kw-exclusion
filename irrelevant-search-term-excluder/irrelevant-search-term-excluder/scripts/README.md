# score_terms.py

Deterministic intent-similarity scorer for the VTM Vending Shopping
Campaign Negative Keyword Cleanup skill (Step 5).

## Why this exists

SKILL.md Step 5 originally called for a genuine per-term LLM judgment
call on every remaining search term. At the scale this skill runs at
(300-400+ terms per run), a fresh LLM judgment pass each time risks
score drift between runs — the same term could plausibly get a
slightly different score next month even with identical calibration
examples. A checked-in, deterministic script guarantees the same term
gets the same score every run.

**There is no manual override or per-term bump mechanism, by design.**
If a real-world case reveals the tier rules produce a wrong outcome
(e.g., a converting term getting flagged), the fix belongs in the
tier logic itself — not a special-cased keyword list. See
CHANGELOG.md for an example of exactly this happening and being fixed
structurally.

## Usage

```bash
python3 scripts/score_terms.py input.json output.json
```

Input: JSON array of objects with at least `searchTerm`, `clicks`,
`cost`, `conversions`. Output: same objects with `score` (int 1-10)
and `reason` (str) added.

## Running tests

```bash
python3 tests/test_score_terms.py
```

All cases must pass before merging any change to the scoring rules.
Every case in the test file maps to either a SKILL.md calibration
anchor or a real bug found in production — do not delete test cases
when they pass; they exist to prevent regressions.

## Tier reference

| Score | Condition |
|---|---|
| 10 | Branded ("vtm") mention, OR vending machine + pokemon/card + purchase modifier |
| 9 | Vending machine + pokemon/card (exact product, no purchase modifier needed) |
| 8 | Generic vending machine + purchase modifier (not pokemon-specific) |
| 7 | Generic vending machine, informational (no pokemon, no purchase modifier) |
| 6 | Vending machine, but wrong dispensed product (candy/toys/stickers/art) |
| 5 | Pokemon/card + purchase modifier, no vending machine — OR generic pokemon/card product-name mention with no vending/retailer/purchase signal |
| 3 | Pokemon/card + specific retailer name (shopping elsewhere) |
| 2 | Pokemon-adjacent informational/browsing, no purchase signal |
| 1 | Pure character/fandom or fully unrelated term |

## Known limitations

- This is a rule-based proxy for genuine semantic judgment. It will
  miss anything the regex patterns don't cover — new Pokemon TCG set
  names, new retailer names, new languages, and novel phrasing all
  require adding a pattern here. Review this script periodically
  (e.g., each quarter, or whenever a run's flagged list looks off) and
  extend the regex/test coverage rather than letting scoring silently
  drift.
- It does not have full multilingual coverage. Spanish "vending
  machine" (máquina/maquina expendedora) is handled; other languages
  are not yet covered. Add patterns as they show up in real search
  term data.
