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
```

mkcert pgadmin.localhost redis.localhost db.localhost traefik.localhost
mv \*.pem core/certs/

cp -r templates/service services/myapp

make routes
make up
make pull # pull images from registries
make build # build local images (if Dockerfile exists)
make rebuild # rebuild without cache
make down # stop everything
make ps # list containers

---

# 📄 `core/certs/.gitkeep`

```text
# Certificates live here (ignored by git)


```
