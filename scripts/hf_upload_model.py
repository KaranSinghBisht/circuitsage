"""Upload the CircuitSage LoRA adapter + model card to Hugging Face.

Usage:
    HF_TOKEN=hf_xxx python scripts/hf_upload_model.py

Requires:
    pip install huggingface_hub>=0.26

Creates `karansinghbisht/circuitsage-lora` (model repo) if missing, then
uploads `train/output/MODEL_CARD.md` (renamed to `README.md`) plus any
of the following present:
- `train/output/circuitsage-lora/` (PEFT adapter folder)
- `train/output/circuitsage-lora-q4_k_m.gguf` (quantized GGUF)
- `train/output/circuitsage.Modelfile` (Ollama Modelfile)
"""

from __future__ import annotations

import os
import sys
import shutil
import tempfile
from pathlib import Path

REPO_ID = "karansinghbisht/circuitsage-lora"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "train" / "output"

CARD = OUT / "MODEL_CARD.md"
GGUF = OUT / "circuitsage-lora-q4_k_m.gguf"
MODELFILE = OUT / "circuitsage.Modelfile"
ADAPTER_DIR = OUT / "circuitsage-lora"


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

    if not CARD.exists():
        print(f"error: missing {CARD}", file=sys.stderr)
        return 1

    login(token=token, add_to_git_credential=False)
    api = HfApi()
    api.create_repo(repo_id=REPO_ID, repo_type="model", exist_ok=True, private=False)

    with tempfile.TemporaryDirectory() as staging_dir:
        staging = Path(staging_dir)
        shutil.copy(CARD, staging / "README.md")
        if MODELFILE.exists():
            shutil.copy(MODELFILE, staging / "circuitsage.Modelfile")
        if GGUF.exists():
            shutil.copy(GGUF, staging / "circuitsage-lora-q4_k_m.gguf")
        else:
            print(f"warning: {GGUF.name} not present; uploading model card only.")
        if ADAPTER_DIR.exists() and ADAPTER_DIR.is_dir():
            target = staging / "adapter"
            shutil.copytree(ADAPTER_DIR, target)

        api.upload_folder(
            folder_path=str(staging),
            repo_id=REPO_ID,
            repo_type="model",
            commit_message="circuitsage: model card + adapter + gguf upload",
        )

    print(f"uploaded to https://huggingface.co/{REPO_ID}")
    print("next: ollama create circuitsage:latest -f train/output/circuitsage.Modelfile")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
