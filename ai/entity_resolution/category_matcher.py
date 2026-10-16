"""
Database-Aware Milk Category Entity Matcher.
Resolves spoken category references against actual Supabase categories.
Never invents category IDs.
"""

import pandas as pd
from ai.entity_resolution.phonetic import phonetic_norm, string_similarity

CATEGORY_SYNONYMS: dict[str, list[str]] = {
    "buffalo": ["buffalo", "buff", "mahis", "mhais", "म्हैस", "म्हैशीचे", "भैस", "bhains", "mahees"],
    "cow": ["cow", "gay", "gaay", "गाय", "गाईचे"],
    "standard": ["standard", "std", "स्टँडर्ड"],
    "gokul special": ["gokul", "gokul special", "गोकुळ", "गोकुळ स्पेशल"],
    "gokul cow": ["gokul cow", "गोकुळ गाय"],
    "amul": ["amul", "अमुल"],
    "amul chaas": ["chaas", "taak", "ताक", "छास", "chaach"],
}


def match_category(
    token_or_phrase: str,
    categories_df: pd.DataFrame,
) -> tuple[dict | None, float]:
    """
    Matches token/phrase against actual categories in Supabase database.
    Returns:
      ({'id': 1, 'name': 'Buffalo'}, confidence_score) or (None, 0.0)
    """
    if not token_or_phrase or categories_df is None or categories_df.empty:
        return None, 0.0

    phrase_norm = phonetic_norm(token_or_phrase)
    phrase_lower = token_or_phrase.lower().strip()

    best_match = None
    best_score = 0.0

    for _, row in categories_df.iterrows():
        cid = int(pd.to_numeric(row.get("category_id", row.get("id", row.get("CID", 0))), errors="coerce") or 0)
        cname = str(row.get("name", "")).strip()
        if cid <= 0 or not cname:
            continue

        cname_lower = cname.lower()
        cname_norm = phonetic_norm(cname)

        score = 0.0

        # Direct name match
        if cname_lower in phrase_lower or phrase_lower in cname_lower:
            score = 1.0
        elif cname_norm in phrase_norm or phrase_norm in cname_norm:
            score = 0.95
        else:
            # Check synonym dictionary
            for canonical_key, syn_list in CATEGORY_SYNONYMS.items():
                if canonical_key in cname_lower:
                    for syn in syn_list:
                        syn_norm = phonetic_norm(syn)
                        if syn in phrase_lower:
                            score = max(score, 0.98)
                        elif syn_norm in phrase_norm:
                            score = max(score, 0.92)
                        else:
                            sim = string_similarity(syn_norm, phrase_norm)
                            if sim >= 0.85:
                                score = max(score, sim * 0.90)

        if score > best_score:
            best_score = score
            best_match = {"id": cid, "name": cname}

    if best_score >= 0.65 and best_match:
        return best_match, round(best_score, 2)

    return None, 0.0
