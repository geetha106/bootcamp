# ingestion/id_converter.py

import requests
from functools import lru_cache
from typing import Optional
from utils.logging import get_logger

logger = get_logger()


@lru_cache(maxsize=128)
def is_pmid(paper_id: str) -> bool:
    """Check if the provided ID is a PMID (all digits)"""
    return paper_id.isdigit()


@lru_cache(maxsize=128)
def convert_pmid_to_pmc(pmid: str) -> str:
    """Convert a PMID to a PMC ID using NCBI E-utilities"""
    try:
        # Use the E-utilities API to convert PMID to PMC ID
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Check if the article has a PMC ID
        result = data.get('result', {})
        article = result.get(pmid, {})

        # Look for PMC ID in the article data
        article_ids = article.get('articleids', [])
        for id_obj in article_ids:
            if id_obj.get('idtype') == 'pmc':
                pmc_id = id_obj.get('value', '')
                if pmc_id:
                    if not pmc_id.startswith("PMC"):
                        pmc_id = f"PMC{pmc_id}"
                    return pmc_id

        logger.warning(f"No PMC ID found for PMID {pmid}")
        return ""
    except Exception as e:
        logger.error(f"Failed to convert PMID to PMC: {e}")
        return ""


@lru_cache(maxsize=128)
def convert_pmc_to_pmid(pmc_id: str) -> str:
    """Convert a PMC ID to a PMID using NCBI E-utilities"""
    # Remove 'PMC' prefix if present for the API call
    pmc_numeric_id = pmc_id.replace("PMC", "")

    try:
        # Use the E-utilities API to convert PMC ID to PMID
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={pmc_id}[pmcid]&retmode=json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Extract the PMID
        id_list = data.get('esearchresult', {}).get('idlist', [])
        if id_list:
            return id_list[0]

        logger.warning(f"No PMID found for PMC ID {pmc_id}")
        return ""
    except Exception as e:
        logger.error(f"Failed to convert PMC to PMID: {e}")
        return ""


def normalize_paper_id(paper_id: str) -> tuple[str, str, str]:
    """
    Normalize a paper ID to get both PMC ID and PMID formats.

    Returns:
        tuple: (original_id, pmc_id, pmid)
    """
    original_id = paper_id
    pmc_id = ""
    pmid = ""

    if is_pmid(paper_id):
        pmid = paper_id
        pmc_id = convert_pmid_to_pmc(paper_id)
    else:
        # Ensure PMC ID has the PMC prefix
        if not paper_id.startswith("PMC"):
            pmc_id = f"PMC{paper_id}"
        else:
            pmc_id = paper_id

        pmid = convert_pmc_to_pmid(pmc_id)

    return original_id, pmc_id, pmid