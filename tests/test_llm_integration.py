import json
import logging
from unittest.mock import patch

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


def test_llm_merge_into_scores(monkeypatch):
    pipeline = ScoringPipeline()
    # create suspect items that will be selected by triage
    scores = [make_score(f'id_{i}', 0.5) for i in range(3)]

    fake_llm_out = {
        'id_0': {'label': 'authentic', 'confidence': 0.9},
        'id_1': {'label': 'suspect', 'confidence': 0.6},
        'id_2': {'label': 'inauthentic', 'confidence': 0.8},
    }

    class FakeLLM:
        def __init__(self, *args, **kwargs):
            pass

        def classify(self, items, rubric_version='unknown'):
            return fake_llm_out

    with patch('scoring.llm.LLMClient', FakeLLM):
        pipeline._calculate_authenticity_ratio(scores, 'test_brand', 'run-test')

    # After the call, scores objects should have class_label set from fake_llm_out
    mapping = {s.content_id: s for s in scores}
    assert mapping['id_0'].class_label == 'authentic'
    assert mapping['id_1'].class_label == 'suspect'
    assert mapping['id_2'].class_label == 'inauthentic'
