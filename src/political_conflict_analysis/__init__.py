"""
Political Conflict Analysis Package

A comprehensive tool for analyzing potential conflicts of interest between
political officials' votes and campaign finance contributions.
"""

from .types import ConflictMatch, ContributionDetail, VoteDetail
from .matchers import FuzzyMatcher
from .validators import ClaudeValidator  
from .processors import ConflictDataProcessor
from .normalizers import EntityNormalizer
from .analyzers import ConflictAnalyzer
from .report_generator import ConflictReportGenerator
from .__main__ import main

__version__ = "1.0.0"
__author__ = "Political Analysis Team"

__all__ = [
    "ConflictMatch",
    "ContributionDetail", 
    "VoteDetail",
    "FuzzyMatcher",
    "ClaudeValidator",
    "ConflictDataProcessor",
    "EntityNormalizer",
    "ConflictAnalyzer",
    "ConflictReportGenerator",
    "main",
] 