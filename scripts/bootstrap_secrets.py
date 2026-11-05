"""Write gitignored bootstrap secrets without printing them."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.local_secrets import ensure_local_secrets


def main() -> None:
    ensure_local_secrets(ROOT)
    print("Wrote artifacts/ADMIN_INITIAL_PASSWORD.txt and .dev.vars")
    print("Plaintext password is only in that artifacts file. Rotate it after first login.")


if __name__ == "__main__":
    main()
