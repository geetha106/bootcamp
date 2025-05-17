# processing/entity_mapper.py

from collections import defaultdict
from models.paper import Figure, Entity
from processing.base import EntityProcessor
import re
from typing import List, Dict, Set


class EntityMapper(EntityProcessor):
    """Class to map and deduplicate entities"""

    def __init__(self):
        # Thresholds for entity matching
        self.similarity_threshold = 0.85  # Minimum similarity to consider duplicates
        self.max_distance = 3  # Maximum Levenshtein distance for similarity

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using Levenshtein distance"""
        if not text1 or not text2:
            return 0.0

        # Use normalized Levenshtein distance
        from Levenshtein import distance
        max_len = max(len(text1), len(text2))
        if max_len == 0:
            return 1.0
        return 1.0 - (distance(text1, text2) / max_len)

    def is_duplicate(self, entity1: Entity, entity2: Entity) -> bool:
        """Check if two entities are duplicates"""
        # Same type and text is an obvious duplicate
        if entity1.type == entity2.type and entity1.text.lower() == entity2.text.lower():
            return True

        # If types are the same, check for similarity
        if entity1.type == entity2.type:
            similarity = self.calculate_similarity(entity1.text.lower(), entity2.text.lower())
            return similarity >= self.similarity_threshold

        return False

    def process_entities(self, entities: List[Entity]) -> List[Entity]:
        """Process and deduplicate entities"""
        if not entities:
            return []

        # Group entities by type
        entities_by_type = defaultdict(list)
        for entity in entities:
            entities_by_type[entity.type].append(entity)

        # Deduplicate within each type
        deduplicated_entities = []
        for entity_type, type_entities in entities_by_type.items():
            added_entities: Set[str] = set()
            for entity in type_entities:
                # Check if we already have a similar entity
                entity_key = entity.text.lower()
                if entity_key not in added_entities:
                    deduplicated_entities.append(entity)
                    added_entities.add(entity_key)

        return deduplicated_entities

    def map_entities_to_caption(self, caption: str, entities: List[Entity]) -> List[Entity]:
        """Map entities to specific portions of the caption"""
        if not caption or not entities:
            return entities

        caption_lower = caption.lower()
        mapped_entities = []

        for entity in entities:
            entity_text_lower = entity.text.lower()

            # Check if the entity text appears in the caption
            if entity_text_lower in caption_lower:
                # Find all occurrences
                positions = [m.start() for m in re.finditer(re.escape(entity_text_lower), caption_lower)]
                if positions:
                    # Copy the entity with its position in the caption
                    new_entity = Entity(
                        type=entity.type,
                        text=entity.text,
                        id=entity.id,
                        position=positions[0]  # Use the first occurrence position
                    )
                    mapped_entities.append(new_entity)
            else:
                # If no exact match, keep the entity but mark it as unmapped
                entity.position = -1
                mapped_entities.append(entity)

        # Sort entities by their position in the caption
        return sorted(mapped_entities, key=lambda e: e.position if e.position >= 0 else float('inf'))