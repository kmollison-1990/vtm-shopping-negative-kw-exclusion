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

No personal Google Ads or Slack connection is assumed; delegate to the agents or tools above. Each
agent call is one-shot (no memory) — batch all needed data into a single, complete instruction.

## Config / Constants
- **Lookback window:** trailing 14 days (rolling, relative to run date).
- **Campaign scope:** ALL Shopping campaigns in the VTM Vending Google Ads account (not a
  fixed list — re-discover active Shopping campaigns each run).
- **Click filter:** only search terms with clicks ≥ 1 in the window.
- **Negative keyword level/match type:** Campaign-level negative, **Exact match**.
- **Conversion-bucket threshold:** search terms with ≥ 1 conversion → flag if intent score ≤ 4.
- **Zero-conversion-bucket threshold:** search terms with 0 conversions → flag if intent score ≤ 6.
- **Approval gate:** none — matched negatives are added directly, no human review step.
- **Slack channel:** `#VTM`
- **Slack mentions:** Kyle Mollison, Lizzie Valenti

## Process

### Step 1 — Pull existing negative keywords
Query the Google Ads Agent for every negative keyword currently applied to VTM Vending's
Shopping campaigns — campaign-level negatives AND any shared negative keyword lists applied to
those campaigns. Capture keyword text and match type for each. This is the exclusion baseline
used in Step 3. If the Google Ads Agent does not have the ability to pull negative keywords directly, it should use the get change history tool to pull any change history events with details including "negative keyword added" in the last 29 days to identify which negative keywords were recently added.

### Step 2 — Pull search terms report
Query the Google Ads Agent for the search terms report across **all Shopping campaigns** in
the VTM Vending account for the **trailing 7 days**, filtered to rows with **clicks ≥ 1**.
For each search term, capture:
- Search term text
- Campaign (and ad group) it rolled up under
- Clicks
- Cost
- Avg. CPC
- Conversions

Output this as a table (search term, campaign, clicks, cost, avg CPC, conversions).

### Step 3 — Cross-check against existing negatives
Compare every search term from Step 2 against the negative keyword list from Step 1, applying
standard Google Ads negative-match logic (exact negative blocks only the identical query;
phrase negative blocks any query containing that phrase in order; broad negative blocks any
query containing all the negative's terms). **Remove any search term already covered by an
existing negative** from the working list — it should not be scored or re-added. Note the
removed count for context but do not include these terms in later steps.

### Step 4 — Score intent similarity (1–10)
For every remaining search term, assign an **intent similarity score from 1 (no match) to 10
(near-perfect match)** against VTM's business (vending machines dispensing Pokemon / trading
cards). Score based on purchase/commercial intent alignment with VTM's actual product, not
just keyword overlap with "Pokemon."

Calibration examples (apply this same bar consistently every run):
- **10** — `pokemon vending machine for sale` (near-perfect match: explicit product + purchase intent)
- **1** — `gengar gifts for men`, `mega chandelure` (Pokemon-adjacent fandom/character interest,
  no vending-machine or purchasing intent)

Score every term individually; do not batch-approximate. Output the full scored table.

### Step 5 — Split into two buckets by conversion status
From the scored table:
- **Bucket A:** search terms with conversions ≥ 1
- **Bucket B:** search terms with conversions = 0

### Step 6 — Flag negative keyword candidates
- From **Bucket A**, flag every term with intent score **≤ 4**.
- From **Bucket B**, flag every term with intent score **≤ 6**.
- Combine both flagged lists into one deduplicated candidate list (a term should only appear
  once even if it somehow appears in both campaign/ad group breakdowns — dedupe by exact term
  text).

### Step 7 — Add negative keywords
For each flagged candidate, add it as a **campaign-level negative keyword, Exact match**, on
the specific Shopping campaign(s) where it appeared in Step 2. Use the Google Ads Agent to
execute the additions directly — no review/approval step before pushing live.

### Step 8 — Calculate spend impact
Sum the **Cost** field (from Step 2) across all flagged/added search terms. This total
represents the ad spend "saved" — i.e., the spend that will no longer be wasted on these
queries going forward.

### Step 9 — Notify Slack
Post a message to the **#VTM** Slack channel, mentioning **Kyle Mollison** and **Lizzie
Valenti**, with a short summary containing:
- Number of negative keywords added this run
- Total ad spend saved (the Step 8 sum), formatted as currency
- (Optional context) date range covered and campaign scope (e.g. "trailing 7 days, all Shopping campaigns")

Example message shape:
> :white_check_mark: **VTM Shopping — Negative Keyword Cleanup**
> Added **{N}** new negative keywords to VTM Vending's Shopping campaigns this week (trailing 7-day search terms).
> Estimated ad spend saved: **${total_cost}**
> cc @Kyle Mollison @Lizzie Valenti

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
