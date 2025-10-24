#!/bin/bash

# UCSD Biology PhD Student Directory
# Deep scraping: Get basic info from listing, then follow links for full profiles

python -m scraper run \
  "https://biology.ucsd.edu/education/grad/phd/student-directory/index" \
  --schema data/schemas/ucsd_bio_phd_listing.json \
  --detail-schema data/schemas/ucsd_bio_phd_detail.json \
  --detail-url-field profile_url \
  --output data/outputs/ucsd_bio_phd_students.json \
  --browser \
  --max-pages 10 \
  --verbose

echo ""
echo "Deep scraping complete!"
echo "Results saved to: data/outputs/ucsd_bio_phd_students.json"
echo ""
echo "Summary:"
jq 'length' data/outputs/ucsd_bio_phd_students.json 2>/dev/null || echo "Check output file for results"
