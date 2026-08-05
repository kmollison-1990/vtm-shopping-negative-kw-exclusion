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
This version assumes the running agent has DIRECT tool access to Google Ads and Slack —
no delegation to a separate Google Ads Agent or Slack Agent. Do not use agent-to-agent
delegation anywhere in this skill; call the tools listed below directly, by these exact names:

- **Get Customer IDs** — resolves the Google Ads customer ID for VTM Vending. Call this first;
  use the resolved customer ID in every other Google Ads tool call below.
- **Get Campaign Performance** — used in Step 1 to discover active Shopping campaigns (this
  toolset has no separate "list campaigns" action, so campaign discovery is done via this
  performance tool, filtered down to the fields needed).
- **Get Search Term Performance** — used in Step 3 to pull the search terms report.
- **Get Change History** — used in Step 2 as the ONLY way to reconstruct existing negative
  keywords (this toolset has no direct "list negative keywords" action — see Step 2 for the
  limitation this implies).
- **Add Negative Keywords** — used in Step 8 to add flagged campaign-level negatives.
- **Slack — Send Message to Channel** (exact name TBD — use whichever Slack tool in your
  toolset posts a message to a channel with user mentions): used in Step 10.

Do not search for or delegate to a separate "Google Ads Agent" or "Slack Agent" anywhere in
this skill — every action above is a direct tool call.

## Config / Constants
- **Lookback window:** trailing 14 days (rolling, relative to run date).
- **Campaign scope:** ALL Shopping campaigns in the VTM Vending Google Ads account (not a
  fixed list — re-discover active Shopping campaigns each run).
- **Click filter:** only search terms with clicks >= 1 in the window.
- **Negative keyword level/match type:** Campaign-level negative, **Exact match**.
- **Conversion-bucket threshold:** search terms with >= 1 conversion -> flag if intent score <= 4.
- **Zero-conversion-bucket threshold:** search terms with 0 conversions -> flag if intent score <= 6.
- **Approval gate:** none — matched negatives are added directly, no human review step.
- **Slack channel:** `#VTM`
- **Slack mentions:** Kyle Mollison, Lizzie Valenti

## Process

### Step 1 — Resolve customer ID and discover active Shopping campaigns
Call **Get Customer IDs** to resolve VTM Vending's Google Ads customer ID. Use this ID in
every subsequent Google Ads tool call in this skill.

Then call **Get Campaign Performance** for that customer ID (this toolset has no dedicated
"list campaigns" action, so campaign discovery rides on the performance tool). Filter/read the
results down to campaigns where advertising channel type = Shopping and status =
Enabled/Active. Record each campaign's ID and name — this defines the scope for every step
below. Re-discover this list every run; never hardcode a campaign list.

### Step 2 — Reconstruct existing negative keywords (baseline)
This toolset has **no direct "list negative keywords" action**. Call **Get Change History**
for the resolved customer ID, filtered to the last 29 days, and extract negative-keyword-added
events (and negative-keyword-removed events, if that event type is present — net them against
additions) to reconstruct the current negative keyword baseline. For each reconstructed
negative keyword, capture: keyword text, match type (broad/phrase/exact), and the campaign (or
shared list name + which Shopping campaigns that list applies to).

**Known limitation:** change history only covers the last 29 days, so negatives added earlier
than that will be missed from this baseline. Note this limitation in the Step 10 Slack summary
if it seems material (e.g., if Get Change History returns very few or zero negative-keyword
events for an account you'd expect to have some). Do not skip Step 4's cross-check just because
this baseline may be incomplete — use whatever is reconstructed as the best available baseline.

### Step 3 — Pull search term performance
Call **Get Search Term Performance** for the resolved customer ID, scoped to the Shopping
campaigns from Step 1, for the **trailing 14 days**, filtered to rows with **clicks >= 1**. For
each row, capture: search term text, campaign name, ad group name, clicks, cost, avg. CPC, and
conversions.

### Step 4 — Cross-check against existing negatives
Compare every search term from Step 3 against the negative keyword list from Step 2, applying
standard Google Ads negative-match logic (exact negative blocks only the identical query;
phrase negative blocks any query containing that phrase in order; broad negative blocks any
query containing all the negative's terms). **Remove any search term already covered by an
existing negative** from the working list — it should not be scored or re-added. Note the
removed count for context but do not include these terms in later steps.

### Step 5 — Score intent similarity (1–10)
For every remaining search term, assign an **intent similarity score from 1 (no match) to 10
(near-perfect match)** against VTM's business (vending machines dispensing Pokemon / trading
cards). Score based on purchase/commercial intent alignment with VTM's actual product, not
just keyword overlap with "Pokemon."

Calibration examples (apply this same bar consistently every run):
- **10** — `pokemon vending machine for sale` (near-perfect match: explicit product + purchase intent)
- **1** — `gengar gifts for men`, `mega chandelure` (Pokemon-adjacent fandom/character interest,
  no vending-machine or purchasing intent)

Score every term individually; do not batch-approximate. Output the full scored table.

### Step 6 — Split into two buckets by conversion status
From the scored table:
- **Bucket A:** search terms with conversions >= 1
- **Bucket B:** search terms with conversions = 0

### Step 7 — Flag negative keyword candidates
- From **Bucket A**, flag every term with intent score **<= 4**.
- From **Bucket B**, flag every term with intent score **<= 6**.
- Combine both flagged lists into one deduplicated candidate list (a term should only appear
  once even if it somehow appears in both campaign/ad group breakdowns — dedupe by exact term
  text).

### Step 8 — Add negative keywords
For each flagged candidate, call **Add Negative Keywords** (using the resolved customer ID)
to add it as a **campaign-level negative keyword, Exact match**, on the specific Shopping
campaign(s) where it appeared in Step 3. No review/approval step before pushing live.

If a single addition call fails, log which term/campaign failed and continue processing the
rest of the flagged list — do not abort the entire run over one failed addition. Track a
running list of any failures to mention in the Slack summary (Step 10).

### Step 9 — Calculate spend impact
Sum the **Cost** field (from Step 3) across all flagged/added search terms (successful
additions only, per Step 8). This total represents the ad spend "saved" — i.e., the spend
that will no longer be wasted on these queries going forward.

### Step 10 — Notify Slack
Call your Slack send-message tool directly, posting to the **#VTM** channel and mentioning
**Kyle Mollison** and **Lizzie Valenti**, with a short summary containing:
- Number of negative keywords added this run
- Total ad spend saved (the Step 9 sum), formatted as currency
- Any failed additions from Step 8, if applicable
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
- If zero candidates are flagged in a given run, still post the Slack summary (0 added, $0
  saved) so the team knows the check ran.
- Do not touch Search or Performance Max campaigns — this skill is scoped to **Shopping**
  campaigns only.
- Because there is no approval gate, scoring consistency (Step 5) is the main safety control —
  always apply the calibration examples the same way every run to avoid over- or
  under-blocking.
- Every step in this skill calls a Google Ads or Slack tool directly (Get Customer IDs, Get
  Campaign Performance, Get Search Term Performance, Get Change History, Add Negative
  Keywords, Slack send-message). Do not introduce delegation to any separate "Google Ads
  Agent" or "Slack Agent."
- Because there is no direct "list negative keywords" tool, Step 2's baseline is
  reconstructed from 29 days of change history and may be incomplete for older negatives —
  see the limitation note in Step 2.
- If a direct tool call fails, don't blindly retry the identical call. Check whether the
  tool/connection is actually available and properly configured in this agent's project
  before retrying, and surface the specific error rather than looping.
