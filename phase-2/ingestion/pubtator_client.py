#pubtator_client.py
import requests
from typing import List
from models.paper import Entity
import logging

logger = logging.getLogger(__name__)

class PubTatorClient:
    BASE_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publication"

    def fetch_entities(self, pmid_or_pmcid: str) -> List[Entity]:

        if pmid_or_pmcid.startswith("PMC"):
            logger.warning(f"PubTator does not support PMCIDs. Skipping ID: {pmid_or_pmcid}")
            return []

        url = f"{self.BASE_URL}/{pmid_or_pmcid}/export/pubtator"
        try:
            response = requests.get(url)
            response.raise_for_status()
            pubtator_text = response.text
        except Exception as e:
            logger.error(f"PubTator request failed: {e}")
            return []

        entities = []
        for line in pubtator_text.strip().split("\n"):
            if line.startswith("#") or "|" not in line:
                continue
            parts = line.split("\t")
            if len(parts) < 6:
                continue  # skip malformed lines

            try:
                start, end = int(parts[1]), int(parts[2])
                mention = parts[3]
                entity_type = parts[4]
                entities.append(Entity(text=mention, type=entity_type, start=start, end=end))
            except ValueError:
                logger.warning(f"Skipping line with invalid integers: {line}")
                continue

        return entities
