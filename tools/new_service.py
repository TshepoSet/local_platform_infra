#!/usr/bin/env python3
"""Backward-compatible generator; implementation lives in lp.services."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lp.services import add_service
from lp.config import find_root


def main():
    parser = argparse.ArgumentParser(description="Create a new service")
    parser.add_argument("name")
    parser.add_argument("--image")
    parser.add_argument("--context", "--path", dest="context")
    parser.add_argument("--dockerfile")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    try:
        add_service(find_root(), **vars(args))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
