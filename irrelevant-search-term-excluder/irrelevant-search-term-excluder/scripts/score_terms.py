#!/usr/bin/env python3
"""
score_terms.py — Deterministic intent-similarity scorer for VTM Vending
Shopping campaign search terms.

Purpose
-------
Assigns a 1-10 intent-similarity score to each search term, measuring
alignment with VTM's actual business: vending machines that dispense
Pokemon cards and other trading cards.

This is a DETERMINISTIC, RULE-BASED classifier — not a per-term LLM
judgment call. It exists so that repeated runs of the negative-keyword
cleanup skill produce the SAME score for the SAME term every time,
which a fresh LLM judgment pass run-to-run cannot guarantee.

There is NO manual override / bump mechanism by design. Any tension
between "correct semantic score" and "protect a converting term" must
be resolved by fixing the tier rules themselves (see CHANGELOG.md),
not by special-casing individual keyword strings.

Calibration anchors (from SKILL.md Step 5 — do not change without
updating SKILL.md too):
  10 = "pokemon vending machine for sale"  (exact product + purchase intent)
   1 = "gengar gifts for men", "mega chandelure"  (fandom, zero relevance)

Usage
-----
    python3 score_terms.py input.json output.json

Input JSON: a list of objects, each with at minimum:
    {"searchTerm": str, "clicks": number, "cost": number, "conversions": number}
Optional: "campaignId", "campaign" (passed through unchanged).

Output JSON: the same list, each row augmented with "score" (int 1-10)
and "reason" (str, human-readable rationale for the score).
"""
import json
import re
import sys

# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

# "vending machine" in English + Spanish ("maquina/máquina expendedora").
# NOTE: a prior version of this script only recognized the English phrase
# and mis-scored "maquina expendedora de cartas pokemon" (Spanish for
# "pokemon card vending machine") as a generic low-intent term. Fixed here.
VENDING = re.compile(
    r"vending machin|vending series|dispenser|kiosk|quarter machine"
    r"|vtm vending|vtm machine|m[aá]quina[s]? expendedora"
)

POKE_CARD = re.compile(
    r"pok[eé]mon|tcg|trading card|card(?!board)|pikachu|eevee|snorlax"
    r"|gengar|chandelure|drakloak|dhelmise|primarina|charizard"
)

PURCHASE_MOD = re.compile(
    r"for sale|\bbuy\b|\bbuying\b|cheap|cost|price|where to buy"
    r"|wholesale|discount|deal|on sale|\bsale\b|business"
)

RETAILER = re.compile(
    r"gamestop|target|walmart|costco|ebay|amazon|mercari|alibaba"
    r"|aliexpress|etsy|depop|barnes and noble|dollar general|toys r us"
    r"|sams club|frys|heb\b|walgreens|lowes"
)

CHARACTER_ONLY = re.compile(
    r"^(eevee|snorlax|pikachu( pikachu pikachu)?|gengar gifts for men"
    r"|mega chandelure|red cheeks pikachu|ooyama pikachu|poncho pikachu)$"
)

# NOTE: word-boundary on "art vending" is required. Without \b, "smart
# vending machine" false-matches this pattern because "art vending" is a
# literal substring of "sm-ART VENDING-machine". Found and fixed during
# the 2026-08-05 run.
WRONG_PRODUCT_VENDING = re.compile(
    r"candy vending|sticker machine|toys vending|\bart vending|quarter machine"
)

INFORMATIONAL = re.compile(
    r"pokemon center|pokémon center|pokemon store|pokémon store|pokecenter"
    r"|pokémoncenter|pokemoncenter|restock|drop|news|deals?$"
    r"|center (online|product|drop|hiroshima|30th)"
)

BRANDED = re.compile(r"\bvtm\b")

GENERIC_UNRELATED = {
    "toys for kids", "cool toys for 9 year olds", "cool boy toys for 7 year old",
    "sun & moon team up", "machine", "alibaba", "mercari",
}


def score(term: str):
    """Return (score:int, reason:str) for a single search term."""
    t = term.lower().strip()

    if BRANDED.search(t):
        return 10, "branded (vtm) mention — treat as near-perfect intent"

    has_vend = bool(VENDING.search(t))
    has_poke = bool(POKE_CARD.search(t))
    has_purchase = bool(PURCHASE_MOD.search(t))
    has_retailer = bool(RETAILER.search(t))
    has_wrong_vend = bool(WRONG_PRODUCT_VENDING.search(t))

    if CHARACTER_ONLY.match(t):
        return 1, "pure character/fandom mention, no commercial signal"
    if t in GENERIC_UNRELATED:
        return 1, "generic/unrelated term, no product or purchase signal"

    if has_vend and has_wrong_vend:
        return 6, "vending machine mentioned, but wrong dispensed product"

    if has_vend and has_poke:
        if has_purchase:
            return 10, "vending machine + pokemon/card + purchase intent"
        return 9, "vending machine + pokemon/card — exact product match"

    if has_vend and not has_poke:
        if has_purchase:
            return 8, "generic vending machine + purchase intent (not pokemon-specific)"
        return 7, "generic vending machine, informational — right product category"

    if has_poke and has_retailer:
        return 3, "pokemon/card + specific retailer — shopping elsewhere, not VTM"

    if has_poke and has_purchase:
        return 5, "pokemon/card + purchase intent, no vending machine mention"

    if has_poke and INFORMATIONAL.search(t):
        return 2, "pokemon-adjacent informational/browsing, no purchase signal"

    if has_poke:
        # Generic pokemon/card product-name mention: no vending machine,
        # no retailer, no explicit purchase modifier (e.g. "pokemon cards",
        # "pokemon boxes", "booster pokemon packs", "pokémon card").
        #
        # This tier was previously split at score 4, which sat exactly on
        # the skill's Bucket-A flag threshold (score <= 4 for converting
        # terms) and would auto-flag genuinely converting generic-product
        # queries as negatives. Rather than special-casing specific
        # keyword strings with a manual override, the tier itself is
        # calibrated to 5 so ANY term in this category — present or
        # future — sits safely above the Bucket-A cutoff while still
        # being flaggable under the more permissive Bucket-B cutoff
        # (score <= 6) when it has zero conversions. See CHANGELOG.md.
        return 5, "generic pokemon/card product mention, no vending/retailer/purchase signal"

    return 1, "no relevance to VTM's product or business"


def process(rows):
    out = []
    for r in rows:
        s, reason = score(r["searchTerm"])
        out.append({**r, "score": s, "reason": reason})
    return out


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 score_terms.py input.json output.json", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        rows = json.load(f)

    scored = process(rows)

    with open(sys.argv[2], "w") as f:
        json.dump(scored, f, indent=2)

    print(f"Scored {len(scored)} terms -> {sys.argv[2]}")


if __name__ == "__main__":
    main()
