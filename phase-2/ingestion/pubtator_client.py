# pubtator_client.py
import requests
from typing import List, Optional
import os
import yaml
from models.paper import Entity
from utils.logging import get_logger
from config.config import get_config

logger = get_logger("figurex.pubtator")


class PubTatorClient:
    BASE_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/export/pubtator"

    def __init__(self):
        """Initialize the PubTator client with API key from settings"""
        self.api_key = self._get_api_key()
        if self.api_key:
            logger.info("PubTator client initialized with NCBI API key")
        else:
            logger.warning("No NCBI API key found - rate limiting will be strict")

    def _get_api_key(self) -> Optional[str]:
        """Get the NCBI API key from settings.yaml"""
        try:
            # Load settings from yaml file
            with open("settings.yaml", "r") as f:
                settings = yaml.safe_load(f)

            # Extract NCBI API key if available
            return settings.get("ncbi", {}).get("api_key")
        except Exception as e:
            logger.error(f"Error loading API key from settings: {e}")
            return None

    def fetch_entities(self, pmid_or_pmcid: str) -> List[Entity]:
        """
        Fetch entities from PubTator for a given PMID or PMCID
        """
        # If it's a PMC ID, try to process it properly
        original_id = pmid_or_pmcid
        if pmid_or_pmcid.startswith("PMC"):
            pmid_or_pmcid = pmid_or_pmcid.replace("PMC", "")
            logger.info(f"Modified PMC ID to numeric format: {pmid_or_pmcid}")

        # PubTator endpoint expects comma-separated IDs
        url = f"{self.BASE_URL}?pmids={pmid_or_pmcid}"
        logger.info(f"Fetching entities from PubTator URL: {url}")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            pubtator_text = response.text
            logger.info(f"PubTator response length: {len(pubtator_text)} characters")

            if not pubtator_text.strip():
                logger.warning(f"Empty response from PubTator for ID: {original_id}")
                return []

        except Exception as e:
            logger.error(f"PubTator request failed: {e}")
            return []

        entities = []
        for line in pubtator_text.strip().split("\n"):
            # Debug raw line
            logger.debug(f"Processing line: {line}")

            # Skip title and abstract lines which contain | character
            if "|" in line:
                continue

            # Skip comment lines
            if line.startswith("#"):
                continue

            parts = line.split("\t")
            if len(parts) < 6:
                logger.debug(f"Skipping line with insufficient parts: {line}")
                continue  # skip malformed lines

            try:
                entity_id = parts[0].strip()
                start, end = int(parts[1]), int(parts[2])
                mention = parts[3]
                entity_type = parts[4]

                logger.debug(f"Found entity: {mention} ({entity_type})")
                entities.append(Entity(text=mention, type=entity_type, start=start, end=end))
            except ValueError:
                logger.warning(f"Skipping line with invalid integers: {line}")
                continue
            except Exception as e:
                logger.warning(f"Error processing entity line: {e}")
                continue

        logger.info(f"Retrieved {len(entities)} entities from PubTator")
        return entities