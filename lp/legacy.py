"""Compatibility adapter for Makefile targets and tools/service.py."""
import argparse
import subprocess
import sys
import yaml
from . import routes, runtime
from .platform import Platform


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("setup", "up", "down", "check", "build", "rebuild",
                                         "start", "stop", "restart", "logs", "remove", "status",
                                         "routes", "certs", "urls", "pull", "ps", "destroy"))
    parser.add_argument("--service", default="")
    args = parser.parse_args()
    if args.action in ("check", "start", "stop", "restart", "logs", "remove") and not args.service:
        parser.error(f"Usage: make {args.action} svc=<service>")
    try:
        platform = Platform()
        name = args.service or None
        if args.action == "check":
            platform.services(name)
        elif args.action in ("build", "rebuild"):
            platform.build(name, no_cache=args.action == "rebuild")
        elif args.action == "start":
            platform.up(name, recreate=True)
        elif args.action == "stop":
            platform.down(name)
        elif args.action == "routes":
            routes.sync(platform.root)
        elif args.action == "certs":
            platform.prepare_files()
        elif args.action == "ps":
            runtime.run("podman", "ps")
        elif args.action in ("up", "down", "urls", "restart", "logs", "remove"):
            getattr(platform, args.action)(name)
        else:
            getattr(platform, args.action)()
    except (ValueError, OSError, yaml.YAMLError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
