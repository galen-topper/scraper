import json
from typing import Dict, Optional
import httpx
import os
import asyncio
from dotenv import load_dotenv
from .models import InputSchema, SelectorMap

load_dotenv()


class LLMSelectorInference:
    """Uses GPT-4.1 to infer CSS selectors from HTML and schema."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.base_url = "https://api.openai.com/v1/chat/completions"
    
    async def infer_selectors(
        self,
        html_sample: str,
        schema: InputSchema,
        url: str
    ) -> SelectorMap:
        """Infer CSS selectors for the given schema from HTML sample."""
        
        # Create DOM sketch - lightweight preprocessing
        from .dom_sketch import make_dom_sketch
        
        sketch_html, metadata = make_dom_sketch(html_sample, max_items=5, max_text=120)
        
        print(f"DOM sketch: {metadata.get('type', 'unknown')} structure")
        print(f"Found {metadata.get('count', 0)} items")
        print(f"Sketch size: {len(sketch_html)} chars (vs {len(html_sample)} original)")
        
        prompt = self._build_prompt(sketch_html, schema, url, metadata)
        
        max_retries = 5
        base_delay = 2
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(
                        self.base_url,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "gpt-4-turbo-preview",
                            "messages": [
                                {
                                    "role": "system",
                                    "content": """You are an expert web scraping analyst with deep knowledge of HTML structures, CSS selectors, and directory patterns.

You understand:
- Table-based directories (government sites, databases, member systems)
- Card/grid layouts (modern websites)
- List-based directories (simple lists)
- Wild Apricot and similar membership platforms
- Complex nested structures

Your goal: Analyze HTML and provide precise, working CSS selectors that will successfully extract all entries from ANY directory structure.

You MUST:
1. Identify the repeated pattern that represents each entry
2. Provide a list_item_selector that matches ALL entries
3. Provide field selectors relative to each list item
4. Think step-by-step about the HTML structure
5. Return valid JSON only

You are extremely thorough and always provide selectors that work."""
                                },
                                {
                                    "role": "user",
                                    "content": prompt
                                }
                            ],
                            "temperature": 0.1,
                            "response_format": {"type": "json_object"}
                        }
                    )
                    response.raise_for_status()
                    break
                
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            print(f"Rate limited by OpenAI. Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            print(f"\nOpenAI Rate Limit Error:")
                            print(f"  Status: 429 Too Many Requests")
                            print(f"  This can happen if:")
                            print(f"    1. Your account has billing issues")
                            print(f"    2. You're on free tier with very low limits")
                            print(f"    3. OpenAI is having service issues")
                            print(f"\n  Check: https://platform.openai.com/settings/organization/limits")
                            raise
                    else:
                        raise
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            selector_data = json.loads(content)
            
            return SelectorMap(
                selectors=selector_data.get("selectors", {}),
                list_item_selector=selector_data.get("list_item_selector"),
                pagination_selector=selector_data.get("pagination_selector")
            )
    
    def _build_prompt(self, html: str, schema: InputSchema, url: str, metadata: Dict = None) -> str:
        """Build a comprehensive prompt for GPT-4 to handle any directory structure."""
        
        # HTML is already compact from SmartHTMLExtractor
        html_truncated = html
        
        if metadata is None:
            metadata = {}
        
        fields_desc = "\n".join(
            f'- "{name}": {desc}'
            for name, desc in schema.fields.items()
        )
        
        return f"""You are an expert web scraping analyst. Analyze this DOM SKETCH (pre-processed, noise-removed HTML) and provide CSS selectors.

URL: {url}

TARGET FIELDS:
{fields_desc}

DOM SKETCH (showing {metadata.get('count', '?')} items, trimmed for clarity):
```html
{html_truncated}
```

CONTEXT:
- Structure: {metadata.get('type', 'unknown') if metadata else 'unknown'}
- Total items: {metadata.get('count', 0) if metadata else 0}
- Base selector hint: {metadata.get('suggested_selector', 'N/A') if metadata else 'N/A'}

⚠️ CRITICAL RULES:
1. The HTML has been TRIMMED - only relevant containers are shown
2. For DYNAMIC/HASHED classes (e.g., _coName_abc123, styles__Name-sc-xyz):
   → Use WILDCARDS: [class*="coName"] NOT .styles__Name-sc-xyz
3. Prefer STABLE attributes: id, data-*, role, aria-label over dynamic classes
4. Selectors are RELATIVE to list_item_selector
5. For tables: list_item is <tr>, fields are <td> children
6. For cards/divs: look for repeated tag+class patterns

═══════════════════════════════════════════════════════════════
ANALYSIS FRAMEWORK - Follow these steps:
═══════════════════════════════════════════════════════════════

STEP 1: IDENTIFY DIRECTORY STRUCTURE TYPE

Look at the HTML and identify which pattern it uses:

A) TABLE-BASED DIRECTORY (common in government sites, databases)
   - Look for: <table>, <tbody>, <tr>, <td>
   - Each row (<tr>) is one entry
   - Example: "table.members tbody tr" or "table#directory tr:not(:first-child)"

B) WILD APRICOT / MEMBER SYSTEMS (membership platforms)
   - Look for: class names like "memberDirectory", "membersTable", "AspNet-GridView"
   - Often table-based with specific classes
   - Example: "table.membersTable tbody tr" or ".memberDirectory .member-row"

C) CARD/GRID LAYOUT (modern websites)
   - Look for: repeated divs with classes like "card", "profile", "member", "person"
   - Example: ".person-card", ".profile-item", ".member-box"

D) LIST LAYOUT (simple directories)
   - Look for: <ul> and <li> elements
   - Example: "ul.directory li", ".people-list > li"

E) ARTICLE/SECTION LAYOUT
   - Look for: <article>, <section> tags
   - Example: "article.profile", "section.person"

STEP 2: FIND THE REPEATED PATTERN

Scan the HTML and find what repeats for EACH person/entry. Count how many times the pattern appears.
- If you see 10+ similar elements, that's likely your list_item_selector
- Look for IDs, classes, or tag patterns that repeat

STEP 3: EXTRACT FIELD SELECTORS

For EACH field in the target schema, find the selector WITHIN each list item:
- Name: Usually in <h2>, <h3>, <h4>, or <a> tags, often first in the item
- Title/Position: Often in <span>, <p>, or <div> with class like "title", "position", "role"
- Email: Look for <a href="mailto:...">, or text with @ symbol
- Phone: Look for <a href="tel:...">, or text with phone pattern
- URL/Link: Look for <a href="...">, extract [href] attribute
- Bio/Description: Usually longer <p> or <div> with class like "bio", "description", "summary"

For TABLES specifically:
- Name: Usually first <td> or <td> with specific class
- Other fields: Often in subsequent <td> elements - use td:nth-child(2), td:nth-child(3), etc.
- OR look for class names on <td> elements

STEP 4: HANDLE SPECIAL CASES

- If fields are in table cells: use "td:nth-child(N)" or "td.classname"
- If links need [href]: add "[href]" to selector (e.g., "a.profile-link[href]")
- If text is nested: use descendant selectors (e.g., "div.name span.text")
- For onclick attributes with URLs: use "tr[onclick]" and extract via [onclick]

STEP 5: FIND PAGINATION

Look for:
- Links with text: "Next", "›", "→", or page numbers
- Common classes: "next", "pagination-next", "pager-next"
- Common rel attributes: rel="next"
- Page number links: "a.page-num", ".pagination a"

═══════════════════════════════════════════════════════════════
EXAMPLES FOR COMMON PATTERNS
═══════════════════════════════════════════════════════════════

EXAMPLE 1 - Table Directory (like nursing facilities, government databases):
{{
  "list_item_selector": "table tbody tr",
  "selectors": {{
    "name": "td:nth-child(1)",
    "address": "td:nth-child(2)",
    "phone": "td:nth-child(3)",
    "page_url": "td:nth-child(1) a[href]"
  }},
  "pagination_selector": "a.next, a[rel='next']"
}}

EXAMPLE 2 - Wild Apricot / Member System (VERY COMMON):
{{
  "list_item_selector": "table tbody tr",
  "selectors": {{
    "name": "td div.memberValue",
    "areas_of_focus": "td:nth-child(2)",
    "office_location": "td:nth-child(3)",
    "insurance": "td:nth-child(4)",
    "profile_url": "td a[href]"
  }},
  "pagination_selector": "a.next"
}}

NOTE: For Wild Apricot, use SIMPLE selectors like "table tbody tr" not complex class chains.
The data is in <td> cells, often with nested <div class="memberValue">.

**IMPORTANT FOR DYNAMIC CLASS NAMES (React/styled-components):**
If you see hashed class names like `_coName_xyz123`, use wildcard attribute selectors:
- Instead of: `.styles__CompanyName-sc-abc123`
- Use: `[class*="coName"], [class*="CompanyName"]`
- Instead of: `.styles__Location-sc-xyz456`
- Use: `[class*="Location"], [class*="location"]`

This works for dynamically generated classes that change on each page load.

EXAMPLE 3 - Card/Grid Layout:
{{
  "list_item_selector": ".person-card, .profile-item",
  "selectors": {{
    "name": "h3.name, h2.person-name",
    "title": ".job-title, .position",
    "email": ".contact-email, a[href^='mailto:']",
    "page_url": "a.profile-link[href]"
  }},
  "pagination_selector": "a.pagination-next, .next-page"
}}

EXAMPLE 4 - List Layout:
{{
  "list_item_selector": "ul.people-list > li, .directory-list li",
  "selectors": {{
    "name": "h4, .name",
    "bio": "p.bio, .description",
    "page_url": "a[href]"
  }},
  "pagination_selector": "a.next"
}}

═══════════════════════════════════════════════════════════════
CRITICAL REQUIREMENTS
═══════════════════════════════════════════════════════════════

1. **list_item_selector MUST match ALL entries** - Count them in the HTML!
2. **Field selectors are RELATIVE to list_item** - They work WITHIN each item
3. **PREFER SIMPLE SELECTORS** - "table tbody tr" works better than ".ComplexClass tbody tr"
4. **Test mentally** - Would your selectors actually extract the right data?
5. **Handle tables properly** - If it's a table, use tr for list_item and td for fields
6. **Multiple selectors OK** - Use commas for fallbacks: "td.name, td:nth-child(1)"
7. **For Wild Apricot tables** - Just use "table tbody tr", data is in <td> cells

IMPORTANT: Keep selectors SIMPLE. Complex class chains often fail.

═══════════════════════════════════════════════════════════════
YOUR RESPONSE (MUST be valid JSON only)
═══════════════════════════════════════════════════════════════

{{
  "list_item_selector": "YOUR SELECTOR HERE",
  "selectors": {{
    {", ".join(f'"{field}": "YOUR SELECTOR HERE"' for field in schema.fields.keys())}
  }},
  "pagination_selector": "YOUR SELECTOR HERE or null"
}}

IMPORTANT: Return ONLY the JSON object above. Use the EXACT field names from the target fields.
Analyze carefully and provide selectors that WILL work based on the HTML structure provided."""

