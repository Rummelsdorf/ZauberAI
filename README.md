# ZauberAI

Datenpipeline für ein Coding-/Agentic-/Cybersecurity-Modell (Fine-Tuning / Distillation).

Ziel: aus öffentlichen Bug-, CVE- und Fix-Quellen Trainingspaare bauen (`buggy -> fix`) und in ein SFT-Format (`messages` JSONL) exportieren.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quickstart (SWE-bench Lite Demo)

```bash
# Daten herunterladen (Parquet)
mkdir -p data/swebench_lite/data
curl -L -o data/swebench_lite/data/test-00000-of-00001.parquet \
  "https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite/resolve/main/data/test-00000-of-00001.parquet"

# Stage 1: Paare extrahieren
python pipeline/build_pairs.py --source swebench_lite --limit 200 --out pairs.jsonl --dedupe

# Stage 2: SFT-Format (OpenAI/HF messages)
python pipeline/export_finetune.py pairs.jsonl --out finetune.jsonl --tasks bug_fixing,explain,detect
```

## Ausgabeformate

### `pairs.jsonl` (Stage 1)

```json
{
  "id": "swebench_lite:django__django-...",
  "source": "swebench_lite",
  "task": "bug_fixing",
  "language": "python",
  "input": "Problemstellung + buggy code",
  "output": "Unified diff Fix",
  "meta": {"tests": ["..."], "lang": "python"}
}
```

### `finetune.jsonl` (Stage 2)

OpenAI/HF-kompatibles `messages`-Format mit `system/user/assistant` pro Beispiel.

## OSV / NVD Extraktion

```bash
# OSV: Ecosystem-Bulk laden und Records mit Fix-Signal extrahieren
mkdir -p data/osv
curl -L -o data/osv/PyPI-all.zip https://storage.googleapis.com/osv-vulnerabilities/PyPI/all.zip
python pipeline/extract_osv.py --zip data/osv/PyPI-all.zip --ecosystem PyPI --only-with-fixes --out osv_pypi.jsonl

# Commit-Patches auflösen (cacht unter .cache/patches)
python pipeline/resolve_commits.py --in osv_pypi.jsonl --out patches.jsonl --limit 50
```

NVD ist vor allem für Metadaten/Labels (CWE, CVSS, CPE, Referenzen) nützlich; Code-Fixes kommen meist über referenzierte Commits/Advisories. Siehe `docs/datasets.md` und `TODO.md`.

## Geplante Quellen

| Quelle | Typ | Link |
|---|---|---|
| SWE-bench / Lite / Verified | Real Issues + PR-Fixes | https://github.com/SWE-bench/SWE-bench |
| Multi-SWE-bench | Multi-Lang Issues + Fixes | https://github.com/Multi-SWE-bench/Multi-SWE-bench |
| OSV.dev Bulk | CVE/Vuln-Metadaten, Commit-Refs | https://storage.googleapis.com/osv-vulnerabilities/ |
| GitHub Advisory DB | Security Advisories (OSV) | https://github.com/github/advisory-database |
| CISA KEV | Aktiv ausgenutzte CVEs | https://www.cisa.gov/known-exploited-vulnerabilities-catalog |
| NVD | CVE-Details/CVSS/CWE | https://nvd.nist.gov/ |

## Roadmap

Siehe [TODO.md](TODO.md) für die detaillierte Planung.

## Hinweis

Prüfe Lizenzen und Herkunft der Daten vor dem Training. Security-Advisories nicht ungeprüft als vollständige Code-Fixes interpretieren.
