"""
Database-Aware Distributor Entity Matcher.
Resolves procurement vendor references against actual Supabase distributors.
Never invents distributor IDs.
"""

import pandas as pd
from ai.config import get_ai_config
from ai.schemas.command_types import AmbiguousCandidate, AmbiguousMatch
from ai.entity_resolution.phonetic import phonetic_norm, string_similarity


def match_distributor(
    spoken_text: str,
    distributors_df: pd.DataFrame,
) -> tuple[dict | None, AmbiguousMatch | None, float]:
    """
    Matches spoken text against actual distributors in Supabase database.
    Returns:
      (matched_distributor_dict, ambiguity_object, confidence_score)
    """
    if not spoken_text or distributors_df is None or distributors_df.empty:
        return None, None, 0.0

    cfg = get_ai_config()
    input_norm = phonetic_norm(spoken_text)
    input_lower = spoken_text.lower().strip()

    candidates: list[AmbiguousCandidate] = []

    for _, row in distributors_df.iterrows():
        did = int(pd.to_numeric(row.get("distributor_id", row.get("id", row.get("ID", 0))), errors="coerce") or 0)
        dname = str(row.get("name", "")).strip()
        dmarathi = str(row.get("marathi_name", "")).strip()
        if did <= 0 or not dname:
            continue

        dname_norm = phonetic_norm(dname)
        dname_lower = dname.lower()
        dmarathi_lower = dmarathi.lower()

        score = 0.0
        if (dname_lower and (dname_lower in input_lower or input_lower in dname_lower)) or (dmarathi_lower and (dmarathi_lower in input_lower or input_lower in dmarathi_lower)):
            score = 1.0
        elif (dname_norm and (dname_norm in input_norm or input_norm in dname_norm)) or (dmarathi and phonetic_norm(dmarathi) in input_norm):
            score = 0.95
        else:
            sim = string_similarity(dname_norm, input_norm)
            if sim >= 0.70:
                score = sim

        if score >= cfg.DISTRIBUTOR_MATCH_THRESHOLD:
            candidates.append(AmbiguousCandidate(id=did, name=dname, score=round(score, 3)))

    if not candidates:
        return None, None, 0.0

    candidates.sort(key=lambda c: c.score, reverse=True)

    # Check for Ambiguity
    if len(candidates) >= 2:
        top1 = candidates[0]
        top2 = candidates[1]
        if (top1.score - top2.score) <= cfg.AMBIGUITY_DELTA_THRESHOLD and top1.score < 0.98:
            amb = AmbiguousMatch(
                query=spoken_text,
                entity_type="distributor",
                candidates=candidates[:3],
            )
            return None, amb, round(top1.score, 2)

    best = candidates[0]
    return (
        {"id": best.id, "name": best.name},
        None,
        best.score,
    )
