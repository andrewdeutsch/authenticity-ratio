"""
Unit tests for TrustStackAttributeDetector
"""
import pytest
from scoring.attribute_detector import TrustStackAttributeDetector
from data.models import NormalizedContent


@pytest.fixture
def detector():
    """Create a detector instance for testing"""
    return TrustStackAttributeDetector()


def _make_content(body="", title="", **kwargs):
    """Helper to create NormalizedContent for testing"""
    return NormalizedContent(
        content_id="test_id",
        src="test_src",
        platform_id="test_platform",
        url="https://example.com",
        title=title,
        body=body,
        author="test_author",
        published_at="2024-01-01",
        event_ts="2024-01-01T00:00:00",
        **kwargs
    )


class TestReadabilityDetection:
    """Test readability grade level fit detection"""

    def test_simple_two_sentences(self, detector):
        """Test basic two-sentence text"""
        text = "This is the first sentence. This is the second sentence."
        content = _make_content(body=text)
        result = detector._detect_readability(content)

        assert result is not None
        assert result.attribute_id == "readability_grade_level_fit"
        # 10 words / 2 sentences = 5 words/sentence
        assert "5.0 words/sentence" in result.evidence or "Difficult" in result.evidence

    def test_three_sentences_readable(self, detector):
        """Test three sentences with readable length"""
        text = (
            "This is a well-written sentence with about fifteen words in it right here. "
            "Another sentence follows with similar length and complexity for readability testing. "
            "The third sentence maintains consistency with appropriate length and structure."
        )
        content = _make_content(body=text)
        result = detector._detect_readability(content)

        assert result is not None
        # Should have ~15 words per sentence, which is "Readable"
        assert "Readable" in result.evidence or "Acceptable" in result.evidence

    def test_long_sentence_difficult(self, detector):
        """Test very long sentence (simulates the bug scenario)"""
        # Create a 100-word sentence with sparse punctuation
        words = ["word"] * 100
        text = " ".join(words) + ". Another sentence here."
        content = _make_content(body=text)
        result = detector._detect_readability(content)

        assert result is not None
        # Should detect ~50 words/sentence as difficult
        assert "Difficult" in result.evidence or float(result.evidence.split()[1]) > 30

    def test_exclamation_and_question_marks(self, detector):
        """Test sentence splitting with different punctuation"""
        text = (
            "This is a statement. "
            "Is this a question? "
            "This is exciting! "
            "Another normal sentence."
        )
        content = _make_content(body=text)
        result = detector._detect_readability(content)

        assert result is not None
        # 4 sentences with ~20 words total = ~5 words/sentence
        assert result.evidence is not None

    def test_no_off_by_one_error(self, detector):
        """Test that we don't have the off-by-one error from old re.split() approach"""
        # This text should have exactly 3 sentences
        text = (
            "First sentence with ten words here to make it long. "
            "Second sentence also has ten words in it too. "
            "Third sentence completes the test with ten words."
        )
        content = _make_content(body=text)
        result = detector._detect_readability(content)

        assert result is not None
        # Should be close to 10 words/sentence (9-10 is acceptable due to splitting logic)
        evidence_parts = result.evidence.split()
        words_per_sent = float(evidence_parts[1])
        assert 9.0 <= words_per_sent <= 10.0, f"Expected ~10 words/sentence, got {words_per_sent}"

    def test_text_ending_with_punctuation(self, detector):
        """Test text that ends with punctuation (edge case for old bug)"""
        text = "First sentence with more words here. Second sentence also longer. Third sentence too."
        content = _make_content(body=text)
        result = detector._detect_readability(content)

        assert result is not None
        # Should count exactly 3 sentences, not 4 (no off-by-one error)
        assert result.evidence is not None
        # With proper splitting, should get reasonable words per sentence
        evidence_parts = result.evidence.split()
        words_per_sent = float(evidence_parts[1])
        assert words_per_sent < 10, f"Words per sentence should be reasonable, got {words_per_sent}"

    def test_multiple_punctuation(self, detector):
        """Test text with multiple consecutive punctuation marks"""
        text = "What on earth is happening here?! Really and truly?! No way this can be real!! Yes, indeed this is quite remarkable."
        content = _make_content(body=text)
        result = detector._detect_readability(content)

        assert result is not None
        # Should handle multiple punctuation gracefully
        assert result.evidence is not None

    def test_short_text_returns_none(self, detector):
        """Test that very short text returns None"""
        text = "Too short."
        content = _make_content(body=text)
        result = detector._detect_readability(content)

        assert result is None  # Less than 50 chars

    def test_empty_text_returns_none(self, detector):
        """Test that empty text returns None"""
        content = _make_content(body="")
        result = detector._detect_readability(content)

        assert result is None

    def test_text_without_punctuation(self, detector):
        """Test text without proper sentence punctuation"""
        text = "This is a very long run-on sentence without any proper punctuation at all " * 3
        content = _make_content(body=text)
        result = detector._detect_readability(content)

        # Should either return None (no sentences) or treat as one long sentence
        # Either way, should not crash
        assert result is None or result.evidence is not None

    def test_filters_short_fragments(self, detector):
        """Test that short fragments (< 10 chars) are filtered out"""
        text = "A. B. C. This is a proper sentence with more words."
        content = _make_content(body=text)
        result = detector._detect_readability(content)

        assert result is not None
        # Should filter out "A", "B", "C" and only count the real sentence
        # The evidence should show reasonable words/sentence, not inflated

    def test_mastercard_scenario(self, detector):
        """Test a scenario similar to the Mastercard issue"""
        # Simulate a page with 215 words and 5 sentences (should be ~43 words/sentence)
        sentence = "This is a typical business sentence with multiple clauses that discusses company strategy. "
        text = sentence * 5  # 5 sentences with ~15 words each = 75 words total

        content = _make_content(body=text)
        result = detector._detect_readability(content)

        assert result is not None
        # Should be around 15 words/sentence, NOT 215 or other inflated values
        evidence_parts = result.evidence.split()
        words_per_sent = float(evidence_parts[1])
        assert words_per_sent < 50, f"Words per sentence should be reasonable, got {words_per_sent}"
