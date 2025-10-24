"""
Browser-based scraping for JavaScript-heavy sites using Playwright.
"""

import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page


class BrowserScraper:
    """Handles browser automation for JS-heavy sites."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.playwright = None
    
    async def __aenter__(self):
        """Context manager entry."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def get_html(self, url: str, wait_for: Optional[str] = None, wait_time: int = 5000, scroll_for_lazy_load: bool = False) -> str:
        """
        Fetch HTML from a URL using browser automation.
        
        Args:
            url: URL to fetch
            wait_for: CSS selector to wait for before returning HTML
            wait_time: Maximum time to wait in milliseconds (default: 5000)
            scroll_for_lazy_load: Scroll down to trigger lazy-loaded content (default: False)
            
        Returns:
            Rendered HTML content
        """
        if not self.browser:
            raise RuntimeError("Browser not initialized. Use async with context manager.")
        
        page = await self.browser.new_page()
        
        try:

            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait for specific element if provided
            if wait_for:
                try:
                    await page.wait_for_selector(wait_for, timeout=wait_time)
                except Exception as e:
                    print(f"Warning: Timeout waiting for selector '{wait_for}': {e}")
            else:
                # Default wait for page load
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(2)  # Additional wait for dynamic content
            

            if scroll_for_lazy_load:
                print(f"Scrolling to load lazy content...")
                await self._scroll_page(page)
                await asyncio.sleep(3)
                
                print(f"Waiting for content to hydrate...")
                await asyncio.sleep(3)
            

            html = await page.content()
            return html
            
        finally:
            await page.close()
    
    async def _scroll_page(self, page: Page, scrolls: int = 3):
        """Scroll down a page multiple times to trigger lazy loading."""
        for i in range(scrolls):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
    
    async def get_multiple_pages(
        self,
        urls: list[str],
        wait_for: Optional[str] = None
    ) -> list[str]:
        """
        Fetch multiple pages concurrently.
        
        Args:
            urls: List of URLs to fetch
            wait_for: CSS selector to wait for on each page
            
        Returns:
            List of HTML content strings
        """
        tasks = [self.get_html(url, wait_for) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def click_and_get_html(
        self,
        url: str,
        click_selector: str,
        wait_after_click: Optional[str] = None
    ) -> str:
        """
        Navigate to a page, click an element, and return the resulting HTML.
        
        Args:
            url: Initial URL
            click_selector: CSS selector of element to click
            wait_after_click: CSS selector to wait for after clicking
            
        Returns:
            HTML after the click action
        """
        if not self.browser:
            raise RuntimeError("Browser not initialized.")
        
        page = await self.browser.new_page()
        
        try:
            await page.goto(url, wait_until="networkidle")
            await page.click(click_selector)
            
            if wait_after_click:
                await page.wait_for_selector(wait_after_click, timeout=5000)
            else:
                await asyncio.sleep(1)
            
            html = await page.content()
            return html
            
        finally:
            await page.close()

