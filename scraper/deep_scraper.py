"""
Deep scraping module for following links and extracting detailed information.
"""

import asyncio
from typing import List, Dict, Any, Optional
import httpx
from .models import InputSchema, OutputRecord
from .parser import DirectoryParser
from .llm import LLMSelectorInference
from .browser import BrowserScraper


class DeepScraper:
    """Deep scraping lets us go a layer deeper to get more information"""
    
    def __init__(
        self,
        detail_schema: InputSchema,
        llm: LLMSelectorInference,
        use_browser: bool = False,
        wait_for_selector: Optional[str] = None,
        max_concurrent: int = 3
    ):
        self.detail_schema = detail_schema
        self.llm = llm
        self.use_browser = use_browser
        self.wait_for_selector = wait_for_selector
        self.max_concurrent = max_concurrent
        self._selector_cache: Dict[str, Any] = {}
    
    async def enrich_records(
        self,
        records: List[OutputRecord],
        detail_url_field: str,
        verbose: bool = True
    ) -> List[OutputRecord]:
        """
        Deep scrapes to generate more information enriching the record. 
        Args:
            records: List of records from listing page
            detail_url_field: Field name containing the URL to detail page
            verbose: Whether to print progress
            
        Returns:
            Enriched records with detail page data merged in
        """
        if verbose:
            print(f" Deep scraping {len(records)} detail pages...")
        
        enriched_records = []
        

        for i in range(0, len(records), self.max_concurrent):
            batch = records[i:i + self.max_concurrent]
            tasks = [
                self._enrich_single_record(record, detail_url_field)
                for record in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    if verbose:
                        print(f"Error enriching record {i+idx+1}: {result}")
                    enriched_records.append(batch[idx])
                else:
                    enriched_records.append(result)
            
            if verbose:
                print(f"Progress: {min(i + self.max_concurrent, len(records))}/{len(records)}")
        
        if verbose:
            print(f"Scraping complete")
        
        return enriched_records
    
    async def _enrich_single_record(
        self,
        record: OutputRecord,
        detail_url_field: str
    ) -> OutputRecord:
        """Fetch and parse a single detail page.
        We do this first to get early information that allow us to generalize selectors. 
        """
        

        detail_url = record.data.get(detail_url_field)
        if not detail_url:
            return record
        

        if self.use_browser:
            html = await self._fetch_with_browser(detail_url)
        else:
            html = await self._fetch_with_httpx(detail_url)
        

        domain = self._get_domain(detail_url)
        if domain not in self._selector_cache:
            selector_map = await self.llm.infer_selectors(
                html,
                self.detail_schema,
                detail_url
            )
            self._selector_cache[domain] = selector_map
        else:
            selector_map = self._selector_cache[domain]
        

        parser = DirectoryParser(selector_map, detail_url)
        detail_records = parser.parse_page(html)
        

        if detail_records:
            detail_data = detail_records[0].data
            merged_data = {**record.data, **detail_data}
            return OutputRecord(data=merged_data)
        
        return record
    
    async def _fetch_with_httpx(self, url: str) -> str:
        """Fetch HTML using httpx."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    
    async def _fetch_with_browser(self, url: str) -> str:
        """Fetch HTML using browser."""
        async with BrowserScraper(headless=True) as browser:
            return await browser.get_html(url, wait_for=self.wait_for_selector)
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL for caching."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

