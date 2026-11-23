# TODO

## Ziel

Trainingsdaten für ein Coding-/Agentic-/Cybersecurity-Modell aufbauen: hochwertige Paare aus **Bug/Schwachstelle → Fix/Patch**, plus Metadaten (CWE, CVSS, Sprache, Tests, Quelle, Lizenz).

---

## 1) NVD (National Vulnerability Database) – Strategie

**Was NVD gut liefert**
- Kanonische CVE-Metadaten: Beschreibung, CVSS, CWE, CPE (betroffene Produkte/Versionen), Referenzen, Zeitstempel.
- Gut als **Anreicherungsquelle** (Label/Metadata), weniger als direkte Code-Fix-Quelle.

**Grenzen**
- NVD enthält meist **keine Diffs/Patches** direkt; Fixes hängen an Referenzen (Advisories, Commits, PRs).
- API ist rate-limited (`services.nvd.nist.gov/rest/json/cves/2.0`); ohne API-Key langsam, mit Key besser. Bulk/Data-Feeds prüfen.
- Bot-Schutz/403 bei einfachem Scraping möglich; offizielle API/Feeds verwenden.

**Extraktionsplan**
- [ ] **NVD-Downloader** bauen (`pipeline/extract_nvd.py`):
  - Quelle: NVD CVE API 2.0 oder JSON Data Feeds.
  - Felder: `cve.id`, `descriptions`, `metrics` (CVSS), `weaknesses` (CWE), `references`, `published`, `lastModified`, `configurations` (CPE).
  - Output: `nvd_cves.jsonl` (normalisiert).
- [ ] **Referenz-Klassifikation**: Referenzen nach Typ/Domain taggen (`commit`, `advisory`, `issue`, `patch`, `vendor`, `github/gitlab`).
- [ ] **Fix-Kandidaten extrahieren**: URLs mit `/commit/`, `/pull/`, `/merge_requests/`, `.patch`, GitHub Advisory Links.
- [ ] **Join mit OSV/GitHub Advisory** über CVE-ID, um Commit-Hashes zu bestätigen.
- [ ] **Lizenz/ToS prüfen** vor Massen-Download; nur öffentliche Quellen, Rate Limits respektieren.

**Wert für Training**
- `bug_detection`/`security_classification`: CVE-Beschreibung + CWE/CVSS als Labels.
- `vuln_explanation`: Beschreibung → Ursache/Impact/Remediation.
- Nicht allein für `bug_fixing` ausreichend ohne aufgelöste Code-Diffs.

---

## 2) OSV.dev – Strategie

**Was OSV gut liefert**
- Maschinenlesbares OSV-Format über viele Ökosysteme (PyPI, npm, Go, Maven, crates.io, Git, Debian, ...).
- Häufig `affected[].ranges[].events[].fixed`, `references` (FIX/ADVISORY/WEB), manchmal `database_specific`.
- Bulk-Downloads: `https://storage.googleapis.com/osv-vulnerabilities/<ECOSYSTEM>/all.zip`
- Inkrementell: `modified_id.csv` (top-level und per Ökosystem).

**Extraktionsplan**
- [ ] **OSV-Bulk-Importer** (`pipeline/extract_osv.py`):
  - Download/Cache `all.zip` pro Ökosystem.
  - Filter: Einträge mit Fix-Signal (`fixed` event, `references[type=FIX]`, Commit-URL).
  - Normalisiertes Output: `osv_records.jsonl`.
- [ ] **Commit-Auflösung** (`pipeline/resolve_commits.py`):
  - GitHub: `https://github.com/{owner}/{repo}/commit/{sha}.patch`
  - GitLab: `.../-/commit/{sha}.patch`
  - Output: `patches.jsonl` mit Diff, Repo, SHA, Quelle, Lizenz-Hinweis.
- [ ] **Diff → Pair-Konvertierung**: Patch in `buggy/fixed`-Snippets + Kontext (Datei, Funktion, Sprache) überführen; in `pairs.jsonl` Schema mappen.
- [ ] **Deduplizierung**: über `(repo, commit, file, hunk)` und Text-Hash.
- [ ] **Qualitätsfilter**: leere/triviale Diffs, generierte Dateien, Vendor/Lockfiles, Binärdateien, riesige Refactors ausschließen.
- [ ] **Inkrementelle Updates** über `modified_id.csv` statt Voll-Download.

**Priorisierte Ökosysteme (für Coding/Cyber)**
- `Git` (C/C++ und andere), `PyPI`, `npm`, `Go`, `Maven`, `crates.io`, `Packagist`, `RubyGems`, `NuGet`.
- Größe/Signal vor Download prüfen (`curl -sI .../all.zip`).

**Wert für Training**
- Sehr gut für `security_fixing`, `vuln_explanation`, `patch_generation`.
- Commit-Diffs liefern echte Before/After-Paare; OSV liefert Metadaten/Ökosystem/Referenzen.

---

## 3) HuggingFace / externe Datensätze (evaluieren)

| Dataset | HF ID / Link | Inhalt | Lizenz/Notes | Priorität |
|---|---:|---|---|---|
| BigVul | `bstee615/bigvul` | C/C++ vulnerable/fixed Funktionen | prüfen; populär, aber Qualitätsprobleme bekannt | Mittel |
| DiverseVul | `bstee615/diversevul` | Diverse C/C++ vuln/non-vuln | prüfen; besser kuratiert als BigVul | Mittel |
| PrimeVul | `colin/PrimeVul` | C/C++ paired vuln data | MIT (Repo-Card prüfen); gute Qualität | Hoch |
| CVEfixes | `DetectVul/CVEFixes` / andere Mirrors | CVE → Fix-Commits | Lizenz/Herkunft sorgfältig prüfen | Hoch |
| CVEfixes+BigVul | `MickyMike/cvefixes_bigvul` | Kombiniert | prüfen | Mittel |
| SWE-bench Verified | `princeton-nlp/SWE-bench_Verified` | Echte Issues+Fixes, eval-ready | prüfen; sehr wertvoll für Agentic Coding | Hoch |
| Multi-SWE-bench | GitHub/HF je nach Release | Multi-Lang SWE Issues | prüfen | Hoch |
| ReposVul / MegaVul / PatchDB | diverse | Security patches | Lizenz/Qualität stark variieren | Später |

**To evaluate**
- [ ] Schema inspizieren (Spalten, Code vor/nach, Commit, CWE, CVE, Sprache).
- [ ] Lizenz und Herkunft dokumentieren (pro Datensatz `docs/datasets.md`).
- [ ] Duplikate zwischen Datensätzen messen (exact hash + near-dedup).
- [ ] Leakage prüfen (Test-Sets nicht in Training mischen; SWE-bench eval sauber halten).
- [ ] Sample-Review: 50–100 Beispiele manuell prüfen.

---

## 4) Pipeline-Verbesserungen

- [ ] `pipeline/extract_osv.py` implementieren (all.zip lesen, Fix-Signale erkennen, normalisieren).
- [ ] `pipeline/extract_nvd.py` implementieren (API/Feed, Metadaten normalisieren).
- [ ] `pipeline/resolve_commits.py` implementieren (Patch download, Cache, Rate-Limit, Retry).
- [ ] `pipeline/build_pairs.py` erweitern: OSV/NVD/CVEfixes Inputs, Sprach-Erkennung, Dateifilter.
- [ ] `pipeline/export_finetune.py` erweitern: Tasks `security_fixing`, `root_cause`, `test_generation`, `patch_generation`.
- [ ] Einheitliches Schema + JSON Schema Datei (`schemas/pair.schema.json`, `schemas/finetune.schema.json`).
- [ ] Dedupe/Filter-Modul (`pipeline/filter.py`): Lizenz, Länge, Binär, Lockfiles, near-dup.
- [ ] Konfigurierbare Pfade/CLI (`--data-dir`, `--cache-dir`, `--out-dir`).
- [ ] Logging + Stats Report (`reports/stats.json`: Counts pro Quelle/Sprache/Task).
- [ ] Tests (`pytest`) für Parser, Diff-Extraktion, Normalisierung.

## 5) Training / Eval

- [ ] Basismodell auswählen (Coding/Agentic, offene Lizenz passend).
- [ ] SFT mit LoRA/PEFT auf kleinem Subset starten; danach skalieren.
- [ ] Eval: SWE-bench Verified/Lite, ggf. Multi-SWE-bench, Security-Patch-Quality-Checks.
- [ ] Datenmischung tracken (Quelle, Sprache, Task, Schwierigkeit).
- [ ] Sicherheits-/Qualitätsreview: keine Secrets, keine schädlichen Exploit-Anleitungen im Trainingsziel.

## 6) Repo-Hygiene

- [ ] `docs/datasets.md` mit Quellen, Lizenzen, Feldmapping.
- [ ] `docs/schema.md` für Pair/SFT-Format.
- [ ] `pyproject.toml` oder sauberes Packaging.
- [ ] CI (lint + tests).
- [ ] Beispiel-Sample `examples/sample_pairs.jsonl` (klein, synthetisch/ungefährlich).
