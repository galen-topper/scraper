# Directory Scraper

A generalized directory scraper that uses an LLM to define the selectors used to extract data from almost any web directory.

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
  "name": "",
  "title": "",
  "email": "",
  "page_url": "",
  "bio": "",
}
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

### This program can run both in code as well

### Code Version Example

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

for record in result.as_dicts:
    print(record)
```

## How It Works

1. **Fetch Initial Page**: Downloads the first page of the directory
2. **LLM Inference**: Sends a temporary sample to GPT-4.1, generating the correct selectors. 
3. **Parse & Extract**: Parse using selectors to extract structured data
4. **Pagination**: Automatically detects and follows "next page" links, allowing us to go 1 level deeper. 
5. **Concurrent Scraping**: Processes multiple pages in parallel for speed




