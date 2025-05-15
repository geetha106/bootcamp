# pmc_ingestor.py
import requests
import xml.etree.ElementTree as ET
import re
from models.paper import Paper, Figure
from ingestion.base import BaseIngestor
from utils.logging import get_logger

logger = get_logger("figurex.pmc")


class PMCIngestor(BaseIngestor):
    BASE_URL = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi"

    def ingest(self, paper_id: str) -> Paper:
        """
        Implement the base class ingest method to ensure consistency
        """
        return self.fetch(paper_id)

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
        abstract = ""
        figures = []
        figure_passages = []

        # First pass: extract title and abstract and collect figure passages
        for document in root.findall(".//document"):
            abstract_texts = []
            for passage in document.findall("passage"):
                infons = {inf.attrib["key"]: inf.text for inf in passage.findall("infon")}
                section_type = infons.get("section_type", "").lower()

                text_elem = passage.find("text")
                if text_elem is None:
                    continue

                text = text_elem.text

                # Extract title
                if section_type == "title" and not title:
                    title = text

                # Collect all abstract passages
                if section_type == "abstract":
                    abstract_texts.append(text)

                # Collect figure passages for later processing
                if section_type in ["fig", "figure"]:
                    figure_passages.append((infons, text))

            # Join all abstract passages into one
            if abstract_texts:
                abstract = " ".join(abstract_texts)

        # Process figure passages to extract figures
        if figure_passages:
            # Use a regex to extract figure numbers
            figure_pattern = re.compile(r'figure\s+(\d+)|fig\.?\s*(\d+)', re.IGNORECASE)
            figure_dict = {}

            # First, identify and group passages by figure number
            for infons, text in figure_passages:
                # Try to get figure number from infons
                fig_label = infons.get("figure_title", "")
                if not fig_label:
                    fig_label = infons.get("title", "")

                # Extract figure number from label or text
                fig_num = None
                if fig_label:
                    match = figure_pattern.search(fig_label)
                    if match:
                        fig_num = match.group(1) or match.group(2)

                if not fig_num and text:
                    match = figure_pattern.search(text)
                    if match:
                        fig_num = match.group(1) or match.group(2)

                # If we have a figure number, use it
                if fig_num:
                    fig_key = f"Figure {fig_num}"
                    if fig_key not in figure_dict:
                        figure_dict[fig_key] = []
                    figure_dict[fig_key].append(text)
                else:
                    # If we can't determine the figure number, use the label as a fallback
                    if fig_label:
                        if fig_label not in figure_dict:
                            figure_dict[fig_label] = []
                        figure_dict[fig_label].append(text)
                    else:
                        # Last resort, create a generic label
                        generic_label = f"Figure {len(figure_dict) + 1}"
                        if generic_label not in figure_dict:
                            figure_dict[generic_label] = []
                        figure_dict[generic_label].append(text)

            # Now create Figure objects from the grouped passages
            for fig_label, texts in figure_dict.items():
                caption = " ".join(texts)
                figures.append(Figure(
                    label=fig_label,
                    caption=caption,
                    url=None
                ))

        # Fall back to extracting figures from any passage mentioning figures
        if not figures:
            # Look for passages that might contain figure references
            figure_texts = []
            for document in root.findall(".//document"):
                for passage in document.findall("passage"):
                    text_elem = passage.find("text")
                    if text_elem is None:
                        continue

                    text = text_elem.text or ""

                    # Check if this passage might be about a figure
                    if "figure" in text.lower() or "fig." in text.lower() or "fig " in text.lower():
                        figure_texts.append(text)

            # Group these texts by figure number
            figure_dict = {}
            for text in figure_texts:
                # Try to determine which figure this is
                match = figure_pattern.search(text)
                if match:
                    fig_num = match.group(1) or match.group(2)
                    fig_key = f"Figure {fig_num}"
                    if fig_key not in figure_dict:
                        figure_dict[fig_key] = []
                    figure_dict[fig_key].append(text)
                else:
                    # If we can't determine the figure number, use a generic label
                    generic_label = f"Figure {len(figure_dict) + 1}"
                    if generic_label not in figure_dict:
                        figure_dict[generic_label] = []
                    figure_dict[generic_label].append(text)

            # Create Figure objects from the grouped texts
            for fig_label, texts in figure_dict.items():
                caption = " ".join(texts)
                figures.append(Figure(
                    label=fig_label,
                    caption=caption,
                    url=None
                ))

        logger.info(f"Extracted {len(figures)} unique figures from paper {pmc_id}")

        return Paper(
            paper_id=pmc_id,
            title=title or f"PMC{pmc_id}",
            abstract=abstract,
            figures=figures
        )