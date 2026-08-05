# Proposed SKILL.md changes to reference score_terms.py

This is a proposed diff, not applied automatically. Review and merge
into SKILL.md manually if you want the skill to call this deterministic
scorer instead of asking the agent for a fresh per-term LLM judgment
each run.

## Required Tools section — add:

> - **score_terms.py** — a deterministic scoring script checked into
>   this repo at `scripts/score_terms.py`. Download it and run it in
>   the sandbox against the Step 3/4 working list rather than scoring
>   terms via fresh LLM judgment each run. This guarantees the same
>   search term gets the same intent score on every run. Do not
>   hand-edit its scoring rules mid-run — if a term's score looks
>   wrong, fix the rule in the script and open a PR; do not override a
>   single term's score inline.

## Step 5 — replace with:

> ### Step 5 — Score intent similarity (1–10)
> Download `scripts/score_terms.py` and `tests/test_score_terms.py`
> from this repo (same pattern as downloading SKILL.md itself — do not
> load them into working context, run them from disk in the sandbox).
> Run the test suite first (`python3 tests/test_score_terms.py`) — it
> must pass before scoring live data. If it fails, stop and report the
> failure; do not proceed with a broken scorer.
>
> Feed the Step 4 working list (as JSON: `searchTerm`, `clicks`,
> `cost`, `conversions`, plus campaign fields) into
> `score_terms.py input.json output.json`. The output adds `score`
> (1-10) and `reason` to every row.
>
> There is no manual override step. If a specific term's score looks
> wrong for a reason not covered by the existing tier logic, do not
> hand-adjust that term's score — flag it to the user and treat it as
> a scoring-rule bug to fix in the script (with an accompanying test
> case), not a one-off exception.

## Rationale

The original Step 5 asked for genuine per-term LLM judgment on every
remaining search term. At production scale (300+ terms/run) that
either requires an impractical number of individual reasoning steps,
or an ad hoc rule-based approximation invented fresh each run — which
is exactly what happened on 2026-08-05, and which produced two real
bugs (a language gap and a regex substring collision) that were only
caught by chance spot-checking.

Checking a single, versioned, tested scorer into the repo:

- Guarantees run-to-run consistency for the same search term
- Makes every scoring rule and its rationale reviewable in one place
  (this repo) instead of reconstructed differently each run
- Lets bugs get fixed once, permanently, with a regression test —
  instead of being silently re-discovered and re-patched every run
- Removes any temptation for manual per-term overrides, which the
  project has explicitly decided against, in favor of fixing the tier
  rules themselves when a real case reveals a gap

The tradeoff: a rule-based scorer will never have the semantic breadth
of genuine LLM judgment. It needs active maintenance — see
`scripts/README.md`'s "Known limitations" section — and should be
reviewed periodically as VTM's product line, competitor set, and the
Pokemon TCG product catalog evolve.
