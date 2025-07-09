"""
Type definitions for political conflict analysis.

This module provides comprehensive type annotations and dataclasses
for all data structures used throughout the application.
"""

from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Any, Union
from datetime import datetime
from enum import Enum


class MatchType(Enum):
    """Types of conflicts that can be detected."""
    NAME = "name"
    EMPLOYER = "employer"


class VoteType(Enum):
    """Types of votes a politician can cast."""
    AYE = "AYE"
    NAY = "NAY"
    ABSTAIN = "ABSTAIN"
    ABSENT = "ABSENT"
    RECUSED = "RECUSED"


class VoteOutcome(Enum):
    """Outcomes of votes."""
    PASSED = "PASSED"
    FAILED = "FAILED"


@dataclass
class ContributionDetail:
    """Details of a campaign contribution."""
    name: str
    employer: Optional[str]
    amount: float
    date: str
    transaction_type: str
    
    def __post_init__(self) -> None:
        """Validate contribution data."""
        if self.amount < 0:
            raise ValueError("Contribution amount cannot be negative")
        if not self.name.strip():
            raise ValueError("Contributor name cannot be empty")


@dataclass
class VoteDetail:
    """Details of a politician's vote on an agenda item."""
    date: str
    vote: VoteType
    item: str
    outcome: VoteOutcome
    beneficiary: str
    
    def __post_init__(self) -> None:
        """Validate vote data."""
        if not self.item.strip():
            raise ValueError("Vote item description cannot be empty")
        if not self.beneficiary.strip():
            raise ValueError("Beneficiary cannot be empty")


@dataclass
class ConflictMatch:
    """A potential conflict of interest match."""
    beneficiary: str
    contributor: str
    similarity: float
    match_type: MatchType
    politician: str
    
    def __post_init__(self) -> None:
        """Validate conflict match data."""
        if not 0 <= self.similarity <= 100:
            raise ValueError("Similarity must be between 0 and 100")
        if not self.beneficiary.strip():
            raise ValueError("Beneficiary cannot be empty")
        if not self.contributor.strip():
            raise ValueError("Contributor cannot be empty")


@dataclass
class AggregatedConflict:
    """An aggregated conflict representing multiple related matches."""
    beneficiary: str
    original_beneficiaries: List[str]
    contributors: List[str]
    contributor_summary: str
    total_contributions: float
    contribution_count: int
    vote_count: int
    contribution_details: List[ContributionDetail]
    vote_details: List[VoteDetail]
    match_types: List[MatchType]
    avg_similarity: float
    max_similarity: float
    min_similarity: float
    politician: str
    
    def __post_init__(self) -> None:
        """Validate aggregated conflict data."""
        if self.total_contributions < 0:
            raise ValueError("Total contributions cannot be negative")
        if not 0 <= self.avg_similarity <= 100:
            raise ValueError("Average similarity must be between 0 and 100")


@dataclass
class SimilarityConfig:
    """Configuration for similarity calculations."""
    wratio_weight: float = 0.4
    partial_ratio_weight: float = 0.3
    token_sort_weight: float = 0.2
    token_set_weight: float = 0.1
    business_context_bonus: float = 5.0
    location_match_bonus: float = 3.0
    industry_match_bonus: float = 2.0
    
    def __post_init__(self) -> None:
        """Validate weights sum to 1.0."""
        total_weight = (
            self.wratio_weight + 
            self.partial_ratio_weight + 
            self.token_sort_weight + 
            self.token_set_weight
        )
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError("Similarity weights must sum to 1.0")


@dataclass
class APIConfig:
    """Configuration for external API calls."""
    api_key: str
    max_tokens: int = 4000
    temperature: float = 0.0
    timeout: float = 30.0
    max_retries: int = 3
    
    def __post_init__(self) -> None:
        """Validate API configuration."""
        if not self.api_key.strip():
            raise ValueError("API key cannot be empty")
        if self.max_tokens <= 0:
            raise ValueError("Max tokens must be positive")
        if not 0 <= self.temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2")


@dataclass
class AnalysisResult:
    """Result of a complete conflict analysis."""
    politician: str
    conflicts: List[AggregatedConflict]
    total_conflicts: int
    total_contribution_amount: float
    analysis_timestamp: datetime
    threshold_used: float
    
    def __post_init__(self) -> None:
        """Validate analysis result."""
        if self.total_conflicts != len(self.conflicts):
            raise ValueError("Total conflicts count doesn't match conflicts list length")
        if self.total_contribution_amount < 0:
            raise ValueError("Total contribution amount cannot be negative")


# Type aliases for complex types
EntityData = Dict[str, Any]
SimilarityScore = float
Threshold = float
FilePath = str
ReportData = Dict[str, Union[str, int, float, List[Any]]] 