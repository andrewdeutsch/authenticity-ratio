import pytest

from scoring.pipeline import ScoringPipeline
from data.models import ContentScores


def make_score(content_id: str, class_label: str, is_authentic: bool, run_id: str = 'run-test') -> ContentScores:
    # Minimal ContentScores for reporting
    return ContentScores(
        content_id=content_id,
        brand='test-brand',
        src='reddit',
        event_ts='2025-01-01T00:00:00Z',
        score_provenance=0.5,
        score_resonance=0.5,
        score_coherence=0.5,
        score_transparency=0.5,
        score_verification=0.5,
        class_label=class_label,
        is_authentic=is_authentic,
        rubric_version='v1.0',
        run_id=run_id,
    )


def test_generate_scoring_report_uses_provided_scores():
    """Ensure report generation computes AR from the provided scores_list."""
    sp = ScoringPipeline()

    # Create two scores: one authentic, one inauthentic -> AR should be 50%
    s1 = make_score('c1', 'authentic', True)
    s2 = make_score('c2', 'inauthentic', False)

    report = sp.generate_scoring_report([s1, s2], {'brand_id': 'test-brand', 'brand_name': 'Test Brand'})

    ar = report.get('authenticity_ratio', {})

    assert report['total_items_analyzed'] == 2
    assert ar.get('total_items') == 2
    assert ar.get('authentic_items') == 1
    # Core AR should be 50.0
    assert pytest.approx(ar.get('authenticity_ratio_pct', 0.0), rel=1e-3) == 50.0
