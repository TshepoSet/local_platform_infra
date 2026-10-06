"""Small orchestration layer shared by lp and the legacy Make commands."""
import shutil
import subprocess
import hashlib

import yaml

from . import certs, routes, runtime
from .config import find_root, validate_name


class Platform:
    def __init__(self, root=None):
        self.root = find_root(root)
        self.traefik = self.root / "core/traefik/docker-compose.yml"

    def services(self, name=None):
        if name:
            validate_name(name)
            path = self.root / "services" / name / "compose.yml"
            if not path.is_file():
                raise ValueError(f"Service '{name}' does not exist")
            return [path]
        return sorted(p for p in (self.root / "services").glob("*/compose.yml")
                      if not p.parent.name.startswith("."))

    def setup(self):
        runtime.require("podman", "podman-compose", "mkcert", "openssl")
        runtime.run("podman", "info", capture=True)
        runtime.ensure_network()
        runtime.run("mkcert", "-install")
        self.prepare_files()

    def prepare_files(self):
        changed = certs.ensure(self.root)
        routes.sync(self.root)
        if changed:
            # Traefik watches the dynamic directory, not certificate file contents.
            # A changed comment triggers its file provider to reload the certificate.
            digest = hashlib.sha256((self.root / "core/certs/cert.pem").read_bytes()).hexdigest()
            (self.root / "core/traefik/routes/lp-tls.yml").write_text(
                f"# Certificate: {digest}\ntls:\n  certificates:\n"
                "    - certFile: /certs/cert.pem\n      keyFile: /certs/key.pem\n"
            )

    def up(self, name=None, recreate=False):
        files = self.services(name)  # Validate before any platform mutations.
        self.setup()
        runtime.compose(self.traefik, "up", "-d")
        for path in files:
            args = ["up", "-d"] + (["--force-recreate"] if recreate else [])
            runtime.compose(path, *args)
        self.assert_running([self.traefik, *files])
        self.urls(name)

    def down(self, name=None):
        for path in reversed(self.services(name)):
            runtime.compose(path, "stop" if name else "down")
        if not name:
            runtime.compose(self.traefik, "down")

    def build(self, name=None, no_cache=False):
        built = []
        for path in self.services(name):
            config = yaml.safe_load(path.read_text())
            names = [key for key, value in config["services"].items() if "build" in value]
            if not names:
                if name:
                    raise ValueError(f"Service '{name}' uses a registry image; no build configured")
                continue
            runtime.compose(path, "build", *(["--no-cache"] if no_cache else []), *names)
            built.append(path.parent.name)
        return built

    def rebuild(self, name):
        self.build(name, no_cache=True)
        self.up(name, recreate=True)

    def restart(self, name):
        self.services(name)
        self.up(name, recreate=True)

    def logs(self, name, follow=True):
        path = self.services(name)[0]
        runtime.compose(path, "logs", *(["-f"] if follow else []))

    def remove(self, name):
        directory = self.services(name)[0].parent
        # Never traverse a symlink to a project outside the service registry.
        if directory.is_symlink():
            raise ValueError("Refusing to remove a symlinked service directory")
        runtime.compose(directory / "compose.yml", "down")
        # Registration is removed, but custom files and data in the directory remain.
        for filename in ("compose.yml", "route.yml"):
            (directory / filename).unlink(missing_ok=True)
        (self.root / "core/traefik/routes" / f"{name}.yml").unlink(missing_ok=True)
        readme = directory / "README.md"
        if readme.is_file() and readme.read_text().startswith(f"# {name}\n\n"):
            readme.unlink()
        if not any(directory.iterdir()):
            directory.rmdir()
        print(f"Removed service '{name}'. Application source and volumes were preserved.")

    def urls(self, name=None):
        for path in self.services(name):
            print(f"https://{path.parent.name}.localhost")
        print("https://traefik.localhost")

    @staticmethod
    def service_state(path, containers):
        config = yaml.safe_load(path.read_text())
        project = config.get("name", path.parent.name)
        states = []
        for name, service in config["services"].items():
            matches = []
            for container in containers:
                labels = container.get("Labels") or {}
                names = container.get("Names") or []
                if isinstance(names, str):
                    names = [names]
                explicit_name = service.get("container_name")
                if (explicit_name and explicit_name in names) or (
                    labels.get("io.podman.compose.project", labels.get("com.docker.compose.project")) == project
                    and labels.get("com.docker.compose.service") == name
                ):
                    matches.append(container.get("State", "unknown"))
            states.extend(matches or ["not created"])
        return "running" if states and all(s == "running" for s in states) else ", ".join(sorted(set(states)))

    def assert_running(self, files):
        # Older Compose versions sometimes return success after a failed podman run.
        containers = runtime.containers()
        failed = [p.parent.name for p in files if self.service_state(p, containers) != "running"]
        if failed:
            raise ValueError("Not running after startup: " + ", ".join(failed) + ". Check lp logs <service>.")

    def status(self):
        try:
            containers = runtime.containers()
        except (OSError, ValueError, subprocess.CalledProcessError) as exc:
            print(f"Podman unavailable: {exc}")
            containers = None
        print(f"{'SERVICE':<24} {'STATUS':<22} URL")
        for path in [self.traefik, *self.services()]:
            name = path.parent.name
            state = self.service_state(path, containers) if containers is not None else "unavailable"
            print(f"{name:<24} {state:<22} https://{name}.localhost")
        try:
            network = "ready" if runtime.network_exists() else "missing"
        except (OSError, ValueError):
            network = "unavailable"
        print(f"proxy network: {network}")
        if not shutil.which("openssl"):
            print("HTTPS certificate: unknown (openssl missing)")
        else:
            print("HTTPS certificate: " + ("ready" if certs.ready(self.root) else "missing, expired or needs update; run lp setup"))

    def pull(self):
        for path in self.services():
            config = yaml.safe_load(path.read_text())
            names = [key for key, value in config["services"].items() if "image" in value and "build" not in value]
            if names:
                runtime.compose(path, "pull", *names)

    def destroy(self):
        if input("This removes platform containers, volumes and certificates. Type 'destroy': ") != "destroy":
            raise ValueError("Cancelled")
        for path in [*reversed(self.services()), self.traefik]:
            runtime.compose(path, "down", "-v")
        for path in (self.root / "core/certs").glob("*.pem"):
            path.unlink()
