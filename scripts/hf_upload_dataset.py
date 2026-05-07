"""Upload the CircuitSage dataset + eval set + dataset card to Hugging Face.

Usage:
    HF_TOKEN=hf_xxx python scripts/hf_upload_dataset.py

Requires:
    pip install huggingface_hub>=0.26

The script creates `karansinghbisht/circuitsage-faults` (dataset repo) if it
does not exist, then uploads `train/dataset/circuitsage_qa.jsonl`,
`train/eval/eval_set.jsonl`, and `train/dataset/card.md` (renamed to
`README.md` per HF convention).
"""

from __future__ import annotations

import os
import sys
import tempfile
import shutil
from pathlib import Path

REPO_ID = "karansinghbisht/circuitsage-faults"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = {
    ROOT / "train" / "dataset" / "circuitsage_qa.jsonl": "circuitsage_qa.jsonl",
    ROOT / "train" / "eval" / "eval_set.jsonl": "eval_set.jsonl",
    ROOT / "train" / "dataset" / "card.md": "README.md",
}


def main() -> int:
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("error: HF_TOKEN env var is required.", file=sys.stderr)
        return 1

    try:
        from huggingface_hub import HfApi, login
    except ImportError:
        print("error: install huggingface_hub: pip install huggingface_hub>=0.26", file=sys.stderr)
        return 1

    missing = [str(src) for src in ASSETS if not src.exists()]
    if missing:
        print("error: missing assets:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 1

    login(token=token, add_to_git_credential=False)
    api = HfApi()
    api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True, private=False)

    with tempfile.TemporaryDirectory() as staging_dir:
        staging = Path(staging_dir)
        for src, dest_name in ASSETS.items():
            shutil.copy(src, staging / dest_name)
        api.upload_folder(
            folder_path=str(staging),
            repo_id=REPO_ID,
            repo_type="dataset",
            commit_message="circuitsage: dataset + eval + card upload",
        )

    print(f"uploaded to https://huggingface.co/datasets/{REPO_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
