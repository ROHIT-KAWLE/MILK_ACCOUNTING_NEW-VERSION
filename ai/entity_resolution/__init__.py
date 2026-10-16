"""
Entity resolution package exports.
"""

from ai.entity_resolution.phonetic import devanagari_to_latin, phonetic_norm, string_similarity
from ai.entity_resolution.retailer_matcher import match_retailer
from ai.entity_resolution.category_matcher import match_category
from ai.entity_resolution.distributor_matcher import match_distributor

__all__ = [
    "devanagari_to_latin",
    "phonetic_norm",
    "string_similarity",
    "match_retailer",
    "match_category",
    "match_distributor",
]
