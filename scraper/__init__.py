"""
Generalized directory scraper with LLM-assisted selector inference.
"""

from .models import InputSchema, OutputRecord, ScraperResult, SelectorMap
from .core import DirectoryScraper
from .parser import DirectoryParser
from .llm import LLMSelectorInference
from .browser import BrowserScraper
from .deep_scraper import DeepScraper
from .dom_sketch import make_dom_sketch

__version__ = "2.1.0"

__all__ = [
    "InputSchema",
    "OutputRecord",
    "ScraperResult",
    "SelectorMap",
    "DirectoryScraper",
    "DirectoryParser",
    "LLMSelectorInference",
    "BrowserScraper",
    "DeepScraper",
    "make_dom_sketch",
]

