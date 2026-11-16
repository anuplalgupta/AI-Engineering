"""Print the API description, or check the committed copy against the code.

    python -m ailms.tools.openapi            prints openapi.json to standard output
    python -m ailms.tools.openapi --check    fails if backend/openapi.json is out of date
"""

import json
import sys
from pathlib import Path

COMMITTED = Path(__file__).resolve().parents[3] / "openapi.json"


def generate() -> dict:
    from ailms.main import create_app

    return create_app().openapi()


def render(document: dict) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def is_current() -> bool:
    if not COMMITTED.exists():
        return False
    # Compare as data, so line endings changed by git on Windows do not matter.
    return json.loads(COMMITTED.read_text(encoding="utf-8")) == json.loads(render(generate()))


def main() -> int:
    if "--check" in sys.argv[1:]:
        if is_current():
            print("openapi.json is up to date")
            return 0
        print(
            "openapi.json does not match the code. Regenerate it; see backend/README.md.",
            file=sys.stderr,
        )
        return 1
    sys.stdout.write(render(generate()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
