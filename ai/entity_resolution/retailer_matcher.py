"""
Database-Aware Retailer Entity Matcher.
Resolves customer names against actual active Supabase master records.
Enforces strict ambiguity detection: never silently guesses between multiple plausible matches.
"""

import pandas as pd
from ai.config import get_ai_config
from ai.schemas.command_types import AmbiguousCandidate, AmbiguousMatch
from ai.entity_resolution.phonetic import phonetic_norm, string_similarity


GENERIC_DAIRY_WORDS: set[str] = {
    "dairy", "milk", "center", "centre", "agency", "supplier", "suppliers", "farm",
    "डेअरी", "डेरी", "सेंटर", "मिल्क", "एजन्सी",
}


def match_retailer(
    spoken_text: str,
    retailers_df: pd.DataFrame,
    active_zone: str | None = None,
) -> tuple[dict | None, AmbiguousMatch | None, float]:
    """
    Matches spoken/typed text against actual retailers in Supabase database.
    Returns:
      (matched_retailer_dict, ambiguity_object, confidence_score)

    If unambiguous match found:
      returns ({'id': 1, 'name': 'Gupta Dairy', 'zone': 'Route 1'}, None, 0.95)
    If ambiguous match found (e.g. Gupta Dairy vs Gupta Milk Center):
      returns (None, AmbiguousMatch(...), 0.50)
    If no match found:
      returns (None, None, 0.0)
    """
    if not spoken_text or retailers_df is None or retailers_df.empty:
        return None, None, 0.0

    cfg = get_ai_config()
    input_norm = phonetic_norm(spoken_text)
    input_lower = spoken_text.lower().strip()

    candidates: list[AmbiguousCandidate] = []

    # Iterate over actual database records
    for _, row in retailers_df.iterrows():
        rid = int(pd.to_numeric(row.get("retailer_id", row.get("id", row.get("ID", 0))), errors="coerce") or 0)
        rname = str(row.get("name", "")).strip()
        rmarathi = str(row.get("marathi_name", "")).strip()
        rzone = str(row.get("zone", "")).strip()
        if rid <= 0 or not rname:
            continue

        rname_norm = phonetic_norm(rname)
        rname_lower = rname.lower()
        rmarathi_lower = rmarathi.lower()

        score = 0.0

        # Exact full name match (English or Marathi name)
        if (rname_lower and rname_lower in input_lower) or (rmarathi_lower and rmarathi_lower in input_lower):
            score = 1.0
        elif (rname_norm and rname_norm in input_norm) or (rmarathi and phonetic_norm(rmarathi) in input_norm):
            score = 0.95
        else:
            # Check primary distinguishing non-generic tokens (e.g. 'Gupta', 'Patel', 'Laxmi')
            raw_tokens = [tok for tok in rname_lower.split() if len(tok) > 1]
            dist_tokens = [tok for tok in raw_tokens if tok not in GENERIC_DAIRY_WORDS]
            if not dist_tokens:
                dist_tokens = raw_tokens

            # Check if all distinguishing tokens are present in input
            dist_matched = 0
            for dtok in dist_tokens:
                dtok_norm = phonetic_norm(dtok)
                if dtok in input_lower or (dtok_norm and dtok_norm in input_norm):
                    dist_matched += 1

            if dist_matched == len(dist_tokens) and len(dist_tokens) > 0:
                score = 0.88
            else:
                # Fallback to SequenceMatcher similarity
                seq_score = string_similarity(rname_norm, input_norm)
                score = seq_score

        # Bonus if retailer belongs to currently selected zone context
        if active_zone and active_zone != "All Zones" and rzone == active_zone:
            score = min(1.0, score + 0.05)

        if score >= cfg.RETAILER_MATCH_THRESHOLD:
            candidates.append(AmbiguousCandidate(
                id=rid,
                name=rname,
                score=round(score, 3),
                extra={"zone": rzone},
            ))

    if not candidates:
        return None, None, 0.0

    # Sort descending by match score
    candidates.sort(key=lambda c: c.score, reverse=True)

    # Check for Ambiguity
    # If 2 or more candidates and the top 2 are within delta threshold
    if len(candidates) >= 2:
        top1 = candidates[0]
        top2 = candidates[1]
        if (top1.score - top2.score) <= cfg.AMBIGUITY_DELTA_THRESHOLD and top1.score < 0.98:
            amb = AmbiguousMatch(
                query=spoken_text,
                entity_type="retailer",
                candidates=candidates[:4],  # Present top candidates to user
            )
            return None, amb, round(top1.score, 2)

    # Highest single candidate
    best = candidates[0]
    return (
        {"id": best.id, "name": best.name, "zone": best.extra.get("zone")},
        None,
        best.score,
    )
