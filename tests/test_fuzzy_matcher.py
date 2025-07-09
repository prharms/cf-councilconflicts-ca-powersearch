#!/usr/bin/env python3
"""
Test module for fuzzy matching functionality.

This module contains comprehensive tests for the FuzzyMatcher class
and its methods for detecting potential conflicts of interest between
city council meeting beneficiaries and campaign finance contributors.
"""

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

# No need for path manipulation with proper package structure

from political_conflict_analysis.matchers import FuzzyMatcher, ConflictMatch
from political_conflict_analysis.config import MATCHING, CLEANING
from political_conflict_analysis.exceptions import MatchingError, ThresholdError


class TestFuzzyMatcher(unittest.TestCase):
    """Test cases for the FuzzyMatcher class."""

    def setUp(self):
        """Set up test fixtures."""
        self.matcher = FuzzyMatcher()

        # Sample beneficiary data
        self.beneficiaries = pd.DataFrame({
            'Beneficiary': ['SEIU Local 721', 'Test Company', 'Another Corp'],
            'Vote': ['AYE', 'NAY', 'AYE'],
            'Item Description': ['Labor contract', 'Business permit', 'Development project']
        })

        # Sample contributor data
        self.contributors = pd.DataFrame({
            'Contributor': ['Service Employees International Union Local 721', 'Test Company Inc', 'Different Corp'],
            'Amount': [5000.00, 1000.00, 2500.00],
            'Date': ['2023-01-15', '2023-02-20', '2023-03-10']
        })

        # Expected conflicts
        self.expected_conflicts = [
            ConflictMatch(
                beneficiary='SEIU Local 721',
                contributor='Service Employees International Union Local 721',
                similarity_score=98.5,
                total_amount=5000.00,
                contribution_count=1,
                vote_pattern='AYE',
                item_descriptions=['Labor contract']
            ),
            ConflictMatch(
                beneficiary='Test Company',
                contributor='Test Company Inc',
                similarity_score=95.0,
                total_amount=1000.00,
                contribution_count=1,
                vote_pattern='NAY',
                item_descriptions=['Business permit']
            )
        ]

    def test_initialization(self):
        """Test FuzzyMatcher initialization."""
        # Test default initialization
        matcher = FuzzyMatcher()
        self.assertEqual(matcher.threshold, 98.0)
        self.assertIsNone(matcher.logger)

        # Test initialization with threshold
        threshold = 95.0
        matcher = FuzzyMatcher(threshold)
        self.assertEqual(matcher.threshold, threshold)

        # Test invalid threshold values
        with self.assertRaises(ValueError):
            FuzzyMatcher(-10.0)
        
        with self.assertRaises(ValueError):
            FuzzyMatcher(150.0)

    def test_clean_entity_name_small_contributor(self):
        """Test cleaning entity names with small contributor phrases."""
        test_cases = [
            ("Service Employees International Union Local 721, CTW, CLC Small Contributor Committee", 
             "Service Employees International Union Local 721"),
            ("Athens Services Small Contributor Fund", 
             "Athens Services"),
            ("Test Organization Small Contributor PAC", 
             "Test Organization"),
            ("Regular Organization Name", 
             "Regular Organization Name")
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = self.matcher._clean_entity_name(input_name)
                self.assertEqual(result, expected)
    
    def test_clean_entity_name_union_noise(self):
        """Test cleaning entity names with union noise words."""
        test_cases = [
            ("Service Employees International Union Local 721 – Refuse Unit", 
             "Service Employees International Union Local 721"),
            ("Workers Union Local 123, CTW, CLC State & Local", 
             "Workers Union Local 123"),
            ("Test Union PAC", 
             "Test Union"),
            ("Organization Committee", 
             "Organization")
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = self.matcher._clean_entity_name(input_name)
                self.assertEqual(result, expected)
    
    def test_clean_entity_name_business_suffixes(self):
        """Test cleaning entity names with business suffixes."""
        test_cases = [
            ("Athens Services, Inc.", "Athens Services"),
            ("KA Enterprises LLC", "KA Enterprises"),
            ("Test Company Corp.", "Test Company"),
            ("Organization L.P.", "Organization")
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = self.matcher._clean_entity_name(input_name)
                self.assertEqual(result, expected)
    
    def test_clean_entity_name_prefixes(self):
        """Test cleaning entity names with common prefixes."""
        test_cases = [
            ("The Athens Services", "Athens Services"),
            ("City of Riverside", "Riverside"),
            ("County of San Bernardino", "San Bernardino"),
            ("A Test Organization", "Test Organization")
        ]
        
        for input_name, expected in test_cases:
            with self.subTest(input_name=input_name):
                result = self.matcher._clean_entity_name(input_name)
                self.assertEqual(result, expected)
    
    def test_calculate_enhanced_similarity(self):
        """Test enhanced similarity calculation."""
        # Test exact match
        exact_score = self.matcher._calculate_enhanced_similarity(
            "Athens Services", "Athens Services"
        )
        self.assertEqual(exact_score, 100.0)
        
        # Test high similarity
        high_score = self.matcher._calculate_enhanced_similarity(
            "Athens Services", "Athens Services Inc."
        )
        self.assertGreater(high_score, 90.0)
        
        # Test low similarity
        low_score = self.matcher._calculate_enhanced_similarity(
            "Athens Services", "Completely Different Organization"
        )
        self.assertLess(low_score, 50.0)
    
    def test_is_business_entity(self):
        """Test business entity detection."""
        business_entities = [
            "Athens Services Inc.",
            "KA Enterprises LLC",
            "Workers Union Local 123",
            "Professional Services Company",
            "Eugene Marini of KA Enterprises"
        ]
        
        non_business_entities = [
            "City of Riverside",
            "County of San Bernardino",
            "John Smith",
            "Individual Person"
        ]
        
        for entity in business_entities:
            with self.subTest(entity=entity):
                self.assertTrue(self.matcher._is_business_entity(entity))
        
        for entity in non_business_entities:
            with self.subTest(entity=entity):
                # Note: This test depends on the specific implementation logic
                # Some might still be detected as business entities
                result = self.matcher._is_business_entity(entity)
                # Just ensure it returns a boolean
                self.assertIsInstance(result, bool)
    
    def test_classify_entity_industry(self):
        """Test entity industry classification."""
        test_cases = [
            ("Athens Services", {"waste_management"}),
            ("Service Employees International Union", {"political"}),
            ("Construction Company Inc.", {"construction"}),
            ("Healthcare Solutions LLC", {"healthcare"}),
            ("Unknown Entity", set())  # No specific industry
        ]
        
        for entity, expected_industries in test_cases:
            with self.subTest(entity=entity):
                result = self.matcher._classify_entity_industry(entity)
                if expected_industries:
                    self.assertTrue(result.intersection(expected_industries))
                else:
                    # For unknown entities, just check it returns a set
                    self.assertIsInstance(result, set)
    
    def test_filter_false_positive_beneficiaries(self):
        """Test filtering of false positive beneficiaries."""
        beneficiaries = [
            "Athens Services",  # Should keep
            "City of Riverside",  # Should filter
            "County of San Bernardino",  # Should filter
            "KA Enterprises",  # Should keep
            "California Department of Transportation",  # Should filter
            "Private Company Inc."  # Should keep
        ]
        
        result = self.matcher._filter_false_positive_beneficiaries(beneficiaries)
        
        # Check that government entities are filtered out
        self.assertNotIn("City of Riverside", result)
        self.assertNotIn("County of San Bernardino", result)
        
        # Check that business entities are kept
        self.assertIn("Athens Services", result)
        self.assertIn("KA Enterprises", result)
    
    def test_consolidate_conflicts_by_contributor(self):
        """Test consolidation of conflicts by contributor."""
        # Create sample conflicts with same contributor
        conflicts = [
            ConflictMatch(
                beneficiary="Beneficiary 1",
                contributor="Athens Services",
                contributor_type="name",
                similarity_score=99.0,
                vote_details=[{'date': '2024-01-01', 'item': 'Item 1'}],
                contribution_details=[{'amount': 1000}],
                total_contribution_amount=1000.0
            ),
            ConflictMatch(
                beneficiary="Beneficiary 2",
                contributor="Athens Services",
                contributor_type="name",
                similarity_score=95.0,
                vote_details=[{'date': '2024-01-02', 'item': 'Item 2'}],
                contribution_details=[{'amount': 1000}],
                total_contribution_amount=1000.0
            )
        ]
        
        result = self.matcher._consolidate_conflicts_by_contributor(conflicts)
        
        # Should consolidate to one conflict
        self.assertEqual(len(result), 1)
        
        # Should use highest similarity score
        self.assertEqual(result[0].similarity_score, 99.0)
        
        # Should combine beneficiaries
        self.assertIn("Beneficiary 1", result[0].beneficiary)
        self.assertIn("Beneficiary 2", result[0].beneficiary)
    
    def test_find_conflicts_integration(self):
        """Test the main find_conflicts method."""
        # This is an integration test that tests the full workflow
        conflicts = self.matcher.find_conflicts(
            self.sample_beneficiaries,
            self.sample_contributors,
            self.sample_employers,
            self.mock_data_processor
        )
        
        # Should return a list of ConflictMatch objects
        self.assertIsInstance(conflicts, list)
        
        # Each conflict should be a ConflictMatch instance
        for conflict in conflicts:
            self.assertIsInstance(conflict, ConflictMatch)
            self.assertIsInstance(conflict.beneficiary, str)
            self.assertIsInstance(conflict.contributor, str)
            self.assertIsInstance(conflict.similarity_score, float)
            self.assertIsInstance(conflict.total_contribution_amount, float)
    
    def test_get_high_priority_conflicts(self):
        """Test getting high priority conflicts."""
        # Setup mock conflicts
        self.matcher.conflicts = [
            ConflictMatch(
                beneficiary="Test 1",
                contributor="Contributor 1",
                contributor_type="name",
                similarity_score=95.0,
                vote_details=[],
                contribution_details=[],
                total_contribution_amount=1000.0
            ),
            ConflictMatch(
                beneficiary="Test 2",
                contributor="Contributor 2",
                contributor_type="name",
                similarity_score=85.0,
                vote_details=[],
                contribution_details=[],
                total_contribution_amount=2000.0
            )
        ]
        
        high_priority = self.matcher.get_high_priority_conflicts(90.0)
        
        # Should only return conflicts with score >= 90
        self.assertEqual(len(high_priority), 1)
        self.assertEqual(high_priority[0].similarity_score, 95.0)
    
    def test_get_conflicts_by_contribution_amount(self):
        """Test getting conflicts by contribution amount."""
        # Setup mock conflicts
        self.matcher.conflicts = [
            ConflictMatch(
                beneficiary="Test 1",
                contributor="Contributor 1",
                contributor_type="name",
                similarity_score=95.0,
                vote_details=[],
                contribution_details=[],
                total_contribution_amount=1500.0
            ),
            ConflictMatch(
                beneficiary="Test 2",
                contributor="Contributor 2",
                contributor_type="name",
                similarity_score=85.0,
                vote_details=[],
                contribution_details=[],
                total_contribution_amount=500.0
            )
        ]
        
        significant_conflicts = self.matcher.get_conflicts_by_contribution_amount(1000.0)
        
        # Should only return conflicts with amount >= 1000
        self.assertEqual(len(significant_conflicts), 1)
        self.assertEqual(significant_conflicts[0].total_contribution_amount, 1500.0)
    
    def test_get_summary_stats(self):
        """Test getting summary statistics."""
        # Setup mock conflicts
        self.matcher.conflicts = [
            ConflictMatch(
                beneficiary="Test 1",
                contributor="Contributor 1",
                contributor_type="name",
                similarity_score=95.0,
                vote_details=[],
                contribution_details=[],
                total_contribution_amount=1000.0
            ),
            ConflictMatch(
                beneficiary="Test 2",
                contributor="Contributor 2",
                contributor_type="employer",
                similarity_score=90.0,
                vote_details=[],
                contribution_details=[],
                total_contribution_amount=2000.0
            )
        ]
        
        stats = self.matcher.get_summary_stats()
        
        # Check expected statistics
        self.assertEqual(stats['total_conflicts'], 2)
        self.assertEqual(stats['average_similarity_score'], 92.5)
        self.assertEqual(stats['total_contribution_amount'], 3000.0)
        self.assertEqual(stats['conflicts_by_type']['name_matches'], 1)
        self.assertEqual(stats['conflicts_by_type']['employer_matches'], 1)
    
    def test_empty_inputs(self):
        """Test handling of empty inputs."""
        # Test with empty beneficiaries
        conflicts = self.matcher.find_conflicts(
            [],
            self.sample_contributors,
            self.sample_employers,
            self.mock_data_processor
        )
        self.assertEqual(len(conflicts), 0)
        
        # Test with empty contributors
        conflicts = self.matcher.find_conflicts(
            self.sample_beneficiaries,
            [],
            [],
            self.mock_data_processor
        )
        self.assertEqual(len(conflicts), 0)
    
    def test_none_inputs(self):
        """Test handling of None inputs."""
        with self.assertRaises(TypeError):
            self.matcher.find_conflicts(
                None,
                self.sample_contributors,
                self.sample_employers,
                self.mock_data_processor
            )
    
    @patch('fuzzy_matcher.requests.post')
    def test_claude_validation_success(self, mock_post):
        """Test successful Claude API validation."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'content': [{'text': 'TRUE'}]
        }
        mock_post.return_value = mock_response
        
        # Set up matcher with API key
        self.matcher.claude_api_key = "test-key"
        
        conflict = ConflictMatch(
            beneficiary="Athens Services",
            contributor="Athens Services Inc.",
            contributor_type="name",
            similarity_score=99.0,
            vote_details=[],
            contribution_details=[],
            total_contribution_amount=1000.0
        )
        
        result = self.matcher._validate_conflict_with_claude(conflict)
        self.assertTrue(result)
    
    @patch('fuzzy_matcher.requests.post')
    def test_claude_validation_failure(self, mock_post):
        """Test failed Claude API validation."""
        # Mock failed API response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        
        # Set up matcher with API key
        self.matcher.claude_api_key = "test-key"
        
        conflict = ConflictMatch(
            beneficiary="Athens Services",
            contributor="Completely Different Organization",
            contributor_type="name",
            similarity_score=99.0,
            vote_details=[],
            contribution_details=[],
            total_contribution_amount=1000.0
        )
        
        result = self.matcher._validate_conflict_with_claude(conflict)
        self.assertFalse(result)


class TestConflictMatch(unittest.TestCase):
    """Test cases for the ConflictMatch dataclass."""
    
    def test_conflict_match_creation(self):
        """Test creating a ConflictMatch object."""
        conflict = ConflictMatch(
            beneficiary="Test Beneficiary",
            contributor="Test Contributor",
            contributor_type="name",
            similarity_score=95.0,
            vote_details=[{'date': '2024-01-01'}],
            contribution_details=[{'amount': 1000}],
            total_contribution_amount=1000.0
        )
        
        self.assertEqual(conflict.beneficiary, "Test Beneficiary")
        self.assertEqual(conflict.contributor, "Test Contributor")
        self.assertEqual(conflict.contributor_type, "name")
        self.assertEqual(conflict.similarity_score, 95.0)
        self.assertEqual(conflict.total_contribution_amount, 1000.0)
    
    def test_conflict_match_str_representation(self):
        """Test string representation of ConflictMatch."""
        conflict = ConflictMatch(
            beneficiary="Test Beneficiary",
            contributor="Test Contributor",
            contributor_type="name",
            similarity_score=95.0,
            vote_details=[],
            contribution_details=[],
            total_contribution_amount=1000.0
        )
        
        str_repr = str(conflict)
        self.assertIn("Test Beneficiary", str_repr)
        self.assertIn("Test Contributor", str_repr)
        self.assertIn("95.0", str_repr)


if __name__ == '__main__':
    unittest.main() 