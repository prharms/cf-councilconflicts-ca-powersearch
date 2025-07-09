#!/usr/bin/env python3
"""
Test module for data processing functionality.

This module contains comprehensive tests for the ConflictDataProcessor class
and its methods for loading, validating, and processing council meeting
minutes and campaign finance data.
"""

import unittest
from unittest.mock import patch, mock_open, MagicMock
import pandas as pd
import tempfile
import os

from political_conflict_analysis.processors import ConflictDataProcessor
from political_conflict_analysis.exceptions import DataLoadError, DataValidationError, ColumnValidationError


class TestConflictDataProcessor(unittest.TestCase):
    """Test cases for the ConflictDataProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = ConflictDataProcessor()

        # Sample minutes data with politician vote column
        self.sample_minutes_data = """Meeting Date,Item Description,Politician Vote,Vote Outcome,Beneficiary
2024-01-15,Infrastructure Project,AYE,PASSED,ABC Construction
2024-01-22,Policy Change,NAY,FAILED,XYZ Corporation
2024-02-01,Budget Allocation,AYE,PASSED,Local Union 123
"""

        # Sample campaign finance data
        self.sample_campaign_data = """Contributor,Amount,Date,Type
ABC Construction Inc.,5000.00,2023-12-01,Contribution
XYZ Corporation,2500.00,2023-11-15,Donation
Local Union 123,1000.00,2023-10-20,Contribution
"""

        # Create temporary files for testing
        self.temp_minutes_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        self.temp_campaign_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        
        self.temp_minutes_file.write(self.sample_minutes_data)
        self.temp_campaign_file.write(self.sample_campaign_data)
        
        self.temp_minutes_file.close()
        self.temp_campaign_file.close()

    def tearDown(self):
        """Clean up temporary files after tests."""
        try:
            os.unlink(self.temp_minutes_file.name)
            os.unlink(self.temp_campaign_file.name)
        except FileNotFoundError:
            pass  # Files may have been cleaned up already

    def test_initialization(self):
        """Test ConflictDataProcessor initialization."""
        processor = ConflictDataProcessor()
        
        self.assertIsNone(processor.minutes_df)
        self.assertIsNone(processor.campaign_df)
        self.assertIsNone(processor.politician_votes)
        self.assertIsNone(processor.politician_name)
        self.assertIsNone(processor.vote_column)

    def test_set_politician_info(self):
        """Test setting politician information."""
        politician_name = "John Doe"
        vote_column = "Doe Vote"
        
        self.processor.set_politician_info(politician_name, vote_column)
        
        self.assertEqual(self.processor.politician_name, politician_name)
        self.assertEqual(self.processor.vote_column, vote_column)

    def test_load_minutes_data_success(self):
        """Test successful loading of minutes data."""
        self.processor.set_politician_info("Test Politician", "Politician Vote")
        
        result = self.processor.load_minutes_data(self.temp_minutes_file.name)
        
        self.assertTrue(result)
        self.assertIsNotNone(self.processor.minutes_df)
        self.assertEqual(len(self.processor.minutes_df), 3)
        self.assertIn('Politician Vote', self.processor.minutes_df.columns)
        self.assertIn('Beneficiary', self.processor.minutes_df.columns)

    def test_extract_politician_votes(self):
        """Test extraction of politician votes."""
        self.processor.set_politician_info("Test Politician", "Politician Vote")
        self.processor.load_minutes_data(self.temp_minutes_file.name)
        
        votes = self.processor.extract_politician_votes()
        
        self.assertIsNotNone(votes)
        self.assertEqual(len(votes), 3)
        self.assertIn('ABC Construction', votes['Beneficiary'].values)
        self.assertIn('XYZ Corporation', votes['Beneficiary'].values)
        self.assertIsNotNone(self.processor.politician_votes)

    def test_extract_politician_votes_no_data(self):
        """Test extraction when no data loaded."""
        with self.assertRaises(DataValidationError):
            self.processor.extract_politician_votes()

    def test_load_campaign_data_success(self):
        """Test successful loading of campaign data."""
        result = self.processor.load_campaign_data(self.temp_campaign_file.name)
        
        self.assertTrue(result)
        self.assertIsNotNone(self.processor.campaign_df)
        self.assertEqual(len(self.processor.campaign_df), 3)
        self.assertIn('Contributor', self.processor.campaign_df.columns)
        self.assertIn('Amount', self.processor.campaign_df.columns)

    def test_extract_campaign_contributors(self):
        """Test extraction of campaign contributors."""
        self.processor.load_campaign_data(self.temp_campaign_file.name)
        
        names, employers = self.processor.extract_campaign_contributors()
        
        self.assertEqual(len(names), 3)
        self.assertEqual(len(employers), 3)
        self.assertIn('ABC Construction Inc.', names)
        self.assertIn('XYZ Corporation', names)
        self.assertIn('Local Union 123', employers)
        self.assertIsNotNone(self.processor.contributors)

    def test_extract_campaign_contributors_no_data(self):
        """Test extraction of contributors without loaded data."""
        with self.assertRaises(ValueError):
            self.processor.extract_campaign_contributors()

    def test_get_contributor_details(self):
        """Test getting contributor details."""
        self.processor.load_campaign_data(self.temp_campaign_file.name)
        
        details = self.processor.get_contributor_details('ABC Construction Inc.')
        
        self.assertEqual(len(details), 1)
        self.assertEqual(details[0]['name'], 'ABC Construction Inc.')
        self.assertEqual(details[0]['amount'], 5000.0)

    def test_get_contributor_details_no_match(self):
        """Test getting contributor details for non-existent contributor."""
        self.processor.load_campaign_data(self.temp_campaign_file.name)
        
        details = self.processor.get_contributor_details('Nonexistent Contributor')
        
        self.assertEqual(len(details), 0)

    def test_get_contributor_details_no_data(self):
        """Test getting contributor details without loaded data."""
        details = self.processor.get_contributor_details('ABC Construction Inc.')
        self.assertEqual(len(details), 0)

    def test_get_employer_contribution_details(self):
        """Test getting employer contribution details."""
        self.processor.load_campaign_data(self.temp_campaign_file.name)
        
        details = self.processor.get_employer_contribution_details('Local Union 123')
        
        self.assertEqual(len(details), 1)
        self.assertEqual(details[0]['name'], 'Local Union 123')
        self.assertEqual(details[0]['employer'], 'Local Union 123')
        self.assertEqual(details[0]['amount'], 1000.0)

    def test_get_beneficiary_vote_details(self):
        """Test getting beneficiary vote details."""
        self.processor.load_minutes_data(self.temp_minutes_file.name)
        self.processor.extract_politician_votes()
        
        details = self.processor.get_beneficiary_vote_details('ABC Construction')
        
        self.assertEqual(len(details), 1)
        self.assertEqual(details[0]['beneficiary'], 'ABC Construction')
        self.assertEqual(details[0]['vote'], 'AYE')

    def test_get_beneficiary_vote_details_no_data(self):
        """Test getting beneficiary vote details without processed data."""
        details = self.processor.get_beneficiary_vote_details('ABC Construction')
        self.assertEqual(len(details), 0)

    def test_get_summary_stats(self):
        """Test getting summary statistics."""
        self.processor.load_minutes_data(self.temp_minutes_file.name)
        self.processor.extract_politician_votes()
        self.processor.load_campaign_data(self.temp_campaign_file.name)
        self.processor.extract_campaign_contributors()
        
        stats = self.processor.get_summary_stats()
        
        self.assertEqual(stats['total_agenda_items'], 3)
        self.assertEqual(stats['politician_votes'], 3)
        self.assertEqual(stats['politician_aye_votes'], 2)
        self.assertEqual(stats['total_contributions'], 3)
        self.assertEqual(stats['total_contribution_amount'], 8500.0)
        self.assertEqual(stats['unique_contributor_names'], 3)
        self.assertEqual(stats['unique_contributor_employers'], 3)

    def test_get_summary_stats_no_data(self):
        """Test getting summary statistics without loaded data."""
        stats = self.processor.get_summary_stats()
        self.assertEqual(stats, {})

    def test_case_insensitive_search(self):
        """Test that searches are case-insensitive."""
        self.processor.load_minutes_data(self.temp_minutes_file.name)
        self.processor.extract_politician_votes()
        self.processor.load_campaign_data(self.temp_campaign_file.name)
        self.processor.extract_campaign_contributors()
        
        details = self.processor.get_contributor_details('abc construction inc')
        self.assertEqual(len(details), 1)
        
        details = self.processor.get_employer_contribution_details('local union 123')
        self.assertEqual(len(details), 1)

    def test_missing_required_columns(self):
        """Test loading data with missing required columns."""
        # Create CSV with missing columns
        invalid_minutes = """Date,Description,Vote
2024-01-01,Test Item,AYE
"""
        
        invalid_file = os.path.join(self.temp_minutes_file.name, 'invalid_minutes.csv')
        with open(invalid_file, 'w') as f:
            f.write(invalid_minutes)
        
        with self.assertRaises(DataValidationError):
            self.processor.load_minutes_data(invalid_file)

    def test_data_types_after_loading(self):
        """Test that data types are correct after loading."""
        self.processor.load_minutes_data(self.temp_minutes_file.name)
        self.processor.extract_politician_votes()
        self.processor.load_campaign_data(self.temp_campaign_file.name)
        
        # Check minutes data types
        self.assertIsInstance(self.processor.minutes_df, pd.DataFrame)
        self.assertIn('Meeting Date', self.processor.minutes_df.columns)
        self.assertIn('Politician Vote', self.processor.minutes_df.columns)
        
        # Check campaign data types
        self.assertIsInstance(self.processor.campaign_df, pd.DataFrame)
        self.assertIn('Contributor', self.processor.campaign_df.columns)
        self.assertIn('Amount', self.processor.campaign_df.columns)
        
        # Check that amounts are numeric
        self.assertTrue(pd.api.types.is_numeric_dtype(self.processor.campaign_df['Amount']))

    def test_empty_csv_handling(self):
        """Test handling of CSV files with headers but no data."""
        # Create CSV with headers but no data
        empty_minutes = """Meeting Date,Item Description,Politician Vote,Vote Outcome,Beneficiary
"""
        
        empty_file = os.path.join(self.temp_minutes_file.name, 'empty_minutes.csv')
        with open(empty_file, 'w') as f:
            f.write(empty_minutes)
        
        # Should load successfully but have empty DataFrame
        result = self.processor.load_minutes_data(empty_file)
        self.assertTrue(result)
        self.assertEqual(len(self.processor.minutes_df), 0)

    def test_null_value_handling(self):
        """Test handling of null values in data."""
        # Create CSV with null values
        null_data = """Contributor,Amount,Date,Type
ABC Construction Inc.,1000.0,2024-01-01,Contribution
,Empty Name,500.0,2024-01-02,Contribution
Local Union 123,,250.0,2024-01-03,Contribution
"""
        
        null_file = os.path.join(self.temp_campaign_file.name, 'null_campaign.csv')
        with open(null_file, 'w') as f:
            f.write(null_data)
        
        # Load data
        self.processor.load_campaign_data(null_file)
        
        # Extract contributors - should handle null values
        names, employers = self.processor.extract_campaign_contributors()
        
        # Should exclude empty/null names and employers
        self.assertNotIn('', names)
        self.assertNotIn('', employers)
        self.assertIn('ABC Construction Inc.', names)
        self.assertIn('Local Union 123', names)


if __name__ == '__main__':
    unittest.main() 