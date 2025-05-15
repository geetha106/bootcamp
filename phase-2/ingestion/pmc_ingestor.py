# pmc_ingestor.py
import requests
import xml.etree.ElementTree as ET
from models.paper import Paper, Figure
from typing import List
from utils.logging import get_logger

logger = get_logger(__name__)


class PMCIngestor():
    BASE_URL = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi"

    def fetch(self, pmc_id: str) -> Paper:
        """
        Fetch a paper from PMC and extract its title, abstract, and figures.

        Args:
            pmc_id: The PMC ID of the paper, with or without "PMC" prefix

        Returns:
            Paper object with title, abstract, and figures
        """
        # Ensure pmc_id has 'PMC' prefix
        if not pmc_id.startswith("PMC"):
            pmc_id = f"PMC{pmc_id}"

        url = f"{self.BASE_URL}/BioC_xml/{pmc_id}/unicode"
        logger.info(f"Fetching from URL: {url}")

        response = requests.get(url)
        response.raise_for_status()
        xml_text = response.text

        if "[Error]" in xml_text:
            raise ValueError(f"PMC returned error: {xml_text.strip()}")

        root = ET.fromstring(xml_text)

        title = None
        abstract = None
        figures: List[Figure] = []

        # Extract document info from BioC XML
        for document in root.findall(".//document"):
            # First, try to get the title
            for passage in document.findall("passage"):
                infons = {inf.attrib["key"]: inf.text for inf in passage.findall("infon")}
                section_type = infons.get("section_type", "").lower()

                text_elem = passage.find("text")
                if text_elem is None or not text_elem.text:
                    continue

                text = text_elem.text

                # Extract title
                if section_type == "title" and not title:
                    title = text

                # Extract abstract
                elif section_type == "abstract" and not abstract:
                    abstract = text

                # Extract figures
                elif section_type == "fig" or "fig" in section_type or "figure" in section_type:
                    caption = text
                    figure_url = None  # PMC BioC format doesn't include URLs directly

                    # Try to get figure label from different sources
                    label = (
                            infons.get("fig_type", "") or
                            infons.get("figure_title", "") or
                            infons.get("title", "")
                    )

                    # If no label found, create a generic one based on figure count
                    if not label or label.lower() in ["fig", "figure"]:
                        label = f"Figure {len(figures) + 1}"

                    figures.append(Figure(label=label, caption=caption, url=figure_url))

        # Log extraction results
        logger.info(f"Extracted paper: {title or pmc_id} with {len(figures)} figures")

        return Paper(
            paper_id=pmc_id,
            title=title or f"Untitled Paper ({pmc_id})",
            abstract=abstract or "",
            figures=figures
        )