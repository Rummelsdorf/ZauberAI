#!/usr/bin/env python3
"""Datenpipeline Stage 1: Buggy-Code/Fix-Paare extrahieren (pairs.jsonl).

Verwendung:
    python build_pairs.py --source swebench_lite --limit 200 --out pairs.jsonl

Ausgabe-Schema (ein Paar pro JSONL-Zeile):
{
  "id": "swebench_lite:django__django-000001",
  "source": "swebench_lite",
  "task": "bug_fixing",
  "language": "python",
  "input":  "Problemstellung + buggy code (entfernte Zeilen)",
  "output": "Fix-Diff (unified diff)",
  "meta": {"tests": ["django.test.x"], "lang": "python"}
}
"""

import argparse
import glob
import hashlib
import json
import sys
from pathlib import Path

DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data"


def norm(text):
    return (text or "").strip()


def code_block(lang, text):
    return f"```{lang}\n{text.rstrip()}\n```"


def parse_diff(patch):
    """Unified diff -> (buggy_lines, fixed_lines): entfernte vs. hinzugefügte Zeilen."""
    buggy, fixed = [], []
    for line in patch.splitlines():
        if line.startswith(("+++", "---", "diff ", "index ", "@@ ", "new file", "deleted file")):
            continue
        if line.startswith("+"):
            fixed.append(line[1:])
        elif line.startswith("-"):
            buggy.append(line[1:])
    return "\n".join(buggy), "\n".join(fixed)


def _col(rec, name):
    for k, v in rec.items():
        if k.lower() == name.lower():
            return v
    return None


def load_parquet(source, data_dir):
    """DuckDB liest Parquet (ohne pandas/pyarrow)."""
    base = Path(data_dir)
    files = sorted(glob.glob(str(base / source / "data" / "*.parquet"))) or sorted(
        glob.glob(str(base / source / "*.parquet"))
    )
    if not files:
        raise SystemExit(f"keine Daten gefunden unter {base / source}/**/*.parquet")
    import duckdb

    con = duckdb.connect()
    con.execute("SELECT * FROM read_parquet(?) LIMIT 0", [files[0]])
    cols = [d[0] for d in con.description]
    rows = con.execute("SELECT * FROM read_parquet(?)", [files[0]]).fetchall()
    return cols, [dict(zip(cols, r)) for r in rows]


def split_tests(text):
    out = []
    for part in norm(text).replace(";", " ").replace(",", " ").split():
        if part.strip():
            out.append(part.strip())
    return out


def load_swebench_family(source, limit, data_dir):
    """Loader für swebench / swebench_lite / swebench_verified (HF parquet via duckdb)."""
    cols, recs = load_parquet(source, data_dir)
    print(f"Geladen: {len(recs)} Zeilen, Spalten: {cols}")
    pairs = []
    for rec in (recs[:limit] if limit else recs):
        iid = norm(_col(rec, "instance_id"))
        desc = norm(_col(rec, "problem_statement"))
        patch = norm(_col(rec, "patch"))
        tests = split_tests(_col(rec, "FAIL_TO_PASS") or _col(rec, "fail_to_pass") or "")
        buggy, fixed = parse_diff(patch)
        if not iid or not desc or not buggy or buggy == fixed:
            continue
        lang = "python"  # SWE-bench-Familie ist heute größtenteils Python
        meta = {"tests": tests, "lang": lang, "source_dataset": source}
        pairs.append(
            {
                "id": f"{source}:{iid}",
                "source": source,
                "task": "bug_fixing",
                "language": lang,
                "input": f"{desc}\n\nBuggy code:\n{code_block(lang, buggy)}",
                "output": patch,
                "meta": meta,
            }
        )
    return pairs


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, help="z.B. swebench_lite")
    ap.add_argument("--limit", type=int, default=0, help="maximale Anzahl Paare (0=unbegrenzt)")
    ap.add_argument("--out", default="pairs.jsonl", help="Ausgabedatei (JSONL)")
    ap.add_argument("--data-dir", default=str(DEFAULT_DATA), help="Basisverzeichnis für Daten")
    ap.add_argument("--dedupe", action="store_true", help="exakte Duplikate auslassen")
    args = ap.parse_args()

    loaders = {
        "swebench": load_swebench_family,
        "swebench_lite": load_swebench_family,
        "swebench_verified": load_swebench_family,
    }
    if args.source not in loaders:
        sys.exit(f"unbekannter source '{args.source}'. Verfügbar: {sorted(loaders)}")

    pairs = loaders[args.source](args.source, args.limit, args.data_dir)

    seen, kept = set(), []
    for p in pairs:
        if args.dedupe:
            key = hashlib.sha256((p["input"] + p["output"]).encode()).hexdigest()
            if key in seen:
                continue
            seen.add(key)
        kept.append(p)

    out = Path(args.out)
    with out.open("w") as f:
        for p in kept:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"{len(pairs)} extrahiert, {len(kept)} geschrieben -> {out}")


if __name__ == "__main__":
    main()
