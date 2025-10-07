"""
Unit tests for data models
"""

import unittest
from datetime import datetime
from data.models import NormalizedContent, ContentScores, AuthenticityRatio, BrandConfig, PipelineRun

class TestNormalizedContent(unittest.TestCase):
    """Test NormalizedContent model"""
    
    def test_normalized_content_creation(self):
        """Test creating NormalizedContent object"""
        content = NormalizedContent(
            content_id="test_123",
            src="reddit",
            platform_id="abc123",
            author="test_user",
            title="Test Title",
            body="Test body content",
            rating=0.85,
            upvotes=42,
            event_ts="2024-01-01T12:00:00",
            run_id="run_123"
        )
        
        self.assertEqual(content.content_id, "test_123")
        self.assertEqual(content.src, "reddit")
        self.assertEqual(content.author, "test_user")
        self.assertEqual(content.rating, 0.85)
        self.assertEqual(content.upvotes, 42)

class TestContentScores(unittest.TestCase):
    """Test ContentScores model"""
    
    def test_content_scores_creation(self):
        """Test creating ContentScores object"""
        scores = ContentScores(
            content_id="test_123",
            brand="Test Brand",
            src="reddit",
            event_ts="2024-01-01T12:00:00",
            score_provenance=0.8,
            score_resonance=0.7,
            score_coherence=0.9,
            score_transparency=0.6,
            score_verification=0.75,
            class_label="authentic",
            is_authentic=True,
            rubric_version="v1.0",
            run_id="run_123"
        )
        
        self.assertEqual(scores.content_id, "test_123")
        self.assertEqual(scores.brand, "Test Brand")
        self.assertEqual(scores.score_provenance, 0.8)
        self.assertTrue(scores.is_authentic)
    
    def test_overall_score_calculation(self):
        """Test overall score calculation"""
        scores = ContentScores(
            content_id="test_123",
            brand="Test Brand",
            src="reddit",
            event_ts="2024-01-01T12:00:00",
            score_provenance=0.8,
            score_resonance=0.7,
            score_coherence=0.9,
            score_transparency=0.6,
            score_verification=0.75,
            class_label="authentic",
            is_authentic=True,
            rubric_version="v1.0",
            run_id="run_123"
        )
        
        # With default weights (20% each), overall should be average
        expected_overall = (0.8 + 0.7 + 0.9 + 0.6 + 0.75) / 5
        self.assertAlmostEqual(scores.overall_score, expected_overall, places=3)

class TestAuthenticityRatio(unittest.TestCase):
    """Test AuthenticityRatio model"""
    
    def test_authenticity_ratio_creation(self):
        """Test creating AuthenticityRatio object"""
        ar = AuthenticityRatio(
            brand_id="test_brand",
            source="reddit",
            run_id="run_123",
            total_items=100,
            authentic_items=75,
            suspect_items=15,
            inauthentic_items=10,
            authenticity_ratio_pct=75.0
        )
        
        self.assertEqual(ar.brand_id, "test_brand")
        self.assertEqual(ar.total_items, 100)
        self.assertEqual(ar.authenticity_ratio_pct, 75.0)
    
    def test_extended_ar_calculation(self):
        """Test extended AR calculation"""
        ar = AuthenticityRatio(
            brand_id="test_brand",
            source="reddit",
            run_id="run_123",
            total_items=100,
            authentic_items=60,
            suspect_items=30,
            inauthentic_items=10,
            authenticity_ratio_pct=60.0
        )
        
        # Extended AR = (60 + 0.5 * 30) / 100 * 100 = 75%
        expected_extended = (60 + 0.5 * 30) / 100 * 100
        self.assertEqual(ar.extended_ar, expected_extended)

class TestBrandConfig(unittest.TestCase):
    """Test BrandConfig model"""
    
    def test_brand_config_creation(self):
        """Test creating BrandConfig object"""
        config = BrandConfig(
            brand_id="test_brand",
            name="Test Brand",
            keywords=["test", "brand", "product"],
            exclude_keywords=["spam", "fake"],
            sources=["reddit", "amazon"],
            active=True
        )
        
        self.assertEqual(config.brand_id, "test_brand")
        self.assertEqual(len(config.keywords), 3)
        self.assertEqual(len(config.sources), 2)
        self.assertTrue(config.active)

class TestPipelineRun(unittest.TestCase):
    """Test PipelineRun model"""
    
    def test_pipeline_run_creation(self):
        """Test creating PipelineRun object"""
        start_time = datetime.now()
        run = PipelineRun(
            run_id="run_123",
            brand_id="test_brand",
            start_time=start_time,
            status="running",
            items_processed=0
        )
        
        self.assertEqual(run.run_id, "run_123")
        self.assertEqual(run.brand_id, "test_brand")
        self.assertEqual(run.status, "running")
        self.assertEqual(run.items_processed, 0)
        self.assertEqual(len(run.errors), 0)

if __name__ == '__main__':
    unittest.main()
