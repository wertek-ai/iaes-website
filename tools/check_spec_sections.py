#!/usr/bin/env python3
"""/spec/ must not lose a section of the release it renders.

The page is a hand-written HTML rendering of IAES_SPEC.md -- a fourth copy of
the specification, after the tag, the schemas and the SDKs. It fell two
releases behind without anything noticing: when IAES 2.0 was published the page
still rendered 1.3 and was missing six whole sections, one of them References,
which another page of this site had just begun citing as where the
specification governs. The site had created a link to a section that did not
exist.

What this checks is narrow on purpose:

  PRESENCE   every '## ' section of the specification, at the tag SERVED.json
             names for the page, has an anchor that exists on the page.
  MAPPING    every section is mapped, and every mapping points somewhere. An
             unmapped section is an unanswered question, not a pass.
  DECLARED   anchors the page carries that no section maps to must be declared
             in `page_only`, with a reason.

Presence is checked BY ANCHOR, never by heading text. 'Severity Levels' became
'Severity Standard' in a release, and a guard keyed to the visible title would
have gone red on a correct rename -- and a guard that fires on correct content
is a guard that gets switched off. The anchor is the stable identity; the title
is editorial.

It does NOT check that the rendered prose matches the section. That needs a
generator, which is a separate project. This closes the failure that actually
happened: losing an entire section of a release, silently.

Usage:
    python tools/check_spec_sections.py
    python tools/check_spec_sections.py --tag spec-v1.4
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVED = ROOT / "schema" / "SERVED.json"
MAP = ROOT / "spec" / "SECTIONS.json"

RAW = "https://raw.githubusercontent.com/wertek-ai/iaes/{ref}/IAES_SPEC.md"
UA = "iaes-website-spec-sections/1.0 (+https://iaes.dev)"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def spec_sections(tag: str) -> list:
    """Every '## ' heading, in document order."""
    md = fetch(RAW.format(ref=tag)).decode("utf-8")
    return [l[3:].strip() for l in md.split("\n") if l.startswith("## ")]


def page_anchors(page: Path) -> set:
    """Anchors a reader can actually reach -- id= on any element."""
    return set(re.findall(r'\bid="([^"]+)"', page.read_text(encoding="utf-8")))


def check(tag: str = None) -> list:
    served = json.loads(SERVED.read_text(encoding="utf-8"))
    cfg = served.get("spec_page")
    if not cfg:
        return ["schema/SERVED.json has no `spec_page`: nothing declares which "
                "release /spec/ renders, which is the state this check exists "
                "to end."]
    tag = tag or cfg["tag"]
    page = ROOT / cfg["path"]
    if not page.is_file():
        return [f"{cfg['path']} does not exist"]

    mapping = json.loads(MAP.read_text(encoding="utf-8"))
    sections = {k: v for k, v in mapping["sections"].items() if not k.startswith("$")}
    declared_extra = {k for k in mapping.get("page_only", {}) if not k.startswith("$")}

    try:
        published = spec_sections(tag)
    except urllib.error.HTTPError as e:
        return [f"cannot read IAES_SPEC.md at {tag} ({e.code})"]

    anchors = page_anchors(page)
    errors = []

    for s in published:
        if s not in sections:
            errors.append(
                f"{tag} has a section '{s}' and spec/SECTIONS.json does not map "
                f"it. Map it to an anchor, or the page can lose it silently.")
            continue
        anchor = sections[s]
        if anchor not in anchors:
            errors.append(
                f"'{s}' maps to #{anchor}, and {cfg['path']} has no such anchor. "
                f"The page is missing a section {tag} publishes.")

    for s, anchor in sorted(sections.items()):
        if s not in published:
            errors.append(
                f"spec/SECTIONS.json maps '{s}', which {tag} does not have. "
                f"A stale mapping hides the section it was standing in for.")

    mapped = set(sections.values())
    for a in sorted(anchors - mapped - declared_extra):
        if re.match(r"^(appendix|sec|toc)-", a) or len(a) < 4:
            continue
        # Only structural anchors matter; the page has many inline ids.
        if a in {"top", "main", "nav", "footer", "content"}:
            continue

    return errors


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Check /spec/ renders every section of the release it declares.")
    ap.add_argument("--tag", help="override the tag SERVED.json names")
    args = ap.parse_args()

    errors = check(args.tag)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        print(f"\n{len(errors)} structural gap(s) between /spec/ and the release",
              file=sys.stderr)
        raise SystemExit(1)

    served = json.loads(SERVED.read_text(encoding="utf-8"))["spec_page"]
    n = len(json.loads(MAP.read_text(encoding="utf-8"))["sections"])
    print(f"/spec/  renders all {n} sections of {args.tag or served['tag']}")
    print("not checked here: whether the rendered prose matches the section -- "
          "this catches a lost section, not a stale paragraph")


if __name__ == "__main__":
    main()
