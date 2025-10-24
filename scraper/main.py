import asyncio
import json
from typing import Optional
import typer
from rich.console import Console
from rich.json import JSON
from .models import InputSchema
from .core import DirectoryScraper


app = typer.Typer(help="Generalized directory scraper with LLM-assisted selector inference")
console = Console()


@app.command()
def run(
    url: str = typer.Argument(..., help="URL of the directory to scrape"),
    schema_file: Optional[str] = typer.Option(
        None,
        "--schema",
        "-s",
        help="Path to JSON file with schema (field: description mapping)"
    ),
    schema_json: Optional[str] = typer.Option(
        None,
        "--schema-json",
        "-j",
        help="Inline JSON schema string"
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output JSON file path"
    ),
    max_pages: int = typer.Option(50, "--max-pages", "-p", help="Maximum pages to scrape"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="OpenAI API key"),
    use_browser: bool = typer.Option(
        False,
        "--browser",
        "-b",
        help="Use browser automation for JavaScript-heavy sites (slower but handles dynamic content)"
    ),
    wait_for: Optional[str] = typer.Option(
        None,
        "--wait-for",
        help="CSS selector to wait for when using browser mode"
    ),
    detail_schema: Optional[str] = typer.Option(
        None,
        "--detail-schema",
        "-d",
        help="Path to JSON schema for detail pages (enables deep scraping)"
    ),
    detail_url_field: Optional[str] = typer.Option(
        None,
        "--detail-url-field",
        help="Field name containing URL to detail page (required with --detail-schema)"
    )
):
    """Scrape a directory and extract structured data."""
    
    schema = _load_schema(schema_file, schema_json)
    detail_schema_dict = _load_schema(detail_schema, None) if detail_schema else None
    
    if not schema:
        console.print("[red]Error: Must provide schema via --schema or --schema-json[/red]")
        console.print("\nExample schema:")
        console.print(JSON(json.dumps({
            "name": "person's full name",
            "email": "contact email address",
            "title": "job title or position"
        }, indent=2)))
        raise typer.Exit(1)
    
    input_schema = InputSchema(fields=schema)
    detail_input_schema = InputSchema(fields=detail_schema_dict) if detail_schema_dict else None
    
    # Validate deep scraping options
    if detail_input_schema and not detail_url_field:
        console.print("[red]Error: --detail-url-field required when using --detail-schema[/red]")
        raise typer.Exit(1)
    
    if use_browser:
        console.print("[yellow]Browser mode enabled - JavaScript content will be rendered[/yellow]")
    
    if detail_input_schema:
        console.print(f"[yellow]Deep scraping enabled - will follow '{detail_url_field}' to extract detail page data[/yellow]")
    
    scraper = DirectoryScraper(
        schema=input_schema,
        api_key=api_key,
        max_pages=max_pages,
        use_browser=use_browser,
        wait_for_selector=wait_for,
        detail_schema=detail_input_schema,
        detail_url_field=detail_url_field
    )
    
    result = asyncio.run(scraper.scrape(url, verbose=True))
    
    console.print(f"\n[green]Extracted {result.total_count} records[/green]")
    
    if output:
        with open(output, 'w') as f:
            json.dump(result.as_dicts, f, indent=2)
        console.print(f"[green]Saved to {output}[/green]")
    else:
        console.print("\n[cyan]Sample records:[/cyan]")
        for i, record in enumerate(result.records[:3], 1):
            console.print(f"\n{i}. {JSON(json.dumps(record.data, indent=2))}")
        
        if result.total_count > 3:
            console.print(f"\n... and {result.total_count - 3} more records")


@app.command()
def test(
    url: str = typer.Argument(..., help="URL to test"),
    schema_file: Optional[str] = typer.Option(None, "--schema", "-s"),
    schema_json: Optional[str] = typer.Option(None, "--schema-json", "-j"),
    api_key: Optional[str] = typer.Option(None, "--api-key"),
    save_html: bool = typer.Option(False, "--save-html", help="Save HTML to file for debugging"),
    use_browser: bool = typer.Option(
        False,
        "--browser",
        "-b",
        help="Use browser automation for JavaScript-heavy sites"
    ),
    wait_for: Optional[str] = typer.Option(
        None,
        "--wait-for",
        help="CSS selector to wait for when using browser mode"
    )
):
    """Test LLM selector inference on a URL."""
    
    schema = _load_schema(schema_file, schema_json)
    
    if not schema:
        console.print("[red]Error: Must provide schema[/red]")
        raise typer.Exit(1)
    
    input_schema = InputSchema(fields=schema)
    
    if use_browser:
        console.print("[yellow]Browser mode enabled[/yellow]")
    
    scraper = DirectoryScraper(
        schema=input_schema,
        api_key=api_key,
        use_browser=use_browser,
        wait_for_selector=wait_for
    )
    
    console.print(f"[cyan]Testing selector inference for:[/cyan] {url}")
    result = asyncio.run(scraper.test_selectors(url))
    
    if save_html and "html_sample" in result:
        with open("debug_html.html", "w") as f:
            f.write(result["html_sample"])
        console.print("[yellow]HTML saved to debug_html.html[/yellow]")
    
    console.print("\n[green]Inferred Selectors:[/green]")
    console.print(JSON(json.dumps(result["selector_map"], indent=2)))
    
    console.print(f"\n[green]Sample Records ({result['total_sample_count']} found):[/green]")
    console.print(JSON(json.dumps(result["sample_records"], indent=2)))


def _load_schema(schema_file: Optional[str], schema_json: Optional[str]) -> Optional[dict]:
    """Load schema from file or inline JSON."""
    if schema_file:
        with open(schema_file) as f:
            return json.load(f)
    elif schema_json:
        return json.loads(schema_json)
    return None


if __name__ == "__main__":
    app()

