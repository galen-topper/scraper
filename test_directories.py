"""
Testing CORE for all directories. However, due to OPENAI rate limiting, it doesn't really work since we get limited before all can run. 
"""

import asyncio
import json
from scraper import DirectoryScraper, InputSchema
from pathlib import Path
from typing import Dict, List, Any


# Test cases with their schemas
TEST_CASES = [
    {
        "name": "Pennsylvania Nursing Facilities",
        "url": "https://sais.health.pa.gov/commonpoc/content/publicweb/nhinformation2.asp?COUNTY=Allegheny",
        "schema": {
            "name": "facility name",
            "address": "facility address",
            "phone": "phone number",
            "county": "county name"
        },
        "use_browser": False,
        "expected_min_records": 10,
        "required_fields": ["name"]
    },
    {
        "name": "San Diego Psychological Association",
        "url": "https://sdpsych.org/Find-a-Psychologist",
        "schema": {
            "name": "psychologist's name",
            "credentials": "degrees (Ph.D., Psy.D., etc.)",
            "areas_of_focus": "specializations and areas of practice",
            "office_location": "office location in San Diego",
            "insurance": "insurance providers accepted",
            "profile_url": "link to their profile page"
        },
        "use_browser": True,
        "expected_min_records": 20,
        "required_fields": ["name", "profile_url"]
    },
    {
        "name": "Stanford Engineering Profiles",
        "url": "https://profiles.stanford.edu/browse/school-of-engineering?p=1&ps=100",
        "schema": {
            "name": "person's name",
            "title": "job title or position",
            "email": "email address",
            "page_url": "URL to their profile page"
        },
        "use_browser": False,
        "expected_min_records": 50,
        "required_fields": ["name", "page_url"]
    },
    {
        "name": "Psychology Houston Directory",
        "url": "https://psychologyhouston.org/directory.php",
        "schema": {
            "name": "psychologist's name",
            "phone": "phone number",
            "email": "email address",
            "address": "office address",
            "specialty": "areas of specialty"
        },
        "use_browser": False,
        "expected_min_records": 10,
        "required_fields": ["name"]
    },
    {
        "name": "Bay Area Psychological Association",
        "url": "https://community.bapapsych.org/search/newsearch.asp?bst=&cdlGroupID=&txt_country=&txt_statelist=&txt_state=&ERR_LS_20250827_222102_27698=txt_state%7CLocation%7C20%7C0%7C%7C0",
        "schema": {
            "name": "psychologist's name",
            "location": "practice location",
            "specialty": "areas of specialty",
            "phone": "phone number"
        },
        "use_browser": True,
        "expected_min_records": 10,
        "required_fields": ["name"]
    },
    {
        "name": "UC Berkeley Math Graduate Students",
        "url": "https://math.berkeley.edu/people/graduate-students",
        "schema": {
            "name": "student's name",
            "email": "email address",
            "advisor": "faculty advisor",
            "research": "research interests"
        },
        "use_browser": False,
        "expected_min_records": 20,
        "required_fields": ["name"]
    },
    {
        "name": "Y Combinator Companies",
        "url": "https://www.ycombinator.com/companies/",
        "schema": {
            "name": "company name",
            "description": "company description",
            "location": "company location",
            "batch": "YC batch (e.g., W21)",
            "url": "company website URL"
        },
        "use_browser": True,
        "expected_min_records": 20,
        "required_fields": ["name"]
    }
]


class TestResults:
    """Track test results across all test cases."""
    
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def add_result(self, test_case: str, passed: bool, records: int, 
                   messages: List[str], sample_record: Dict = None):
        """Add a test result."""
        self.results.append({
            "test": test_case,
            "passed": passed,
            "records": records,
            "messages": messages,
            "sample": sample_record
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {len(self.results)}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"Success Rate: {(self.passed/len(self.results)*100):.1f}%")
        print("="*80)
        
        for result in self.results:
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"\n{status}: {result['test']}")
            print(f"  Records: {result['records']}")
            for msg in result["messages"]:
                print(f"  {msg}")
            if result["sample"]:
                print(f"  Sample data:")
                for key, value in list(result["sample"].items())[:3]:
                    display_val = str(value)[:60] + "..." if len(str(value)) > 60 else value
                    print(f"    - {key}: {display_val}")
    
    def save_to_file(self):
        """Save detailed results to JSON."""
        output_path = Path("data/outputs/test_results.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {output_path}")


async def test_directory(test_case: Dict, test_results: TestResults):
    """Test a single directory."""
    
    print(f"\n{'='*80}")
    print(f"🧪 Testing: {test_case['name']}")
    print(f"URL: {test_case['url']}")
    print(f"Browser Mode: {test_case['use_browser']}")
    print(f"Expected Min Records: {test_case['expected_min_records']}")
    print(f"{'='*80}")
    
    messages = []
    
    try:
        # Create schema
        input_schema = InputSchema(fields=test_case["schema"])
        
        # Create scraper
        scraper = DirectoryScraper(
            schema=input_schema,
            max_pages=1,  # Test just first page
            use_browser=test_case["use_browser"]
        )
        
        # Run scraper
        result = await scraper.scrape(test_case["url"], verbose=True)
        
        # Validate results
        passed = True
        records_count = len(result.records)
        
        # Check 1: Did we get any records?
        if records_count == 0:
            messages.append("❌ No records extracted")
            passed = False
        else:
            messages.append(f"✅ Extracted {records_count} records")
        
        # Check 2: Did we meet minimum threshold?
        if records_count < test_case["expected_min_records"]:
            messages.append(f"⚠️  Below expected minimum ({records_count} < {test_case['expected_min_records']})")
            # Don't fail, just warn
        else:
            messages.append(f"✅ Meets minimum threshold ({records_count} >= {test_case['expected_min_records']})")
        
        # Check 3: Are required fields populated?
        if records_count > 0:
            sample = result.records[0].data
            missing_fields = []
            
            for field in test_case["required_fields"]:
                if field not in sample or not sample[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                messages.append(f"❌ Missing required fields: {missing_fields}")
                passed = False
            else:
                messages.append(f"✅ All required fields present: {test_case['required_fields']}")
        
        # Check 4: Sample data quality
        if records_count > 0:
            sample = result.records[0].data
            populated_fields = sum(1 for v in sample.values() if v)
            total_fields = len(sample)
            
            if populated_fields == 0:
                messages.append("❌ No fields populated in sample record")
                passed = False
            else:
                messages.append(f"✅ Sample record has {populated_fields}/{total_fields} fields populated")
        
        # Add result
        sample_record = result.records[0].data if result.records else None
        test_results.add_result(
            test_case["name"],
            passed,
            records_count,
            messages,
            sample_record
        )
        
    except Exception as e:
        messages.append(f"❌ Exception: {str(e)}")
        test_results.add_result(
            test_case["name"],
            False,
            0,
            messages,
            None
        )
        print(f"\n❌ Test failed with exception: {e}")


async def run_all_tests():
    """Run all test cases."""
    
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "DIRECTORY SCRAPER TEST SUITE" + " "*30 + "║")
    print("╚" + "="*78 + "╝")
    
    test_results = TestResults()
    
    for i, test_case in enumerate(TEST_CASES):
        await test_directory(test_case, test_results)
        
        # Longer pause between tests to avoid rate limiting
        if i < len(TEST_CASES) - 1:
            print(f"\n⏸️  Waiting 5 seconds before next test to avoid rate limiting...")
            await asyncio.sleep(5)
    
    # Print summary
    test_results.print_summary()
    test_results.save_to_file()
    
    return test_results


if __name__ == "__main__":
    results = asyncio.run(run_all_tests())
    
    # Exit with appropriate code
    if results.failed > 0:
        print(f"\n⚠️  {results.failed} test(s) failed")
        exit(1)
    else:
        print(f"\n🎉 All {results.passed} tests passed!")
        exit(0)

