#!/usr/bin/env python3

import argparse
import subprocess
import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
SERVICES_DIR = BASE_DIR / "services"
TEMPLATE_DIR = BASE_DIR / "templates" / "service"

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
    print(f"❌ {msg}")
    sys.exit(1)

def run(cmd):
    return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode()
    
def normalize_image(image):
    # If image already contains a registry, leave it alone
    if "/" in image and "." in image.split("/")[0]:
        return image

    # Otherwise assume docker.io
    return f"docker.io/{image}"

def detect_port(image):
    print("🔍 Detecting service port...")

    try:
        # Ensure image metadata is available
        subprocess.run(
            ["podman", "pull", "--quiet", image],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

        inspect_raw = run(["podman", "inspect", image])
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
        if len(ports) == 1:
            print(f"✅ Detected exposed port: {ports[0]}")
            return ports[0]

    image_name = image.split("/")[-1].split(":")[0]
    if image_name in KNOWN_PORTS:
        port = KNOWN_PORTS[image_name]
        print(f"⚠️  Using known default port: {port}")
        return port

    die(
        "Could not auto-detect port.\n"
        "Please specify explicitly:\n"
        "  make new-service name=... image=... port=..."
    )


def render(template, **vars):
    out = template
    for k, v in vars.items():
        out = out.replace(f"{{{{{k}}}}}", str(v))
    return out

def main():
    parser = argparse.ArgumentParser(description="Create a new service")
    parser.add_argument("name")
    parser.add_argument("--image", required=True)
    parser.add_argument("--port", help="Internal service port (optional)")
    args = parser.parse_args()

    name = args.name.lower()
    image = normalize_image(args.image)
    port = args.port or detect_port(image)

    service_dir = SERVICES_DIR / name
    if service_dir.exists():
        die(f"Service already exists: {name}")

    service_dir.mkdir(parents=True)

    compose_tpl = (TEMPLATE_DIR / "compose.yml").read_text()
    route_tpl = (TEMPLATE_DIR / "route.yml").read_text()

    (service_dir / "compose.yml").write_text(
        render(compose_tpl, SERVICE_NAME=name, IMAGE=image)
    )

    (service_dir / "route.yml").write_text(
        render(route_tpl, SERVICE_NAME=name, PORT=port)
    )

    (service_dir / "README.md").write_text(
        f"# {name}\n\nImage: `{image}`\nPort: `{port}`\n"
    )

    print(f"\n🎉 Service '{name}' created")
    print(f"🔗 Will be available at: https://{name}.localhost")
    print("\nNext:")
    print("  make up")

if __name__ == "__main__":
    main()
