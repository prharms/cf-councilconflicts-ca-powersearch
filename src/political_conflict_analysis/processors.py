"""
Data processing for conflict analysis.

This module provides comprehensive data processing capabilities for
loading and transforming CSV data for conflict analysis.
"""

import csv
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from .types import ContributionDetail, VoteDetail, VoteType, VoteOutcome, FilePath


class ConflictDataProcessor:
    """
    Handles data processing for conflict analysis.
    
    This class is responsible for:
    - Loading CSV data files
    - Validating data integrity
    - Transforming raw data into structured formats
    - Handling data cleaning and normalization
    """
    
    def __init__(self):
        """Initialize the data processor."""
        self.logger = logging.getLogger(__name__)
    
    def load_minutes_data(self, file_path: FilePath) -> List[Dict[str, Any]]:
        """
        Load and validate minutes data from CSV file.
        
        Args:
            file_path: Path to the minutes CSV file
            
        Returns:
            List of dictionaries containing minutes data
        """
        try:
            data = self._load_csv_file(file_path)
            
            # Map actual column names to expected names
            data = self._map_minutes_columns(data)
            
            # Validate required columns after mapping
            required_columns = ['Date', 'Politician', 'Vote', 'Item', 'Outcome', 'Beneficiary']
            self._validate_columns(data, required_columns, 'minutes')
            
            # Clean and normalize data
            cleaned_data = self._clean_minutes_data(data)
            
            self.logger.info(f"Loaded {len(cleaned_data)} minutes records from {file_path}")
            return cleaned_data
            
        except Exception as e:
            self.logger.error(f"Failed to load minutes data from {file_path}: {str(e)}")
            raise
    
    def load_campaign_finance_data(self, file_path: FilePath) -> List[Dict[str, Any]]:
        """
        Load and validate campaign finance data from CSV file.
        
        Args:
            file_path: Path to the campaign finance CSV file
            
        Returns:
            List of dictionaries containing campaign finance data
        """
        try:
            data = self._load_csv_file(file_path)
            
            # Map actual column names to expected names
            data = self._map_campaign_finance_columns(data)
            
            # Validate required columns after mapping
            required_columns = ['Contributor', 'Amount', 'Date', 'Transaction Type']
            self._validate_columns(data, required_columns, 'campaign finance')
            
            # Clean and normalize data
            cleaned_data = self._clean_campaign_finance_data(data)
            
            self.logger.info(f"Loaded {len(cleaned_data)} campaign finance records from {file_path}")
            return cleaned_data
            
        except Exception as e:
            self.logger.error(f"Failed to load campaign finance data from {file_path}: {str(e)}")
            raise
    
    def create_contribution_details(self, campaign_finance_data: List[Dict]) -> List[ContributionDetail]:
        """
        Create structured contribution details from raw data.
        
        Args:
            campaign_finance_data: Raw campaign finance data
            
        Returns:
            List of structured contribution details
        """
        contributions = []
        
        for row in campaign_finance_data:
            try:
                contribution = ContributionDetail(
                    name=row.get('Contributor', '').strip(),
                    employer=row.get('Employer', '').strip() if row.get('Employer') else None,
                    amount=float(row.get('Amount', 0)),
                    date=row.get('Date', '').strip(),
                    transaction_type=row.get('Transaction Type', '').strip()
                )
                contributions.append(contribution)
                
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Skipping invalid contribution record: {str(e)}")
                continue
        
        return contributions
    
    def create_vote_details(self, minutes_data: List[Dict]) -> List[VoteDetail]:
        """
        Create structured vote details from raw data.
        
        Args:
            minutes_data: Raw minutes data
            
        Returns:
            List of structured vote details
        """
        votes = []
        
        for row in minutes_data:
            try:
                # Map vote strings to enum values
                vote_str = row.get('Vote', 'AYE').upper()
                vote_type = VoteType(vote_str) if vote_str in [v.value for v in VoteType] else VoteType.AYE
                
                # Map outcome strings to enum values
                outcome_str = row.get('Outcome', 'PASSED').upper()
                outcome_type = VoteOutcome(outcome_str) if outcome_str in [o.value for o in VoteOutcome] else VoteOutcome.PASSED
                
                vote = VoteDetail(
                    date=row.get('Date', '').strip(),
                    vote=vote_type,
                    item=row.get('Item', '').strip(),
                    outcome=outcome_type,
                    beneficiary=row.get('Beneficiary', '').strip()
                )
                votes.append(vote)
                
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Skipping invalid vote record: {str(e)}")
                continue
        
        return votes
    
    def _load_csv_file(self, file_path: FilePath) -> List[Dict[str, str]]:
        """
        Load CSV file into list of dictionaries.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            List of dictionaries with CSV data
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        
        data = []
        try:
            with open(path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row_num, row in enumerate(reader, start=2):  # Start at 2 to account for header
                    if any(value.strip() for value in row.values()):  # Skip empty rows
                        data.append(row)
                    
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            with open(path, 'r', encoding='latin-1') as file:
                reader = csv.DictReader(file)
                for row_num, row in enumerate(reader, start=2):
                    if any(value.strip() for value in row.values()):
                        data.append(row)
        
        return data
    
    def _validate_columns(self, data: List[Dict], required_columns: List[str], data_type: str) -> None:
        """
        Validate that required columns exist in the data.
        
        Args:
            data: List of data dictionaries
            required_columns: List of required column names
            data_type: Type of data for error messages
        """
        if not data:
            raise ValueError(f"No data found in {data_type} file")
        
        # Check if all required columns exist
        available_columns = set(data[0].keys())
        missing_columns = set(required_columns) - available_columns
        
        if missing_columns:
            raise ValueError(
                f"Missing required columns in {data_type} file: {missing_columns}. "
                f"Available columns: {available_columns}"
            )
    
    def _clean_minutes_data(self, data: List[Dict]) -> List[Dict]:
        """
        Clean and normalize minutes data.
        
        Args:
            data: Raw minutes data
            
        Returns:
            Cleaned minutes data
        """
        cleaned_data = []
        
        for row in data:
            cleaned_row = {}
            
            # Clean each field
            for key, value in row.items():
                if value is not None:
                    cleaned_value = str(value).strip()
                    cleaned_row[key] = cleaned_value if cleaned_value else None
                else:
                    cleaned_row[key] = None
            
            # Skip rows with missing critical data
            if (cleaned_row.get('Beneficiary') and 
                cleaned_row.get('Vote') and 
                cleaned_row.get('Item')):
                cleaned_data.append(cleaned_row)
        
        return cleaned_data
    
    def _clean_campaign_finance_data(self, data: List[Dict]) -> List[Dict]:
        """
        Clean and normalize campaign finance data.
        
        Args:
            data: Raw campaign finance data
            
        Returns:
            Cleaned campaign finance data
        """
        cleaned_data = []
        
        for row in data:
            cleaned_row = {}
            
            # Clean each field
            for key, value in row.items():
                if value is not None:
                    cleaned_value = str(value).strip()
                    cleaned_row[key] = cleaned_value if cleaned_value else None
                else:
                    cleaned_row[key] = None
            
            # Clean amount field specifically
            if cleaned_row.get('Amount'):
                try:
                    # Remove currency symbols and commas
                    amount_str = cleaned_row['Amount'].replace('$', '').replace(',', '')
                    cleaned_row['Amount'] = float(amount_str)
                except ValueError:
                    self.logger.warning(f"Invalid amount value: {cleaned_row['Amount']}")
                    continue
            
            # Skip rows with missing critical data
            if (cleaned_row.get('Contributor') and 
                cleaned_row.get('Amount') is not None and
                cleaned_row.get('Date')):
                cleaned_data.append(cleaned_row)
        
        return cleaned_data
    
    def get_data_summary(self, data: List[Dict], data_type: str) -> Dict[str, Any]:
        """
        Get summary statistics for loaded data.
        
        Args:
            data: List of data dictionaries
            data_type: Type of data ('minutes' or 'campaign_finance')
            
        Returns:
            Summary statistics
        """
        if not data:
            return {
                'total_records': 0,
                'data_type': data_type,
                'columns': [],
                'sample_record': None
            }
        
        columns = list(data[0].keys())
        sample_record = data[0] if data else None
        
        summary = {
            'total_records': len(data),
            'data_type': data_type,
            'columns': columns,
            'sample_record': sample_record
        }
        
        # Add data-specific statistics
        if data_type == 'minutes':
            summary.update(self._get_minutes_statistics(data))
        elif data_type == 'campaign_finance':
            summary.update(self._get_campaign_finance_statistics(data))
        
        return summary
    
    def _get_minutes_statistics(self, data: List[Dict]) -> Dict[str, Any]:
        """Get statistics specific to minutes data."""
        unique_beneficiaries = set()
        unique_politicians = set()
        vote_counts = {}
        
        for row in data:
            if row.get('Beneficiary'):
                unique_beneficiaries.add(row['Beneficiary'])
            if row.get('Politician'):
                unique_politicians.add(row['Politician'])
            
            vote = row.get('Vote', 'Unknown')
            vote_counts[vote] = vote_counts.get(vote, 0) + 1
        
        return {
            'unique_beneficiaries': len(unique_beneficiaries),
            'unique_politicians': len(unique_politicians),
            'vote_distribution': vote_counts,
            'sample_beneficiaries': list(unique_beneficiaries)[:5]
        }
    
    def _get_campaign_finance_statistics(self, data: List[Dict]) -> Dict[str, Any]:
        """Get statistics specific to campaign finance data."""
        unique_contributors = set()
        total_amount = 0.0
        amount_counts = []
        
        for row in data:
            if row.get('Contributor'):
                unique_contributors.add(row['Contributor'])
            
            try:
                amount = float(row.get('Amount', 0))
                total_amount += amount
                amount_counts.append(amount)
            except (ValueError, TypeError):
                continue
        
        return {
            'unique_contributors': len(unique_contributors),
            'total_contribution_amount': total_amount,
            'average_contribution': total_amount / len(amount_counts) if amount_counts else 0.0,
            'max_contribution': max(amount_counts) if amount_counts else 0.0,
            'min_contribution': min(amount_counts) if amount_counts else 0.0,
            'sample_contributors': list(unique_contributors)[:5]
        }
    
    def _map_minutes_columns(self, data: List[Dict]) -> List[Dict]:
        """
        Map actual CSV column names to expected names for minutes data.
        
        Args:
            data: Raw data with actual column names
            
        Returns:
            Data with mapped column names
        """
        if not data:
            return data
        
        # Column mapping from actual to expected
        column_mapping = {
            '\ufeffMeeting Date': 'Date',
            'Meeting Date': 'Date',
            'Cervantes Vote': 'Vote', 
            'Item Description': 'Item',
            'Vote Outcome': 'Outcome',
            'Beneficiary': 'Beneficiary'  # Already correct
        }
        
        mapped_data = []
        for row in data:
            mapped_row = {}
            
            # Map known columns
            for actual_col, expected_col in column_mapping.items():
                if actual_col in row:
                    mapped_row[expected_col] = row[actual_col]
            
            # Add politician name (fixed value)
            mapped_row['Politician'] = 'Cervantes'
            
            # Copy any unmapped columns
            for col, value in row.items():
                if col not in column_mapping and col not in mapped_row:
                    mapped_row[col] = value
            
            mapped_data.append(mapped_row)
        
        return mapped_data
    
    def _map_campaign_finance_columns(self, data: List[Dict]) -> List[Dict]:
        """
        Map actual CSV column names to expected names for campaign finance data.
        
        Args:
            data: Raw data with actual column names
            
        Returns:
            Data with mapped column names
        """
        if not data:
            return data
        
        # Column mapping from actual to expected
        column_mapping = {
            'Contributor Name': 'Contributor',
            'Contributor': 'Contributor',  # In case it's already correct
            'Amount': 'Amount',  # Already correct
            'Start Date': 'Date',
            'Date': 'Date',  # In case it's already correct
            'Transaction Type': 'Transaction Type',  # Already correct
            'Contributor Employer': 'Employer'
        }
        
        mapped_data = []
        for row in data:
            mapped_row = {}
            
            # Map known columns
            for actual_col, expected_col in column_mapping.items():
                if actual_col in row:
                    mapped_row[expected_col] = row[actual_col]
            
            # Copy any unmapped columns
            for col, value in row.items():
                if col not in column_mapping and col not in mapped_row:
                    mapped_row[col] = value
            
            mapped_data.append(mapped_row)
        
        return mapped_data 