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


def spec_text(tag: str) -> str:
    return fetch(RAW.format(ref=tag)).decode("utf-8")


def spec_sections(md: str) -> list:
    """Every '## ' heading, in document order."""
    return [l[3:].strip() for l in md.split("\n") if l.startswith("## ")]


SCHEMA_URI = re.compile(r"https://iaes\.(?:dev|wertek\.ai)/schema/v[0-9]+/")


# A version-history row is identified by its DATE column, not by starting with
# a number. The specification has other tables whose first cell looks like a
# version -- ISO 14224 mechanism codes run 1.1, 3.1, 4.1 -- and a row keyed on
# the number alone collected those too, then overwrote the real 1.4 row with a
# second table's 1.4 and reported it as having no URIs at all. The date is what
# makes the history table the history table.
MONTH = (r"(?:January|February|March|April|May|June|July|August|September|"
         r"October|November|December)\s+[0-9]{4}")


def history_uris(md: str) -> dict:
    """{version: the schema URIs its version-history row names}, from the tag."""
    out = {}
    for line in md.split("\n"):
        m = re.match(r"\|\s*([0-9]+\.[0-9]+)\s*\|\s*%s\s*\|" % MONTH, line)
        if m:
            out[m.group(1)] = sorted(set(SCHEMA_URI.findall(line)))
    return out


def page_history_uris(page: Path) -> dict:
    """The same, as the page publishes it. Same discriminator, same reason."""
    t = page.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(
            r"<tr>\s*<td>(?:<strong>)?([0-9]+\.[0-9]+)(?:</strong>)?</td>\s*"
            r"<td>%s</td>.*?</tr>" % MONTH, t, re.S):
        out[m.group(1)] = sorted(set(SCHEMA_URI.findall(m.group(0))))
    return out


def page_anchors(page: Path) -> set:
    """Anchors a reader can actually reach -- id= on any element."""
    return set(re.findall(r'\bid="([^"]+)"', page.read_text(encoding="utf-8")))


def page_sections(page: Path) -> set:
    """The ids the page uses as SECTIONS of the specification.

    Structural by construction, not by heuristic: the page carries thirty ids
    and only the ones on a `section.spec-section` stand for a section of the
    document. The other ten are sub-anchors and UI elements, and a rule that
    tried to tell them apart by name would be guessing.
    """
    return set(re.findall(r'<section class="spec-section" id="([^"]+)"',
                          page.read_text(encoding="utf-8")))


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
        md = spec_text(tag)
    except urllib.error.HTTPError as e:
        return [f"cannot read IAES_SPEC.md at {tag} ({e.code})"]
    published = spec_sections(md)

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

    # HISTORY. A version-history row states what a PAST release did, and its
    # schema URIs belong to that release's major forever -- 2.0 says so in
    # words: a representation served under a major's URI stays that major's and
    # is never regenerated from a later one.
    #
    # This exists because a sweep broke it. Migrating the live content to 2.0
    # replaced `/schema/v1/` with `/schema/v2/` across the file, and the 1.4 row
    # went with it: the page then said 1.4's schemas declared a v2 URI, which
    # is both false and the exact thing the major rule forbids. Version numbers
    # were handled carefully in that sweep and URIs were not.
    page_hist, spec_hist = page_history_uris(page), history_uris(md)
    for version, want in sorted(spec_hist.items()):
        got = page_hist.get(version)
        if got is None or got == want:
            continue
        errors.append(
            f"{cfg['path']} -- the {version} version-history row names "
            f"{got or 'no schema URI'}, and {tag} names {want}. A past "
            f"release's URIs belong to its own major and are never rewritten "
            f"forward.")

    # DECLARED. This promise was in the docstring and not in the code: the loop
    # skipped and then did nothing with what it kept, so a section the release
    # has no counterpart for passed in silence. A guard that states a property
    # it does not execute is the defect it exists to catch.
    mapped = set(sections.values())
    for a in sorted(page_sections(page) - mapped - declared_extra):
        errors.append(
            f"{cfg['path']} has a section #{a} that no part of {tag} maps to. "
            f"Map it in spec/SECTIONS.json, or declare it under `page_only` "
            f"with a reason. An undeclared section reads as specification and "
            f"is not.")

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
