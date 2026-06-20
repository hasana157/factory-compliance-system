#!/usr/bin/env bash
# scripts/download_kaggle.sh
#
# Downloads the factory safety behavior video dataset from Kaggle.
# Dataset: trnhhngqiang/video-dataset-for-safe-and-unsafe-behaviours
#
# Prerequisites:
#   1. Install Kaggle CLI:  pip install kaggle
#   2. Set up API credentials:
#      - Go to https://www.kaggle.com/settings -> Account -> API -> Create New Token
#      - Place the downloaded kaggle.json at ~/.kaggle/kaggle.json (Linux/Mac)
#        or %USERPROFILE%\.kaggle\kaggle.json (Windows)
#      - Set permissions: chmod 600 ~/.kaggle/kaggle.json
#
# Usage:
#   bash scripts/download_kaggle.sh
#   bash scripts/download_kaggle.sh --dest /path/to/custom/dir

set -euo pipefail

DATASET="trnhhngqiang/video-dataset-for-safe-and-unsafe-behaviours"
DEFAULT_DEST="data/kaggle_dataset"

# Parse optional --dest argument
DEST="${DEFAULT_DEST}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest) DEST="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

echo "=============================================="
echo "  FactoryGuard — Kaggle Dataset Downloader"
echo "=============================================="
echo "  Dataset : ${DATASET}"
echo "  Dest    : ${DEST}"
echo "=============================================="

# Check kaggle CLI is available
if ! command -v kaggle &> /dev/null; then
  echo ""
  echo "ERROR: 'kaggle' CLI not found."
  echo "Install it with:  pip install kaggle"
  exit 1
fi

# Check credentials
CREDS_LINUX="${HOME}/.kaggle/kaggle.json"
CREDS_WIN="${USERPROFILE}/.kaggle/kaggle.json"
if [[ ! -f "${CREDS_LINUX}" ]] && [[ ! -f "${CREDS_WIN:-/nonexistent}" ]]; then
  echo ""
  echo "ERROR: Kaggle credentials not found."
  echo "Go to https://www.kaggle.com/settings -> API -> Create New Token"
  echo "Place kaggle.json at ~/.kaggle/kaggle.json"
  exit 1
fi

mkdir -p "${DEST}"

echo ""
echo "Downloading dataset (this may take several minutes)..."
kaggle datasets download \
  --dataset "${DATASET}" \
  --path "${DEST}" \
  --unzip \
  --force

echo ""
echo "✅ Dataset downloaded to: ${DEST}"
echo ""
echo "Directory structure:"
ls -la "${DEST}" 2>/dev/null || dir "${DEST}" 2>/dev/null || true

echo ""
echo "Next step:"
echo "  python scripts/batch_inference.py --dataset ${DEST}"
