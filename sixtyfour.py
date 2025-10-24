"""
Simple lead enrichment using Sixtyfour AI API.
Samples 100 random profiles from Stanford data and enriches them.
"""

import json
import os
import random
import time
import requests
from dotenv import load_dotenv

load_dotenv()


def enrich_lead(lead_info, struct, api_key):
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    # Submit job
    response = requests.post(
        "https://api.sixtyfour.ai/enrich-lead",
        headers=headers,
        json={"lead_info": lead_info, "struct": struct}
    )
    
    
    if response.ok:
        result = response.json()
        print("✅ Success! Keys:", list(result.keys()))
        print("\n" + "="*50)
        print("STRUCTURED DATA:")
        print("="*50)
        structured_data = result.get("structured_data", {})
        for key, value in structured_data.items():
            print(f"{key}: {value}")
    else:
        print("❌ Request failed:", response.status_code, response.text[:800])
    return response.json()

def main():
    api_key = os.getenv("SIXTYFOUR_API_KEY")
    if not api_key:
        print("ERROR: SIXTYFOUR_API_KEY not set in .env file")
        return

    with open("data/outputs/stanford_engineering_profiles.json") as f:
        all_profiles = json.load(f)
    
    sample_size = min(100, len(all_profiles))
    profiles = random.sample(all_profiles, sample_size)
    
    print(f"Sampled {len(profiles)} random profiles from {len(all_profiles)} total")
    print("=" * 60)

    struct = {
        "name": "name of the student",
        "title": "job title or position",
        "email": "email address",
        "page_url": "url of their profile page",
        "bio": "bio"

    }
    results = []
    
    for i, profile in enumerate(profiles, 1):
        print(f"\n[{i}/{len(profiles)}] Enriching: {profile.get('name', 'Unknown')}")
        
        lead_info = {
            "name": profile.get("name", ""),
            "title": profile.get("title", ""),
            "email": profile.get("email", ""),
            "page_url": profile.get("page_url", "")
        }
        
        lead_info = {k: v for k, v in lead_info.items() if v}
        
        try:
            result = enrich_lead(lead_info, struct, api_key)
            
            enriched = {
                "original": profile,
                "enriched": result.get("structured_data", {}),
                "confidence": result.get("confidence_score", 0),
                "notes": result.get("notes", "")
            }
            
            results.append(enriched)
            
            print(f"Success (confidence: {enriched['confidence']}/10)")
            
            with open("data/outputs/stanford_enriched.json", "w") as f:
                json.dump(results, f, indent=2)
            
        except Exception as e:
            print(f"Error: {e}")
            results.append({
                "original": profile,
                "error": str(e)
            })
    
    print("\n" + "=" * 60)
    print(f"Complete! Enriched {len(results)} profiles")
    print(f"Successful: {sum(1 for r in results if 'enriched' in r)}")
    print(f"Failed: {sum(1 for r in results if 'error' in r)}")
    print(f"\nSaved to: data/outputs/stanford_enriched.json")


if __name__ == "__main__":
    main()
