"""Fail if a pull request makes a URL disappear without a redirect or a retirement.

Usage: python3 scripts/ci/check_url_changes.py BASE_MANIFEST HEAD_MANIFEST

Both manifests come from _plugins/url_manifest.rb: {"/url/": "source/file" or null}.
For each URL the base branch built that the pull request does not:

- its source file still exists but builds nowhere: a visibility decision (hidden,
  `portfolio` topic removed, album excluded). Reported, not a failure.
- its source file now builds at another URL: the URL moved. Fails; add the old URL
  to _data/redirects.yml.
- its source file is gone: fails unless the URL is listed in _data/retired_urls.yml.
- it was generated (no source file, e.g. a tag page whose last post lost the tag):
  reported, not a failure. WordPress-era URLs are guarded separately by
  scripts/ci/check_wordpress_urls.py.

The rule is written down in docs/site-contract.md.
"""
import json
import os
import sys
from pathlib import Path

import yaml


def main() -> int:
    base_path, head_path = Path(sys.argv[1]), Path(sys.argv[2])
    if not base_path.exists():
        print("::notice::The base branch wrote no URL manifest (it predates the check, or its build failed); skipping.")
        return 0
    base = json.loads(base_path.read_text())
    head = json.loads(head_path.read_text())
    retired_file = Path("_data/retired_urls.yml")
    retired = {r["url"] for r in (yaml.safe_load(retired_file.read_text()) or [])} if retired_file.exists() else set()
    head_by_source = {src: url for url, src in head.items() if src}

    failures, notes = [], []
    for url, src in sorted(base.items()):
        if url in head:
            continue
        if src is None:
            notes.append(f"{url}: generated page no longer built")
        elif src in head_by_source:
            failures.append(f"{url}: {src} now builds at {head_by_source[src]}. Add a redirect in _data/redirects.yml.")
        elif Path(src).exists():
            notes.append(f"{url}: {src} is no longer built (hidden or excluded)")
        elif url in retired:
            notes.append(f"{url}: retired in _data/retired_urls.yml")
        else:
            failures.append(f"{url}: {src} was removed. Add a redirect in _data/redirects.yml, "
                            "or list the URL in _data/retired_urls.yml with a reason.")

    added = sorted(set(head) - set(base))
    for n in notes:
        print(f"::notice::{n}")
    for f in failures:
        print(f"::error::{f}")
    summary = [f"URL check: {len(base)} URLs before, {len(head)} after, {len(added)} added, "
               f"{len(notes)} removed by decision, {len(failures)} removed without a redirect."]
    summary += [f"- added {u}" for u in added[:50]] + [f"- {n}" for n in notes] + [f"- **{f}**" for f in failures]
    print("\n".join(summary))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as fh:
            fh.write("\n".join(summary) + "\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
