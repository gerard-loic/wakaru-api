SHELL := /bin/bash

up: ## Construire et démarrer les conteneurs (peut être long)
	@$(MAKE) init -s

bash: ## Lance un prompte bash dans le conteneur
	@docker compose -f docker/docker-compose.yml exec $(DOCKER_SERVICE_NAME) /bin/bash

init: ## Initilaisation du projet (a ne pas lancer seul)
	@$(MAKE) pull -s
	@docker compose -f docker/docker-compose.yml up -d;

pull: ## Récupère la dernière version de l'image
	@docker compose -f docker/docker-compose.yml pull

down: ## Arrête les conteneurs et supprime les conteneurs, les réseaux, les volumes et les images
	@docker compose -f docker/docker-compose.yml down

start: ## Lance les services
	@docker compose -f docker/docker-compose.yml start

stop: ## Arrêter les services
	@docker compose -f docker/docker-compose.yml stop

help: ## Affiche la liste des commandes disponibles
	@IFS=$$'\n' ; \
	help_lines=(`fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##/:/'`); \
	printf "%-30s %s\n" "target" "help" ; \
	printf "%-30s %s\n" "------" "----" ; \
	for help_line in $${help_lines[@]}; do \
	IFS=$$':' ; \
	help_split=($$help_line) ; \
	help_command=`echo $${help_split[0]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
	help_info=`echo $${help_split[2]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
	printf '\033[36m'; \
	printf "%-30s %s" $$help_command ; \
	printf '\033[0m'; \
	printf "%s\n" $$help_info; \
	done