"""Keep the existing shared mkcert certificate current without needless rewrites."""
import re
import yaml
from . import runtime


def hosts(root):
    result = {"traefik.localhost"}
    for path in (root / "services").glob("*/route.yml"):
        if path.parent.name.startswith("."):
            continue
        data = yaml.safe_load(path.read_text()) or {}
        for router in data.get("http", {}).get("routers", {}).values():
            for expression in re.findall(r"Host\(([^)]+)\)", router.get("rule", "")):
                result.update(re.findall(r"[`\"']([^`\"']+)[`\"']", expression))
    return sorted(result)


def ready(root):
    cert, key = root / "core/certs/cert.pem", root / "core/certs/key.pem"
    if not cert.is_file() or not key.is_file():
        return False
    public_cert = runtime.run("openssl", "x509", "-in", cert, "-pubkey", "-noout", capture=True, check=False)
    public_key = runtime.run("openssl", "pkey", "-in", key, "-pubout", capture=True, check=False)
    if (public_cert.returncode or public_key.returncode or not public_cert.stdout.strip()
            or public_cert.stdout.strip() != public_key.stdout.strip()):
        return False
    # Renew within 30 days and when a newly registered hostname is missing.
    checks = [["-checkend", "2592000"]] + [["-checkhost", host] for host in hosts(root)]
    return all(runtime.run("openssl", "x509", "-in", cert, "-noout", *args,
                           capture=True, check=False).returncode == 0 for args in checks)


def ensure(root):
    runtime.require("mkcert", "openssl")
    if ready(root):
        return False
    directory = root / "core/certs"
    directory.mkdir(parents=True, exist_ok=True)
    runtime.run("mkcert", "-cert-file", directory / "cert.pem",
                "-key-file", directory / "key.pem", *hosts(root))
    return True
