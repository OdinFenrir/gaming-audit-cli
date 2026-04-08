from __future__ import annotations

import sys
from pathlib import Path

from .app import main as app_main



def main() -> int:
    return app_main(Path.cwd(), sys.argv[1:])


if __name__ == '__main__':
    raise SystemExit(main())
