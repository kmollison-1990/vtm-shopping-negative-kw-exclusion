"""
Regression tests for scripts/score_terms.py

Run with:  python3 -m pytest tests/test_score_terms.py -v
or simply:  python3 tests/test_score_terms.py    (falls back to plain asserts)

Every test case here maps to either:
  (a) a calibration anchor explicitly defined in SKILL.md Step 5, or
  (b) a real bug found and fixed during an actual run (dated in comments),
      kept here permanently so it can never silently regress.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from score_terms import score  # noqa: E402


CASES = [
    # --- SKILL.md Step 5 calibration anchors ---------------------------
    ("pokemon vending machine for sale", 10,
     "SKILL.md calibration anchor: near-perfect match"),
    ("gengar gifts for men", 1,
     "SKILL.md calibration anchor: fandom, zero relevance"),
    ("mega chandelure", 1,
     "SKILL.md calibration anchor: fandom, zero relevance"),

    # --- Bug fix regression: Spanish-language vending machine ----------
    # Found 2026-08-05: scorer only recognized English "vending machine",
    # mis-scoring this Spanish equivalent as a generic low-intent term (4).
    ("maquina expendedora de cartas pokemon", 9,
     "Spanish for 'pokemon card vending machine' — must score as exact "
     "product match, not generic pokemon mention"),
    ("maquinas expendedoras", 7,
     "Spanish for 'vending machines' (generic) — must score as generic "
     "vending machine informational, not 'no relevance'"),

    # --- Bug fix regression: substring collision ------------------------
    # Found 2026-08-05: "art vending" (wrong-product pattern) matched
    # inside "sm-ART VENDING-machine" without a word boundary.
    ("smart vending machine", 7,
     "must NOT match the 'art vending' wrong-product pattern"),
    ("smart vending machines", 7,
     "must NOT match the 'art vending' wrong-product pattern"),
    ("toys vending machine", 6,
     "genuine wrong-product vending match — should still be tier 6"),
    ("art vending machine", 6,
     "genuine wrong-product vending match — should still be tier 6"),

    # --- Tier-boundary fix: generic pokemon/card product mentions ------
    # Found 2026-08-05: this tier previously scored 4, exactly on the
    # skill's Bucket-A (converting-term) flag threshold of <=4, which
    # would auto-flag genuinely converting generic-product queries.
    # Recalibrated to 5 so it never crosses that cutoff. No manual
    # override/bump mechanism exists — this must be fixed at the tier
    # level, as done here.
    ("pokemon cards", 5, "generic product mention must clear the Bucket-A cutoff"),
    ("pokemon boxes", 5, "generic product mention must clear the Bucket-A cutoff"),
    ("booster pokemon packs", 5, "generic product mention must clear the Bucket-A cutoff"),
    ("pokémon card", 5, "generic product mention must clear the Bucket-A cutoff"),

    # --- Branded terms ---------------------------------------------------
    ("vtm vending machine", 10, "branded mention, always near-perfect"),
    ("vtm machine", 10, "branded mention, always near-perfect"),

    # --- Retailer-specific ------------------------------------------------
    ("costco pokemon cards", 3, "retailer-specific — shopping elsewhere"),
    ("target pokemon", 3, "retailer-specific — shopping elsewhere"),

    # --- Informational / no purchase signal --------------------------------
    ("pokemon center", 2, "informational browsing, no purchase signal"),
    ("pokemon store", 2, "informational browsing, no purchase signal"),
]


def run():
    failures = []
    for term, expected_score, note in CASES:
        actual_score, reason = score(term)
        status = "OK" if actual_score == expected_score else "FAIL"
        if actual_score != expected_score:
            failures.append(
                f"[{status}] {term!r}: expected {expected_score}, got "
                f"{actual_score} ({reason}) -- {note}"
            )
        print(f"[{status}] {term!r} -> {actual_score} (expected {expected_score})")

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    else:
        print(f"All {len(CASES)} test cases passed.")


# Allow running under pytest too
def test_all_cases():
    for term, expected_score, note in CASES:
        actual_score, _ = score(term)
        assert actual_score == expected_score, (
            f"{term!r}: expected {expected_score}, got {actual_score} ({note})"
        )


if __name__ == "__main__":
    run()
