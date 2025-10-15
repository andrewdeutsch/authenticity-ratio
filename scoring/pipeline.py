"""
Scoring pipeline for AR tool
Orchestrates the scoring and classification process
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from data.models import NormalizedContent, ContentScores, PipelineRun, AuthenticityRatio
from data.athena_client import AthenaClient
from .scorer import ContentScorer
from .triage import triage_filter
from config.settings import SETTINGS
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
            triage_enabled = SETTINGS.get('triage_enabled', True)
            exclude_demoted = SETTINGS.get('exclude_demoted_from_upload', False)

            if triage_enabled:
                logger.info("Step 1: Running triage filter to reduce expensive scoring")
                promoted, demoted = triage_filter(content_list, brand_config.get('keywords', []), promote_threshold=None)

                # Step 2: Score promoted items with the high-quality LLM scorer
                logger.info("Step 2: Scoring promoted content on 5D dimensions")
                high_quality_scores = self.scorer.batch_score_content(promoted, brand_config) if promoted else []
                pipeline_run.items_processed += len(high_quality_scores)

                if exclude_demoted:
                    # If configured, exclude demoted items from uploads/reports
                    scores_list = high_quality_scores
                else:
                    # Create neutral ContentScores for demoted items to keep them in reports
                    neutral_scores = []
                    for c in demoted:
                        neutral = ContentScores(
                            content_id=c.content_id,
                            brand=brand_config.get('brand_id', 'unknown'),
                            src=c.src,
                            event_ts=c.event_ts,
                            score_provenance=0.5,
                            score_resonance=0.5,
                            score_coherence=0.5,
                            score_transparency=0.5,
                            score_verification=0.5,
                            class_label='pending',
                            is_authentic=False,
                            rubric_version=self.scorer.rubric_version,
                            run_id=run_id,
                            meta='{"triage": "demoted"}'
                        )
                        neutral_scores.append(neutral)

                    # Combine high-quality scores with neutral demoted scores for classification/upload
                    scores_list = high_quality_scores + neutral_scores
            else:
                # Triage disabled: run full scoring on all items
                logger.info("Triage disabled; scoring all content on 5D dimensions")
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
            
            # Attach classified scores to the pipeline run so callers can use
            # the exact objects that were uploaded to S3/Athena.
            pipeline_run.classified_scores = classified_scores

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
                                    brand_id: str, run_id: str) -> AuthenticityRatio:
        """Calculate Authenticity Ratio from scores and return an AuthenticityRatio dataclass"""
        if not scores_list:
            logger.info(f"AR Calculation for {brand_id}: no scores")
            return AuthenticityRatio(
                brand_id=brand_id,
                source=",",
                run_id=run_id,
                total_items=0,
                authentic_items=0,
                suspect_items=0,
                inauthentic_items=0,
                authenticity_ratio_pct=0.0
            )

        # Count classifications
        authentic_count = sum(1 for s in scores_list if s.class_label == "authentic")
        suspect_count = sum(1 for s in scores_list if s.class_label == "suspect")
        inauthentic_count = sum(1 for s in scores_list if s.class_label == "inauthentic")
        total_count = len(scores_list)

        # Calculate AR percentages
        core_ar = (authentic_count / total_count * 100) if total_count > 0 else 0.0

        # Build source string from unique sources in the scores list
        sources = sorted({s.src for s in scores_list})
        source_str = ",".join(sources) if sources else ""

        logger.info(f"AR Calculation for {brand_id}:")
        logger.info(f"  Total items: {total_count}")
        logger.info(f"  Authentic: {authentic_count} ({(authentic_count/total_count*100) if total_count else 0:.1f}%)")
        logger.info(f"  Suspect: {suspect_count} ({(suspect_count/total_count*100) if total_count else 0:.1f}%)")
        logger.info(f"  Inauthentic: {inauthentic_count} ({(inauthentic_count/total_count*100) if total_count else 0:.1f}%)")
        logger.info(f"  Core AR: {core_ar:.2f}%")

        return AuthenticityRatio(
            brand_id=brand_id,
            source=source_str,
            run_id=run_id,
            total_items=total_count,
            authentic_items=authentic_count,
            suspect_items=suspect_count,
            inauthentic_items=inauthentic_count,
            authenticity_ratio_pct=core_ar
        )
    
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
        # If no scores are provided, return a structured report with zeros so
        # callers don't need to handle a special error case.
        if not scores_list:
            ar_zero = {
                'brand_id': brand_config.get('brand_id', 'unknown'),
                'run_id': 'unknown',
                'total_items': 0,
                'authentic_items': 0,
                'suspect_items': 0,
                'inauthentic_items': 0,
                'authenticity_ratio_pct': 0.0,
                'extended_ar_pct': 0.0
            }

            return {
                "brand_id": brand_config.get('brand_id', 'unknown'),
                "run_id": 'unknown',
                "generated_at": datetime.now().isoformat(),
                "authenticity_ratio": ar_zero,
                "classification_analysis": {},
                "dimension_breakdown": {},
                "total_items_analyzed": 0,
                "rubric_version": "unknown"
            }
        
        # Get classification analysis
        analysis = self.classifier.analyze_dimension_performance(scores_list)
        
        # Calculate AR
        ar_result = self._calculate_authenticity_ratio(
            scores_list, 
            brand_config.get('brand_id', 'unknown'),
            scores_list[0].run_id if scores_list else 'unknown'
        )

        # Reporting expects a dict-like structure (with .get). If we returned
        # an AuthenticityRatio dataclass, convert it to a dict with the
        # previous keys including extended_ar_pct.
        if hasattr(ar_result, '__dict__'):
            ar_dict = {
                'brand_id': ar_result.brand_id,
                'run_id': ar_result.run_id,
                'total_items': ar_result.total_items,
                'authentic_items': ar_result.authentic_items,
                'suspect_items': ar_result.suspect_items,
                'inauthentic_items': ar_result.inauthentic_items,
                'authenticity_ratio_pct': ar_result.authenticity_ratio_pct,
                'extended_ar_pct': ar_result.extended_ar
            }
        else:
            ar_dict = ar_result
        
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
            "authenticity_ratio": ar_dict,
            "classification_analysis": analysis,
            "dimension_breakdown": dimension_breakdown,
            "total_items_analyzed": len(scores_list),
            # Include data sources used for this report (prefer explicit brand_config, fallback to sources present on scores)
            "sources": brand_config.get('sources') if brand_config.get('sources') else sorted({s.src for s in scores_list}),
            "rubric_version": scores_list[0].rubric_version if scores_list else "unknown"
        }

        # Compute a content-type breakdown (percentage) using meta JSON where available
        content_type_counts = {}
        total = 0
        for s in scores_list:
            total += 1
            try:
                # meta might be a JSON string or dict depending on upstream. Try to parse
                meta = s.meta
                if isinstance(meta, str):
                    import json as _json
                    meta_obj = _json.loads(meta) if meta else {}
                elif isinstance(meta, dict):
                    meta_obj = meta
                else:
                    meta_obj = {}

                ctype = meta_obj.get('content_type') or getattr(s, 'content_type', None) or 'unknown'
            except Exception:
                ctype = 'unknown'

            content_type_counts[ctype] = content_type_counts.get(ctype, 0) + 1

        # Convert to percentage breakdown
        content_type_pct = {k: (v / total * 100.0) for k, v in content_type_counts.items()} if total > 0 else {}
        report['content_type_breakdown_pct'] = content_type_pct
        
        return report
    
    def _calculate_std_dev(self, scores: List[float]) -> float:
        """Calculate standard deviation"""
        if len(scores) < 2:
            return 0.0
        
        mean = sum(scores) / len(scores)
        variance = sum((x - mean) ** 2 for x in scores) / (len(scores) - 1)
        return variance ** 0.5
