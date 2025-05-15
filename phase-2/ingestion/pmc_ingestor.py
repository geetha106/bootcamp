#pmc_ingestor.py
import requests
import xml.etree.ElementTree as ET
from models.paper import Paper, Figure

from rich.logging import RichHandler
import logging

logging.basicConfig(level="INFO", handlers=[RichHandler()])
logger = logging.getLogger("figurex")

class PMCIngestor():
    BASE_URL = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi"

    def fetch(self, pmc_id: str) -> Paper:
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
        figures = []

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
                elif section_type == "fig":
                    caption = text
                    figure_url = None  # No URL in BioC, maybe construct using known patterns or skip
                    label = infons.get("figure_title", "Unknown Figure")
                    figures.append(Figure(label=label, caption=caption, url=figure_url))

        return Paper(
            paper_id=pmc_id,
            title=title or f"PMC{pmc_id}",
            abstract=abstract or "",
            figures=figures
        )
