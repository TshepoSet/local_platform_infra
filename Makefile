up:
	podman-compose -f infra/core/traefik/docker-compose.yml up -d
	podman-compose -f infra/services/*/compose.yml up -d

down:
	podman-compose down

routes:
	cp infra/services/*/route.yml infra/core/traefik/routes/
