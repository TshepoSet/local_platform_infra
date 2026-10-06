# Local Platform Infra

A local development platform using **Podman, podman-compose, Traefik and mkcert**.
Use the first-party Python CLI, **`lp`**, to manage applications with predictable
HTTPS addresses such as `https://employee-api.localhost`.

Application source code can live outside this repository. Register an external
Dockerfile build or a prebuilt registry image; the platform keeps only its
Compose and routing configuration in `services/`. Containers join the external
`proxy` network, and Traefik routes requests through its existing file provider.

## Quick start

Install Podman, podman-compose, mkcert, OpenSSL, and Python 3.10 or newer. Use the
same non-root user for all Podman commands. Traefik uses host ports 80 and 443;
those ports must be available and permitted by your host's rootless setup.

From the infrastructure checkout:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

lp setup
lp up
lp status
```

`lp setup` checks dependencies and Podman access, creates `proxy` if needed,
ensures the mkcert CA is trusted, and prepares certificates and routing files.
The first mkcert trust installation may ask for your operating system password.
Repeated setup is safe.

`lp up` performs setup automatically, starts Traefik and all registered services,
builds local images when missing, and prints URLs. Repeated startup reuses
unchanged containers. Certificates are renewed when hostnames change or expiry
is approaching, and Traefik reloads them through its file provider.

The editable installation also works from other directories. To select a
particular checkout explicitly, use `lp --root /path/to/local_platform_infra ...`
or set `LP_ROOT`. The CLI first looks for a checkout in the current directory or
its parents, then uses the editable installation's checkout. A non-editable
installation needs a checkout selected through `--root`, `LP_ROOT`, or the
current directory.

## Add applications

### External Dockerfile project

From the infrastructure checkout, register a sibling application:

```bash
lp add employee-api --path ../employee-management --port 8080
lp up employee-api
```

The source and Dockerfile remain in `../employee-management`. `--path` is the
build context, resolved relative to the directory where you invoke `lp` and
stored as an absolute path. The Dockerfile defaults to `Dockerfile` in that
context. Applications must listen on `0.0.0.0` at the specified internal HTTP port.
Local builds require `--port`; generation does not run or pull an image to guess it.

To choose a Dockerfile and an optional local image tag:

```bash
lp add worker --path "../worker app" --dockerfile docker/dev.Dockerfile \
  --image localhost/worker:dev --port 8000
lp up worker
```

`--dockerfile` is relative to the build context unless it is an absolute path.
Without `--image`, podman-compose assigns a local image name. Build image tags
are used verbatim. If you edit Compose directly, relative context paths are
relative to the Compose file, following the
[Compose build specification](https://docs.docker.com/reference/compose-file/build/).

### Registry image

```bash
lp add dashboard --image grafana/grafana:latest --port 3000
lp up dashboard
```

Use `lp add grafana --image grafana/grafana:latest` in a checkout where `grafana`
is not already registered. Existing registrations are never overwritten.
Short registry image names default to `docker.io`. Explicit registries,
including `localhost:5000`, are preserved. If `--port` is omitted, the existing
image inspection and known-port fallback are used. Multiple exposed ports are
ambiguous and require an explicit `--port`.

The service name determines the generated container name, `proxy` network alias,
route name, and `https://<service>.localhost` hostname. Use letters, digits and
hyphens; names are normalized to lowercase. `traefik`, `routes` and `lp-tls` are
reserved for platform routing. The existing Grafana, Prometheus and Redis
registrations retain their original Compose configuration and routes. The
included `redis` service runs RedisInsight, as before.

## Daily commands

```bash
lp up employee-api          # Start one service and all platform prerequisites
lp down employee-api        # Stop only that service; keep its container/volumes
lp logs employee-api        # Follow logs; Ctrl-C stops following
lp logs employee-api --no-follow
lp restart employee-api     # Recreate and start the service
lp rebuild employee-api     # Build without cache, then recreate/start it
lp remove employee-api      # Stop and unregister; preserve source and volumes

lp status                   # Services, URLs, Traefik, network and HTTPS readiness
lp down                     # Remove platform containers; keep persistent volumes
lp help
```

Startup creates missing local images. After source changes, `lp rebuild` applies
them in one command. It affects only the selected service and starts Traefik if
needed. Registry-only services cannot be rebuilt; use `make pull` and
`lp restart <service>` to apply a newer registry image.

`lp status` reports registered services even when they have never been started,
using Compose labels as well as explicit container names. It does not start
anything. A running container is not an application health check.

Removal cleans the service's Compose registration and generated route, including
its copied Traefik route. It preserves external application directories, named
volumes, and custom files/data inside the service directory. It does not delete
images or unrelated routes. Certificate SANs may retain a removed hostname until
the next renewal; the removed route no longer serves it.

## Makefile compatibility

The Makefile remains fully supported and calls the same Python orchestration.
Install with `python -m pip install -e .` as above; Make defaults to
`.venv/bin/python` and also accepts `PYTHON=/path/to/python`.

| Developer task | Preferred CLI | Make alternative |
| --- | --- | --- |
| Prepare platform | `lp setup` | `make setup` |
| Start everything | `lp up` | `make up` |
| Start one service | `lp up employee-api` | `make up svc=employee-api` |
| Recreate/start one | `lp restart employee-api` | `make start svc=employee-api` |
| Stop one service | `lp down employee-api` | `make stop svc=employee-api` |
| Stop everything | `lp down` | `make down` |
| Platform status | `lp status` | `make status` |
| Follow logs | `lp logs employee-api` | `make logs svc=employee-api` |
| Restart one | `lp restart employee-api` | `make restart svc=employee-api` |
| Unregister one | `lp remove employee-api` | `make remove svc=employee-api` |
| Help | `lp help` | `make help` |

Both `make up` and `make start` now handle network, certificates, routing and
Traefik prerequisites. `make down svc=employee-api` also stops just that service.

Register services using either spelling:

```bash
make add name=employee-api path=../employee-management port=8080
make new-service name=worker context="../worker app" \
  dockerfile=docker/dev.Dockerfile image=localhost/worker:dev port=8000
make add name=dashboard image=grafana/grafana:latest port=3000
```

All existing lower-level targets remain available:

```bash
make build svc=employee-api     # Cached build only
make rebuild svc=employee-api   # No-cache build only: preserved legacy behavior
make start svc=employee-api     # Apply that built image
make build                     # Build all Compose services declaring build
make rebuild                   # Rebuild all local images without cache
make pull                      # Pull registry-only images
make routes                    # Sync file-provider routes
make certs                     # Update certificates and TLS routing if needed
make urls                      # Print URLs
make ps                        # Original raw podman ps output
make destroy                   # Destructive removal including volumes; prompts first
```

Unlike legacy `make rebuild`, **`lp rebuild` automatically restarts afterward**.
The build-only Make targets remain useful for scripts. Normal startup does not
require manually sequencing build, certificate and route commands.

## Project structure

```text
lp/                    CLI and shared platform orchestration
  cli.py               Typer commands and installed lp entry point
  platform.py          Startup, services, status and lifecycle orchestration
  runtime.py           Podman / podman-compose subprocess boundary
  config.py            Checkout discovery and name conventions
  services.py          Registry-image and external-build registration
  certs.py, routes.py   mkcert and Traefik file-provider maintenance
  legacy.py            Makefile compatibility adapter
core/                  Existing Traefik, network and TLS configuration
services/<name>/       Compose registration and route (source lives anywhere)
templates/service/     Compose and route templates
tools/                 Backward-compatible script entry points
tests/                 CLI, Make, generation and orchestration regression tests
pyproject.toml         Python package dependencies and lp console script
Makefile               Supported alternative interface and lower-level commands
```

Flow: developer → `lp` or Make → shared orchestration → Podman + Traefik + `proxy`.
No Docker daemon, Kubernetes, or Traefik Docker provider is required.

## Validation

```bash
make test
```

Tests use isolated checkouts and runtime doubles, plus the installed
podman-compose parser in dry-run mode when available. They cover external paths,
registry images, command isolation, repeated setup/startup, removal, readiness
reporting, and both interfaces. They do not start containers or alter CA trust.

## License

[MIT](LICENSE.txt). Built by Tshepo Setshedi.
