from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
import re


class InputSchema(BaseModel):
    """Schema defining what fields to extract from the directory."""
    fields: Dict[str, str] = Field(
        ...,
        description="Field name -> description mapping"
    )
    
    @validator('fields')
    def validate_fields(cls, v):
        if not v:
            raise ValueError("At least one field must be specified")
        return v


class SelectorMap(BaseModel):
    """Mapping of field names to CSS/XPath selectors."""
    selectors: Dict[str, Optional[str]]
    list_item_selector: Optional[str] = None
    pagination_selector: Optional[str] = None


class OutputRecord(BaseModel):
    """A single extracted record from the directory."""
    data: Dict[str, Any]
    
    class Config:
        extra = "allow"
    
    @validator('data', pre=True)
    def clean_data(cls, v):
        if not isinstance(v, dict):
            return v
        cleaned = {}
        for key, value in v.items():
            if isinstance(value, str):
                value = value.strip()
                if 'email' in key.lower():
                    value = cls._clean_email(value)
                if 'url' in key.lower() or 'link' in key.lower():
                    value = cls._clean_url(value)
            cleaned[key] = value
        return cleaned
    
    @staticmethod
    def _clean_email(email: str) -> str:
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', email)
        return match.group(0) if match else email
    
    @staticmethod
    def _clean_url(url: str) -> str:
        url = url.strip()
        if url and not url.startswith(('http://', 'https://', '//')):
            url = 'https://' + url
        return url


class ScraperResult(BaseModel):
    """Complete result from a scraping session."""
    url: str
    records: List[OutputRecord]
    total_count: int
    schema_used: InputSchema
    
    @property
    def as_dicts(self) -> List[Dict[str, Any]]:
        return [r.data for r in self.records]

