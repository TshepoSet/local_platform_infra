"""The single subprocess boundary for Podman, Compose and certificate tooling."""
import json
import shutil
import subprocess


def run(*args, capture=False, check=True):
    return subprocess.run([str(arg) for arg in args], check=check, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None)


def require(*commands):
    missing = [cmd for cmd in commands if not shutil.which(cmd)]
    if missing:
        raise ValueError("Missing dependencies: " + ", ".join(missing))


def compose(path, *args):
    return run("podman-compose", "-f", path, *args)


def network_exists():
    result = run("podman", "network", "exists", "proxy", capture=True, check=False)
    if result.returncode not in (0, 1) or (result.returncode and result.stderr.strip()):
        raise ValueError(result.stderr.strip() or "Unable to check the proxy network")
    return result.returncode == 0


def ensure_network():
    if not network_exists():
        run("podman", "network", "create", "proxy")


def containers():
    return json.loads(run("podman", "ps", "--all", "--format", "json", capture=True).stdout)
