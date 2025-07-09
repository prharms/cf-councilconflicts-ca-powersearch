"""
Claude AI validation implementation for conflict analysis.

This module provides API validation capabilities for filtering
false positives in conflict detection using Claude AI.
"""

import json
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import anthropic
from anthropic.types import MessageParam

from .types import ConflictMatch, APIConfig, AggregatedConflict


class ClaudeValidator:
    """
    Handles Claude AI validation for conflict analysis.
    
    This class is responsible for:
    - Validating potential conflicts using Claude AI
    - Filtering false positives
    - Managing API communication and retries
    - Parsing and validating API responses
    """
    
    def __init__(self, config: APIConfig):
        """
        Initialize the Claude validator.
        
        Args:
            config: Configuration parameters for API calls
        """
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.api_key)
        self.logger = logging.getLogger(__name__)
        
        # Standard validation prompt template
        self.validation_prompt = """
        <task>
        You are analyzing potential conflicts of interest between political officials' votes and their campaign contributors. This analysis identifies potential conflicts of interest by systematically examining overlapping relationships between vote beneficiaries and campaign contributors. Results represent patterns that warrant further investigation, not determinations of wrongdoing.
        
        Your goal is to identify genuine potential conflicts while filtering out false positives by determining whether entities are truly the same organization or merely similar.
        </task>
        
        <input_data>
        Beneficiary: {beneficiary}
        Contributors: {contributors}
        Vote details: {vote_details}
        Contribution details: {contribution_details}
        </input_data>
        
        <analysis_framework>
        A genuine conflict requires that the beneficiary and contributor represent the SAME organizational entity or have direct operational control over each other. Apply rigorous analysis to distinguish between "same entity" and "similar but separate entities."
        
        <entity_identity_analysis>
        To determine if entities are the same:
        1. Legal structure: Are they the same legal entity, subsidiary, or parent company?
        2. Operational control: Does one entity control the other's operations, finances, or decision-making?
        3. Corporate identity: Are they explicitly identified as the same organization using different names (e.g., "doing business as")?
        4. Individual ownership: Is the beneficiary a person who owns or controls the contributor organization?
        
        Entities are SEPARATE if they have:
        - Different legal structures and governance
        - Independent operations and decision-making
        - Distinct missions or target constituencies
        - Separate leadership and membership
        - Different corporate ownership structures
        </entity_identity_analysis>
        
        <rules>
        Apply these rules in strict order:
        
        1. GOVERNMENT/ACADEMIC EMPLOYEES: If the contributor is an employee of a government entity (including "City of", "County of", "State of"), college, or university, then this is NOT a potential conflict of interest.
        
        2. LABOR UNION RELATIONSHIPS: If the contributor is a labor union, local union, or union PAC that represents the same specific worker group as the beneficiary union, then this IS a potential conflict of interest.
        
        3. ORGANIZATIONAL IDENTITY TEST: Apply the entity identity analysis above. The beneficiary and contributor must pass the "same entity" test to constitute a potential conflict.
        
        IMPORTANT: Geographic proximity, similar names, related industries, or overlapping membership alone do not make entities the same. Focus on actual organizational control and legal identity.
        </rules>
        
        <critical_instruction>
        TIMING IS IRRELEVANT: Do not consider when contributions vs votes occurred. Conflicts exist regardless of chronological order.
        </critical_instruction>
        </analysis_framework>
        
        <output_format>
        Respond with a JSON object containing:
        {{
            "is_genuine_conflict": true/false,
            "confidence_level": "high"/"medium"/"low",
            "reasoning": "Detailed explanation of your analysis",
            "key_factors": ["list", "of", "key", "factors", "considered"]
        }}
        </output_format>
        """
    
    def validate_conflict(self, conflict: AggregatedConflict) -> Tuple[bool, str, str]:
        """
        Validate a single conflict using Claude AI.
        
        Args:
            conflict: The aggregated conflict to validate
            
        Returns:
            Tuple of (is_genuine, confidence_level, reasoning)
        """
        try:
            # Prepare context for validation
            context = self._prepare_validation_context(conflict)
            
            # Make API call with retries
            response = self._make_api_call(context)
            
            # Parse and validate response
            result = self._parse_validation_response(response)
            
            return result['is_genuine_conflict'], result['confidence_level'], result['reasoning']
            
        except Exception as e:
            self.logger.error(f"Validation failed for conflict {conflict.beneficiary}: {str(e)}")
            # Default to treating as genuine conflict if validation fails
            return True, "low", f"Validation failed: {str(e)}"
    
    def validate_conflicts_batch(self, conflicts: List[AggregatedConflict]) -> List[Tuple[bool, str, str]]:
        """
        Validate multiple conflicts in batch.
        
        Args:
            conflicts: List of aggregated conflicts to validate
            
        Returns:
            List of validation results (is_genuine, confidence_level, reasoning)
        """
        results = []
        
        for conflict in conflicts:
            result = self.validate_conflict(conflict)
            results.append(result)
            
            # Log validation result
            is_genuine, confidence, reasoning = result
            self.logger.info(
                f"Validated conflict {conflict.beneficiary}: "
                f"genuine={is_genuine}, confidence={confidence}"
            )
        
        return results
    
    def _prepare_validation_context(self, conflict: AggregatedConflict) -> str:
        """
        Prepare context string for validation API call.
        
        Args:
            conflict: The conflict to prepare context for
            
        Returns:
            Formatted context string
        """
        # Format contributors
        contributors_str = ", ".join(conflict.contributors)
        
        # Format vote details
        vote_details = []
        for vote in conflict.vote_details:
            vote_details.append(f"Date: {vote.date}, Vote: {vote.vote.value}, Item: {vote.item}")
        vote_details_str = "; ".join(vote_details)
        
        # Format contribution details
        contribution_details = []
        for contrib in conflict.contribution_details:
            employer_str = f" (Employer: {contrib.employer})" if contrib.employer else ""
            contribution_details.append(
                f"${contrib.amount:.2f} from {contrib.name}{employer_str} on {contrib.date}"
            )
        contribution_details_str = "; ".join(contribution_details)
        
        # Fill in the template
        context = self.validation_prompt.format(
            beneficiary=conflict.beneficiary,
            contributors=contributors_str,
            vote_details=vote_details_str,
            contribution_details=contribution_details_str
        )
        
        return context
    
    def _make_api_call(self, context: str) -> str:
        """
        Make API call to Claude with retry logic.
        
        Args:
            context: The validation context to send
            
        Returns:
            Raw API response text
        """
        for attempt in range(self.config.max_retries):
            try:
                messages: List[MessageParam] = [
                    {"role": "user", "content": context}
                ]
                
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    messages=messages
                )
                
                # Handle both stop reason and refusal
                if hasattr(response, 'stop_reason') and response.stop_reason == 'refusal':
                    raise Exception("Claude refused to process the request")
                
                return response.content[0].text
                
            except Exception as e:
                self.logger.warning(f"API call attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.config.max_retries - 1:
                    raise
                
        raise Exception("All API call attempts failed")
    
    def _parse_validation_response(self, response: str) -> Dict[str, any]:
        """
        Parse and validate the API response.
        
        Args:
            response: Raw API response text
            
        Returns:
            Parsed validation result
        """
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response[json_start:json_end]
            result = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['is_genuine_conflict', 'confidence_level', 'reasoning']
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate field types and values
            if not isinstance(result['is_genuine_conflict'], bool):
                raise ValueError("is_genuine_conflict must be boolean")
            
            if result['confidence_level'] not in ['high', 'medium', 'low']:
                raise ValueError("confidence_level must be 'high', 'medium', or 'low'")
            
            if not isinstance(result['reasoning'], str) or not result['reasoning'].strip():
                raise ValueError("reasoning must be a non-empty string")
            
            return result
            
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to parse validation response: {str(e)}")
            self.logger.error(f"Raw response: {response}")
            
            # Return default response for parsing failures
            return {
                'is_genuine_conflict': True,
                'confidence_level': 'low',
                'reasoning': f"Failed to parse AI response: {str(e)}",
                'key_factors': []
            }
    
    def get_validation_stats(self, results: List[Tuple[bool, str, str]]) -> Dict[str, any]:
        """
        Get statistics about validation results.
        
        Args:
            results: List of validation results
            
        Returns:
            Statistics dictionary
        """
        if not results:
            return {
                'total_validated': 0,
                'genuine_conflicts': 0,
                'false_positives': 0,
                'confidence_distribution': {},
                'validation_rate': 0.0
            }
        
        genuine_count = sum(1 for is_genuine, _, _ in results if is_genuine)
        false_positive_count = len(results) - genuine_count
        
        # Count confidence levels
        confidence_counts = {}
        for _, confidence, _ in results:
            confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1
        
        return {
            'total_validated': len(results),
            'genuine_conflicts': genuine_count,
            'false_positives': false_positive_count,
            'confidence_distribution': confidence_counts,
            'validation_rate': genuine_count / len(results) if results else 0.0
        }
    
    def test_api_connection(self) -> bool:
        """
        Test the API connection and configuration.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            test_message = "Please respond with 'API test successful'"
            
            messages: List[MessageParam] = [
                {"role": "user", "content": test_message}
            ]
            
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=50,
                temperature=0.0,
                messages=messages
            )
            
            return "API test successful" in response.content[0].text
            
        except Exception as e:
            self.logger.error(f"API connection test failed: {str(e)}")
            return False 