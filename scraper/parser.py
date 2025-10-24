from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from selectolax.parser import HTMLParser
from .models import SelectorMap, OutputRecord


class DirectoryParser:
    """Parses HTML and extracts structured data based on selectors."""
    
    def __init__(self, selector_map: SelectorMap, base_url: str):
        self.selector_map = selector_map
        self.base_url = base_url
    
    def parse_page(self, html: str) -> List[OutputRecord]:
        """Extract all records from a single page."""
        tree = HTMLParser(html)
        records = []
        
        if self.selector_map.list_item_selector:
            items = tree.css(self.selector_map.list_item_selector)
            for item in items:
                record_data = self._extract_from_element(item)
                if record_data:
                    records.append(OutputRecord(data=record_data))
        else:
            record_data = self._extract_from_element(tree)
            if record_data:
                records.append(OutputRecord(data=record_data))
        
        return records
    
    def _extract_from_element(self, element) -> Dict[str, Any]:
        """Extract all fields from a single element."""
        data = {}
        
        for field_name, selector in self.selector_map.selectors.items():
            try:
                value = self._extract_field(element, selector)
                if value:
                    if 'url' in field_name.lower() or 'link' in field_name.lower():
                        value = urljoin(self.base_url, value)
                    data[field_name] = value
            except Exception:
                data[field_name] = None
        
        return data if any(data.values()) else {}
    
    def _extract_field(self, element, selector: str) -> Optional[str]:
        """Extract a single field using selector."""
        matches = element.css(selector)
        
        if not matches:
            return None
        
        target = matches[0]
        
        if target.attributes.get('href'):
            return target.attributes['href']
        elif target.attributes.get('src'):
            return target.attributes['src']
        else:
            text = target.text(strip=True)
            return text if text else None
    
    def find_next_page_url(self, html: str) -> Optional[str]:
        """Find the URL of the next page if pagination exists."""
        if not self.selector_map.pagination_selector:
            return None
        
        tree = HTMLParser(html)
        next_links = tree.css(self.selector_map.pagination_selector)
        
        if not next_links:
            return None
        
        for link in next_links:
            href = link.attributes.get('href')
            if href:
                return urljoin(self.base_url, href)
        
        return None

