"""Maintain service files in Traefik's existing watched directory."""


def sync(root):
    destination = root / "core/traefik/routes"
    destination.mkdir(parents=True, exist_ok=True)
    for source in sorted((root / "services").glob("*/route.yml")):
        if source.parent.name.startswith("."):
            continue
        target = destination / f"{source.parent.name}.yml"
        content = source.read_bytes()
        if not target.exists() or target.read_bytes() != content:
            target.write_bytes(content)
