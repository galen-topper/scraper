# Directory Scraper

A generalized, high-performance directory scraper that uses LLM-assisted selector inference to extract structured data from any web directory.

## Features

- 🤖 **LLM-Powered**: Uses GPT-4 to automatically infer CSS selectors from HTML
- ⚡ **High Performance**: Async/await architecture with concurrent requests
- 🔄 **Pagination Support**: Automatically detects and follows pagination links
- 🎯 **Schema-Based**: Extract any fields you define via a simple schema
- 🧹 **Data Cleaning**: Automatic normalization and validation of extracted data
- 🌐 **Generalized**: Works across different directory structures

## Installation

```bash
pip install -r requirements.txt
```

Set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

## Quick Start

### Define Your Schema

Create a JSON file in `data/schemas/` (e.g., `data/schemas/my_schema.json`) describing what to extract:

```json
{
  "name": "person's full name",
  "title": "their job title or position",
  "email": "contact email address",
  "page_url": "link to their profile page",
  "bio": "short biography"
}
```

### Run the Scraper

```bash
python -m scraper run https://example.com/directory \
  --schema data/schemas/my_schema.json \
  --output data/outputs/results.json
```

Or use inline schema:

```bash
python -m scraper run https://example.com/directory \
  --schema-json '{"name": "person name", "email": "email address"}' \
  --output data/outputs/results.json
```

### Test Selector Inference

Before scraping, test if the LLM can properly infer selectors:

```bash
python -m scraper test https://example.com/directory --schema data/schemas/my_schema.json
```

## Usage

### CLI Commands

#### `run` - Scrape a directory

```bash
python -m scraper run <url> [OPTIONS]

Options:
  --schema, -s PATH          Path to JSON schema file
  --schema-json, -j TEXT     Inline JSON schema string
  --output, -o PATH          Output JSON file path
  --max-pages, -p INT        Maximum pages to scrape (default: 50)
  --api-key TEXT            OpenAI API key (or use OPENAI_API_KEY env var)
```

#### `test` - Test selector inference

```bash
python -m scraper test <url> [OPTIONS]

Options:
  --schema, -s PATH          Path to JSON schema file
  --schema-json, -j TEXT     Inline JSON schema string
  --api-key TEXT            OpenAI API key
```

### Programmatic Usage

```python
import asyncio
from scraper import DirectoryScraper, InputSchema

schema = InputSchema(fields={
    "name": "person's name",
    "email": "email address",
    "title": "job title"
})

scraper = DirectoryScraper(schema=schema, max_pages=10)
result = asyncio.run(scraper.scrape("https://example.com/directory"))

# Access records as dictionaries
for record in result.as_dicts:
    print(record)
```

## How It Works

1. **Fetch Initial Page**: Downloads the first page of the directory
2. **LLM Inference**: Sends HTML sample to GPT-4 to infer optimal CSS selectors
3. **Parse & Extract**: Uses inferred selectors to extract structured data
4. **Pagination**: Automatically detects and follows "next page" links
5. **Concurrent Scraping**: Processes multiple pages in parallel for speed
6. **Data Cleaning**: Normalizes emails, URLs, and text fields

## Architecture

```
scraper/
├── __init__.py       # Package exports
├── __main__.py       # Module entry point
├── main.py           # Typer CLI interface
├── models.py         # Pydantic schemas
├── llm.py            # GPT-4 selector inference
├── parser.py         # HTML parsing & extraction
└── core.py           # Main orchestration & pagination
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)

### Scraper Options

```python
DirectoryScraper(
    schema=schema,           # InputSchema defining fields to extract
    api_key=None,           # OpenAI API key (or from env)
    max_pages=50,           # Maximum pages to scrape
    max_concurrent=5        # Concurrent page requests
)
```

## Examples

### Stanford Faculty Directory

```bash
python -m scraper run https://profiles.stanford.edu/bioengineering \
  --schema-json '{
    "name": "faculty name",
    "title": "academic position",
    "email": "contact email",
    "page_url": "profile page URL"
  }' \
  --output data/outputs/stanford_faculty.json
```

### Generic Contact Directory

```bash
python -m scraper run https://example.com/contacts \
  --schema-json '{
    "name": "contact name",
    "phone": "phone number",
    "address": "physical address"
  }' \
  --max-pages 20
```

## Performance

- **LLM Call**: Once per site/schema combination
- **Scraping Speed**: ~5-10 pages/second with concurrency
- **Memory**: Efficient streaming, minimal overhead

## Limitations

- Requires OpenAI API access
- May not work with JavaScript-heavy SPAs (use Playwright/Selenium for those)
- Pagination detection may fail on unusual patterns
- Rate limiting depends on target site

## License

MIT

