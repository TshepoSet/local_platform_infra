PYTHON := .venv/bin/python

SERVICES := $(shell ls services | grep -v "^\.template$$")
TAG ?= latest

.DEFAULT_GOAL := help

.PHONY: help up down pull build rebuild ps routes certs new-service

## Show available commands
help:
	@echo ""
	@echo "Local Platform Infrastructure"
	@echo "----------------------------"
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

## Generate TLS certificates automatically
certs: ## Generate mkcert TLS certificates from service routes
	$(PYTHON) tools/generate_certs.py

## Sync service routes into Traefik
routes: ## Sync all service route definitions into Traefik
	cp services/*/route.yml core/traefik/routes/

## Start Traefik and all services
up: certs routes ## Generate certs, sync routes, and start everything
	podman-compose -f core/traefik/docker-compose.yml up -d
	@for svc in $(SERVICES); do \
		podman-compose -f services/$$svc/compose.yml up -d; \
	done
	@$(MAKE) urls

## Stop all services
down: ## Stop all running containers
	podman-compose -f core/traefik/docker-compose.yml down
	@for svc in $(SERVICES); do \
		podman-compose -f services/$$svc/compose.yml down; \
	done

## Pull images from registries
pull: ## Pull all service images from their registries
	@for svc in $(SERVICES); do \
		podman-compose -f services/$$svc/compose.yml pull || true; \
	done

## Build local images
build: ## Build local images (services with Dockerfile only)
	@for svc in $(SERVICES); do \
		if [ -f services/$$svc/Dockerfile ]; then \
			podman-compose -f services/$$svc/compose.yml build; \
		fi \
	done

## Rebuild local images without cache
rebuild: ## Rebuild local images without cache
	@for svc in $(SERVICES); do \
		if [ -f services/$$svc/Dockerfile ]; then \
			podman-compose -f services/$$svc/compose.yml build --no-cache; \
		fi \
	done

## List running containers
ps: ## Show running containers
	podman ps

## Create a new service from template
new-service: ## Generate a new service (name= image= [port=])
	$(PYTHON) tools/new_service.py $(name) --image $(image) $(if $(port),--port $(port))

## Print service URLs
urls: ## Show service access URLs
	@echo ""
	@echo "Service URLs"
	@echo "------------"
	@for svc in $(SERVICES); do \
		echo "  https://$$svc.localhost"; \
	done
	@echo "  https://traefik.localhost"
	@echo ""

## Destroy all containers, volumes, and generated artifacts (DANGEROUS)
destroy:
	@echo "🔥 WARNING: This will REMOVE all containers, volumes, and certs."
	@read -p "Type 'destroy' to continue: " CONFIRM && [ "$$CONFIRM" = "destroy" ]

	@echo "🛑 Stopping services..."
	-@podman-compose -f core/traefik/docker-compose.yml down -v

	@for svc in $(SERVICES); do \
		echo "🛑 Stopping $$svc"; \
		-@podman-compose -f services/$$svc/compose.yml down -v; \
	done

	@echo "🗑 Removing generated TLS certs..."
	-@rm -f core/certs/*.pem

	@echo "✅ Infrastructure destroyed"
