"""Locate the infrastructure checkout without tying apps to its directory."""
import os
from pathlib import Path
import re


def validate_name(name):
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", name):
        raise ValueError("Service names must be 1-63 lowercase letters, digits or hyphens")
    if name in ("traefik", "routes", "lp-tls"):
        raise ValueError(f"'{name}' is reserved for platform routing")
    return name


def find_root(root=None):
    explicit = root or os.environ.get("LP_ROOT")
    candidates = [Path(explicit).expanduser()] if explicit else [
        Path.cwd(), *Path.cwd().parents, Path(__file__).resolve().parents[1]
    ]
    for candidate in candidates:
        if (candidate / "core/traefik/docker-compose.yml").is_file():
            return candidate.resolve()
    raise ValueError("Infrastructure checkout not found. Use lp --root PATH or set LP_ROOT.")
