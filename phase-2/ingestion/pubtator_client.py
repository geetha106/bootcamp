# pubtator_client.py
import requests
from typing import List, Dict, Any
import re
from models.paper import Entity
from utils.logging import get_logger
import time
import spacy
from collections import defaultdict

logger = get_logger(__name__)


class PubTatorClient:
    BASE_URL = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api"

    def __init__(self):
        """Initialize the PubTator client and load NLP model for fallback extraction"""
        # Try to load spaCy model for fallback NER
        try:
            self.nlp = spacy.load("en_core_web_sm")
            self.has_spacy = True
            logger.info("Loaded spaCy NER model for fallback entity extraction")
        except Exception:
            self.has_spacy = False
            logger.warning("Could not load spaCy model for fallback entity extraction")

    def fetch_entities(self, id_value: str) -> List[Entity]:
        """
        Fetch entities from PubTator using PubMed ID or PMC ID.
        Attempts multiple methods to ensure we get entities.
        """
        entities = []

        # Method 1: Try PubTator3 API
        entities = self._try_pubtator3_api(id_value)
        if entities:
            return entities

        # Method 2: Try legacy PubTator format
        entities = self._try_legacy_pubtator(id_value)
        if entities:
            return entities

        # Method 3: Try EUtils PubMed API to get abstract + extract entities from it
        abstract = self._fetch_abstract_from_eutils(id_value)
        if abstract:
            entities = self.extract_entities_from_text(abstract)
            if entities:
                return entities

        # If all methods fail, return empty list
        logger.warning(f"Could not extract entities for {id_value} through any method")
        return []

    def _try_pubtator3_api(self, id_value: str) -> List[Entity]:
        """Try the PubTator3 API with different ID formats"""
        entities = []

        # Determine ID type
        if id_value.startswith("PMC"):
            id_type = "pmcid"
            query_id = id_value.replace("PMC", "")
        else:
            id_type = "pmid"
            query_id = id_value

        # URLs to try
        urls = [
            f"{self.BASE_URL}/publications/{id_type}/{query_id}/annotations",
            f"https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/RESTful/tmTool.cgi/{id_type}/{query_id}/Chemical,Disease,Gene/JSON",
            f"https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/RESTful/tmTool.cgi/{id_type}/{query_id}/BioConcept/JSON"
        ]

        for url in urls:
            logger.info(f"Trying PubTator API URL: {url}")
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()

                # Process response based on API format
                if "annotations" in data:
                    # Standard PubTator3 format
                    for annotation in data["annotations"]:
                        if "infons" in annotation and "text" in annotation:
                            entity_type = annotation["infons"].get("type", "UNKNOWN")
                            mention = annotation["text"]
                            locations = annotation.get("locations", [])
                            start = locations[0]["offset"] if locations else None
                            end = start + len(mention) if start is not None else None

                            entities.append(Entity(
                                text=mention,
                                type=entity_type,
                                start=start,
                                end=end
                            ))

                elif isinstance(data, list):
                    # CBBresearch format
                    for doc in data:
                        for denotation in doc.get("denotations", []):
                            entity_id = denotation.get("id", "")
                            span = denotation.get("span", {})
                            start = span.get("begin")
                            end = span.get("end")

                            # Get entity text and type
                            entity_text = ""
                            entity_type = "UNKNOWN"

                            # Find matching object annotation
                            for obj in doc.get("objects", []):
                                if obj.get("id") == entity_id:
                                    entity_text = obj.get("name", "")
                                    entity_type = obj.get("type", "UNKNOWN")
                                    break

                            if not entity_text and "text" in doc:
                                # Extract text from document if available
                                try:
                                    entity_text = doc["text"][start:end]
                                except (IndexError, TypeError):
                                    pass

                            if entity_text:
                                entities.append(Entity(
                                    text=entity_text,
                                    type=entity_type,
                                    start=start,
                                    end=end
                                ))

                if entities:
                    logger.info(f"Successfully extracted {len(entities)} entities from {url}")
                    return entities

            except Exception as e:
                logger.error(f"Error with {url}: {e}")

        return []

    def _try_legacy_pubtator(self, id_value: str) -> List[Entity]:
        """Try the legacy PubTator format"""
        logger.info(f"Trying legacy PubTator format for {id_value}")

        # Remove PMC prefix if present
        if id_value.startswith("PMC"):
            query_id = id_value.replace("PMC", "")
        else:
            query_id = id_value

        # URLs to try
        urls = [
            f"https://www.ncbi.nlm.nih.gov/research/pubtator3/publications/export/pubtator?pmcids={query_id}",
            f"https://www.ncbi.nlm.nih.gov/research/pubtator3/publications/export/pubtator?pmids={query_id}",
            f"https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/RESTful/tmTool.cgi/BioConcept/{query_id}/PubTator/"
        ]

        for url in urls:
            try:
                logger.info(f"Trying legacy URL: {url}")
                response = requests.get(url)
                response.raise_for_status()
                pubtator_text = response.text

                entities = []
                for line in pubtator_text.strip().split("\n"):
                    if line.startswith("#") or "|t|" in line or "|a|" in line:
                        continue

                    parts = line.split("\t")
                    if len(parts) < 5:
                        continue  # Skip malformed lines

                    try:
                        if len(parts) >= 6:
                            # Standard PubTator format
                            start, end = int(parts[1]), int(parts[2])
                            mention = parts[3]
                            entity_type = parts[4]
                        else:
                            # Some variations have fewer columns
                            mention = parts[2]
                            entity_type = parts[3]
                            start = end = None

                        entities.append(Entity(
                            text=mention,
                            type=entity_type,
                            start=start,
                            end=end
                        ))
                    except (ValueError, IndexError):
                        continue

                if entities:
                    logger.info(f"Successfully extracted {len(entities)} entities using legacy format")
                    return entities

            except Exception as e:
                logger.error(f"Legacy PubTator request failed: {e}")

        return []

    def _fetch_abstract_from_eutils(self, id_value: str) -> str:
        """Fetch abstract from NCBI EUtils"""
        logger.info(f"Trying to fetch abstract from EUtils for {id_value}")

        try:
            # Remove PMC prefix if present and determine ID type
            if id_value.startswith("PMC"):
                db = "pmc"
                query_id = id_value.replace("PMC", "")
            else:
                db = "pubmed"
                query_id = id_value

            # Use EFetch to get the abstract
            url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db={db}&id={query_id}&retmode=xml"
            response = requests.get(url)
            response.raise_for_status()
            xml_text = response.text

            # Extract abstract using regex
            abstract_pattern = r"<AbstractText[^>]*>(.*?)</AbstractText>"
            abstract_matches = re.findall(abstract_pattern, xml_text, re.DOTALL)

            if abstract_matches:
                # Combine all abstract sections
                abstract = " ".join(abstract_matches)
                # Clean up XML tags
                abstract = re.sub(r"<[^>]+>", "", abstract)
                logger.info(f"Retrieved abstract of length {len(abstract)} characters")
                return abstract

            # Try to find title if abstract is not available
            title_pattern = r"<ArticleTitle>(.*?)</ArticleTitle>"
            title_match = re.search(title_pattern, xml_text)

            if title_match:
                logger.info("No abstract found, using title for entity extraction")
                return title_match.group(1)

        except Exception as e:
            logger.error(f"Failed to fetch abstract from EUtils: {e}")

        return ""

    def extract_entities_from_text(self, text: str) -> List[Entity]:
        """
        Extract entities from text using spaCy or rule-based methods.
        This is used as a fallback when API methods fail.
        """
        entities = []

        # Method 1: Using spaCy if available
        if self.has_spacy and text:
            logger.info("Extracting entities using spaCy NER")

            # Process text with spaCy
            doc = self.nlp(text)

            # Entity mapping for spaCy entity types
            entity_type_map = {
                "ORG": "ORGANIZATION",
                "PERSON": "PERSON",
                "GPE": "LOCATION",
                "LOC": "LOCATION",
                "NORP": "GROUP",
                "FAC": "LOCATION",
                "PRODUCT": "PRODUCT",
                "EVENT": "EVENT",
                "WORK_OF_ART": "CREATION",
                "LAW": "LAW",
                "LANGUAGE": "LANGUAGE",
                "DATE": "DATE",
                "TIME": "TIME",
                "PERCENT": "PERCENT",
                "MONEY": "MONEY",
                "QUANTITY": "QUANTITY",
                "ORDINAL": "ORDINAL",
                "CARDINAL": "NUMBER"
            }

            # Extract entities
            for ent in doc.ents:
                entity_type = entity_type_map.get(ent.label_, "MISC")

                # Map to biomedical entities based on text patterns
                if re.search(r"\b(protein|gene|receptor|enzyme|factor)\b", ent.text, re.I):
                    entity_type = "GENE"
                elif re.search(r"\b(disease|syndrome|disorder|infection|cancer|tumor)\b", ent.text, re.I):
                    entity_type = "DISEASE"
                elif re.search(r"\b(drug|compound|molecule|inhibitor|antibody|medication)\b", ent.text, re.I):
                    entity_type = "CHEMICAL"

                entities.append(Entity(
                    text=ent.text,
                    type=entity_type,
                    start=ent.start_char,
                    end=ent.end_char
                ))

        # Method 2: Simple regex-based extraction for biomedical terms
        if not entities and text:
            logger.info("Using regex patterns for entity extraction")

            # Simple patterns for biomedical entities
            patterns = {
                r"\b[A-Z][A-Za-z0-9]+-[0-9]+\b": "GENE",  # Gene patterns like IL-6, TNF-α
                r"\b[A-Z][A-Za-z0-9]+[0-9]+\b": "GENE",  # Gene patterns like BRCA1, p53
                r"\b[A-Z]{2,}[0-9]*\b": "GENE",  # Gene patterns like TNF, IL2
                r"\b[a-z]+[A-Z][a-z]+\b": "GENE",  # Camel case genes like mTOR
                r"\b[A-Za-z\s]+ (syndrome|disease|disorder|cancer)\b": "DISEASE",
                r"\b[A-Za-z]+[ia]sis\b": "DISEASE",  # Diseases ending in -iasis or -osis
                r"\b[A-Za-z]+[io]ma\b": "DISEASE",  # Diseases ending in -oma or -ima
                r"\b[A-Za-z]+ (receptor|kinase|phosphatase)\b": "PROTEIN",
                r"\b[0-9]+-[a-z]+-[0-9]+-[a-z]+\b": "CHEMICAL"  # Chemical formulas
            }

            # Extract entities based on patterns
            for pattern, entity_type in patterns.items():
                for match in re.finditer(pattern, text):
                    entities.append(Entity(
                        text=match.group(0),
                        type=entity_type,
                        start=match.start(),
                        end=match.end()
                    ))

        # Method 3: Dictionary lookup for common biomedical terms
        # This is a very simplified version of a dictionary approach
        common_terms = {
            "metformin": "CHEMICAL",
            "nitrosamine": "CHEMICAL",
            "NDMA": "CHEMICAL",
            "N-Nitrosodimethylamine": "CHEMICAL",
            "diabetes": "DISEASE",
            "cancer": "DISEASE",
            "carcinogen": "CHEMICAL",
            "FDA": "ORGANIZATION",
            "HPLC": "METHOD",
            "chromatography": "METHOD",
            "mass spectrometry": "METHOD",
            "LC-MS": "METHOD"
        }

        for term, entity_type in common_terms.items():
            if term.lower() in text.lower():
                # Find all occurrences (case-insensitive)
                term_pattern = re.compile(re.escape(term), re.IGNORECASE)
                for match in term_pattern.finditer(text):
                    entities.append(Entity(
                        text=match.group(0),
                        type=entity_type,
                        start=match.start(),
                        end=match.end()
                    ))

        # Deduplicate entities
        unique_entities = []
        seen = set()

        for entity in entities:
            entity_key = (entity.text.lower(), entity.type)
            if entity_key not in seen:
                seen.add(entity_key)
                unique_entities.append(entity)

        logger.info(f"Extracted {len(unique_entities)} unique entities from text")
        return unique_entities