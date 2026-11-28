#!/usr/bin/env python3
"""Automatischer Download von HuggingFace-Datensätzen für ZauberAI.

Verfügbare Datensätze:
- SWE-bench (Coding/Bugs)
- Cyber-Security (Vyber07)
- WizardLM (Instruct/Chat)
- Wikipedia (Text/Enwik8)

Gated Datensätze (HF-Token erforderlich):
- Unaligned, Toxiic-DPO, DPO, Eli5, WizardLM-Vicuna
"""

import argparse
import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Optional

DATA_DIR = Path.home() / "ZauberAI" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def parse_size(size_str: str) -> int:
    """Parsen Größenstring (z.B. '100MB' -> 100_000_000)"""
    match = re.match(r'^(\d+)\s*(B|M|G)$', size_str, re.I)
    if not match:
        return 0
    num = int(match.group(1))
    unit = match.group(2)
    if unit == 'B':
        return num
    elif unit == 'M':
        return num * 1_000_000
    elif unit == 'G':
        return num * 1_000_000_000
    return 0


def download_file(url: str, local_path: Path, timeout: int = 60) -> bool:
    """Download eine Datei mit Retry-Logik"""
    retries = 3
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ZauberAI-DataDownloader/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                content_length = int(r.headers.get("content-length", 0))
                print(f"\n[{i+1}/{retries}] Download: {url[:80]}...")
                print(f"  Content-Length: {content_length:,} bytes")
                
                # Cache-Header prüfen
                cache_range = r.headers.get("range")
                if cache_range:
                    # Bei resumiable downloads
                    pass
                
                with open(local_path, 'wb') as f:
                    data = r.read()
                    f.write(data)
                
                print(f"  ✓ Download complete: {local_path.name} ({len(data):,} bytes)")
                return True
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
            if i < retries - 1:
                print(f"  Retrying in 5s...")
                import time
                time.sleep(5)
            else:
                print(f"  ✗ Failed after {retries} attempts")
                return False
    return False


def download_parquet(file: str, url: str) -> Optional[Path]:
    """Download ein Parquet-File"""
    local_path = DATA_DIR / file
    if local_path.exists():
        print(f"  Already exists: {local_path}")
        return local_path
    
    print(f"\nDownloading {file}...")
    if download_file(url, local_path):
        return local_path
    return None


def download_json(file: str, url: str) -> Optional[Path]:
    """Download ein JSON-File"""
    local_path = DATA_DIR / file
    if local_path.exists():
        print(f"  Already exists: {local_path}")
        return local_path
    
    print(f"\nDownloading {file}...")
    if download_file(url, local_path):
        return local_path
    return None


def download_text(file: str, url: str, encoding: str = 'utf-8') -> Optional[Path]:
    """Download ein Text-File"""
    local_path = DATA_DIR / file
    if local_path.exists():
        print(f"  Already exists: {local_path}")
        return local_path
    
    print(f"\nDownloading {file}...")
    if download_file(url, local_path):
        return local_path
    return None


def main():
    parser = argparse.ArgumentParser(description="Download HuggingFace Datensätze")
    parser.add_argument("--source", required=True, help="Quelle (swebench_lite, cyber, wizardlm, wikipedia)")
    parser.add_argument("--file", type=str, help="Spezifisches File (optional)")
    parser.add_argument("--list", action="store_true", help="Nur Liste anzeigen")
    args = parser.parse_args()
    
    source = args.source.lower()
    files = []
    
    if source == "swebench_lite":
        files = [
            ("test-00000-of-00001.parquet", 
             "https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite/resolve/main/data/test-00000-of-00001.parquet"),
        ]
    
    elif source == "cyber":
        files = [
            ("CyberSec-Dataset_escaped.jsonl",
             "https://huggingface.co/datasets/Vyber07/cyber-security/resolve/main/CyberSec-Dataset_escaped.jsonl"),
        ]
    
    elif source == "wizardlm":
        files = [
            ("alpaca_evol_instruct_70k.json",
             "https://huggingface.co/datasets/WizardLMTeam/WizardLM_evol_instruct_70k/resolve/main/alpaca_evol_instruct_70k.json"),
        ]
    
    elif source == "wikipedia":
        files = [
            ("enwik8-20190126-en-100M-train-100M.txt",
             "https://huggingface.co/datasets/Wikipedia/enwik8-20190126-en-100M-train-100M.txt/resolve/main/enwik8-20190126-en-100M-train-100M.txt"),
            ("enwik9-20190126-en-100M-train-100M.txt",
             "https://huggingface.co/datasets/Wikipedia/enwik9-20190126-en-100M-train-100M.txt/resolve/main/enwik9-20190126-en-100M-train-100M.txt"),
        ]
    
    else:
        print(f"Unknown source: {source}")
        return 1
    
    if args.list:
        print("Verfügbare Dateien für Source:", source)
        for f, u in files:
            print(f"  - {f}")
        return 0
    
    if args.file:
        # Spezifisches File
        for f, u in files:
            if f == args.file:
                if f.endswith('.parquet'):
                    path = download_parquet(f, u)
                elif f.endswith('.json'):
                    path = download_json(f, u)
                else:
                    path = download_text(f, u)
                break
    else:
        # Alle Dateien
        print(f"\nDownloading all files for {source}...")
        for f, u in files:
            if f.endswith('.parquet'):
                path = download_parquet(f, u)
            elif f.endswith('.json'):
                path = download_json(f, u)
            else:
                path = download_text(f, u)
            if path:
                print(f"  ✓ Downloaded: {path} ({path.stat().st_size:,} bytes)")
    
    print(f"\n=== Download complete ===")
    print(f"Dateien in {DATA_DIR}:")
    for p in sorted(DATA_DIR.glob("*")):
        if p.is_file():
            print(f"  {p.name} ({p.stat().st_size:,} bytes)")
    
    return 0


if __name__ == "__main__":
    exit(main())
