"""
Lightweight DOM sketching utility for LLM selector inference.
Extracts only the relevant directory structure, removing noise.
"""

from selectolax.parser import HTMLParser
from typing import Tuple
import re


def make_dom_sketch(html: str, max_items: int = 5, max_text: int = 80) -> Tuple[str, dict]:
    tree = HTMLParser(html)
    
    # Remove noise
    for tag in tree.css('script, style, svg, noscript'):
        tag.decompose()
    
    # Strategy 1: Find tables with many rows
    tables = tree.css('table')
    for table in tables:
        rows = table.css('tr')
        data_rows = [r for r in rows if len(r.css('td')) >= 2]
        
        if len(data_rows) >= 5:
            sketch = _sketch_table(table, max_items, max_text)
            return sketch, {
                'type': 'table',
                'count': len(data_rows),
                'suggested_selector': _get_table_selector(table)
            }
    
    # Strategy 2: Find repeated elements (cards, list items)
    patterns = [
        (r'[class*="company"]', 'company'),
        (r'[class*="member"]', 'member'),
        (r'[class*="profile"]', 'profile'),
        (r'[class*="card"]', 'card'),
        (r'[class*="item"]', 'item'),
    ]
    
    for pattern, keyword in patterns:
        elements = tree.css(f'[class*="{keyword}"]')
        # Filter to just top-level containers (not nested)
        containers = [e for e in elements if e.tag in ['a', 'div', 'article', 'li']]
        
        if len(containers) >= 10:
            sketch = _sketch_repeated_elements(containers[:max_items], max_text)
            return sketch, {
                'type': 'repeated_divs',
                'count': len(containers),
                'suggested_selector': f'{containers[0].tag}[class*="{keyword}"]'
            }
    
    # Fallback: return a heavily truncated version
    return html[:8000], {'type': 'unknown', 'count': 0, 'suggested_selector': 'N/A'}


def _sketch_table(table, max_rows: int, max_text: int) -> str:
    """Extract table structure with sample rows."""
    lines = ['<table>']
    
    # Headers
    headers = table.css('thead th, thead td, tr:first-child th')
    if headers:
        lines.append('  <thead><tr>')
        for h in headers[:8]:
            text = _truncate(h.text(strip=True), 40)
            lines.append(f'    <th>{text}</th>')
        lines.append('  </tr></thead>')
    
    # Sample rows
    lines.append('  <tbody>')
    rows = [r for r in table.css('tbody tr, tr') if r.css('td')][:max_rows]
    
    for row in rows:
        lines.append('    <tr>')
        for cell in row.css('td')[:8]:
            cls = cell.attributes.get('class', '')[:50]
            content = _describe_cell(cell, max_text)
            if cls:
                lines.append(f'      <td class="{cls}">{content}</td>')
            else:
                lines.append(f'      <td>{content}</td>')
        lines.append('    </tr>')
    
    lines.append('  </tbody>')
    lines.append('</table>')
    lines.append(f'<!-- Total rows: {len([r for r in table.css("tr") if r.css("td")])} -->')
    
    return '\n'.join(lines)


def _sketch_repeated_elements(elements, max_text: int) -> str:
    """Extract structure of repeated cards/items."""
    lines = []
    
    # Filter to only elements with actual content (skip empty duplicates)
    non_empty = []
    for elem in elements:
        # Check if this element has any text content in descendants
        all_text = elem.text(deep=True, strip=True)
        if all_text and len(all_text) > 10:  # Has substantial content
            non_empty.append(elem)
        if len(non_empty) >= 3:  # Only need 3 examples
            break
    
    if not non_empty:
        # Fallback: just use first 3
        non_empty = elements[:3]
    
    for elem in non_empty:
        tag = elem.tag
        cls = elem.attributes.get('class', '')[:60]
        href = elem.attributes.get('href', '')[:50]
        
        # Build opening tag
        attrs = []
        if cls:
            attrs.append(f'class="{cls}"')
        if href:
            attrs.append(f'href="{href}"')
        
        lines.append(f'<{tag} {" ".join(attrs)}>')
        
        # Show ALL descendants with classes
        _show_descendants(elem, lines, indent=1, max_text=max_text)
        
        lines.append(f'</{tag}>')
        lines.append('')
    
    lines.append(f'<!-- Total items: {len(non_empty)} shown, {len(elements)} total -->')
    
    return '\n'.join(lines)


def _show_descendants(elem, lines, indent=1, max_text=60):
    """Show all significant descendants with text content."""
    prefix = '  ' * indent
    
    # Get all descendant elements
    all_elements = elem.css('*')
    
    # Filter to elements that have:
    # 1. A class attribute, OR
    # 2. Actual text content (not just whitespace)
    significant = []
    for el in all_elements:
        cls = el.attributes.get('class', '')
        # Get element's OWN text (not descendants)
        own_text = el.text(deep=False, strip=True) if hasattr(el.text, '__call__') else ''
        
        if cls or (own_text and len(own_text) > 2):
            significant.append(el)
    
    # Limit to first 20 significant elements
    for child in significant[:20]:
        tag = child.tag
        cls = child.attributes.get('class', '')[:70]
        href = child.attributes.get('href', '')[:50]
        # Get the element's direct text only
        text = child.text(deep=False, strip=True) if hasattr(child.text, '__call__') else ''
        
        # Build compact representation  
        attrs = []
        if cls:
            # Highlight key patterns with annotations
            if any(kw in cls for kw in ['_coName', 'coName', 'CompanyName', 'company-name', 'name', 'Name', 'title', 'Title']):
                attrs.append(f'class="{cls}" ← NAME')
            elif any(kw in cls for kw in ['_coLocation', 'coLocation', 'Location', 'location', 'loc']):
                attrs.append(f'class="{cls}" ← LOCATION')
            elif any(kw in cls for kw in ['desc', 'Desc', 'tagline', 'Tagline']):
                attrs.append(f'class="{cls}" ← DESC')
            elif any(kw in cls for kw in ['batch', 'Batch']):
                attrs.append(f'class="{cls}" ← BATCH')
            elif any(kw in cls for kw in ['industry', 'Industry', 'category', 'Category']):
                attrs.append(f'class="{cls}" ← INDUSTRY')
            else:
                attrs.append(f'class="{cls}"')
        
        if href:
            attrs.append(f'href="{href}"')
        
        attr_str = ' '.join(attrs)
        text_short = _truncate(text, 50) if text else ''
        
        # Only show if there's something meaningful
        if attr_str and text_short:
            lines.append(f'{prefix}<{tag} {attr_str}>{text_short}</{tag}>')
        elif attr_str and any(marker in attr_str for marker in ['← NAME', '← LOCATION', '← DESC', '← BATCH', '← INDUSTRY']):
            # Show annotated elements even without text (might be empty in sample)
            lines.append(f'{prefix}<{tag} {attr_str}/>')
        elif text_short and len(text_short) > 5:
            lines.append(f'{prefix}<{tag}>{text_short}</{tag}>')


def _describe_cell(cell, max_text: int) -> str:
    """Describe cell contents compactly."""
    # Check for links
    links = cell.css('a')
    if links:
        link = links[0]
        href = link.attributes.get('href', '')[:40]
        text = _truncate(link.text(strip=True), 30)
        return f'<a href="{href}">{text}</a>'
    
    # Check for nested divs/spans with classes
    for child in cell.css('[class]'):
        cls = child.attributes.get('class', '')
        if any(k in cls for k in ['name', 'Name', 'value', 'Value', 'text']):
            text = _truncate(child.text(strip=True), max_text)
            return f'<{child.tag} class="{cls[:30]}">{text}</{child.tag}>'
    
    # Plain text
    return _truncate(cell.text(strip=True), max_text)


def _get_table_selector(table) -> str:
    """Generate a good selector for a table."""
    table_id = table.attributes.get('id')
    if table_id:
        return f'#{table_id}'
    
    table_class = table.attributes.get('class', '').split()[0] if table.attributes.get('class') else None
    if table_class:
        return f'table.{table_class}'
    
    return 'table'


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max length."""
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > max_len:
        return text[:max_len] + '...'
    return text

