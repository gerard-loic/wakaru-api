SHELL := /bin/bash
-include ./docker/.env
-include ./docker/vendor/basecmd.mk

TRAEFIK_LOCAL := docker compose -f docker/traefik/docker-compose.local.yml
TRAEFIK_PROD  := docker compose -f docker/traefik/docker-compose.yml

# Ajoute la creation du reseau Traefik comme prerequis du "up" de basecmd.mk
up: network

network: ## Cree le reseau Docker externe traefik-network s'il n'existe pas
	@docker network inspect traefik-network >/dev/null 2>&1 || docker network create traefik-network

cmd: ## Execute une commande scripts/ dans le conteneur : make cmd c="create_role --name Admin --uid ADMIN"
	@docker compose -f docker/docker-compose.yml exec --user $$(id -u):$$(id -g) sylo ./cmd.sh $(c)

traefik-up: network ## Demarre Traefik en local (HTTP, dashboard :8080)
	@$(TRAEFIK_LOCAL) up -d

traefik-down: ## Arrete Traefik (local)
	@$(TRAEFIK_LOCAL) down

traefik-logs: ## Suit les logs de Traefik (local)
	@$(TRAEFIK_LOCAL) logs -f

traefik-prod-up: network ## Demarre Traefik en prod (HTTPS + Let's Encrypt)
	@$(TRAEFIK_PROD) up -d

traefik-prod-down: ## Arrete Traefik (prod)
	@$(TRAEFIK_PROD) down
