# AI Context – ZauberAI

Kompakte Kontextdatei für zukünftige Agenten/Sessions. Stand: 2026-11-23.

## Projektziel

Trainingsdaten-Pipeline für ein Coding-/Agentic-/Cybersecurity-Modell aufbauen (Fine-Tuning/Distillation). Fokus: hochwertige Paare **Bug/Schwachstelle → Fix/Patch** plus Metadaten (CWE, CVSS, Sprache, Tests, Quelle, Lizenz). Langfristiges Ziel: an starke Frontier-Coding/Cyber-Fähigkeiten herankommen (Mythos-Niveau als Referenz, nicht als realistisches from-scratch-Ziel).

## Hintergrund: Claude Mythos 5.2 (öffentlich bekannt)

- Quelle: Anthropic System Card "Claude Fable 5.2 & Claude Mythos 5.2" (2026-11-09), https://www.anthropic.com/claude-fable-5-2-mythos-5-2-system-card; Wikipedia Claude Mythos.
- **Training (offiziell beschrieben)**: proprietärer Mix aus öffentlichem Internet, öffentlichen/privaten Datasets, opt-in User-Feedback/Bug-Daten, synthetischen Daten anderer Modelle; Cleaning/Dedup/Klassifikation; ClaudeBot-Crawler respektiert robots.txt; nach Pretraining erhebliches Post-Training/Fine-Tuning für Alignment/Constitution. Knowledge cutoff: Juni 2026.
- **Nicht öffentlich**: exakte Architektur, Parameterzahl, Compute, detailliertes Trainingsrezept. FT-Schätzung (per Wikipedia): ~8T Parameter (Mythos), ~5T (Fable) – unbestätigte Industrieschätzung.
- **Einordnung**: Fable 5.2 = öffentliche Variante mit stärkeren Safeguards; Mythos 5.2 = eingeschränkter Zugang/vetted, stärkere Cyber-Capabilities.

## Repo

- Lokal: `~/ZauberAI`
- GitHub: https://github.com/Rummelsdorf/ZauberAI (public, master)

## Aktuelle Struktur

```
.
├── .gitignore
├── README.md
├── TODO.md
├── aicontext.md
├── docs/
│   └── datasets.md
├── pipeline/
│   ├── build_pairs.py        # Stage 1: Quelle -> pairs.jsonl
│   ├── export_finetune.py    # Stage 2: pairs.jsonl -> finetune.jsonl (SFT messages)
│   ├── extract_osv.py        # OSV bulk/dir -> normalisierte Records mit Fix-Signalen
│   └── resolve_commits.py    # Commit-URLs -> .patch (Cache .cache/patches)
└── requirements.txt          # duckdb, huggingface_hub
```

`data/`, `*.jsonl`, `*.parquet`, `.cache/`, `reports/` sind gitignored.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# SWE-bench Lite Demo
mkdir -p data/swebench_lite/data
curl -L -o data/swebench_lite/data/test-00000-of-00001.parquet \
  https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite/resolve/main/data/test-00000-of-00001.parquet

python pipeline/build_pairs.py --source swebench_lite --limit 200 --out pairs.jsonl --dedupe
python pipeline/export_finetune.py pairs.jsonl --out finetune.jsonl --tasks bug_fixing,explain,detect
```

## Datenformate

### pairs.jsonl
```json
{"id":"swebench_lite:...","source":"swebench_lite","task":"bug_fixing","language":"python","input":"Problem + buggy code","output":"Unified diff","meta":{"tests":[...],"lang":"python"}}
```

### finetune.jsonl
OpenAI/HF-kompatibel: `{"messages":[{"role":"system|user|assistant","content":"..."}],"meta":{...}}`

## Quellen & Extraktionsstrategie

### SWE-bench / Multi-SWE-bench
- Real GitHub Issues + PR-Fixes; gut für agentic coding. HF: `princeton-nlp/SWE-bench_Lite`, `princeton-nlp/SWE-bench_Verified`. Multi-SWE-bench für C/C++, Java, JS/TS, Rust, Go.

### OSV.dev (gut für Security-Fixes)
- Bulk: `https://storage.googleapis.com/osv-vulnerabilities/<ECOSYSTEM>/all.zip`
- Index: `ecosystems.txt`; inkrementell: `modified_id.csv`.
- Fix-Signale: `affected[].ranges[type=GIT].events[].fixed` (SHA) und `references[type=FIX]`/Commit-URLs.
- Workflow: `extract_osv.py` normalisiert Records → `resolve_commits.py` lädt `.patch` → Diff zu buggy/fixed-Paaren parsen.
- Priorisierte Ökosysteme: Git, PyPI, npm, Go, Maven, crates.io, Packagist, RubyGems, NuGet.

### NVD (gut für Metadaten, nicht primär Diffs)
- API 2.0: `https://services.nvd.nist.gov/rest/json/cves/2.0`. Felder: CWE, CVSS, CPE, Beschreibungen, Referenzen.
- Nutzen: Label/Anreicherung, CVE-Join mit OSV/GitHub Advisory. Rate-Limits/ToS beachten.

### GitHub Advisory DB / CISA KEV
- Advisory DB: https://github.com/github/advisory-database (OSV-Format).
- CISA KEV: aktiv ausgenutzte CVEs, hohe Priorität für Security-Fixes.

## HuggingFace-Datasets (erste Sichtung, vor Nutzung prüfen)

| Dataset | Hinweis |
|---|---|
| `bstee615/bigvul` | C/C++ vuln/fix, groß; Qualität prüfen |
| `bstee615/diversevul` | C/C++ diverse vuln detection |
| `colin/PrimeVul` | Paired C/C++ vuln data, gute Kandidaten |
| `DetectVul/CVEFixes` | CVE→Fixes; Herkunft/Lizenz prüfen |
| `MickyMike/cvefixes_bigvul` | Kombiniert; Duplikate prüfen |
| `princeton-nlp/SWE-bench_Lite/Verified` | Real issues+fixes; Eval-Leakage vermeiden |

## Wichtige Caveats

- **Lizenz/Herkunft** pro Quelle dokumentieren; keine ungeprüfte Vermischung.
- **Leakage vermeiden**: Eval-Sets (z. B. SWE-bench Verified) nicht ins Training.
- **Qualitätsfilter**: Lockfiles/generated/binär/große Refactors/dubiose Patches raus; Dedupe über Repo+Commit+Hunk+Hash.
- **NVD/OSV sind nicht direkt Trainingspaare**: Commit-Auflösung, Diff-Parsing, Review nötig.
- **Sicherheit**: keine Secrets in Daten; keine schädlichen Exploit-Anleitungen als Trainingsziel.

## Nächste sinnvolle Schritte

Siehe `TODO.md`. Priorität: OSV-Commit-Auflösung zu echten buggy/fixed-Paaren ausbauen, Multi-SWE-bench Loader, Dedupe/Lizenzfilter, kleines LoRA/PEFT-SFT auf Basiscoding-Modell.
