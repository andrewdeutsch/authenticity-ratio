from scoring.pipeline import ScoringPipeline
from data.models import ContentScores


def _make_score(p=0.9, r=0.9, c=0.9, t=0.9, v=0.9, meta=None, run_id='r1'):
    return ContentScores(
        content_id='id', brand='b', src='brave', event_ts='ts',
        score_provenance=p, score_resonance=r, score_coherence=c,
        score_transparency=t, score_verification=v,
        class_label='pending', is_authentic=False, rubric_version='v', run_id=run_id,
        meta=meta or {}
    )


def test_ar_authentic():
    sp = ScoringPipeline()
    scores = [
        _make_score(),
        _make_score(),
        _make_score(),
    ]
    ar = sp._calculate_authenticity_ratio(scores, 'brand', 'run')
    assert ar.authentic_items == 3
    assert ar.suspect_items == 0
    assert ar.inauthentic_items == 0


def test_ar_mixed():
    sp = ScoringPipeline()
    scores = [
        _make_score(p=0.8),
        _make_score(p=0.5, r=0.4, c=0.4, t=0.5, v=0.5),
        _make_score(p=0.1, r=0.1, c=0.1, t=0.1, v=0.1),
    ]
    ar = sp._calculate_authenticity_ratio(scores, 'brand', 'run')
    assert ar.total_items == 3
    assert ar.authentic_items + ar.suspect_items + ar.inauthentic_items == 3


def test_ar_meta_bonus_penalty():
    sp = ScoringPipeline()
    # High base but dup similarity penalizes
    s1 = _make_score()
    s2 = _make_score(meta={'c2pa': True})
    s3 = _make_score(p=0.8, meta={'dup_similarity': 0.9})
    ar = sp._calculate_authenticity_ratio([s1, s2, s3], 'brand', 'run')
    # Expect at least one authentic, the dup should lower that item's score
    assert ar.total_items == 3
    assert ar.authentic_items >= 1
