#!/usr/bin/env python3
"""The site must declare one specification version, and it must be a real one.

For months this site served "IAES Specification v1.3" beside a markdown copy
that said v1.2, while the standard's packages emitted 1.4. Three claims, no
mechanism to notice, and a reader had no way to tell which one to believe.

What this checks is narrower than it sounds, and deliberately so:

  1. every surface names the SAME version -- the page title, the structured
     data, the visible heading, and all fourteen translations;
  2. that version is not AHEAD of the latest `spec-vX.Y` tag in the standard's
     repository. A site may lag a release; it may not announce one that does
     not exist.

What it does NOT check is whether the site is current. A site honestly serving
1.3 while 1.4 exists is behind, which is a decision for a person, not a defect,
and the check says so and passes. Forcing the number forward would produce a
page claiming 1.4 while describing 1.3 -- worse than behind, because it would
be wrong. The content moves first; the number follows.

Usage:
    python tools/check_declared_version.py
    python tools/check_declared_version.py --releases spec-v1.3,spec-v1.4
"""

import argparse
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Where the site states which specification it serves.
SURFACES = [
    "index.html",
    "spec/index.html",
    "js/i18n.js",
]

# The phrase the site uses to declare what it serves. Deliberately not "any
# v1.x": the version history legitimately names 1.0, 1.1 and 1.2, and the
# example payloads carry the spec_version they illustrate. A guard that fires
# on correct content is a guard that gets switched off.
VERSION = re.compile(r"(?:IAES\s+)?Specification\s+v(\d+\.\d+)(?![\d.])")

TAGS_API = "https://api.github.com/repos/wertek-ai/iaes/tags"


def declared_versions() -> dict:
    """Every version this site declares, per file, with how often."""
    found = {}
    for rel in SURFACES:
        path = ROOT / rel
        if not path.exists():
            continue
        counts = Counter(VERSION.findall(path.read_text(encoding="utf-8", errors="replace")))
        if counts:
            found[rel] = counts
    return found


def published_specification_versions(explicit):
    if explicit:
        return {t.strip().removeprefix("spec-v") for t in explicit.split(",") if t.strip()}
    req = urllib.request.Request(TAGS_API, headers={"User-Agent": "iaes-website"})
    with urllib.request.urlopen(req, timeout=20) as r:
        tags = json.load(r)
    return {t["name"].removeprefix("spec-v") for t in tags if t["name"].startswith("spec-v")}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--releases", help="comma-separated spec tags, for offline runs")
    args = ap.parse_args()

    found = declared_versions()
    if not found:
        print("error: the site declares no specification version at all", file=sys.stderr)
        raise SystemExit(1)

    all_versions = set()
    for counts in found.values():
        all_versions |= set(counts)

    problems = []

    if len(all_versions) > 1:
        problems.append(
            "the site declares more than one specification version: "
            + ", ".join(sorted(all_versions))
        )
        for rel, counts in sorted(found.items()):
            problems.append(
                "  " + rel + ": " + ", ".join(f"{v} x{n}" for v, n in sorted(counts.items()))
            )

    declared = sorted(all_versions)[0] if len(all_versions) == 1 else None

    if declared:
        try:
            published = published_specification_versions(args.releases)
        except Exception as e:  # offline, rate-limited, whatever
            print(f"note: could not reach the tag list ({e}); checked coherence only")
            published = None

        if published:
            def key(v):
                return tuple(int(x) for x in v.split("."))

            latest = max(published, key=key)
            if key(declared) > key(latest):
                problems.append(
                    f"the site declares IAES {declared}, which is ahead of the latest "
                    f"published specification release ({latest}). A site may lag a "
                    f"release; it may not announce one that does not exist."
                )
            elif declared != latest:
                print(
                    f"note: the site serves IAES {declared} and the latest release is "
                    f"{latest}. That is a lag, not a defect -- but the content has to "
                    f"move before the number does."
                )

    if problems:
        for p in problems:
            print(p if p.startswith("  ") else f"error: {p}", file=sys.stderr)
        raise SystemExit(1)

    total = sum(sum(c.values()) for c in found.values())
    print(
        f"the site declares IAES {declared}, consistently, "
        f"in {total} places across {len(found)} files"
    )
    print(
        "note: this checks what the site claims to serve, not whether it is current. "
        "Serving an older specification honestly is a decision, not a defect."
    )


if __name__ == "__main__":
    main()
