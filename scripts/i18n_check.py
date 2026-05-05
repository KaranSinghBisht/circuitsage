from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
I18N_DIR = ROOT / "frontend" / "src" / "i18n"
KEY_RE = re.compile(r"^\s{2}([A-Za-z][A-Za-z0-9_]*):", re.MULTILINE)


def keys_for(path: Path) -> set[str]:
    return set(KEY_RE.findall(path.read_text()))


def main() -> int:
    files = sorted(I18N_DIR.glob("*.ts"))
    if not files:
        print("No locale files found", file=sys.stderr)
        return 1
    keysets = {path.name: keys_for(path) for path in files}
    reference_name, reference = next(iter(keysets.items()))
    failed = False
    for name, keys in keysets.items():
        missing = sorted(reference - keys)
        extra = sorted(keys - reference)
        if missing or extra:
            failed = True
            print(f"{name} differs from {reference_name}", file=sys.stderr)
            if missing:
                print(f"  missing: {', '.join(missing)}", file=sys.stderr)
            if extra:
                print(f"  extra: {', '.join(extra)}", file=sys.stderr)
    if failed:
        return 1
    print(f"i18n ok: {len(reference)} keys across {len(files)} locales")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
