#!/usr/bin/env python3
"""
Main entry point for the political conflict analysis package.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Import from the installed package using relative imports
from .types import SimilarityConfig, APIConfig
from .matchers import FuzzyMatcher
from .validators import ClaudeValidator
from .normalizers import EntityNormalizer
from .processors import ConflictDataProcessor
from .analyzers import ConflictAnalyzer
from .report_generator import ConflictReportGenerator


def setup_logging(log_level: str = 'INFO') -> None:
    """
    Configure logging for the application.
    
    Args:
        log_level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('conflict_analysis.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def load_api_key() -> str:
    """
    Load API key from .env file.
    
    Returns:
        Claude API key
        
    Raises:
        ValueError: If API key is not found
    """
    # Load environment variables from .env file
    load_dotenv()
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError(
            "Anthropic API key not found. Please add ANTHROPIC_API_KEY to your .env file."
        )
    return api_key


def create_components(api_key: str, threshold: float) -> tuple:
    """
    Create and configure all analysis components.
    
    Args:
        api_key: Claude API key
        threshold: Similarity threshold for matching
        
    Returns:
        Tuple of (analyzer, report_generator) components
    """
    # Create configuration objects
    similarity_config = SimilarityConfig(
        wratio_weight=0.4,
        partial_ratio_weight=0.3,
        token_sort_weight=0.2,
        token_set_weight=0.1,
        business_context_bonus=5.0,
        location_match_bonus=3.0,
        industry_match_bonus=2.0
    )
    
    api_config = APIConfig(
        api_key=api_key,
        max_tokens=4000,
        temperature=0.0,
        timeout=30.0,
        max_retries=3
    )
    
    # Create individual components
    fuzzy_matcher = FuzzyMatcher(similarity_config)
    claude_validator = ClaudeValidator(api_config)
    entity_normalizer = EntityNormalizer()
    data_processor = ConflictDataProcessor()
    
    # Create main analyzer with dependency injection
    analyzer = ConflictAnalyzer(
        fuzzy_matcher=fuzzy_matcher,
        claude_validator=claude_validator,
        entity_normalizer=entity_normalizer,
        data_processor=data_processor
    )
    
    # Create report generator
    report_generator = ConflictReportGenerator()
    
    return analyzer, report_generator


def main() -> None:
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description=(
            'Analyze potential conflicts of interest between political votes and campaign contributions. '
            'This analysis identifies potential conflicts of interest by systematically examining '
            'overlapping relationships between vote beneficiaries and campaign contributors. '
            'Results represent patterns that warrant further investigation, not determinations of wrongdoing.'
        )
    )
    parser.add_argument(
        '--minutes', 
        required=True,
        help='Path to minutes CSV file'
    )
    parser.add_argument(
        '--campaign-finance', 
        required=True,
        help='Path to campaign finance CSV file'
    )
    parser.add_argument(
        '--threshold', 
        type=float, 
        default=85.0,
        help='Similarity threshold for matching (default: 85.0)'
    )
    parser.add_argument(
        '--output-dir', 
        default='output',
        help='Output directory for reports (default: output)'
    )
    parser.add_argument(
        '--log-level', 
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    parser.add_argument(
        '--test-api', 
        action='store_true',
        help='Test API connection and exit'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Load API key (always required)
        api_key = load_api_key()
        
        # Create components
        analyzer, report_generator = create_components(api_key, args.threshold)
        
        # Test API connection if requested
        if args.test_api:
            logger.info("Testing API connection...")
            if analyzer.claude_validator.test_api_connection():
                logger.info("API connection successful!")
                sys.exit(0)
            else:
                logger.error("API connection failed!")
                sys.exit(1)
        
        # Validate input files
        minutes_path = Path(args.minutes)
        campaign_finance_path = Path(args.campaign_finance)
        
        if not minutes_path.exists():
            raise FileNotFoundError(f"Minutes file not found: {args.minutes}")
        
        if not campaign_finance_path.exists():
            raise FileNotFoundError(f"Campaign finance file not found: {args.campaign_finance}")
        
        # Create output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Perform analysis
        logger.info("Starting conflict analysis...")
        logger.info(f"Minutes file: {args.minutes}")
        logger.info(f"Campaign finance file: {args.campaign_finance}")
        logger.info(f"Threshold: {args.threshold}")
        logger.info(f"AI validation: True")
        
        result = analyzer.analyze_conflicts(
            minutes_file=str(minutes_path),
            campaign_finance_file=str(campaign_finance_path),
            threshold=args.threshold,
            validate_with_ai=True
        )
        
        # Generate reports
        logger.info("Generating reports...")
        
        # Generate summary report
        summary_path = output_dir / f"{result.politician.lower()}_conflicts_summary.txt"
        report_generator.generate_summary_report(result, str(summary_path))
        
        # Generate detailed report
        detailed_path = output_dir / f"{result.politician.lower()}_conflicts_detailed.txt"
        report_generator.generate_detailed_report(result, str(detailed_path))
        
        # Generate CSV report
        csv_path = output_dir / f"{result.politician.lower()}_conflicts.csv"
        report_generator.generate_csv_report(result, str(csv_path))
        
        logger.info("Analysis complete!")
        logger.info(f"Reports saved to: {output_dir}")
        logger.info(f"Found {len(result.conflicts)} potential conflicts")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 