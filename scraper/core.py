import asyncio
from typing import List, Set, Optional
from urllib.parse import urlparse
import httpx
from tqdm.asyncio import tqdm
from .models import InputSchema, ScraperResult, OutputRecord
from .llm import LLMSelectorInference
from .parser import DirectoryParser
from .browser import BrowserScraper
from .deep_scraper import DeepScraper


class DirectoryScraper:
    """Main orchestrator for directory scraping with pagination."""
    
    def __init__(
        self,
        schema: InputSchema,
        api_key: Optional[str] = None,
        max_pages: int = 50,
        max_concurrent: int = 5,
        use_browser: bool = False,
        wait_for_selector: Optional[str] = None,
        detail_schema: Optional[InputSchema] = None,
        detail_url_field: Optional[str] = None
    ):
        self.schema = schema
        self.llm = LLMSelectorInference(api_key=api_key)
        self.max_pages = max_pages
        self.max_concurrent = max_concurrent
        self.visited_urls: Set[str] = set()
        self.use_browser = use_browser
        self.wait_for_selector = wait_for_selector
        self.detail_schema = detail_schema
        self.detail_url_field = detail_url_field
        

        if detail_schema and detail_url_field:
            self.deep_scraper = DeepScraper(
                detail_schema=detail_schema,
                llm=self.llm,
                use_browser=use_browser,
                wait_for_selector=wait_for_selector,
                max_concurrent=3
            )
        else:
            self.deep_scraper = None
    
    async def scrape(self, url: str, verbose: bool = True) -> ScraperResult:
        """Main scraping entrypoint."""
        
        if self.use_browser:
            return await self._scrape_with_browser(url, verbose)
        else:
            return await self._scrape_with_httpx(url, verbose)
    
    async def _scrape_with_httpx(self, url: str, verbose: bool = True) -> ScraperResult:
        """Fast scraping with httpx (for non-JS sites)."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }
        
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers=headers
        ) as client:
            if verbose:
                print(f"Fetching initial page: {url}")
            
            response = await client.get(url)
            response.raise_for_status()
            initial_html = response.text
            
            if verbose:
                print("🤖 Inferring selectors with LLM (enhanced prompting)...")
            
            selector_map = await self.llm.infer_selectors(
                initial_html,
                self.schema,
                url
            )
            
            if verbose:
                print(f"Selectors inferred")
                print(f"  List item: {selector_map.list_item_selector or 'N/A'}")
                print(f"  Pagination: {selector_map.pagination_selector or 'N/A'}")
                print(f"  Field selectors:")
                for field, selector in selector_map.selectors.items():
                    print(f"    - {field}: {selector}")
            
            parser = DirectoryParser(selector_map, url)
            
            all_records: List[OutputRecord] = []
            pages_to_scrape = [url]
            self.visited_urls.add(url)
            
            if verbose:
                print("Scraping pages...")
            
            page_count = 0
            
            while pages_to_scrape and page_count < self.max_pages:
                batch = pages_to_scrape[:self.max_concurrent]
                pages_to_scrape = pages_to_scrape[self.max_concurrent:]
                
                tasks = [
                    self._fetch_and_parse(client, page_url, parser)
                    for page_url in batch
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        if verbose:
                            print(f"Error: {result}")
                        continue
                    
                    records, next_url = result
                    all_records.extend(records)
                    
                    if next_url and next_url not in self.visited_urls:
                        self.visited_urls.add(next_url)
                        pages_to_scrape.append(next_url)
                    
                    page_count += 1
                
                if verbose and page_count > 1:
                    print(f"  Pages scraped: {page_count}, Records: {len(all_records)}")
            
            if verbose:
                print(f"Scraping complete: {len(all_records)} records from {page_count} pages")
            

            if self.deep_scraper and self.detail_url_field:
                all_records = await self.deep_scraper.enrich_records(
                    all_records,
                    self.detail_url_field,
                    verbose=verbose
                )
            
            return ScraperResult(
                url=url,
                records=all_records,
                total_count=len(all_records),
                schema_used=self.schema
            )
    
    async def _scrape_with_browser(self, url: str, verbose: bool = True) -> ScraperResult:
        """Scraping with Playwright browser (for JS-heavy sites)."""
        
        if verbose:
            print(f"Using browser mode for JavaScript rendering...")
            print(f"Fetching initial page: {url}")
        
        async with BrowserScraper(headless=True) as browser:

            initial_html = await browser.get_html(url, wait_for=self.wait_for_selector, scroll_for_lazy_load=True)
            
            if verbose:
                print("🤖 Inferring selectors with LLM (enhanced prompting)...")
            
            selector_map = await self.llm.infer_selectors(
                initial_html,
                self.schema,
                url
            )
            
            if verbose:
                print(f"Selectors inferred")
                print(f"  List item: {selector_map.list_item_selector or 'N/A'}")
                print(f"  Pagination: {selector_map.pagination_selector or 'N/A'}")
                print(f"  Field selectors:")
                for field, selector in selector_map.selectors.items():
                    print(f"    - {field}: {selector}")
            
            parser = DirectoryParser(selector_map, url)
            
            all_records: List[OutputRecord] = []
            pages_to_scrape = [url]
            self.visited_urls.add(url)
            
            if verbose:
                print("Scraping pages...")
            
            page_count = 0
            
            while pages_to_scrape and page_count < self.max_pages:

                current_url = pages_to_scrape.pop(0)
                
                try:
                    html = await browser.get_html(current_url, wait_for=self.wait_for_selector)
                    records = parser.parse_page(html)
                    all_records.extend(records)
                    

                    next_url = parser.find_next_page_url(html)
                    if next_url and next_url not in self.visited_urls:
                        self.visited_urls.add(next_url)
                        pages_to_scrape.append(next_url)
                    
                    page_count += 1
                    
                    if verbose:
                        print(f"  Page {page_count}: {len(records)} records found")
                    
                    await asyncio.sleep(1)  # Respectful delay
                    
                except Exception as e:
                    if verbose:
                        print(f"Error on page {current_url}: {e}")
                    continue
            
            if verbose:
                print(f"Scraping complete: {len(all_records)} records from {page_count} pages")
            
            all_records = self._clean_records(all_records, verbose)
            

            if self.deep_scraper and self.detail_url_field:
                all_records = await self.deep_scraper.enrich_records(
                    all_records,
                    self.detail_url_field,
                    verbose=verbose
                )
            
            return ScraperResult(
                url=url,
                records=all_records,
                total_count=len(all_records),
                schema_used=self.schema
            )
    
    async def _fetch_and_parse(
        self,
        client: httpx.AsyncClient,
        url: str,
        parser: DirectoryParser
    ) -> tuple[List[OutputRecord], Optional[str]]:
        """Fetch a page and parse its records."""
        await asyncio.sleep(0.5)
        response = await client.get(url)
        response.raise_for_status()
        html = response.text
        
        records = parser.parse_page(html)
        next_url = parser.find_next_page_url(html)
        
        return records, next_url
    
    def _clean_records(self, records: List[OutputRecord], verbose: bool = False) -> List[OutputRecord]:
        """Remove empty records and deduplicate."""
        

        non_empty = []
        for rec in records:

            data = rec.data if hasattr(rec, 'data') else rec.model_dump()
            non_none_fields = sum(1 for v in data.values() if v is not None)
            if non_none_fields >= 2:
                non_empty.append(rec)
        

        seen = set()
        unique = []
        for rec in non_empty:

            data = rec.data if hasattr(rec, 'data') else rec.model_dump()
            rec_tuple = tuple(sorted(data.items()))
            if rec_tuple not in seen:
                seen.add(rec_tuple)
                unique.append(rec)
        
        if verbose and len(records) != len(unique):
            print(f"Cleaned: {len(records)} -> {len(unique)} records (removed {len(records) - len(unique)} empty/duplicates)")
        
        return unique
    
    async def test_selectors(self, url: str) -> dict:
        """Test selector inference without full scrape."""
        
        if self.use_browser:
            async with BrowserScraper(headless=True) as browser:
                html = await browser.get_html(url, wait_for=self.wait_for_selector)
        else:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
                response = await client.get(url)
                response.raise_for_status()
                html = response.text
        
        selector_map = await self.llm.infer_selectors(html, self.schema, url)
        
        parser = DirectoryParser(selector_map, url)
        sample_records = parser.parse_page(html)
        
        return {
            "selector_map": selector_map.dict(),
            "sample_records": [r.data for r in sample_records[:3]],
            "total_sample_count": len(sample_records),
            "html_sample": html[:5000]
        }

