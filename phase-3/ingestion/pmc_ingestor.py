# pmc_ingestor.py
import requests
import yaml
import xml.etree.ElementTree as ET
from models.paper import Paper, Figure
from ingestion.base import BaseIngestor
from utils.logging import get_logger
from config.config import get_config
from collections import defaultdict
import re

logger = get_logger("figurex.pmc")


class PMCIngestor(BaseIngestor):
    def __init__(self):
        """Initialize the PMC ingestor with API key from settings"""
        config = get_config()
        self.base_url = config.ncbi.pmc_base_url
        self.api_key = config.ncbi.api_key
        if self.api_key:
            logger.info("PMC ingestor initialized with NCBI API key")
        else:
            logger.warning("No NCBI API key found - rate limiting will be strict")

    def ingest(self, paper_id: str) -> Paper:
        """
        Implement the base class ingest method to ensure consistency
        """
        return self.fetch(paper_id)

    def fetch(self, pmc_id: str) -> Paper:
        # Ensure pmc_id has 'PMC' prefix
        if not pmc_id.startswith("PMC"):
            pmc_id = f"PMC{pmc_id}"

        url = f"{self.base_url}/BioC_xml/{pmc_id}/unicode"
        logger.info(f"Fetching from URL: {url}")

        response = requests.get(url)
        response.raise_for_status()
        xml_text = response.text

        if "[Error]" in xml_text:
            raise ValueError(f"PMC returned error: {xml_text.strip()}")

        root = ET.fromstring(xml_text)

        title = None
        abstract = None

        # Use defaultdict to collect all passages for each figure
        figure_data = defaultdict(lambda: {"label": "", "caption": ""})

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
                    # Extract the figure identifier to group related passages
                    fig_id = infons.get("id", "")

                    # Some papers might use figure_id instead of id
                    if not fig_id and "figure_id" in infons:
                        fig_id = infons.get("figure_id", "")

                    # If we still don't have an ID, try creating one from the figure title/label
                    if not fig_id and "figure_title" in infons:
                        # Extract numeric part from figure title to create an ID
                        fig_title = infons.get("figure_title", "")
                        match = re.search(r'(\d+)', fig_title)
                        if match:
                            fig_id = f"fig{match.group(1)}"
                        else:
                            fig_id = fig_title

                    # If still no ID, use a counter (last resort)
                    if not fig_id:
                        fig_id = f"fig_{len(figure_data) + 1}"

                    # Update figure data
                    if "figure_title" in infons:
                        figure_data[fig_id]["label"] = infons["figure_title"]

                    # Append to caption (with space if not empty)
                    if figure_data[fig_id]["caption"]:
                        figure_data[fig_id]["caption"] += " " + text
                    else:
                        figure_data[fig_id]["caption"] = text

        # Convert collected figure data to Figure objects
        figures = []
        # Sort by any numeric part in the fig_id to maintain order
        sorted_fig_ids = sorted(figure_data.keys(), 
                              key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else float('inf'))
        
        for i, fig_id in enumerate(sorted_fig_ids, 1):
            data = figure_data[fig_id]
            figure_url = None  # No URL in BioC, maybe construct using known patterns or skip
            figures.append(Figure(
                label=f"Figure {i}",  # Use sequential numbering
                caption=data["caption"],
                url=figure_url
            ))

        return Paper(
            paper_id=pmc_id,
            title=title or f"PMC{pmc_id}",
            abstract=abstract or "",
            figures=figures
        )