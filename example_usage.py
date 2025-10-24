"""
Example usage of the directory scraper framework.
"""

import asyncio
import json
from scraper import DirectoryScraper, InputSchema


async def example_1_basic_usage():
    """Basic scraping example."""
    print("=" * 60)
    print("Example 1: Basic Directory Scraping")
    print("=" * 60)
    
    schema = InputSchema(fields={
        "name": "person's full name",
        "email": "email address",
        "title": "job title or position",
        "page_url": "link to their profile page"
    })
    
    scraper = DirectoryScraper(
        schema=schema,
        max_pages=3,
        max_concurrent=2
    )
    
    # Replace with actual directory URL
    url = "https://example.com/directory"
    
    try:
        result = await scraper.scrape(url, verbose=True)
        
        print(f"\n✓ Scraped {result.total_count} records")
        print("\nFirst 3 records:")
        for i, record in enumerate(result.records[:3], 1):
            print(f"\n{i}. {json.dumps(record.data, indent=2)}")
        
        with open("output.json", "w") as f:
            json.dump(result.as_dicts, f, indent=2)
        print("\n✓ Saved to output.json")
        
    except Exception as e:
        print(f"Error: {e}")


async def example_2_test_selectors():
    """Test selector inference without full scrape."""
    print("\n" + "=" * 60)
    print("Example 2: Test Selector Inference")
    print("=" * 60)
    
    schema = InputSchema(fields={
        "name": "person's name",
        "email": "contact email"
    })
    
    scraper = DirectoryScraper(schema=schema)
    
    url = "https://example.com/directory"
    
    try:
        result = await scraper.test_selectors(url)
        
        print("\nInferred Selectors:")
        print(json.dumps(result["selector_map"], indent=2))
        
        print(f"\nSample Records ({result['total_sample_count']} found):")
        print(json.dumps(result["sample_records"], indent=2))
        
    except Exception as e:
        print(f"Error: {e}")


async def example_3_custom_schema():
    """Custom schema for specific use case."""
    print("\n" + "=" * 60)
    print("Example 3: Custom Schema")
    print("=" * 60)
    
    schema = InputSchema(fields={
        "company_name": "name of the company",
        "industry": "industry or sector",
        "website": "company website URL",
        "description": "brief company description",
        "founding_year": "year the company was founded"
    })
    
    scraper = DirectoryScraper(
        schema=schema,
        max_pages=5
    )
    
    url = "https://example.com/companies"
    
    try:
        result = await scraper.scrape(url, verbose=True)
        print(f"\n✓ Extracted {result.total_count} companies")
        
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Run examples."""
    print("Directory Scraper - Example Usage\n")
    print("Note: Replace example URLs with actual directory URLs")
    print("Set OPENAI_API_KEY environment variable before running\n")
    
    # Run examples (comment out as needed)
    asyncio.run(example_1_basic_usage())
    # asyncio.run(example_2_test_selectors())
    # asyncio.run(example_3_custom_schema())


if __name__ == "__main__":
    main()

