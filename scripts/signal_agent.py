#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import sys


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from sdsa.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
