#!/usr/bin/env python3
"""The site must stop saying what the specification withdrew.

IAES 2.0 withdrew the ISO 13374 attributions and stopped describing its ISO
citations as alignment: the correspondences had never been verified against the
cited documents, and three of the four documents were never held. That decision
was made in the standard's repository, and this site went on publishing the
withdrawn claims -- measured on 2026-09-08, in seven surfaces, and in fourteen
languages for the ones that live in `js/i18n.js`.

Nothing could have noticed. `/schema/` has a parity check because a schema is
bytes; prose has no schema, and a person re-adding "ISO-aligned" to a hero
subtitle six months from now will not remember an RFC.

So this gives the site mechanical memory of what it can no longer say. Two
tests, because two kinds of claim need different ones:

  PHRASES  English wording that asserts a withdrawn claim, in HTML and in the
           English block of i18n.js, where the source text lives.
  KEYS     i18n keys whose whole purpose was to carry one. Checked by NAME,
           across every language: a regex for an English phrase cannot find its
           Japanese translation, and retiring the key retires all fourteen.

What this does NOT do is verify prose. It cannot tell whether a paragraph
describing ISO 14224 is accurate. It kills known-retired claims, which is a
smaller promise honestly kept -- and the honest limit is why the file is called
CLAIMS and not TRUTH.

A claim may carry `phrases` (literals) and `patterns` (regular expressions).
Both are needed: the literal records the wording that was actually published,
which is greppable and auditable; the pattern covers the inflections and
synonyms of the same assertion. The sentence "fields that map directly to
established industrial standards" escaped a list containing "maps directly to
ISO" on two counts at once -- a plural verb and a synonym for ISO.

`allowed` carries exact strings that look like a claim and are not. The title of
the DOI'd preprint contains "ISO-Aligned" and cannot be changed: it is a
published work with a permanent identifier, and citing it accurately is not
making the claim. That is the same distinction the standard's own frontier
guard draws between attribution and dependency.

Usage:
    python tools/check_withdrawn_claims.py
    python tools/check_withdrawn_claims.py --list
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAIMS = ROOT / "content" / "CLAIMS.json"
I18N = ROOT / "js" / "i18n.js"

SKIP_DIRS = {".git", "node_modules", "content", "tools", "schema", "schemas"}


def surfaces():
    """Every page a reader can reach, plus the translation source."""
    for p in sorted(ROOT.rglob("*.html")):
        if not any(d in p.parts for d in SKIP_DIRS):
            yield p
    if I18N.is_file():
        yield I18N


def english_block(text: str):
    """i18n.js holds fourteen languages; the phrase rules apply to the source.

    Returns the block AND where it starts, because a finding is reported with a
    line number and that number has to point at the line in the file. Counting
    newlines inside the block reports line 786 for something on line 1204 --
    a number that looks precise and sends the reader to the wrong place.
    """
    start = text.find("  en: {")
    if start < 0:
        return text, 0
    nxt = re.search(r"\n  [a-z]{2}(-[A-Za-z]+)?: \{", text[start + 8:])
    end = start + 8 + nxt.start() if nxt else len(text)
    return text[start:end], text.count("\n", 0, start)


def declared_keys(text: str) -> set:
    """Every i18n key declared anywhere in the file, in any language."""
    return set(re.findall(r'"([a-z_]+[a-z0-9_.]*)"\s*:', text))


def check() -> list:
    spec = json.loads(CLAIMS.read_text(encoding="utf-8"))
    errors = []

    # PHRASES
    for path in surfaces():
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(ROOT).as_posix()
        haystack, line_offset = english_block(text) if path == I18N else (text, 0)
        # Remove the exempt strings first, so a phrase inside one is not a hit.
        # An exemption applies ONLY in the file that declared it: a page that
        # explains a withdrawal must name what was withdrawn, and that licence
        # must not leak to a page that is simply still making the claim.
        for a in spec.get("allowed", []):
            if a["where"] != rel:
                continue
            if a["text"] not in haystack:
                errors.append(
                    f"{rel} -- the exemption '{a['text'][:60]}...' no longer "
                    f"matches anything. An exemption that stops matching is "
                    f"either stale or the text it protected was edited; "
                    f"re-read it rather than leaving it declared.")
                continue
            haystack = haystack.replace(a["text"], " [allowed citation] ")
        for claim in spec["withdrawn"]:
            # A literal names the wording actually found, so a reader of this
            # file can grep for it. A pattern covers the family it belongs to:
            # every mapping literal here said `maps`, and the sentence that
            # escaped said `map`, because its subject was plural. A list keyed
            # to one inflection is a list for one inflection.
            rules = ([(re.escape(p), p) for p in claim.get("phrases", [])]
                     + [(p, p) for p in claim.get("patterns", [])])
            for rx, phrase in rules:
                for m in re.finditer(rx, haystack, re.I):
                    line = haystack.count("\n", 0, m.start()) + 1 + line_offset
                    ctx = " ".join(
                        haystack[max(0, m.start() - 45):m.end() + 45].split())
                    errors.append(
                        f"{rel}:{line} -- '{phrase}' ({claim['id']}, withdrawn "
                        f"in {claim['since']})\n       ...{ctx}...")

    # KEYS
    if I18N.is_file():
        text = I18N.read_text(encoding="utf-8")
        present = declared_keys(text)
        # A key is retired at the moment it is removed, so the file records
        # names that are no longer declared -- that is the point. What it must
        # not record is a name that was NEVER declared: `field_timestamp` was
        # retired here while the real key was `envelope.field_timestamp`, so the
        # list read as protection and protected nothing. History is the test:
        # if git has never seen the key, the entry is a typo.
        # The history test needs history. A shallow clone -- which is what
        # actions/checkout gives by default -- has none, so every retired key
        # looks like it never existed and the check invents one finding per
        # entry. A check that cannot run must SAY SO, not produce answers: this
        # reports the missing precondition once, and the workflow asks for the
        # full history.
        shallow = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT,
            capture_output=True).stdout.decode().strip() == "true"

        for key in spec.get("retired_keys", []):
            if key in present:
                errors.append(
                    f"js/i18n.js -- retired key '{key}' is still declared. "
                    f"Remove it in every language, or take it off retired_keys "
                    f"and say why it may stay.")
                continue
            if shallow:
                continue
            seen = subprocess.run(
                ["git", "log", "--oneline", "-1", "-S", f'"{key}":', "--",
                 "js/i18n.js"], cwd=ROOT, capture_output=True)
            if not seen.stdout.strip():
                errors.append(
                    f"content/CLAIMS.json retires '{key}', and js/i18n.js has "
                    f"never declared it in this repository's history. A retired "
                    f"name that never existed reads as protection and protects "
                    f"nothing -- check the spelling.")

        if shallow:
            errors.append(
                "this is a shallow clone, so the retired-key spelling check "
                "cannot run: `git log` has no history to search. Check out with "
                "`fetch-depth: 0`. Reported rather than skipped, because a "
                "silent skip is how a check stops checking.")

    return errors


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Check that the site does not publish claims IAES withdrew.")
    ap.add_argument("--list", action="store_true",
                    help="print what is withdrawn and stop")
    args = ap.parse_args()

    spec = json.loads(CLAIMS.read_text(encoding="utf-8"))
    if args.list:
        for c in spec["withdrawn"]:
            print(f"{c['id']}  (withdrawn in {c['since']})")
            print(f"  why:       {c['why']}")
            print(f"  authority: {c['authority']}")
            print(f"  phrases:   {', '.join(c['phrases'])}\n")
        print(f"retired i18n keys: {len(spec.get('retired_keys', []))}")
        return

    errors = check()
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        # A missing precondition is not a published claim, and a summary that
        # calls it one sends the reader looking for the wrong thing.
        claims = [e for e in errors if "shallow clone" not in e]
        if claims:
            print(f"\n{len(claims)} withdrawn claim(s) still published",
                  file=sys.stderr)
        if len(claims) != len(errors):
            print("\nand the retired-key spelling check could not run at all",
                  file=sys.stderr)
        raise SystemExit(1)

    n = len(spec["withdrawn"])
    print(f"no withdrawn claim is published: {n} claim families checked across "
          f"{len(list(surfaces()))} surfaces")
    print("not checked here: whether the prose that remains is accurate -- "
          "this kills known-retired claims, it does not verify content")


if __name__ == "__main__":
    main()
