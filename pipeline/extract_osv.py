#!/usr/bin/env python3
"""Extract OSV records with fix signals into normalized JSONL.

Examples:
  python pipeline/extract_osv.py --zip data/osv/PyPI/all.zip --out osv_pypi.jsonl
  python pipeline/extract_osv.py --dir data/osv/PyPI --ecosystem PyPI --out osv_pypi.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

COMMIT_RE = re.compile(
    r"https?://(?P<host>github\.com|gitlab\.com|bitbucket\.org)/(?P<repo>[^/]+/[^/]+)/(?:commit|-/commit)/(?P<sha>[0-9a-f]{7,40})",
    re.I,
)
GIT_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$", re.I)


def iter_json_records(zip_path: Path | None, dir_path: Path | None):
    if zip_path:
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if not name.endswith(".json"):
                    continue
                with zf.open(name) as f:
                    try:
                        yield name, json.load(f)
                    except json.JSONDecodeError:
                        continue
    elif dir_path:
        for p in sorted(Path(dir_path).rglob("*.json")):
            try:
                yield str(p), json.loads(p.read_text())
            except Exception:
                continue
    else:
        raise ValueError("zip_path or dir_path required")


def extract_fix_commits(rec: dict) -> list[dict]:
    fixes: list[dict] = []
    seen = set()

    def add(url=None, sha=None, repo=None, host=None, source=""):
        key = (url or "", (sha or "").lower(), repo or "")
        if key in seen or (not url and not sha):
            return
        seen.add(key)
        fixes.append({"url": url, "sha": (sha or "").lower() or None, "repo": repo, "host": host, "source": source})

    for ref in rec.get("references") or []:
        url = (ref.get("url") or "").strip()
        m = COMMIT_RE.search(url)
        if m:
            repo = m.group("repo").removesuffix(".git")
            add(url=url, sha=m.group("sha"), repo=repo, host=m.group("host"), source=f"reference:{ref.get('type','')}")
        elif ref.get("type") == "FIX" and url:
            add(url=url, source="reference:FIX")

    for aff in rec.get("affected") or []:
        for rng in aff.get("ranges") or []:
            if rng.get("type") != "GIT":
                continue
            repo_url = (rng.get("repo") or "").strip()
            for ev in rng.get("events") or []:
                fixed = ev.get("fixed")
                if isinstance(fixed, str) and GIT_SHA_RE.match(fixed):
                    url = None
                    mrepo = re.match(r"https?://(?P<host>github\.com|gitlab\.com|bitbucket\.org)/(?P<repo>[^/]+/[^/]+?)(?:\.git)?/?$", repo_url, re.I)
                    if mrepo:
                        host = mrepo.group("host")
                        repo = mrepo.group("repo")
                        slug = "/-/commit" if host == "gitlab.com" else "/commit"
                        url = f"https://{host}/{repo}{slug}/{fixed}"
                        add(url=url, sha=fixed, repo=repo, host=host, source="git_range_fixed")
                    else:
                        add(sha=fixed, repo=repo_url or None, source="git_range_fixed")
    return fixes


def normalize(rec: dict, ecosystem_hint: str | None = None) -> dict:
    affected = []
    ecosystems = set()
    for aff in rec.get("affected") or []:
        pkg = aff.get("package") or {}
        eco = pkg.get("ecosystem") or ecosystem_hint
        if eco:
            ecosystems.add(eco)
        affected.append({
            "ecosystem": eco,
            "name": pkg.get("name"),
            "purl": pkg.get("purl"),
            "ranges": aff.get("ranges"),
            "versions": aff.get("versions"),
        })
    sev = rec.get("severity") or []
    aliases = rec.get("aliases") or []
    cves = [a for a in aliases if a.startswith("CVE-")]
    return {
        "id": rec.get("id"),
        "aliases": aliases,
        "cves": cves,
        "summary": rec.get("summary"),
        "details": rec.get("details"),
        "severity": sev,
        "affected": affected,
        "ecosystems": sorted(ecosystems),
        "references": rec.get("references") or [],
        "fix_commits": extract_fix_commits(rec),
        "modified": rec.get("modified"),
        "published": rec.get("published"),
        "source": "osv",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zip", type=Path, help="Pfad zu OSV all.zip")
    ap.add_argument("--dir", type=Path, help="Verzeichnis mit OSV JSON-Dateien")
    ap.add_argument("--ecosystem", help="Ecosystem-Hint (falls in Records fehlend)")
    ap.add_argument("--out", type=Path, required=True, help="Ausgabe JSONL")
    ap.add_argument("--only-with-fixes", action="store_true", help="Nur Records mit Fix-Signal")
    args = ap.parse_args()

    n = n_fix = 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as out:
        for _, rec in iter_json_records(args.zip, args.dir):
            n += 1
            norm = normalize(rec, args.ecosystem)
            has_fix = bool(norm["fix_commits"])
            if has_fix:
                n_fix += 1
            if args.only_with_fixes and not has_fix:
                continue
            out.write(json.dumps(norm, ensure_ascii=False) + "\n")
    print(f"records={n} with_fix_signals={n_fix} written={args.out}")


if __name__ == "__main__":
    main()
