"""
Conflict analysis orchestration for political conflict detection.

This module provides the main analysis orchestration that coordinates
between different components to detect and analyze potential conflicts of interest.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .types import (
    ConflictMatch, AggregatedConflict, AnalysisResult, 
    SimilarityConfig, APIConfig, ContributionDetail, VoteDetail,
    VoteType, VoteOutcome, MatchType
)
from .matchers import FuzzyMatcher
from .validators import ClaudeValidator
from .normalizers import EntityNormalizer
from .processors import ConflictDataProcessor


class ConflictAnalyzer:
    """
    Main orchestrator for conflict analysis.
    
    This class is responsible for:
    - Coordinating between different analysis components
    - Managing the overall analysis workflow
    - Aggregating results from different stages
    - Providing a high-level interface for analysis
    """
    
    def __init__(
        self, 
        fuzzy_matcher: FuzzyMatcher,
        claude_validator: ClaudeValidator,
        entity_normalizer: EntityNormalizer,
        data_processor: ConflictDataProcessor
    ):
        """
        Initialize the conflict analyzer with dependencies.
        
        Args:
            fuzzy_matcher: Fuzzy matching component
            claude_validator: AI validation component
            entity_normalizer: Entity normalization component
            data_processor: Data processing component
        """
        self.fuzzy_matcher = fuzzy_matcher
        self.claude_validator = claude_validator
        self.entity_normalizer = entity_normalizer
        self.data_processor = data_processor
        self.logger = logging.getLogger(__name__)
    
    def analyze_conflicts(
        self, 
        minutes_file: str, 
        campaign_finance_file: str, 
        threshold: float = 80.0,
        validate_with_ai: bool = True
    ) -> AnalysisResult:
        """
        Perform complete conflict analysis.
        
        Args:
            minutes_file: Path to minutes CSV file
            campaign_finance_file: Path to campaign finance CSV file
            threshold: Similarity threshold for matching
            validate_with_ai: Whether to validate with Claude AI
            
        Returns:
            Complete analysis result
        """
        start_time = datetime.now()
        
        try:
            # Load and process data
            self.logger.info("Loading data files...")
            minutes_data = self.data_processor.load_minutes_data(minutes_file)
            campaign_finance_data = self.data_processor.load_campaign_finance_data(campaign_finance_file)
            
            # Find initial matches
            self.logger.info("Finding potential matches...")
            initial_matches = self._find_initial_matches(
                minutes_data, 
                campaign_finance_data, 
                threshold
            )
            
            # Aggregate related matches
            self.logger.info("Aggregating related matches...")
            aggregated_conflicts = self._aggregate_conflicts(
                initial_matches, 
                minutes_data, 
                campaign_finance_data
            )
            
            # Validate with AI if requested
            if validate_with_ai and aggregated_conflicts:
                self.logger.info("Validating conflicts with AI...")
                validated_conflicts = self._validate_conflicts(aggregated_conflicts)
            else:
                validated_conflicts = aggregated_conflicts
            
            # Calculate totals
            total_contribution_amount = sum(
                conflict.total_contributions for conflict in validated_conflicts
            )
            
            # Create result
            result = AnalysisResult(
                politician=self._extract_politician_name(minutes_data),
                conflicts=validated_conflicts,
                total_conflicts=len(validated_conflicts),
                total_contribution_amount=total_contribution_amount,
                analysis_timestamp=start_time,
                threshold_used=threshold
            )
            
            self.logger.info(
                f"Analysis complete. Found {len(validated_conflicts)} conflicts "
                f"totaling ${total_contribution_amount:,.2f}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {str(e)}")
            raise
    
    def _find_initial_matches(
        self, 
        minutes_data: List[Dict], 
        campaign_finance_data: List[Dict], 
        threshold: float
    ) -> List[ConflictMatch]:
        """Find initial conflict matches using fuzzy matching."""
        matches = []
        
        # Extract unique beneficiaries from minutes
        beneficiaries = set()
        excluded_terms = ['city of', 'county of', 'college', 'university']
        
        for row in minutes_data:
            if row.get('Beneficiary'):
                beneficiary = row['Beneficiary']
                # Check if beneficiary should be excluded
                beneficiary_lower = beneficiary.lower()
                should_exclude = any(term in beneficiary_lower for term in excluded_terms)
                
                if not should_exclude:
                    beneficiaries.add(beneficiary)
                else:
                    self.logger.info(f"Excluding beneficiary: {beneficiary}")
        
        # Extract contributor names AND employer names from campaign finance
        entities_to_check = []
        for row in campaign_finance_data:
            if row.get('Contributor'):
                entities_to_check.append(row['Contributor'])
            if row.get('Employer'):
                entities_to_check.append(row['Employer'])
        
        # Find matches for each beneficiary
        politician = self._extract_politician_name(minutes_data)
        for beneficiary in beneficiaries:
            beneficiary_matches = self.fuzzy_matcher.find_matches(
                beneficiary, 
                entities_to_check, 
                threshold,
                politician
            )
            matches.extend(beneficiary_matches)
        
        return matches
    
    def _aggregate_conflicts(
        self, 
        matches: List[ConflictMatch], 
        minutes_data: List[Dict], 
        campaign_finance_data: List[Dict]
    ) -> List[AggregatedConflict]:
        """Aggregate related matches into consolidated conflicts."""
        if not matches:
            return []
        
        # Group matches by beneficiary using entity normalization
        beneficiary_groups = {}
        all_beneficiaries = [match.beneficiary for match in matches]
        entity_groups = self.entity_normalizer.group_related_entities(all_beneficiaries)
        
        # Create mapping from original to canonical names
        beneficiary_to_canonical = {}
        for group in entity_groups:
            canonical_name = group.canonical_name
            for original_name in group.original_names:
                beneficiary_to_canonical[original_name] = canonical_name
        
        # Group matches by canonical beneficiary
        canonical_groups = {}
        for match in matches:
            canonical_name = beneficiary_to_canonical.get(match.beneficiary, match.beneficiary)
            if canonical_name not in canonical_groups:
                canonical_groups[canonical_name] = []
            canonical_groups[canonical_name].append(match)
        
        # Create aggregated conflicts
        aggregated_conflicts = []
        for canonical_name, group_matches in canonical_groups.items():
            conflict = self._create_aggregated_conflict(
                canonical_name, 
                group_matches, 
                minutes_data, 
                campaign_finance_data
            )
            aggregated_conflicts.append(conflict)
        
        return aggregated_conflicts
    
    def _create_aggregated_conflict(
        self, 
        canonical_beneficiary: str, 
        matches: List[ConflictMatch], 
        minutes_data: List[Dict], 
        campaign_finance_data: List[Dict]
    ) -> AggregatedConflict:
        """Create an aggregated conflict from individual matches."""
        # Get all related data
        original_beneficiaries = list(set(match.beneficiary for match in matches))
        contributors = list(set(match.contributor for match in matches))
        
        # Find contribution details
        contribution_details = []
        for contributor in contributors:
            for row in campaign_finance_data:
                # Check if match is against contributor name OR employer name
                if row.get('Contributor') == contributor or row.get('Employer') == contributor:
                    try:
                        contribution_details.append(ContributionDetail(
                            name=row['Contributor'],
                            employer=row.get('Employer'),
                            amount=float(row.get('Amount', 0)),
                            date=row.get('Date', ''),
                            transaction_type=row.get('Transaction Type', '')
                        ))
                    except ValueError:
                        continue
        
        # Find vote details
        vote_details = []
        for beneficiary in original_beneficiaries:
            for row in minutes_data:
                if row.get('Beneficiary') == beneficiary:
                    try:
                        vote_details.append(VoteDetail(
                            date=row.get('Date', ''),
                            vote=VoteType(row.get('Vote', 'AYE')),
                            item=row.get('Item', ''),
                            outcome=VoteOutcome(row.get('Outcome', 'PASSED')),
                            beneficiary=beneficiary
                        ))
                    except ValueError:
                        continue
        
        # Calculate aggregated metrics
        total_contributions = sum(detail.amount for detail in contribution_details)
        similarities = [match.similarity for match in matches]
        match_types = list(set(match.match_type for match in matches))
        
        # Create contributor summary
        contributor_summary = self._create_contributor_summary(contributors, contribution_details)
        
        return AggregatedConflict(
            beneficiary=canonical_beneficiary,
            original_beneficiaries=original_beneficiaries,
            contributors=contributors,
            contributor_summary=contributor_summary,
            total_contributions=total_contributions,
            contribution_count=len(contribution_details),
            vote_count=len(vote_details),
            contribution_details=contribution_details,
            vote_details=vote_details,
            match_types=match_types,
            avg_similarity=sum(similarities) / len(similarities),
            max_similarity=max(similarities),
            min_similarity=min(similarities),
            politician=matches[0].politician if matches else ""
        )
    
    def _create_contributor_summary(
        self, 
        contributors: List[str], 
        contribution_details: List[ContributionDetail]
    ) -> str:
        """Create a summary string for contributors."""
        if not contributors:
            return ""
        
        if len(contributors) == 1:
            return contributors[0]
        
        # Group by employer for summary
        employer_groups = {}
        for detail in contribution_details:
            employer = detail.employer or "Individual"
            if employer not in employer_groups:
                employer_groups[employer] = []
            employer_groups[employer].append(detail.name)
        
        # Create summary
        summary_parts = []
        for employer, names in employer_groups.items():
            if employer == "Individual":
                summary_parts.append(f"{len(names)} individual contributor(s)")
            else:
                summary_parts.append(f"{len(names)} from {employer}")
        
        return "; ".join(summary_parts)
    
    def _validate_conflicts(self, conflicts: List[AggregatedConflict]) -> List[AggregatedConflict]:
        """Validate conflicts using Claude AI."""
        if not conflicts:
            return []
        
        validation_results = self.claude_validator.validate_conflicts_batch(conflicts)
        validated_conflicts = []
        
        for conflict, (is_genuine, confidence, reasoning) in zip(conflicts, validation_results):
            if is_genuine:
                validated_conflicts.append(conflict)
            else:
                self.logger.info(
                    f"Filtered out false positive: {conflict.beneficiary} "
                    f"(Confidence: {confidence}, Reason: {reasoning})"
                )
        
        return validated_conflicts
    
    def _extract_politician_name(self, minutes_data: List[Dict]) -> str:
        """Extract politician name from minutes data."""
        for row in minutes_data:
            if row.get('Politician'):
                return row['Politician']
        return "Unknown"
    
    def get_analysis_summary(self, result: AnalysisResult) -> Dict[str, any]:
        """
        Get a summary of the analysis results.
        
        Args:
            result: Analysis result to summarize
            
        Returns:
            Summary dictionary
        """
        if not result.conflicts:
            return {
                'politician': result.politician,
                'total_conflicts': 0,
                'total_contribution_amount': 0.0,
                'analysis_timestamp': result.analysis_timestamp.isoformat(),
                'threshold_used': result.threshold_used,
                'conflicts_by_amount': [],
                'top_contributors': []
            }
        
        # Sort conflicts by contribution amount
        conflicts_by_amount = sorted(
            result.conflicts,
            key=lambda x: x.total_contributions,
            reverse=True
        )
        
        # Get top contributors
        all_contributors = []
        for conflict in result.conflicts:
            all_contributors.extend(conflict.contribution_details)
        
        top_contributors = sorted(
            all_contributors,
            key=lambda x: x.amount,
            reverse=True
        )[:10]
        
        return {
            'politician': result.politician,
            'total_conflicts': result.total_conflicts,
            'total_contribution_amount': result.total_contribution_amount,
            'analysis_timestamp': result.analysis_timestamp.isoformat(),
            'threshold_used': result.threshold_used,
            'conflicts_by_amount': [
                {
                    'beneficiary': conflict.beneficiary,
                    'amount': conflict.total_contributions,
                    'contributor_count': len(conflict.contributors)
                }
                for conflict in conflicts_by_amount
            ],
            'top_contributors': [
                {
                    'name': contrib.name,
                    'employer': contrib.employer,
                    'amount': contrib.amount
                }
                for contrib in top_contributors
            ]
        } 