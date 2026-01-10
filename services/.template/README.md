# Service Module Template

Each service must provide:

- compose.yml (container definition)
- route.yml (Traefik routing)
- .env (optional, not committed)

Services must NOT modify Traefik directly.
