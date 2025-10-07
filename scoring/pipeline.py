"""
Scoring pipeline for AR tool
Orchestrates the scoring and classification process
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from data.models import NormalizedContent, ContentScores, PipelineRun
from data.athena_client import AthenaClient
from .scorer import ContentScorer
from .classifier import ContentClassifier

logger = logging.getLogger(__name__)

class ScoringPipeline:
    """Orchestrates the scoring and classification pipeline"""
    
    def __init__(self):
        self.scorer = ContentScorer()
        self.classifier = ContentClassifier()
        self.athena_client = AthenaClient()
    
    def run_scoring_pipeline(self, content_list: List[NormalizedContent], 
                           brand_config: Dict[str, Any]) -> PipelineRun:
        """
        Run the complete scoring pipeline
        
        Args:
            content_list: List of normalized content to score
            brand_config: Brand configuration and context
            
        Returns:
            PipelineRun object with execution details
        """
        run_id = str(uuid.uuid4())
        brand_id = brand_config.get('brand_id', 'unknown')
        
        # Initialize pipeline run
        pipeline_run = PipelineRun(
            run_id=run_id,
            brand_id=brand_id,
            start_time=datetime.now(),
            status="running"
        )
        
        logger.info(f"Starting scoring pipeline {run_id} for brand {brand_id}")
        logger.info(f"Processing {len(content_list)} content items")
        
        try:
            # Step 1: Score content on 5D dimensions
            logger.info("Step 1: Scoring content on 5D dimensions")
            scores_list = self.scorer.batch_score_content(content_list, brand_config)
            pipeline_run.items_processed += len(scores_list)
            
            # Step 2: Classify content (Authentic/Suspect/Inauthentic)
            logger.info("Step 2: Classifying content")
            classified_scores = self.classifier.batch_classify_content(scores_list)
            
            # Step 3: Upload scores to S3/Athena
            logger.info("Step 3: Uploading scores to S3/Athena")
            self._upload_scores_to_athena(classified_scores, brand_id)
            
            # Step 4: Calculate and log Authenticity Ratio
            logger.info("Step 4: Calculating Authenticity Ratio")
            ar_result = self._calculate_authenticity_ratio(classified_scores, brand_id, run_id)
            
            # Complete pipeline run
            pipeline_run.end_time = datetime.now()
            pipeline_run.status = "completed"
            
            logger.info(f"Scoring pipeline {run_id} completed successfully")
            logger.info(f"Authenticity Ratio: {ar_result.authenticity_ratio_pct:.2f}%")
            
        except Exception as e:
            pipeline_run.end_time = datetime.now()
            pipeline_run.status = "failed"
            pipeline_run.errors.append(str(e))
            logger.error(f"Scoring pipeline {run_id} failed: {e}")
            raise
        
        return pipeline_run
    
    def _upload_scores_to_athena(self, scores_list: List[ContentScores], brand_id: str) -> None:
        """Upload content scores to S3/Athena"""
        if not scores_list:
            logger.warning("No scores to upload")
            return
        
        # Group scores by source
        scores_by_source = {}
        for score in scores_list:
            source = score.src
            if source not in scores_by_source:
                scores_by_source[source] = []
            scores_by_source[source].append(score)
        
        # Upload each source separately
        for source, source_scores in scores_by_source.items():
            run_id = source_scores[0].run_id
            self.athena_client.upload_content_scores(source_scores, brand_id, source, run_id)
    
    def _calculate_authenticity_ratio(self, scores_list: List[ContentScores], 
                                    brand_id: str, run_id: str) -> Dict[str, Any]:
        """Calculate Authenticity Ratio from scores"""
        if not scores_list:
            return {
                "brand_id": brand_id,
                "run_id": run_id,
                "total_items": 0,
                "authentic_items": 0,
                "suspect_items": 0,
                "inauthentic_items": 0,
                "authenticity_ratio_pct": 0.0,
                "extended_ar_pct": 0.0
            }
        
        # Count classifications
        authentic_count = sum(1 for s in scores_list if s.class_label == "authentic")
        suspect_count = sum(1 for s in scores_list if s.class_label == "suspect")
        inauthentic_count = sum(1 for s in scores_list if s.class_label == "inauthentic")
        total_count = len(scores_list)
        
        # Calculate AR percentages
        core_ar = (authentic_count / total_count * 100) if total_count > 0 else 0.0
        extended_ar = ((authentic_count + 0.5 * suspect_count) / total_count * 100) if total_count > 0 else 0.0
        
        ar_result = {
            "brand_id": brand_id,
            "run_id": run_id,
            "total_items": total_count,
            "authentic_items": authentic_count,
            "suspect_items": suspect_count,
            "inauthentic_items": inauthentic_count,
            "authenticity_ratio_pct": core_ar,
            "extended_ar_pct": extended_ar
        }
        
        logger.info(f"AR Calculation for {brand_id}:")
        logger.info(f"  Total items: {total_count}")
        logger.info(f"  Authentic: {authentic_count} ({authentic_count/total_count*100:.1f}%)")
        logger.info(f"  Suspect: {suspect_count} ({suspect_count/total_count*100:.1f}%)")
        logger.info(f"  Inauthentic: {inauthentic_count} ({inauthentic_count/total_count*100:.1f}%)")
        logger.info(f"  Core AR: {core_ar:.2f}%")
        logger.info(f"  Extended AR: {extended_ar:.2f}%")
        
        return ar_result
    
    def get_pipeline_status(self, run_id: str) -> Optional[PipelineRun]:
        """Get status of a pipeline run"""
        # In production, this would query a database
        # For now, return None as we don't persist pipeline runs
        return None
    
    def list_recent_runs(self, brand_id: str, limit: int = 10) -> List[PipelineRun]:
        """List recent pipeline runs for a brand"""
        # In production, this would query a database
        # For now, return empty list
        return []
    
    def analyze_dimension_trends(self, brand_id: str, days: int = 30) -> Dict[str, Any]:
        """Analyze dimension score trends over time"""
        # This would query Athena for historical scores
        # For now, return placeholder analysis
        return {
            "brand_id": brand_id,
            "analysis_period_days": days,
            "trend_analysis": "Placeholder - implement Athena queries for historical data",
            "dimension_trends": {
                "provenance": {"trend": "stable", "average": 0.75},
                "verification": {"trend": "improving", "average": 0.68},
                "transparency": {"trend": "declining", "average": 0.72},
                "coherence": {"trend": "stable", "average": 0.70},
                "resonance": {"trend": "improving", "average": 0.65}
            }
        }
    
    def generate_scoring_report(self, scores_list: List[ContentScores], 
                              brand_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed scoring report"""
        if not scores_list:
            return {"error": "No scores to report on"}
        
        # Get classification analysis
        analysis = self.classifier.analyze_dimension_performance(scores_list)
        
        # Calculate AR
        ar_result = self._calculate_authenticity_ratio(
            scores_list, 
            brand_config.get('brand_id', 'unknown'),
            scores_list[0].run_id if scores_list else 'unknown'
        )
        
        # Generate dimension breakdown
        dimension_breakdown = {}
        for dimension in ["provenance", "verification", "transparency", "coherence", "resonance"]:
            scores = [getattr(s, f"score_{dimension}") for s in scores_list]
            dimension_breakdown[dimension] = {
                "average": sum(scores) / len(scores),
                "min": min(scores),
                "max": max(scores),
                "std_dev": self._calculate_std_dev(scores)
            }
        
        report = {
            "brand_id": brand_config.get('brand_id', 'unknown'),
            "run_id": scores_list[0].run_id if scores_list else 'unknown',
            "generated_at": datetime.now().isoformat(),
            "authenticity_ratio": ar_result,
            "classification_analysis": analysis,
            "dimension_breakdown": dimension_breakdown,
            "total_items_analyzed": len(scores_list),
            "rubric_version": scores_list[0].rubric_version if scores_list else "unknown"
        }
        
        return report
    
    def _calculate_std_dev(self, scores: List[float]) -> float:
        """Calculate standard deviation"""
        if len(scores) < 2:
            return 0.0
        
        mean = sum(scores) / len(scores)
        variance = sum((x - mean) ** 2 for x in scores) / (len(scores) - 1)
        return variance ** 0.5
