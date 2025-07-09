"""
Entity name normalization for conflict analysis.

This module provides comprehensive entity name normalization capabilities
for standardizing and grouping related business entities.
"""

import re
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass

from .types import EntityData


@dataclass
class EntityGroup:
    """Represents a group of related entities."""
    canonical_name: str
    aliases: List[str]
    original_names: List[str]
    confidence_score: float


class EntityNormalizer:
    """
    Handles entity name normalization and grouping.
    
    This class is responsible for:
    - Normalizing entity names for comparison
    - Grouping related entities together
    - Handling business suffix variations
    - Processing "doing business as" patterns
    - Standardizing entity representations
    """
    
    def __init__(self):
        """Initialize the entity normalizer."""
        self._business_suffixes = {
            'inc', 'inc.', 'incorporated',
            'corp', 'corp.', 'corporation',
            'company', 'co', 'co.',
            'llc', 'l.l.c.',
            'ltd', 'ltd.', 'limited',
            'lp', 'l.p.',
            'llp', 'l.l.p.',
            'pllc', 'p.l.l.c.',
            'enterprise', 'enterprises',
            'group', 'groups',
            'services', 'service',
            'solutions', 'solution',
            'systems', 'system',
            'associates', 'associate',
            'partners', 'partner',
            'holdings', 'holding',
            'international', 'intl'
        }
        
        self._dba_patterns = [
            r'\bdoing business as\b',
            r'\bd\.?b\.?a\.?\b',
            r'\baka\b',
            r'\balso known as\b',
            r'\boperating as\b',
            r'\btrading as\b'
        ]
        
        self._name_connectors = {
            'and', '&', 'with', 'plus', 'or', 'of', 'for', 'in', 'at', 'on'
        }
        
        self._stop_words = {
            'the', 'a', 'an', 'this', 'that', 'these', 'those'
        }
    
    def normalize_entity_name(self, name: str) -> str:
        """
        Normalize a single entity name.
        
        Args:
            name: Raw entity name to normalize
            
        Returns:
            Normalized entity name
        """
        if not name or not name.strip():
            return ""
        
        # Start with basic cleaning
        normalized = self._basic_clean(name)
        
        # Handle DBA patterns
        normalized = self._handle_dba_patterns(normalized)
        
        # Handle slash notation
        normalized = self._handle_slash_notation(normalized)
        
        # Remove business suffixes
        normalized = self._remove_business_suffixes(normalized)
        
        # Remove stop words
        normalized = self._remove_stop_words(normalized)
        
        # Final cleanup
        normalized = self._final_cleanup(normalized)
        
        return normalized
    
    def group_related_entities(self, entities: List[str], threshold: float = 0.8) -> List[EntityGroup]:
        """
        Group related entities together.
        
        Args:
            entities: List of entity names to group
            threshold: Similarity threshold for grouping
            
        Returns:
            List of entity groups
        """
        if not entities:
            return []
        
        # Normalize all entities
        normalized_entities = {}
        for entity in entities:
            normalized = self.normalize_entity_name(entity)
            if normalized:  # Only include non-empty normalized names
                if normalized not in normalized_entities:
                    normalized_entities[normalized] = []
                normalized_entities[normalized].append(entity)
        
        # Create groups based on normalized names
        groups = []
        for normalized_name, original_names in normalized_entities.items():
            group = EntityGroup(
                canonical_name=self._select_canonical_name(original_names),
                aliases=list(set(original_names)),
                original_names=original_names,
                confidence_score=1.0  # Perfect match since they normalize to same name
            )
            groups.append(group)
        
        return groups
    
    def get_canonical_name(self, entity_group: EntityGroup) -> str:
        """
        Get the canonical name for an entity group.
        
        Args:
            entity_group: The entity group
            
        Returns:
            Canonical name for the group
        """
        return entity_group.canonical_name
    
    def standardize_entity_names(self, entities: List[str]) -> Dict[str, str]:
        """
        Create a mapping from original names to standardized names.
        
        Args:
            entities: List of entity names to standardize
            
        Returns:
            Dictionary mapping original names to standardized names
        """
        groups = self.group_related_entities(entities)
        
        name_mapping = {}
        for group in groups:
            canonical_name = group.canonical_name
            for original_name in group.original_names:
                name_mapping[original_name] = canonical_name
        
        return name_mapping
    
    def _basic_clean(self, name: str) -> str:
        """Apply basic cleaning to entity name."""
        # Convert to lowercase and strip
        cleaned = name.lower().strip()
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove common punctuation but keep important business symbols
        cleaned = re.sub(r'[^\w\s&/\-\.]', '', cleaned)
        
        # Normalize common abbreviations
        cleaned = re.sub(r'\bst\b', 'street', cleaned)
        cleaned = re.sub(r'\bave\b', 'avenue', cleaned)
        cleaned = re.sub(r'\brd\b', 'road', cleaned)
        cleaned = re.sub(r'\bblvd\b', 'boulevard', cleaned)
        
        return cleaned
    
    def _handle_dba_patterns(self, name: str) -> str:
        """Handle 'doing business as' patterns."""
        for pattern in self._dba_patterns:
            if re.search(pattern, name, re.IGNORECASE):
                # Split on the pattern and take the part after it
                parts = re.split(pattern, name, flags=re.IGNORECASE)
                if len(parts) > 1:
                    # Take the last part (after the DBA)
                    after_dba = parts[-1].strip()
                    if after_dba:
                        return after_dba
        return name
    
    def _handle_slash_notation(self, name: str) -> str:
        """Handle slash notation (e.g., 'Company A/Company B')."""
        if '/' in name:
            parts = [part.strip() for part in name.split('/')]
            if len(parts) > 1:
                # Take the longer/more specific part
                return max(parts, key=len)
        return name
    
    def _remove_business_suffixes(self, name: str) -> str:
        """Remove business suffixes from entity name."""
        words = name.split()
        filtered_words = []
        
        for word in words:
            # Remove trailing punctuation for comparison
            clean_word = word.rstrip('.,;:')
            if clean_word.lower() not in self._business_suffixes:
                filtered_words.append(word)
        
        return ' '.join(filtered_words) if filtered_words else name
    
    def _remove_stop_words(self, name: str) -> str:
        """Remove stop words from entity name."""
        words = name.split()
        filtered_words = []
        
        for word in words:
            if word.lower() not in self._stop_words:
                filtered_words.append(word)
        
        return ' '.join(filtered_words) if filtered_words else name
    
    def _final_cleanup(self, name: str) -> str:
        """Apply final cleanup to normalized name."""
        # Remove extra whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Remove trailing punctuation
        name = re.sub(r'[^\w\s]+$', '', name)
        
        # Remove leading punctuation
        name = re.sub(r'^[^\w\s]+', '', name)
        
        return name
    
    def _select_canonical_name(self, names: List[str]) -> str:
        """
        Select the canonical name from a list of related names.
        
        Args:
            names: List of related entity names
            
        Returns:
            The canonical name to use for the group
        """
        if not names:
            return ""
        
        if len(names) == 1:
            return names[0]
        
        # Prefer names that are:
        # 1. Longer (more descriptive)
        # 2. Don't contain abbreviations
        # 3. Are more commonly used business names
        
        scored_names = []
        for name in names:
            score = 0
            
            # Length bonus
            score += len(name) * 0.1
            
            # Prefer full words over abbreviations
            if not re.search(r'\b\w\.\w\b', name):
                score += 10
            
            # Prefer names without numbers (often more generic)
            if not re.search(r'\d', name):
                score += 5
            
            # Prefer names that don't start with initials
            if not re.match(r'^[A-Z]\s+[A-Z]', name):
                score += 5
            
            scored_names.append((score, name))
        
        # Sort by score (descending) and return the best
        scored_names.sort(reverse=True)
        return scored_names[0][1]
    
    def get_normalization_stats(self, entities: List[str]) -> Dict[str, any]:
        """
        Get statistics about entity normalization.
        
        Args:
            entities: List of entity names
            
        Returns:
            Statistics about normalization results
        """
        if not entities:
            return {
                'total_entities': 0,
                'unique_normalized': 0,
                'compression_ratio': 0.0,
                'groups': []
            }
        
        groups = self.group_related_entities(entities)
        
        total_entities = len(entities)
        unique_normalized = len(groups)
        compression_ratio = unique_normalized / total_entities if total_entities > 0 else 0.0
        
        group_stats = []
        for group in groups:
            group_stats.append({
                'canonical_name': group.canonical_name,
                'entity_count': len(group.original_names),
                'aliases': group.aliases,
                'confidence': group.confidence_score
            })
        
        return {
            'total_entities': total_entities,
            'unique_normalized': unique_normalized,
            'compression_ratio': compression_ratio,
            'groups': group_stats
        } 