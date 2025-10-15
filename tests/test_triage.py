from scoring.triage import triage_score_item, triage_filter


class DummyContent:
    def __init__(self, content_id, title, body, src='web', event_ts='2025-01-01T00:00:00'):
        self.content_id = content_id
        self.title = title
        self.body = body
        self.src = src
        self.event_ts = event_ts


def test_triage_promotes_relevant_content():
    c1 = DummyContent('1', 'Nike update', 'This article mentions Nike and new product launches with multiple links http://example.com')
    c2 = DummyContent('2', 'Short', 'hi')
    promoted, demoted = triage_filter([c1, c2], ['nike'], promote_threshold=0.6)
    assert len(promoted) == 1
    assert promoted[0].content_id == '1'
    assert len(demoted) == 1


def test_triage_score_range_and_behavior():
    c = DummyContent('3', 'Neutral', 'This is some medium length content with no brand')
    s = triage_score_item(c, ['nike'])
    assert 0.0 <= s <= 1.0
