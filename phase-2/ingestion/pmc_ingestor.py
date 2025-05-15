# pmc_ingestor.py
import requests
import xml.etree.ElementTree as ET
from typing import List
from models.paper import Paper, Figure
from utils.logging import get_logger

logger = get_logger(__name__)


class PMCIngestor():
    BASE_URL = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi"

    def fetch(self, pmc_id: str) -> Paper:
        """
        Fetch a paper from PubMed Central by its PMC ID.
        Returns a Paper model with title, abstract, and figures.
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

        for document in root.findall(".//document"):
            for passage in document.findall("passage"):
                infons = {inf.attrib["key"]: inf.text for inf in passage.findall("infon")}
                section_type = infons.get("section_type", "").lower()

                text_elem = passage.find("text")
                if text_elem is None:
                    continue

                text = text_elem.text

                if section_type == "title" and not title:
                    title = text
                elif section_type == "abstract" and not abstract:
                    abstract = text
                elif section_type == "fig" or "fig_caption" in section_type:
                    caption = text
                    figure_url = None

                    # Try to get figure label from infons
                    label = None
                    for key in ["figure_title", "fig_title", "title"]:
                        if key in infons:
                            label = infons[key]
                            break

                    if not label:
                        # Try to extract figure label from caption
                        if caption and caption.strip().lower().startswith(("figure", "fig")):
                            parts = caption.split(".", 1)
                            if len(parts) > 1:
                                label = parts[0].strip()
                            else:
                                label = "Figure"
                        else:
                            label = f"Figure {len(figures) + 1}"

                    figures.append(Figure(label=label, caption=caption, url=figure_url))

        if not title:
            title = f"Paper {pmc_id}"

        logger.info(f"Extracted paper: {title} with {len(figures)} figures")

        return Paper(
            paper_id=pmc_id,
            title=title,
            abstract=abstract or "",
            figures=figures
        )