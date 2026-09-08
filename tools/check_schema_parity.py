#!/usr/bin/env python3
"""What this site serves must be what the specification published.

The eight schemas of IAES 2.0 declare `$id: https://iaes.dev/schema/v2/...`.
That identity is a promise made in the standard's repository about THIS site,
and for the first forty minutes after 2.0 was published the path did not exist:
every schema in a released major named a URI that answered 404. The same defect
1.4 corrected -- an `$id` under a host that never resolved -- reintroduced from
the other side, because the two repositories share a contract and nothing
mechanical connected them.

So this checks the contract, per major declared in schema/SERVED.json:

  1. IDENTITY   the served filename is the last segment of the schema's own
                `$id`, and that `$id` sits under the major it is served from.
                A file under v2 declaring a v1 identity is served at a URI that
                is not its own name.
  2. PARITY     the bytes served are byte-identical to the bytes that tag
                published. Not "equivalent JSON": a schema is retrieved and
                hashed by third parties, and a reformat changes what they get.
  3. COMPLETE   every schema in the tag is served, and nothing is served that
                the tag does not contain.

Rule 2 is what stops the failure GOVERNANCE forbids in words: regenerating an
older major's URIs from a newer release. Copy a 2.0 schema over /schema/v1/ and
this goes red, which no amount of prose could do.

Read from git, not from the filesystem. On Windows a checkout with
core.autocrlf turns every LF into CRLF, so the working tree of an untouched
clone differs from the tag in every schema -- 8 of 8, purely in line endings.
A guard that read the filesystem would fail on the maintainer's machine and
pass in CI, which is worse than not having it.

--live additionally fetches from iaes.dev and compares. Off by default: on a
pull request the site has not deployed yet, so a live check there would measure
the previous deploy and report on code that is not the code under review.

Usage:
    python tools/check_schema_parity.py
    python tools/check_schema_parity.py --live
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVED = ROOT / "schema" / "SERVED.json"

REPO = "wertek-ai/iaes"
TREE_API = "https://api.github.com/repos/{repo}/git/trees/{ref}?recursive=1"
RAW = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"
LIVE = "https://iaes.dev/schema/{major}/{name}"

# Netlify and GitHub both reject urllib's default User-Agent.
UA = "iaes-website-schema-parity/1.0 (+https://iaes.dev)"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    token = os.environ.get("GITHUB_TOKEN")
    if token and "github" in url:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def committed(path: str) -> bytes:
    """The blob as committed -- never the working tree. See the docstring."""
    out = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT,
                         capture_output=True)
    if out.returncode != 0:
        raise FileNotFoundError(path)
    return out.stdout


def tag_schemas(tag: str) -> dict:
    """{filename in the tag: bytes}, for every schema/*.json it publishes."""
    tree = json.loads(fetch(TREE_API.format(repo=REPO, ref=tag)))
    paths = [e["path"] for e in tree.get("tree", [])
             if e["path"].startswith("schema/") and e["path"].endswith(".json")]
    return {p: fetch(RAW.format(repo=REPO, ref=tag, path=p)) for p in paths}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def check(live: bool = False) -> list:
    errors = []
    served = json.loads(SERVED.read_text(encoding="utf-8"))

    for major, spec in sorted(served["majors"].items()):
        tag = spec["tag"]
        try:
            published = tag_schemas(tag)
        except urllib.error.HTTPError as e:
            errors.append(f"{major}: cannot read {tag} from {REPO} ({e.code}). "
                          "A tag this file names must exist.")
            continue

        expected = {}
        for path, raw in published.items():
            try:
                schema_id = json.loads(raw)["$id"]
            except (json.JSONDecodeError, KeyError):
                errors.append(f"{tag}:{path} has no $id")
                continue
            name = schema_id.rsplit("/", 1)[-1]
            # 1. IDENTITY -- the $id must live under the major serving it.
            if not schema_id.startswith(f"https://iaes.dev/schema/{major}/"):
                errors.append(
                    f"{major}/{name}: $id is {schema_id}, which is not under "
                    f"/schema/{major}/ -- it would be served at a URI that is "
                    f"not its own name")
                continue
            expected[name] = raw

        directory = ROOT / "schema" / major
        on_disk = {p.name for p in directory.iterdir()} if directory.is_dir() else set()

        # 3. COMPLETE, both directions.
        for name in sorted(set(expected) - on_disk):
            errors.append(f"{major}/{name}: published by {tag} and not served")
        for name in sorted(on_disk - set(expected)):
            errors.append(f"{major}/{name}: served and not published by {tag}")

        # 2. PARITY.
        for name, raw in sorted(expected.items()):
            if name not in on_disk:
                continue
            rel = f"schema/{major}/{name}"
            try:
                blob = committed(rel)
            except FileNotFoundError:
                errors.append(f"{rel}: present on disk, not committed")
                continue
            if sha(blob) != sha(raw):
                errors.append(
                    f"{rel}: differs from {tag} "
                    f"({len(blob)} bytes, sha {sha(blob)[:12]} -- "
                    f"published: {len(raw)} bytes, sha {sha(raw)[:12]})")
                continue
            if live:
                try:
                    body = fetch(LIVE.format(major=major, name=name))
                except urllib.error.HTTPError as e:
                    errors.append(f"{rel}: /schema/{major}/{name} answers {e.code}")
                    continue
                if sha(body) != sha(raw):
                    errors.append(
                        f"{rel}: what iaes.dev serves differs from {tag} "
                        f"(sha {sha(body)[:12]} vs {sha(raw)[:12]})")

    # Legacy paths: same rule, different naming. These are frozen copies of a
    # published release kept so old links resolve, and the check exists to keep
    # them frozen -- a third copy nobody verifies is where drift starts.
    for path, spec in sorted(served.get("legacy_paths", {}).items()):
        if path.startswith("$"):
            continue
        tag = spec["tag"]
        try:
            published = tag_schemas(tag)
        except urllib.error.HTTPError as e:
            errors.append(f"{path}/: cannot read {tag} ({e.code})")
            continue
        by_name = {p.rsplit("/", 1)[-1]: raw for p, raw in published.items()}
        directory = ROOT / path
        on_disk = {p.name for p in directory.iterdir()
                   if p.suffix == ".json"} if directory.is_dir() else set()
        for name in sorted(set(by_name) - on_disk):
            errors.append(f"{path}/{name}: published by {tag} and not served")
        for name in sorted(on_disk - set(by_name)):
            errors.append(f"{path}/{name}: served and not published by {tag}")
        for name in sorted(set(by_name) & on_disk):
            rel = f"{path}/{name}"
            try:
                blob = committed(rel)
            except FileNotFoundError:
                errors.append(f"{rel}: present on disk, not committed")
                continue
            if sha(blob) != sha(by_name[name]):
                errors.append(
                    f"{rel}: differs from {tag} -- this path is frozen, and its "
                    f"content is a published release")

    return errors


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Check that iaes.dev serves exactly what each release published.")
    ap.add_argument("--live", action="store_true",
                    help="also fetch from iaes.dev (use after a deploy, not on a PR)")
    args = ap.parse_args()

    errors = check(live=args.live)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        print(f"\n{len(errors)} parity problem(s)", file=sys.stderr)
        raise SystemExit(1)

    served = json.loads(SERVED.read_text(encoding="utf-8"))["majors"]
    for major, spec in sorted(served.items()):
        n = len(list((ROOT / "schema" / major).iterdir()))
        print(f"/schema/{major}/  {n} schemas, byte-identical to {spec['tag']}"
              + ("  (verified live)" if args.live else ""))
    for path, spec in sorted(json.loads(SERVED.read_text(encoding="utf-8"))
                             .get("legacy_paths", {}).items()):
        if path.startswith("$"):
            continue
        n = len([f for f in (ROOT / path).iterdir() if f.suffix == ".json"])
        print(f"/{path}/    {n} schemas, frozen at {spec['tag']} (legacy path)")


if __name__ == "__main__":
    main()
