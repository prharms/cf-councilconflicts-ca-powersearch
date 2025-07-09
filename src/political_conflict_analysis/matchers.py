"""
Fuzzy matching implementation for conflict analysis.

This module provides simple fuzzy matching capabilities for
detecting potential conflicts of interest between entities.
"""

import re
from typing import List, Dict, Set, Optional, Tuple
from rapidfuzz import fuzz
from dataclasses import dataclass

from .types import ConflictMatch, MatchType, SimilarityConfig, SimilarityScore


class FuzzyMatcher:
    """
    Handles fuzzy matching and similarity scoring for entity comparison.
    
    Simple fuzzy matching between beneficiary names and contributor names/employers.
    """
    
    def __init__(self, config: SimilarityConfig):
        """
        Initialize the fuzzy matcher.
        
        Args:
            config: Configuration parameters for similarity calculations
        """
        self.config = config
        self._business_suffixes = {
            'inc', 'inc.', 'corp', 'corp.', 'corporation', 'company', 'co', 'co.',
            'llc', 'l.l.c.', 'ltd', 'ltd.', 'limited', 'lp', 'l.p.', 'llp',
            'l.l.p.', 'pllc', 'p.l.l.c.', 'enterprise', 'enterprises', 'group',
            'services', 'solutions', 'systems', 'associates', 'partners'
        }
    
    def calculate_similarity(self, entity1: str, entity2: str) -> SimilarityScore:
        """
        Calculate similarity score between two entities.
        
        Args:
            entity1: First entity name
            entity2: Second entity name
            
        Returns:
            Similarity score between 0 and 100
        """
        if not entity1 or not entity2:
            return 0.0
            
        # Normalize entities for comparison
        norm1 = self._normalize_entity(entity1)
        norm2 = self._normalize_entity(entity2)
        
        # Calculate weighted similarity score
        wratio = fuzz.WRatio(norm1, norm2)
        partial_ratio = fuzz.partial_ratio(norm1, norm2)
        token_sort = fuzz.token_sort_ratio(norm1, norm2)
        token_set = fuzz.token_set_ratio(norm1, norm2)
        
        # Apply weighted average
        similarity = (
            wratio * self.config.wratio_weight +
            partial_ratio * self.config.partial_ratio_weight +
            token_sort * self.config.token_sort_weight +
            token_set * self.config.token_set_weight
        )
        
        return similarity
    
    def find_matches(
        self, 
        beneficiary: str, 
        contributors: List[str], 
        threshold: float = 80.0,
        politician: str = ""
    ) -> List[ConflictMatch]:
        """
        Find potential matches between a beneficiary and contributors.
        
        Args:
            beneficiary: The beneficiary entity to match against
            contributors: List of contributor names to check
            threshold: Minimum similarity score for matches
            politician: Politician name for context
            
        Returns:
            List of potential conflict matches
        """
        matches = []
        
        # Get all possible normalized variants of the beneficiary
        beneficiary_variants = self._get_entity_variants(beneficiary)
        
        for contributor in contributors:
            # Get all possible normalized variants of the contributor
            contributor_variants = self._get_entity_variants(contributor)
            
            # Check all combinations of variants
            best_similarity = 0.0
            best_beneficiary_form = beneficiary
            best_contributor_form = contributor
            
            for ben_variant in beneficiary_variants:
                for con_variant in contributor_variants:
                    similarity = self.calculate_similarity(ben_variant, con_variant)
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_beneficiary_form = ben_variant
                        best_contributor_form = con_variant
            
            # If best match exceeds threshold, record it
            if best_similarity >= threshold:
                matches.append(ConflictMatch(
                    beneficiary=beneficiary,  # Keep original for display
                    contributor=contributor,  # Keep original for display  
                    similarity=best_similarity,
                    match_type=MatchType.NAME,
                    politician=politician
                ))
        
        return matches
    
    def _get_entity_variants(self, entity: str) -> List[str]:
        """
        Get all possible normalized variants of an entity name.
        
        This handles slash notation by creating separate variants for each component,
        rather than just choosing the longest one.
        
        Args:
            entity: Raw entity name
            
        Returns:
            List of normalized variants to check
        """
        if not entity:
            return [""]
        
        variants = []
        
        # Always include the standard normalized form
        standard_normalized = self._normalize_entity(entity)
        if standard_normalized:
            variants.append(standard_normalized)
        
        # Handle slash notation specially - create variants for each component
        if '/' in entity:
            parts = [part.strip() for part in entity.split('/')]
            for part in parts:
                if part:  # Skip empty parts
                    # Normalize each part individually
                    normalized_part = self._normalize_entity_without_slash_handling(part)
                    if normalized_part and normalized_part not in variants:
                        variants.append(normalized_part)
        
        return variants if variants else [""]
    
    def _normalize_entity(self, entity: str) -> str:
        """
        Normalize entity name for comparison.
        
        Args:
            entity: Raw entity name
            
        Returns:
            Normalized entity name
        """
        return self._normalize_entity_without_slash_handling(entity)
    
    def _normalize_entity_without_slash_handling(self, entity: str) -> str:
        """
        Normalize entity name without special slash handling.
        
        This is used when we want to normalize individual components
        of slash-separated entities separately.
        
        Args:
            entity: Raw entity name
            
        Returns:
            Normalized entity name
        """
        if not entity:
            return ""
            
        # Convert to lowercase and strip whitespace
        normalized = entity.lower().strip()
        
        # Remove common punctuation and special characters
        normalized = re.sub(r'[^\w\s&/-]', '', normalized)
        
        # Handle "doing business as" patterns
        dba_patterns = [
            r'\bdoing business as\b',
            r'\bd\.?b\.?a\.?\b',
            r'\baka\b',
            r'\balso known as\b'
        ]
        
        for pattern in dba_patterns:
            if re.search(pattern, normalized):
                # Extract the part after DBA
                parts = re.split(pattern, normalized)
                if len(parts) > 1:
                    normalized = parts[-1].strip()
                    break
        
        # NOTE: No slash handling here - that's handled at the variant level
        
        # Handle "Person of Company" patterns - keep the company name
        if ' of ' in normalized:
            parts = normalized.split(' of ')
            if len(parts) == 2:
                # Keep the company part (after "of")
                normalized = parts[1].strip()
        
        # Handle common abbreviations for better matching
        # Expand SEIU to full name for better matching
        if normalized.startswith('seiu '):
            normalized = normalized.replace('seiu ', 'service employees international union ')
        
        # Normalize union names by removing common phrases that don't distinguish unions
        if 'union' in normalized:
            # Remove generic union terms that don't distinguish between different unions
            union_noise_phrases = [
                'international',
                'local \\d+',  # Local followed by numbers
                'local',
                'small contributor committee',
                'candidate pac',
                'pac',
                'committee',
                '\\d+rn',  # Numbers followed by RN (e.g., 121RN)
                'state',
                'refuse unit',
                'healthcare workers west',
                'interns and resident physician'
            ]
            
            for phrase in union_noise_phrases:
                normalized = re.sub(f'\\b{phrase}\\b', '', normalized, flags=re.IGNORECASE)
            
            # Clean up extra spaces
            normalized = re.sub('\\s+', ' ', normalized).strip()
        
        # Don't remove business suffixes - they're important for distinguishing companies
        return normalized
    

    
    def get_similarity_breakdown(self, entity1: str, entity2: str) -> Dict[str, float]:
        """
        Get detailed breakdown of similarity calculation.
        
        Args:
            entity1: First entity name
            entity2: Second entity name
            
        Returns:
            Dictionary with similarity component scores
        """
        if not entity1 or not entity2:
            return {
                'wratio': 0.0,
                'partial_ratio': 0.0,
                'token_sort': 0.0,
                'token_set': 0.0,
                'final_score': 0.0
            }
        
        norm1 = self._normalize_entity(entity1)
        norm2 = self._normalize_entity(entity2)
        
        # Individual scores
        wratio = fuzz.WRatio(norm1, norm2)
        partial_ratio = fuzz.partial_ratio(norm1, norm2)
        token_sort = fuzz.token_sort_ratio(norm1, norm2)
        token_set = fuzz.token_set_ratio(norm1, norm2)
        
        # Final score
        final_score = (
            wratio * self.config.wratio_weight +
            partial_ratio * self.config.partial_ratio_weight +
            token_sort * self.config.token_sort_weight +
            token_set * self.config.token_set_weight
        )
        
        return {
            'wratio': wratio,
            'partial_ratio': partial_ratio,
            'token_sort': token_sort,
            'token_set': token_set,
            'final_score': final_score
        } 