#!/usr/bin/env python3

import subprocess
import json
from pathlib import Path
import yaml
from .config import validate_name
from . import runtime

# Known fallback ports for common images
KNOWN_PORTS = {
    "postgres": 5432,
    "mysql": 3306,
    "mariadb": 3306,
    "redis": 6379,
    "mongo": 27017,
    "grafana": 3000,
    "nginx": 80,
    "httpd": 80,
}

def die(msg):
    raise ValueError(msg)

def normalize_image(image):
    # If image already contains a registry, leave it alone
    if "/" in image and (
        "." in image.split("/")[0]
        or ":" in image.split("/")[0]
        or image.split("/")[0] == "localhost"
    ):
        return image

    # Otherwise assume docker.io
    return f"docker.io/{image}"

def detect_port(image):
    print("🔍 Detecting service port...")

    try:
        # Ensure image metadata is available
        runtime.run("podman", "pull", "--quiet", image, capture=True)
        inspect_raw = runtime.run("podman", "inspect", image, capture=True).stdout
        inspect = json.loads(inspect_raw)[0]

    except subprocess.CalledProcessError:
        die(
            f"Failed to inspect image '{image}'.\n"
            "Make sure the image name is correct.\n"
            "Example:\n"
            "  grafana/grafana:latest\n"
        )

    exposed = inspect.get("Config", {}).get("ExposedPorts", {})

    if exposed:
        ports = sorted(int(p.split('/')[0]) for p in exposed.keys())
        if len(ports) == 1 and next(iter(exposed)).endswith("/tcp"):
            print(f"✅ Detected exposed port: {ports[0]}")
            return ports[0]
        die("Ambiguous exposed ports; specify --port explicitly.")

    image_name = image.split("/")[-1].split(":")[0]
    if image_name in KNOWN_PORTS:
        port = KNOWN_PORTS[image_name]
        print(f"⚠️  Using known default port: {port}")
        return port

    die(
        "Could not auto-detect port.\n"
        "Please specify explicitly:\n"
        "  lp add <service> --image <image> --port <port>"
    )


def render(template, **vars):
    out = template
    for k, v in vars.items():
        out = out.replace(f"{{{{{k}}}}}", str(v))
    return out

def add_service(root, name, image=None, context=None, dockerfile=None, port=None):
    """Register a Compose service without touching its application source."""
    name = validate_name(name.lower())
    if not image and not context:
        raise ValueError("provide --image or --path (legacy: --context)")
    if dockerfile and not context:
        raise ValueError("--dockerfile requires --path / --context")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("--port must be between 1 and 65535")
    service_dir = root / "services" / name
    if service_dir.is_symlink():
        raise ValueError("Refusing to register into a symlinked service directory")
    if any((service_dir / file).exists() for file in ("compose.yml", "route.yml")):
        raise ValueError(f"Service already exists: {name}")

    source = {}
    if context:
        if port is None:
            die("--port is required for build-based services")
        context = Path(context).expanduser().resolve()
        if not context.is_dir():
            die(f"build context is not a directory: {context}")
        dockerfile_path = Path(dockerfile or "Dockerfile").expanduser()
        if not (context / dockerfile_path).is_file():
            die(f"Dockerfile does not exist: {context / dockerfile_path}")
        source["build"] = {"context": str(context)}
        if dockerfile:
            source["build"]["dockerfile"] = str(dockerfile_path)
        if image:
            source["image"] = image
    else:
        source["image"] = normalize_image(image)
        port = port or detect_port(source["image"])

    compose_tpl = ((root / "templates/service") / "compose.yml").read_text()
    route_tpl = ((root / "templates/service") / "route.yml").read_text()
    # YAML serialization keeps paths with spaces, colons and '#' safe.
    source_yaml = "\n".join(
        "    " + line for line in yaml.safe_dump(source, sort_keys=False).splitlines()
    )

    service_dir.mkdir(parents=True, exist_ok=True)
    (service_dir / "compose.yml").write_text(
        render(compose_tpl, SERVICE_NAME=name, SOURCE=source_yaml)
    )

    (service_dir / "route.yml").write_text(
        render(route_tpl, SERVICE_NAME=name, PORT=port)
    )

    if not (service_dir / "README.md").exists():
        (service_dir / "README.md").write_text(
            f"# {name}\n\n"
            + (f"Build context: `{context}`\n" if context else "")
            + (f"Image: `{source['image']}`\n" if "image" in source else "")
            + f"Port: `{port}`\n"
        )

    print(f"\n🎉 Service '{name}' created")
    print(f"🔗 Will be available at: https://{name}.localhost")
    return service_dir
