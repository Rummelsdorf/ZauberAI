#!/usr/bin/env python3
"""Datenpipeline Stage 2: pairs.jsonl -> finetune.jsonl (Multi-Turn SFT, HF/OpenAI-Stil).

Verwendung:
    python export_finetune.py pairs.jsonl --out finetune.jsonl --tasks bug_fixing,explain,detect
"""

import argparse
import json
from pathlib import Path

SYSTEM_DEFAULT = (
    "Du bist ein erfahrener {lang}-Entwickler. Du schreibst korrekten, vollständigen "
    "und wartbaren Code. Denke kurz durch, was im Bug ansteht (Ursache, nicht nur Symptom), "
    "und liefere die gefixte Lösung als markdown-Codeblock zurück."
)


def norm_str(x):
    return str(x or "").strip()


def to_example(pair, task):
    lang = pair.get("language", "python")
    meta = pair.get("meta", {})
    sys_text = SYSTEM_DEFAULT.format(lang=lang)
    input_text = pair["input"]
    if task == "bug_fixing":
        user = "Repariere den Bug:\n\n" + input_text + "\n\nFixed code:"
        asst = "Fixed code:\n" + pair["output"]
    elif task == "security_fixing":
        user = "Fech diese Sicherheitslücke:\n\n" + input_text + "\n\nFixed code:"
        asst = "Fixed code (Fehlerbehebung für " + norm_str(meta.get("cwe", "?")) + "):\n" + pair["output"]
    elif task == "explain":
        user = "Erkläre den Bug im Code:\n\n" + input_text
        asst = "Ursache + Root Cause + korrigierter Snippet:\n" + pair["output"]
    elif task == "detect":
        user = "Identifiziere den Bug im Code. Nenne CWE und kurze Beschreibung."
        asst = norm_str(meta.get("cwe") or "Bug") + ": " + norm_str(meta.get("desc") or "kurze Beschreibung des Bugs")
    else:
        raise ValueError(task)
    return {
        "messages": [
            {"role": "system", "content": sys_text},
            {"role": "user", "content": user},
            {"role": "assistant", "content": asst},
        ],
        "meta": {"source": pair["source"], "task": task, "id": pair["id"]},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pairs", help="pairs.jsonl (Ausgabe von build_pairs.py)")
    ap.add_argument("--out", default="finetune.jsonl")
    ap.add_argument("--tasks", default="bug_fixing,explain,detect", help="Komma-getrennte Liste von Tasks")
    args = ap.parse_args()

    pairs = [json.loads(l) for l in Path(args.pairs).read_text().splitlines() if l.strip()]
    tasks = [t for t in args.tasks.split(",") if t]

    n = 0
    with Path(args.out).open("w") as f:
        for pair in pairs:
            for task in tasks:
                f.write(json.dumps(to_example(pair, task), ensure_ascii=False) + "\n")
                n += 1
    print(f"{len(pairs)} Paare -> {n} Beispiele geschrieben -> {args.out}")


if __name__ == "__main__":
    main()
