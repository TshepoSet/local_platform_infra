# Local Platform Infra

Reusable local infrastructure based on:

- Rootless Podman
- Traefik v3
- File provider routing
- Trusted HTTPS via mkcert

## Requirements

- Podman
- podman-compose
- mkcert

## Setup

```bash
mkcert -install

mkcert pgadmin.localhost redis.localhost db.localhost traefik.localhost
mv \*.pem core/certs/

cp -r templates/service services/myapp
```

## Common Commands

| Command        | Description                                              |
| -------------- | -------------------------------------------------------- |
| `make pull`    | Pull all service images from their configured registries |
| `make build`   | Build local images (only for services with a Dockerfile) |
| `make rebuild` | Rebuild local images without using cache                 |
| `make routes`  | Sync all service route definitions into Traefik          |
| `make up`      | Start Traefik and all services                           |
| `make down`    | Stop all running containers                              |
| `make ps`      | List running containers                                  |

---

# 📄 `core/certs/.gitkeep`

```text
# Certificates live here (ignored by git)


```
