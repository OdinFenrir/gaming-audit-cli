from __future__ import annotations

import sys
from pathlib import Path



def main() -> int:
    project_root = Path(__file__).resolve().parent
    src_path = project_root / 'src'
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    from gaming_audit.app import main as app_main

    return app_main(project_root, sys.argv[1:])


if __name__ == '__main__':
    raise SystemExit(main())
