PYTHON := .venv/bin/python
PLATFORM = $(PYTHON) -m lp.legacy

.DEFAULT_GOAL := help

.PHONY: help setup up down start stop restart logs remove status pull build rebuild ps routes certs new-service add urls destroy test

help: ## Show available Make commands (lp help for the recommended CLI)
	@echo "Local Platform Infrastructure — Make compatibility interface"
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

setup: ## Check dependencies, ensure proxy network and prepare trusted HTTPS
	$(PLATFORM) setup

up: ## Start everything, or one service (svc=), including prerequisites
	$(PLATFORM) up --service "$(svc)"

down: ## Stop everything, or one service (svc=); retain volumes
	$(PLATFORM) down --service "$(svc)"

start: ## Recreate/start one service with all prerequisites (svc=)
	$(PLATFORM) start --service "$(svc)"

stop: ## Stop a specific service (svc=)
	$(PLATFORM) stop --service "$(svc)"

restart: ## Recreate/restart a specific service (svc=)
	$(PLATFORM) restart --service "$(svc)"

logs: ## Follow a service's logs (svc=)
	$(PLATFORM) logs --service "$(svc)"

remove: ## Unregister a service; preserve application source and volumes (svc=)
	$(PLATFORM) remove --service "$(svc)"

status: ## Show platform services, URLs, network and HTTPS readiness
	$(PLATFORM) status

pull: ## Pull registry-only service images
	$(PLATFORM) pull

build: ## Build one service (svc=), or all build-based services
	$(PLATFORM) build --service "$(svc)"

rebuild: ## Build without cache (svc= optional); legacy build-only behavior
	$(PLATFORM) rebuild --service "$(svc)"

ps: ## Show raw Podman container status (legacy)
	$(PLATFORM) ps

routes: ## Sync service file routes into Traefik
	$(PLATFORM) routes

certs: ## Generate/update mkcert certificates and refresh Traefik TLS files
	$(PLATFORM) certs

new-service: ## Generate service (name= image= OR context= port= [dockerfile=] [image=])
	$(PYTHON) tools/new_service.py "$(name)" $(if $(image),--image "$(image)") $(if $(context),--context "$(context)",$(if $(path),--context "$(path)")) $(if $(dockerfile),--dockerfile "$(dockerfile)") $(if $(port),--port "$(port)")

add: new-service ## Register a service (name=, path=/context= or image=, optional port=)

urls: ## Show registered service URLs
	$(PLATFORM) urls --service "$(svc)"

destroy: ## Destroy all containers, volumes and certificates (requires confirmation)
	$(PLATFORM) destroy

test: ## Run CLI, orchestration and Make regression tests
	$(PYTHON) -m unittest discover -s tests -v
