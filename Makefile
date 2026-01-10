SERVICES := $(shell ls services)
TAG ?= latest

.PHONY: up down pull build rebuild ps logs

## Pull all images from registries
pull:
	@for svc in $(SERVICES); do \
		echo "Pulling $$svc"; \
		podman-compose -f services/$$svc/compose.yml pull || true; \
	done

## Build local images (only services with Dockerfile)
build:
	@for svc in $(SERVICES); do \
		if [ -f services/$$svc/Dockerfile ]; then \
			echo "Building $$svc"; \
			podman-compose -f services/$$svc/compose.yml build; \
		fi \
	done

## Force rebuild
rebuild:
	@for svc in $(SERVICES); do \
		if [ -f services/$$svc/Dockerfile ]; then \
			echo "Rebuilding $$svc"; \
			podman-compose -f services/$$svc/compose.yml build --no-cache; \
		fi \
	done

## Start everything
up:
	podman-compose -f core/traefik/docker-compose.yml up -d
	@for svc in $(SERVICES); do \
		podman-compose -f services/$$svc/compose.yml up -d; \
	done

## Stop everything
down:
	podman-compose down
	@for svc in $(SERVICES); do \
		podman-compose -f services/$$svc/compose.yml down; \
	done

## Status
ps:
	podman ps

## Logs
logs:
	podman logs -f traefik
