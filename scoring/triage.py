"""Lightweight triage scorer to cheaply filter content before full LLM scoring.

This module provides a fast heuristic scorer that assigns a cheap authenticity
probability (0.0-1.0) based on simple signals (presence of brand keywords,
length of body, presence of external links). The scoring pipeline will run
the triage stage first to reduce the number of items sent to the expensive
LLM-based `ContentScorer`.
"""
from typing import List, Dict, Any
import logging
import os

from config.settings import SETTINGS

logger = logging.getLogger(__name__)


def _get_threshold(default: float = 0.6) -> float:
    try:
        return float(SETTINGS.get('triage_promote_threshold', default))
    except Exception:
        return default


def triage_score_item(content, brand_keywords: List[str]) -> float:
    """Compute a cheap triage score for a single content item.

    Returns a float between 0.0 and 1.0 where higher means more likely authentic
    and should be promoted to the high-quality scorer.
    """
    text = (getattr(content, 'body', '') or '') + ' ' + (getattr(content, 'title', '') or '')
    text_l = text.lower()

    score = 0.5

    # Boost if brand keywords appear (slightly larger boost to promote relevant content)
    for kw in brand_keywords:
        if kw.lower() in text_l:
            score += 0.20

    # Penalize extremely short content (likely low-value) but less harshly
    if len(text_l.split()) < 30:
        score -= 0.10

    # Slight boost if there are external http links present (citations)
    if 'http://' in text_l or 'https://' in text_l:
        score += 0.05

    final = max(0.0, min(1.0, score))
    logger.debug('Triage score for content %s = %s', getattr(content, 'content_id', 'unknown'), final)
    return final


def triage_filter(content_list: List, brand_keywords: List[str], promote_threshold: float | None = None):
    """Return a tuple (promoted, demoted) where promoted items have triage score >= threshold.

    If promote_threshold is None, the value will be read from configuration.
    """
    if promote_threshold is None:
        promote_threshold = _get_threshold()

    promoted = []
    demoted = []
    for c in content_list:
        s = triage_score_item(c, brand_keywords)
        if s >= promote_threshold:
            promoted.append(c)
        else:
            demoted.append(c)
    logger.info('Triage filter: %d promoted, %d demoted (threshold=%s)', len(promoted), len(demoted), promote_threshold)
    return promoted, demoted
