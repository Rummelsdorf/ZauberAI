#!/bin/bash
# Download all datasets for ZauberAI

set -e

cd "$(dirname "$0")"/..

# Create data directory
mkdir -p data

echo "=== Downloading SWE-bench Lite ==="
python scripts/download_datasets.py --source swebench_lite

echo ""
echo "=== Downloading Cyber-Security Dataset ==="
python scripts/download_datasets.py --source cyber

echo ""
echo "=== Downloading WizardLM ==="
python scripts/download_datasets.py --source wizardlm

echo ""
echo "=== Downloading Wikipedia ==="
python scripts/download_datasets.py --source wikipedia

echo ""
echo "=== Download Summary ==="
du -sh data/*
echo ""
ls -lh data/
