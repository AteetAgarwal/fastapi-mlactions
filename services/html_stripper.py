import html
from html.parser import HTMLParser
import re
import string
import unicodedata


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)

def _strip_tags(text: str) -> str:
    stripper = MLStripper()
    stripper.feed(text)
    return stripper.get_data()

def clean_text_advanced(text: str) -> str:
    """
    Advanced text cleaning using built-in Python modules
    Enhanced to handle escaped HTML and complex patterns
    """
    if not text:
        return text
    
    # 1. Unescape HTML entities (e.g., &amp;, &quot;)
    text = html.unescape(text)

    # 2. Remove HTML tags using HTMLParser
    text = _strip_tags(text)
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(char for char in text if char in string.printable)
    
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text