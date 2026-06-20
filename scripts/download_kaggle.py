"""Script to download the Kaggle EHS dataset.

Uses the kaggle API to fetch 'trnhhngqiang/video-dataset-for-safe-and-unsafe-behaviours'.
Requires kaggle credentials configured in ~/.kaggle/kaggle.json.
"""

import os
from pathlib import Path

# Add parent directory to path
import sys
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.config import settings

def download_dataset():
    dataset_name = "trnhhngqiang/video-dataset-for-safe-and-unsafe-behaviours"
    dest_dir = Path("data/kaggle")
    
    print("Checking Kaggle API credentials...")
    kaggle_config = Path.home() / ".kaggle" / "kaggle.json"
    
    if not kaggle_config.exists() and "KAGGLE_USERNAME" not in os.environ:
        print("\n[WARNING] Kaggle credentials not found!")
        print("Please place your 'kaggle.json' in '~/.kaggle/' or set KAGGLE_USERNAME and KAGGLE_KEY env variables.")
        print("You can obtain API credentials from your Kaggle account settings page.")
        print("\nSkipping automated download. If you have the dataset locally, please extract it to 'data/kaggle/'.")
        return False

    try:
        import kaggle
        print(f"Downloading dataset '{dataset_name}' to '{dest_dir}'...")
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        kaggle.api.authenticate()
        kaggle.api.dataset_download_files(dataset_name, path=str(dest_dir), unzip=True)
        print("Download completed successfully!")
        return True
    except Exception as exc:
        print(f"Error downloading dataset: {exc}")
        return False

if __name__ == "__main__":
    download_dataset()
