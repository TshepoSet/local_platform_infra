# Traefik Dynamic Routes

This directory is watched by Traefik.

Each service provides its own `route.yml` which is copied here
using:

```bash
make routes
```

---

# 📄 `services/.template/README.md`

```md
# Service Module Template

Each service must provide:

- compose.yml → container definition
- route.yml → Traefik routing
- .env → optional (not committed)

Rules:

- No Traefik labels
- No TLS logic
- No Docker socket usage
```
