import json
import logging

from scoring.pipeline import ScoringPipeline
from data.models import ContentScores


def make_score(cid, score, src='brave'):
    return ContentScores(
        content_id=cid,
        brand='test_brand',
        src=src,
        event_ts='2025-10-15T00:00:00Z',
        score_provenance=score,
        score_resonance=score,
        score_coherence=score,
        score_transparency=score,
        score_verification=score,
        class_label='pending',
        is_authentic=False,
        rubric_version='test',
        run_id='run-test',
        meta='{}'
    )


def test_triage_selects_expected_items(caplog):
    caplog.set_level(logging.INFO)
    pipeline = ScoringPipeline()

    # Create 6 suspect-range items (scores between 0.4 and 0.75)
    scores = [
        make_score(f'id_{i}', 0.55 + i * 0.01) for i in range(6)
    ]

    # Call the internal method (brand_id and run_id are arbitrary)
    pipeline._calculate_authenticity_ratio(scores, 'test_brand', 'run-test')

    logs = [r.message for r in caplog.records if 'Triage selected' in r.message]
    assert len(logs) == 1
    # Ensure it selected up to max_llm_items (default 10 in config, but there are only 6)
    assert 'selected 6 items' in logs[0]
