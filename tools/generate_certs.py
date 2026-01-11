#!/usr/bin/env python3

import subprocess
import sys
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SERVICES_DIR = BASE_DIR / "services"
CERTS_DIR = BASE_DIR / "core" / "certs"

CERT_FILE = CERTS_DIR / "cert.pem"
KEY_FILE = CERTS_DIR / "key.pem"


def die(msg):
    print(f"❌ {msg}")
    sys.exit(1)


def require(cmd):
    if subprocess.call(["which", cmd], stdout=subprocess.DEVNULL) != 0:
        die(f"Required command not found: {cmd}")


def extract_hosts():
    hosts = set()

    for route in SERVICES_DIR.glob("*/route.yml"):
        # Skip hidden/template directories (e.g. .template)
        if route.parent.name.startswith("."):
            continue

        content = route.read_text()

        # Skip unrendered templates safely
        if "{{" in content or "}}" in content:
            continue

        try:
            data = yaml.safe_load(content)
        except Exception as e:
            die(f"Failed to parse YAML in {route}: {e}")

        if not isinstance(data, dict):
            continue

        routers = data.get("http", {}).get("routers", {})
        if not isinstance(routers, dict):
            continue

        for router in routers.values():
            rule = router.get("rule", "")
            if "Host(" in rule:
                hostname = (
                    rule.split("Host(")[1]
                    .split(")")[0]
                    .strip("`'")
                )
                hosts.add(hostname)

    # Always include Traefik dashboard
    hosts.add("traefik.localhost")

    return sorted(hosts)


def generate_certs(hosts):
    if not hosts:
        die("No hostnames found")

    CERTS_DIR.mkdir(parents=True, exist_ok=True)

    print("🔐 Generating certificates for:")
    for h in hosts:
        print(f"  - {h}")

    cmd = ["mkcert"]

    # Reuse existing key if present
    if KEY_FILE.exists():
        cmd.extend(["-key-file", str(KEY_FILE)])
        cmd.extend(["-cert-file", str(CERT_FILE)])
    else:
        cmd.extend(["-cert-file", str(CERT_FILE)])
        cmd.extend(["-key-file", str(KEY_FILE)])

    cmd.extend(hosts)

    subprocess.run(cmd, check=True)

    print(f"\n✅ Certificates written to {CERTS_DIR}")


def main():
    require("mkcert")

    hosts = extract_hosts()
    generate_certs(hosts)


if __name__ == "__main__":
    main()
