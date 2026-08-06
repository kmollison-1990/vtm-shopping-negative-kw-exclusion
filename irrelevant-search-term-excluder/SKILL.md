# Skill: VTM Vending — Shopping Campaign Negative Keyword Cleanup

## Purpose
Cleanup of irrelevant search terms triggering VTM Vending's Google Ads
Shopping campaigns. Identifies low-intent search terms based on a semantic match against VTM's
business (vending machines that dispense Pokemon / trading cards), adds them as negative
keywords automatically, and reports the outcome to the team in Slack.

**Client:** VTM Vending
**Business description used for intent scoring:** VTM Vending sells vending machines that
dispense Pokemon cards and other trading cards.

## Required Tools
- **Google Ads Agent** — pull campaigns, search terms report, existing negative keywords.
- **Slack Agent** — post the summary notification to `#VTM`.
- **Add Negative Keywords** - Google Ads tool to add negative keywords
- **score_terms.py** — a deterministic scoring script checked into this repo at `scripts/score_terms.py`. Download it and run it in the sandbox against the Step 3/4 working list rather than scoring terms via fresh LLM judgment each run. This guarantees the same search term gets the same intent score on every run. Do not hand-edit its scoring rules mid-run — if a term's score looks wrong, fix the rule in the script and open a PR; do not override a single term's score inline.

No personal Google Ads or Slack connection is assumed; delegate to the agents or tools above. Each
agent call is one-shot (no memory) — batch all needed data into a single, complete instruction.

## Delegation Guidelines
- Each Google Ads Agent / Slack Agent call must be a single, self-contained, ASCII-only
  instruction under ~900 characters.
- Do NOT restate this skill's Purpose, business description, or Step 4 calibration
  examples inside a Google Ads Agent or Slack Agent delegation — those are only needed
  by the calling agent itself, not by the tool being called.
- Use plain ASCII comparison operators (`>=`, `-`) in delegation text, not typographic
  characters (`≥`, `—`), to minimize payload size and avoid multi-byte overhead.
- Use the exact templates provided in Steps 1, 2, 7, and 9 verbatim; do not expand them,
  add markdown bolding, or restate context the receiving agent doesn't need.
- If a step's template ever needs to grow, keep the total under ~900 characters — this
  margin exists specifically to avoid downstream storage/column-length failures.

## Skill-Loading Guidance (avoid sandbox-state / context bleed)
This file is ~8 KB. If the executing agent fetches this SKILL.md via a code-execution or
scrape step, **do not load the full file into the agent's active conversation context and
then delegate from that same context.** Observed failure mode: even a short (~500 char),
fully ASCII delegation instruction can still trigger a `P2000` / `prisma.task.create()`
"value too long for the column" error on the Google Ads Agent or Slack Agent call if the
full file content was echoed into context immediately beforehand — the platform appears to
snapshot some portion of the calling agent's recent context when creating the child task,
independent of the explicit `data` argument sent to the tool.

Correct pattern:
1. **Download to disk, not into context.** Fetch the raw file to a sandbox path (e.g. via
   `curl -s -o /workspace/SKILL.md <raw-file-url>`). Do not print or return the full file
   contents as a tool result that re-enters the conversation.
2. **Extract only the one step's template needed right now** (e.g. via `sed`/`grep`/a small
   script scoped to the specific blockquote for that step). Return only that small
   extracted snippet as the tool output.
3. **Use only that extracted snippet** as the `data` argument for the next Google Ads Agent
   or Slack Agent delegation — never a restated/summarized version of the whole file, and
   never immediately after a step that dumped the whole file into context.
4. If the only available fetch/read tool always returns full-file content into context with
   no way to scope it, add a bash/code-execution capability to this agent specifically for
   the download-then-extract steps above, rather than relying on a single "load and display"
   action.

## Config / Constants
- **Lookback window:** trailing 14 days (rolling, relative to run date).
- **Campaign scope:** ALL Shopping campaigns in the VTM Vending Google Ads account (not a
  fixed list — re-discover active Shopping campaigns each run).
- **Click filter:** only search terms with clicks >= 1 in the window.
- **Negative keyword level/match type:** Campaign-level negative, **Exact match**.
- **Conversion-bucket threshold:** search terms with >= 1 conversion → flag if intent score <= 4.
- **Zero-conversion-bucket threshold:** search terms with 0 conversions → flag if intent score <= 6.
- **Approval gate:** none — matched negatives are added directly, no human review step.
- **Slack channel:** `#VTM`
- **Slack mentions:** Kyle Mollison, Lizzie Valenti

## Process

### Step 1 — Pull existing negative keywords
Send this exact instruction to the Google Ads Agent:

> Google Ads account: VTM Vending. List every negative keyword applied to all active
> Shopping campaigns (re-discover the list; exclude Search and Performance Max campaigns).
> Include campaign-level negatives and shared negative keyword lists applied to those
> campaigns. Return keyword text, match type, and the campaign(s) or shared list it applies
> to. If not available via standard objects, use change history (last 29 days) for
> negative-keyword-added events instead. Output as a markdown table titled "Existing
> Negative Keywords".

This is the exclusion baseline used in Step 3.

### Step 2 — Pull search terms report
Send this exact instruction to the Google Ads Agent:

> Google Ads account: VTM Vending. Pull the search terms report for all active Shopping
> campaigns (re-discover the list; exclude Search and Performance Max campaigns), trailing
> 14 days, filtered to clicks >= 1. Return search term, campaign, ad group, clicks, cost,
> avg CPC, and conversions for every row (no truncation). Output as a markdown table
> titled "Search Terms Report (Trailing 7 Days, Clicks >= 1)".

### Step 3 — Cross-check against existing negatives
Compare every search term from Step 2 against the negative keyword list from Step 1, applying
standard Google Ads negative-match logic (exact negative blocks only the identical query;
phrase negative blocks any query containing that phrase in order; broad negative blocks any
query containing all the negative's terms). **Remove any search term already covered by an
existing negative** from the working list — it should not be scored or re-added. Note the
removed count for context but do not include these terms in later steps.

> ### Step 4 — Score intent similarity (1–10)
> Download `scripts/score_terms.py` and `tests/test_score_terms.py`
> from this repo (same pattern as downloading SKILL.md itself — do not
> load them into working context, run them from disk in the sandbox).
> Run the test suite first (`python3 tests/test_score_terms.py`) — it
> must pass before scoring live data. If it fails, stop and report the
> failure; do not proceed with a broken scorer.
>
> Feed the Step 3 working list (as JSON: `searchTerm`, `clicks`,
> `cost`, `conversions`, plus campaign fields) into
> `score_terms.py input.json output.json`. The output adds `score`
> (1-10) and `reason` to every row.
>
> There is no manual override step. If a specific term's score looks
> wrong for a reason not covered by the existing tier logic, do not
> hand-adjust that term's score — flag it to the user and treat it as
> a scoring-rule bug to fix in the script (with an accompanying test
> case), not a one-off exception.

### Step 5 — Split into two buckets by conversion status
From the scored table:
- **Bucket A:** search terms with conversions >= 1
- **Bucket B:** search terms with conversions = 0

### Step 6 — Flag negative keyword candidates
- From **Bucket A**, flag every term with intent score **<= 4**.
- From **Bucket B**, flag every term with intent score **<= 6**.
- Combine both flagged lists into one deduplicated candidate list (a term should only appear
  once even if it somehow appears in both campaign/ad group breakdowns — dedupe by exact term
  text).

### Step 7 — Add negative keywords
For each flagged candidate, send a single, self-contained instruction to the Google Ads Agent
in this form (batch all candidates for one campaign into one call where possible):

> Google Ads account: VTM Vending. Add the following as campaign-level negative keywords,
> Exact match, on campaign "{campaign_name}": {comma-separated list of flagged search terms
> for that campaign}. Confirm each was added successfully.

No review/approval step before pushing live.

### Step 8 — Calculate spend impact
Sum the **Cost** field (from Step 2) across all flagged/added search terms. This total
represents the ad spend "saved" — i.e., the spend that will no longer be wasted on these
queries going forward.

### Step 9 — Notify Slack
Send this exact instruction to the Slack Agent:

> Post to the #VTM Slack channel, mentioning Kyle Mollison and Lizzie Valenti: "VTM Shopping
> - Negative Keyword Cleanup. Added {N} new negative keywords to VTM Vending's Shopping
> campaigns this week (trailing 7-day search terms). Estimated ad spend saved: ${total_cost}."

Fill in `{N}` and `{total_cost}` with the actual values from Steps 6 and 8 before sending.

## Edge Cases & Notes
- If a search term's cost/conversions/clicks vary across ad groups within the same campaign,
  treat it as one row per campaign for review purposes, but when adding the negative, one
  campaign-level negative covers the whole campaign — do not add duplicates.
- If zero candidates are flagged in a given run, still post the Slack summary (0 added, $0 saved) so the team knows the check ran.
- Do not touch Search or Performance Max campaigns — this skill is scoped to **Shopping**
  campaigns only.
- Because there is no approval gate, scoring consistency (Step 4) is the main safety control —
  always apply the calibration examples in Step 4 the same way every run to avoid over- or
  under-blocking.
- If any Google Ads Agent or Slack Agent call fails with a "value too long for column" /
  P2000-style error, check the Skill-Loading Guidance section above first — this has been
  observed even with short, compliant delegation instructions when the full SKILL.md was
  loaded into context immediately beforehand. If that's ruled out, the delegation message
  itself was likely expanded beyond the ~900-character guideline — trim it back to the
  literal template for that step rather than adding restated context.
