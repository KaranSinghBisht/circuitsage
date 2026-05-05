from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="source", required=True)
    parser.add_argument("--out", dest="output", required=True)
    parser.add_argument("--variants", type=int, default=5)
    args = parser.parse_args()

    # Placeholder for local Ollama paraphrasing. Until a local model is available,
    # preserve labels exactly by copying the seed file.
    shutil.copyfile(Path(args.source), Path(args.output))
    print(json.dumps({"copied": args.source, "out": args.output, "variants_requested": args.variants}))


if __name__ == "__main__":
    main()
