#!/usr/bin/env python3
"""Resolve commit URLs from OSV/NVD-normalized records to patch files.

Input: JSONL with records containing `fix_commits[].url` (from extract_osv.py).
Output: JSONL with fetched patch text (cached).

Example:
  python pipeline/resolve_commits.py --in osv_pypi.jsonl --out patches.jsonl --cache .cache/patches
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path


def cache_path(cache_dir: Path, url: str) -> Path:
    h = hashlib.sha256(url.encode()).hexdigest()
    return cache_dir / f"{h}.patch"


def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "ZauberAI-data-pipeline/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cache", type=Path, default=Path(".cache/patches"))
    ap.add_argument("--sleep", type=float, default=0.2, help="Sekunden zwischen Requests")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    args.cache.mkdir(parents=True, exist_ok=True)
    n = ok = err = 0
    with args.inp.open() as inp, args.out.open("w", encoding="utf-8") as out:
        for line in inp:
            if not line.strip():
                continue
            rec = json.loads(line)
            for fix in rec.get("fix_commits") or []:
                url = fix.get("url")
                if not url or "/commit/" not in url:
                    continue
                if not url.endswith(".patch"):
                    url = url + ".patch"
                n += 1
                if args.limit and n > args.limit:
                    print(f"limit reached: fetched={ok} errors={err}")
                    return
                cp = cache_path(args.cache, url)
                try:
                    if cp.exists():
                        patch = cp.read_text(encoding="utf-8", errors="replace")
                    else:
                        patch = fetch(url)
                        cp.write_text(patch, encoding="utf-8")
                        time.sleep(args.sleep)
                    out.write(json.dumps({
                        "source_id": rec.get("id"), "cves": rec.get("cves", []),
                        "ecosystems": rec.get("ecosystems", []), "commit_url": url,
                        "patch": patch,
                    }, ensure_ascii=False) + "\n")
                    ok += 1
                except Exception as e:
                    err += 1
                    out.write(json.dumps({"source_id": rec.get("id"), "commit_url": url, "error": str(e)}, ensure_ascii=False) + "\n")
    print(f"commits={n} ok={ok} errors={err} out={args.out}")


if __name__ == "__main__":
    main()
