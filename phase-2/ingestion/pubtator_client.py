# pubtator_client.py
import requests
from typing import List, Dict
from models.paper import Entity
from utils.logging import get_logger

logger = get_logger(__name__)


class PubTatorClient:
    BASE_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications"

    def fetch_entities(self, id_value: str) -> List[Entity]:
        """
        Fetch entities from PubTator for a given ID.

        Args:
            id_value: Can be either PMID (just numbers) or PMC ID (with or without "PMC" prefix)

        Returns:
            List of Entity objects extracted from PubTator
        """
        # Clean up the ID value
        # Remove PMC prefix if present
        if id_value.upper().startswith("PMC"):
            id_value = id_value[3:]
            id_type = "pmcid"
        else:
            id_type = "pmid"

        # Construct the PubTator API URL
        url = f"{self.BASE_URL}/{id_type}/{id_value}/annotations"
        logger.info(f"Querying PubTator with {id_type.upper()} {id_value} at URL: {url}")

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            if not data:
                logger.warning(f"PubTator returned empty data for {id_type.upper()} {id_value}")
                return []

        except Exception as e:
            logger.error(f"PubTator request failed for {id_type.upper()} {id_value}: {e}")
            return []

        # Parse the JSON response
        entities: List[Entity] = []
        entity_dict: Dict[str, Entity] = {}  # To avoid duplicates

        try:
            # Extract annotations from the response
            annotations = data.get("annotations", [])

            for annotation in annotations:
                mention = annotation.get("text", "")
                entity_type = annotation.get("type", "")
                locations = annotation.get("locations", [])

                if not mention or not entity_type or not locations:
                    continue

                # Get the first location
                location = locations[0]
                start = location.get("offset", 0)
                end = start + location.get("length", 0)

                # Create unique key for this entity to avoid duplicates
                entity_key = f"{mention}_{entity_type}"

                if entity_key not in entity_dict:
                    entity = Entity(text=mention, type=entity_type, start=start, end=end)
                    entity_dict[entity_key] = entity
                    entities.append(entity)

            logger.info(f"Found {len(entities)} unique entities for {id_type.upper()} {id_value}")

        except Exception as e:
            logger.error(f"Error parsing PubTator response: {e}")

        return entities