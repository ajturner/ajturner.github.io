"""Check that every URL in _data/wordpress_urls.yml exists in a built site.

Usage: python3 scripts/ci/check_wordpress_urls.py _site [/baseurl]
These are the URLs the WordPress site served, so links and search results that
point at them keep working when this build replaces it.
"""
import sys
from pathlib import Path

import yaml

site = Path(sys.argv[1])
urls = yaml.safe_load(Path("_data/wordpress_urls.yml").read_text())["urls"]

missing = []
for url in urls:
    target = site / url.strip("/")
    if url.endswith("/"):
        target = target / "index.html"
    if not target.is_file():
        missing.append(url)

for url in missing:
    print(f"missing: {url}")
print(f"{len(urls) - len(missing)} of {len(urls)} WordPress URLs present")
sys.exit(1 if missing else 0)
