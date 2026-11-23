# Datensätze & Quellen

## HuggingFace (erste Sichtung)

| Dataset | Inhalt | Format | Hinweise |
|---|---|---|---|
| `bstee615/bigvul` | C/C++ Vulnerabilities/Fixes | Parquet | Groß, bekannt; Qualität manuell prüfen |
| `bstee615/diversevul` | C/C++ vuln detection | Parquet | Kuratierter als BigVul |
| `colin/PrimeVul` | C/C++ paired vulnerability data | JSON/File contents | MIT laut Card; gute Kandidaten für SFT |
| `DetectVul/CVEFixes` | CVE → Fixes | siehe Repo | Herkunft/Lizenz pro Feld prüfen |
| `MickyMike/cvefixes_bigvul` | CVEfixes+BigVul | CSV | Kombination, Duplikate prüfen |
| `princeton-nlp/SWE-bench_Lite` | Real GitHub issues+fixes | Parquet | Eval/Agentic; bereits im Quickstart |
| `princeton-nlp/SWE-bench_Verified` | Kuratiertes SWE-bench | Parquet | Für Eval sauber halten (kein Leakage) |

Vor Training: Lizenz, Herkunft, Duplikate, Leakage und Sample-Qualität prüfen.

## OSV.dev

- Bulk: `https://storage.googleapis.com/osv-vulnerabilities/<ECOSYSTEM>/all.zip`
- Index: `https://storage.googleapis.com/osv-vulnerabilities/ecosystems.txt`
- Inkrementell: `modified_id.csv` (global und pro Ökosystem)
- Wertvoll für: CVE/Advisory-Metadaten, `fixed` Events in GIT-Ranges, FIX-Referenzen.
- Code-Fixes meist über verlinkte Commits (`.patch`) auflösbar.

Priorisierte Ökosysteme: `Git`, `PyPI`, `npm`, `Go`, `Maven`, `crates.io`, `Packagist`, `RubyGems`, `NuGet`.

## NVD

- API 2.0: `https://services.nvd.nist.gov/rest/json/cves/2.0`
- Wertvoll für: CWE, CVSS, CPE, Beschreibungen, Referenzen.
- Nicht primär für Diffs; als Metadaten-Enrichment und CVE-Join verwenden.
- Rate Limits beachten; offizielle Feeds/API bevorzugen.
