# processing/caption_cleaner.py

import re
from bs4 import BeautifulSoup
from models.paper import Figure
from processing.base import CaptionProcessor


class CaptionCleaner(CaptionProcessor):
    """Class to clean and normalize figure captions"""

    def __init__(self):
        # Common HTML entities and their replacements
        self.html_replacements = {
            '&lt;': '<',
            '&gt;': '>',
            '&amp;': '&',
            '&quot;': '"',
            '&apos;': "'",
            '&nbsp;': ' ',
        }

        # Patterns to remove
        self.patterns_to_remove = [
            r'<[^>]+>',  # HTML tags
            r'\[\d+\]',  # Citation numbers
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',  # URLs
        ]

    def clean_caption(self, caption: str) -> str:
        """Clean and normalize a caption"""
        if not caption:
            return ""

        # Replace HTML entities
        for entity, replacement in self.html_replacements.items():
            caption = caption.replace(entity, replacement)

        # Remove HTML tags using BeautifulSoup
        try:
            soup = BeautifulSoup(caption, 'html.parser')
            caption = soup.get_text()
        except Exception:
            # If BeautifulSoup fails, use regex as fallback
            for pattern in self.patterns_to_remove:
                caption = re.sub(pattern, '', caption)

        # Remove extra whitespace
        caption = re.sub(r'\s+', ' ', caption).strip()

        # Normalize punctuation
        caption = re.sub(r'\.{2,}', '...', caption)  # Replace multiple periods with ellipsis
        caption = re.sub(r'\s([.,;:!?])', r'\1', caption)  # Remove space before punctuation

        return caption

    def process_figure(self, figure: Figure) -> Figure:
        """Process a figure's caption"""
        figure.caption = self.clean_caption(figure.caption)
        return figure