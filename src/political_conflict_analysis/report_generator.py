#!/usr/bin/env python3
"""
Report generator for political potential conflict of interest analysis.

This module generates detailed reports of potential conflicts of interest
between meeting beneficiaries and campaign contributors for any elected official.
"""

import pandas as pd
import csv
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

from .types import AnalysisResult, AggregatedConflict, ReportData, FilePath

logger = logging.getLogger(__name__)


class ConflictReportGenerator:
    """
    Generate detailed reports for political potential conflict of interest analysis.
    
    This class creates comprehensive reports including summaries, detailed
    breakdowns, and CSV exports of potential conflicts of interest.
    """
    
    def __init__(self):
        """Initialize the report generator."""
        self.logger = logging.getLogger(__name__)
        
    def generate_summary_report(self, result: AnalysisResult, output_path: FilePath) -> None:
        """
        Generate a summary report of potential conflicts.
        
        Args:
            result: Analysis result containing conflicts and metadata
            output_path: Path to write the summary report
        """
        try:
            self.logger.info(f"Generating summary report for {result.politician}")
            
            report = []
            report.append(f"Political Potential Conflict of Interest Analysis Report")
            report.append(f"Politician: {result.politician}")
            report.append(f"Generated: {result.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("=" * 60)
            report.append("")
            report.append("ANALYSIS SCOPE:")
            report.append("This analysis identifies potential conflicts of interest by systematically")
            report.append("examining overlapping relationships between vote beneficiaries and campaign")
            report.append("contributors. Results represent patterns that warrant further investigation,")
            report.append("not determinations of wrongdoing.")
            report.append("")
            
            if not result.conflicts:
                report.append("No potential conflicts of interest found.")
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(report))
                return
            
            report.append(f"SUMMARY:")
            report.append(f"Total potential conflicts: {result.total_conflicts}")
            report.append(f"Total contribution amount: ${result.total_contribution_amount:,.2f}")
            report.append(f"Analysis threshold: {result.threshold_used}")
            report.append("")
            
            report.append("TOP CONFLICTS:")
            report.append("-" * 40)
            
            for i, conflict in enumerate(result.conflicts, 1):
                report.append(f"{i}. {conflict.beneficiary} ↔ {conflict.contributor_summary}")
                report.append(f"   Similarity: {conflict.avg_similarity:.1f}%")
                
                # Show match types
                match_type_strs = [mt.value for mt in conflict.match_types]
                if len(match_type_strs) > 1:
                    report.append(f"   Match Types: {', '.join(match_type_strs)}")
                else:
                    report.append(f"   Match Type: {match_type_strs[0]}")
                
                report.append(f"   Total Contributions: ${conflict.total_contributions:,.2f}")
                report.append(f"   Contribution Count: {conflict.contribution_count}")
                report.append(f"   Vote Count: {conflict.vote_count}")
                
                # Show range if multiple similarities
                if conflict.min_similarity != conflict.max_similarity:
                    report.append(f"   Similarity Range: {conflict.min_similarity:.1f}% - {conflict.max_similarity:.1f}%")
                
                report.append("")
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(report))
                
            self.logger.info(f"Summary report saved to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error generating summary report: {e}")
            raise
    
    def generate_detailed_report(self, result: AnalysisResult, output_path: FilePath) -> None:
        """
        Generate a detailed report with full information for each conflict.
        
        Args:
            result: Analysis result containing conflicts and metadata
            output_path: Path to write the detailed report
        """
        try:
            self.logger.info(f"Generating detailed report for {result.politician}")
            
            report = []
            report.append(f"Detailed Political Potential Conflict of Interest Analysis Report")
            report.append(f"Politician: {result.politician}")
            report.append(f"Generated: {result.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("=" * 80)
            report.append("")
            report.append("ANALYSIS SCOPE:")
            report.append("This analysis identifies potential conflicts of interest by systematically")
            report.append("examining overlapping relationships between vote beneficiaries and campaign")
            report.append("contributors. Results represent patterns that warrant further investigation,")
            report.append("not determinations of wrongdoing.")
            report.append("")
            
            if not result.conflicts:
                report.append("No potential conflicts of interest found.")
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(report))
                return
            
            for i, conflict in enumerate(result.conflicts, 1):
                report.append(f"CONFLICT #{i}")
                report.append("-" * 50)
                report.append(f"Entity: {conflict.beneficiary}")
                report.append(f"Contributors: {conflict.contributor_summary}")
                report.append(f"Average Similarity: {conflict.avg_similarity:.1f}%")
                report.append(f"Similarity Range: {conflict.min_similarity:.1f}% - {conflict.max_similarity:.1f}%")
                
                match_type_strs = [mt.value for mt in conflict.match_types]
                report.append(f"Match Types: {', '.join(match_type_strs)}")
                report.append(f"Total Contributions: ${conflict.total_contributions:,.2f}")
                report.append("")
                
                # Show original beneficiary variations
                if len(conflict.original_beneficiaries) > 1:
                    report.append("BENEFICIARY VARIATIONS:")
                    for beneficiary in set(conflict.original_beneficiaries):
                        report.append(f"  • {beneficiary}")
                    report.append("")
                
                # Show all contributors
                if len(conflict.contributors) > 1:
                    report.append("ALL CONTRIBUTORS:")
                    for contributor in set(conflict.contributors):
                        report.append(f"  • {contributor}")
                    report.append("")
                
                # Contribution details
                if conflict.contribution_details:
                    report.append("CONTRIBUTION DETAILS:")
                    for detail in conflict.contribution_details:
                        employer_str = f" ({detail.employer})" if detail.employer else ""
                        report.append(f"  • {detail.name}{employer_str}")
                        report.append(f"    Amount: ${detail.amount:,.2f}")
                        report.append(f"    Date: {detail.date}")
                        report.append(f"    Type: {detail.transaction_type}")
                        report.append("")
                
                # Vote details
                if conflict.vote_details:
                    report.append("VOTING DETAILS:")
                    for vote in conflict.vote_details:
                        report.append(f"  • {vote.date}: {vote.vote.value} vote")
                        report.append(f"    Item: {vote.item}")
                        report.append(f"    Outcome: {vote.outcome.value}")
                        report.append(f"    Beneficiary: {vote.beneficiary}")
                        report.append("")
                
                report.append("=" * 80)
                report.append("")
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(report))
                
            self.logger.info(f"Detailed report saved to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error generating detailed report: {e}")
            raise
    
    def generate_csv_report(self, result: AnalysisResult, output_path: FilePath) -> None:
        """
        Generate a CSV report of conflicts.
        
        Args:
            result: Analysis result containing conflicts and metadata
            output_path: Path to write the CSV report
        """
        try:
            self.logger.info(f"Generating CSV report for {result.politician}")
            
            if not result.conflicts:
                # Create empty CSV with headers
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'Politician', 'Beneficiary', 'Contributor', 'Employer',
                        'Amount', 'Date', 'Transaction_Type', 'Similarity',
                        'Match_Type', 'Total_Contributions', 'Contributor_Count', 'Vote_Count'
                    ])
                return
            
            csv_data = []
            
            for conflict in result.conflicts:
                # Create a row for each contribution detail
                for detail in conflict.contribution_details:
                    row = {
                        'Politician': result.politician,
                        'Beneficiary': conflict.beneficiary,
                        'Contributor': detail.name,
                        'Employer': detail.employer or '',
                        'Amount': detail.amount,
                        'Date': detail.date,
                        'Transaction_Type': detail.transaction_type,
                        'Similarity': conflict.avg_similarity,
                        'Match_Type': ', '.join([mt.value for mt in conflict.match_types]),
                        'Total_Contributions': conflict.total_contributions,
                        'Contributor_Count': conflict.contribution_count,
                        'Vote_Count': conflict.vote_count
                    }
                    csv_data.append(row)
            
            # Write CSV file
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                if csv_data:
                    writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
                    writer.writeheader()
                    writer.writerows(csv_data)
                    
            self.logger.info(f"CSV report saved to {output_path} with {len(csv_data)} rows")
            
        except Exception as e:
            self.logger.error(f"Error generating CSV report: {e}")
            raise
    
 