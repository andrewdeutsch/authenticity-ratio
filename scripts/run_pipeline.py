#!/usr/bin/env python3
"""
Main pipeline runner script for AR tool
Executes the complete AR analysis pipeline
"""

import sys
import os
import argparse
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logging_config import setup_logging
from utils.helpers import generate_run_id, validate_config
from ingestion.reddit_crawler import RedditCrawler
from ingestion.amazon_scraper import AmazonScraper
from ingestion.youtube_scraper import YouTubeScraper
from ingestion.normalizer import ContentNormalizer
from scoring.pipeline import ScoringPipeline
from reporting.pdf_generator import PDFReportGenerator
from reporting.markdown_generator import MarkdownReportGenerator
from data.athena_client import AthenaClient
from config.settings import APIConfig
import sys

logger = logging.getLogger(__name__)

# Import reddit auth helper
from ingestion.reddit_auth import obtain_token

def main():
    """Main pipeline execution function"""
    parser = argparse.ArgumentParser(description='Run AR analysis pipeline')
    parser.add_argument('--brand-id', required=True, help='Brand ID to analyze')
    parser.add_argument('--brand-name', help='Brand name (defaults to brand-id)')
    parser.add_argument('--keywords', nargs='+', required=True, help='Brand keywords to search for')
    parser.add_argument('--sources', nargs='+', default=['reddit', 'amazon'], help='Data sources to use')
    parser.add_argument('--output-dir', default='./output', help='Output directory for reports')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--dry-run', action='store_true', help='Run without making API calls or uploading data')
    parser.add_argument('--max-content', type=int, default=1000, help='Maximum content items to process')
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = os.path.join(args.output_dir, 'logs', f'ar_pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    setup_logging(log_level=args.log_level, log_file=log_file)
    
    logger.info("Starting AR analysis pipeline")
    logger.info(f"Brand ID: {args.brand_id}")
    logger.info(f"Keywords: {args.keywords}")
    logger.info(f"Sources: {args.sources}")
    logger.info(f"Max content: {args.max_content}")
    logger.info(f"Dry run: {args.dry_run}")
    
    try:
        # Validate configuration
        logger.info("Validating configuration...")
        config_issues = validate_config()
        if config_issues:
            logger.warning(f"Configuration issues found: {config_issues}")
        
        # Validate API credentials for selected sources
        def _missing_keys_for_source(sources_list):
            missing = {}
            cfg = APIConfig()
            if 'reddit' in sources_list:
                if not cfg.reddit_client_id or not cfg.reddit_client_secret:
                    missing['reddit'] = ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET']
            if 'youtube' in sources_list:
                if not cfg.youtube_api_key:
                    missing['youtube'] = ['YOUTUBE_API_KEY']
            if 'amazon' in sources_list:
                if not cfg.amazon_access_key or not cfg.amazon_secret_key:
                    missing['amazon'] = ['AMAZON_ACCESS_KEY', 'AMAZON_SECRET_KEY']
            if 'yelp' in sources_list:
                # Yelp Fusion uses a single API Key
                if not os.getenv('YELP_API_KEY'):
                    missing['yelp'] = ['YELP_API_KEY']
            return missing

        missing = _missing_keys_for_source(args.sources)
        if missing:
            for src, keys in missing.items():
                logger.error(f"Missing API keys for source '{src}': {', '.join(keys)}")
            logger.error("Please set the required environment variables (e.g., in .env) and retry.")
            sys.exit(2)
        
        # Generate run ID
        run_id = generate_run_id()
        logger.info(f"Generated run ID: {run_id}")
        
        # Create output directory
        os.makedirs(args.output_dir, exist_ok=True)
        
        # Setup brand configuration
        brand_config = {
            'brand_id': args.brand_id,
            'brand_name': args.brand_name or args.brand_id,
            'keywords': args.keywords,
            'sources': args.sources
        }
        
        # Initialize components
        logger.info("Initializing pipeline components...")
        # Obtain Reddit token early (if reddit is in sources and not a dry run)
        if 'reddit' in args.sources and not args.dry_run:
            token, resp = obtain_token()
            if token:
                logger.info("Obtained Reddit access token for pipeline (masked)")
            else:
                logger.warning(f"Could not obtain Reddit token: {resp}")
                # Proceeding without token will cause Reddit ingestion to fail later; exit early
                logger.error("Reddit authentication failed; aborting pipeline.")
                sys.exit(3)
        if not args.dry_run:
            athena_client = AthenaClient()
            reddit_crawler = RedditCrawler()
            amazon_scraper = AmazonScraper()
            youtube_scraper = YouTubeScraper()
        else:
            athena_client = None
            reddit_crawler = None
            amazon_scraper = None
            youtube_scraper = None
        
        normalizer = ContentNormalizer()
        scoring_pipeline = ScoringPipeline()
        pdf_generator = PDFReportGenerator()
        markdown_generator = MarkdownReportGenerator()
        
        # Step 1: Data Ingestion
        logger.info("Step 1: Data Ingestion")
        all_content = []
        
        if 'reddit' in args.sources:
            logger.info("Ingesting Reddit data...")
            if not args.dry_run:
                reddit_posts = reddit_crawler.search_posts(
                    keywords=args.keywords,
                    limit=args.max_content // len(args.sources)
                )
                reddit_content = reddit_crawler.convert_to_normalized_content(
                    reddit_posts, args.brand_id, run_id
                )
                all_content.extend(reddit_content)
                logger.info(f"Retrieved {len(reddit_content)} Reddit content items")
            else:
                logger.info("Dry run: Skipping Reddit ingestion")
        
        if 'amazon' in args.sources:
            logger.info("Ingesting Amazon data...")
            if not args.dry_run:
                # mock_reviews_for_demo signature = (brand_keywords: List[str], num_reviews: int = 50)
                amazon_reviews = amazon_scraper.mock_reviews_for_demo(
                    args.keywords,
                    num_reviews=args.max_content // len(args.sources)
                )
                amazon_content = amazon_scraper.convert_to_normalized_content(
                    amazon_reviews, args.brand_id, run_id
                )
                all_content.extend(amazon_content)
                logger.info(f"Retrieved {len(amazon_content)} Amazon content items")
            else:
                logger.info("Dry run: Skipping Amazon ingestion")

        if 'youtube' in args.sources:
            logger.info("Ingesting YouTube data...")
            if not args.dry_run:
                # Build a search query from keywords
                query = ' '.join(args.keywords)
                videos = youtube_scraper.search_videos(query=query, max_results=args.max_content // len(args.sources))
                youtube_content = youtube_scraper.convert_videos_to_normalized(videos, args.brand_id, run_id)
                all_content.extend(youtube_content)
                logger.info(f"Retrieved {len(youtube_content)} YouTube content items")
            else:
                logger.info("Dry run: Skipping YouTube ingestion")
        
        if not all_content:
            logger.warning("No content retrieved from any source")
            return
        
        # Step 2: Content Normalization
        logger.info("Step 2: Content Normalization")
        normalized_content = normalizer.normalize_content(all_content)
        logger.info(f"Normalized {len(normalized_content)} content items")
        
        # Step 3: Upload normalized content to S3/Athena
        if not args.dry_run and athena_client:
            logger.info("Uploading normalized content to S3/Athena...")
            for source in args.sources:
                source_content = [c for c in normalized_content if c.src == source]
                if source_content:
                    athena_client.upload_normalized_content(
                        source_content, args.brand_id, source, run_id
                    )
        
        # Step 4: Content Scoring and Classification
        logger.info("Step 3: Content Scoring and Classification")
        pipeline_run = scoring_pipeline.run_scoring_pipeline(
            normalized_content, brand_config
        )
        
        # Step 5: Generate Reports
        logger.info("Step 4: Generating Reports")

        # Use the classified scores produced by the scoring pipeline for report
        # generation. This ensures the report reflects the actual classifications
        # that were uploaded to S3/Athena.
        scores_list = pipeline_run.classified_scores or []

        # Generate scoring report
        scoring_report = scoring_pipeline.generate_scoring_report(scores_list, brand_config)
        
        # Generate PDF report
        pdf_path = os.path.join(args.output_dir, f'ar_report_{args.brand_id}_{run_id}.pdf')
        pdf_generator.generate_report(scoring_report, pdf_path)
        logger.info(f"Generated PDF report: {pdf_path}")
        
        # Generate Markdown report
        md_path = os.path.join(args.output_dir, f'ar_report_{args.brand_id}_{run_id}.md')
        markdown_generator.generate_report(scoring_report, md_path)
        logger.info(f"Generated Markdown report: {md_path}")
        
        # Pipeline completion
        logger.info("Pipeline completed successfully!")
        logger.info(f"Run ID: {run_id}")
        logger.info(f"Total content processed: {len(normalized_content)}")
        logger.info(f"Reports generated in: {args.output_dir}")
        
        if not args.dry_run:
            logger.info(f"Data uploaded to S3/Athena for brand: {args.brand_id}")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    main()
