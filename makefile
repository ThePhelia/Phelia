SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE_DIR := deploy
COMPOSE := cd $(COMPOSE_DIR) && docker compose

up:
	$(COMPOSE) up -d --build

rebuild:
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

down-v:
	$(COMPOSE) down -v

restart: down up

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f

api-logs:
	$(COMPOSE) logs -f api

web-logs:
	$(COMPOSE) logs -f web

worker-logs:
	$(COMPOSE) logs -f worker

beat-logs:
	$(COMPOSE) logs -f beat

db-logs:
	$(COMPOSE) logs -f db

redis-logs:
	$(COMPOSE) logs -f redis

revision:
	@if [ -z "$(m)" ]; then echo 'ERROR: provide message via m="..."'; exit 1; fi
	$(COMPOSE) run --rm --no-deps -e PYTHONPATH=/app --entrypoint bash api -lc 'alembic revision --autogenerate -m "$(m)"'

migrate:
	$(COMPOSE) run --rm --no-deps -e PYTHONPATH=/app --entrypoint bash api -lc 'alembic upgrade head'

api-sh:
	$(COMPOSE) exec api bash

worker-sh:
	$(COMPOSE) exec worker bash

web-sh:
	$(COMPOSE) exec web sh

psql:
	$(COMPOSE) exec db bash -lc 'psql -U "$${POSTGRES_USER:-phelia}" -d "$${POSTGRES_DB:-phelia}"'

redis-cli:
	$(COMPOSE) exec redis redis-cli

health:
	curl -fsS http://localhost:$${API_PORT:-8000}/api/v1/health >/dev/null && echo "OK" || (echo "FAILED"; exit 1)

api-restart:
	$(COMPOSE) restart api

help:
	@printf "\nTargets:\n\n"
	@grep -E '^[a-zA-Z0-9_.-]+:|^## ' $(MAKEFILE_LIST) | \
	awk 'BEGIN{FS=":|## "}{if($$0 ~ /:$$/){t=$$1}else if($$0 ~ /^## /){printf "  \033[36m%-18s\033[0m %s\n", t, $$2}}'

.PHONY: up rebuild down down-v restart ps logs api-logs web-logs worker-logs beat-logs db-logs redis-logs \
        revision migrate api-sh worker-sh web-sh psql redis-cli health api-restart help

