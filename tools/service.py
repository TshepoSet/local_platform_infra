#!/usr/bin/env python3
"""Compatibility entry point for existing service commands."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lp.legacy import main

if __name__ == "__main__":
    main()
