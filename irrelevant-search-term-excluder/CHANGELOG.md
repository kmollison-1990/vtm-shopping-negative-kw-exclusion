# Changelog — score_terms.py

## 2026-08-05 — Initial version, hardened from first production run

**Context:** First run of the skill with direct-tool-calling (no agent
delegation). 360 search terms needed scoring; a rule-based classifier
was written as a tractable proxy for genuine per-term LLM judgment.
The issues below were found during that run and fixed before this
script was checked into the repo.

### Fixed

- **Spanish-language "vending machine" blind spot.** The `VENDING`
  pattern only recognized the English phrase "vending machine".
  `maquina expendedora de cartas pokemon` (Spanish for "pokemon card
  vending machine" — exactly VTM's product) scored 4 (generic, low
  intent) instead of 9 (exact product match). Added a Spanish pattern
  (`m[aá]quina[s]? expendedora`).

- **Substring collision: "smart vending machine" false-matched
  "art vending".** The wrong-product-vending pattern for `art
  vending` had no word boundary, so it matched inside
  "sm**ART VENDING** machine" and incorrectly scored generic "smart
  vending machine(s)" queries as wrong-product (tier 6) instead of
  generic-vending-informational (tier 7). Added `\b` boundary.

- **Tier-4 boundary sat exactly on the Bucket-A flag threshold.**
  Generic pokemon/card product-name mentions (e.g. "pokemon cards",
  "pokemon boxes", "booster pokemon packs", "pokémon card") scored 4.
  The skill flags Bucket-A (converting) terms at score <= 4 — meaning
  any of these terms that happened to convert would get auto-flagged
  as a negative keyword despite having real conversions. This
  happened in the 2026-08-05 run: 4 such terms had 2-8 conversions
  each and would have been incorrectly negated.

  **Fix applied:** rather than adding a manual override/bump for
  those specific terms (which the project has decided against — see
  scripts/README.md), the tier itself was recalibrated. Generic
  pokemon/card product-name mentions with no vending/retailer/purchase
  signal now score 5, safely above the Bucket-A cutoff, while still
  being flaggable under the more permissive Bucket-B cutoff (<=6) when
  they have zero conversions. This resolves the tension for this
  category of term permanently, not just for the specific strings seen
  in one run.

  **Regression caught during this same fix:** recalibrating the
  generic-product tier initially broke the informational tier
  ("pokemon center", "pokemon store" — should score 2) because the
  informational check was reordered below the generic catch-all and
  never reached. Caught immediately by the test suite before merge.
  This is the exact reason the test suite exists — future tier changes
  must run `tests/test_score_terms.py` before being considered done.

### Known limitations carried forward (see scripts/README.md)

- No override mechanism, by design — fix wrong scores in the tier
  rules, not with a keyword-specific exception.
- Multilingual coverage is partial (Spanish only so far).
- Regex-pattern-based, not true semantic understanding — will miss
  novel product names, slang, and phrasing not yet seen in production
  data. Extend patterns + tests as new gaps are found.
