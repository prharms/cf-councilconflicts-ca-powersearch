#!/usr/bin/env python3
"""
Test package for the Political Conflict Analysis project.

This package contains comprehensive test suites for all modules in the
Political Conflict Analysis system, ensuring robust functionality for
analyzing potential conflicts of interest between city council meeting
beneficiaries and campaign finance contributors.

Key test modules:
- test_data_processor: Tests for data loading and processing
- test_fuzzy_matcher: Tests for fuzzy matching algorithms
- test_report_generator: Tests for report generation
- test_similarity_calculator: Tests for similarity calculations

Usage:
    python -m pytest tests/
    python -m pytest tests/test_data_processor.py
    python -m pytest tests/test_fuzzy_matcher.py -v
"""

# No need for path manipulation with proper package structure

__version__ = "1.0.0"
__author__ = "Political Analysis Team"
__email__ = "analysis@city.gov" 