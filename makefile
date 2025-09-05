# =========================
# Makefile for Phelia stack
# =========================
# Quick control for Docker Compose stack, Alembic migrations, and utilities.
# Usage examples:
#   make up            # bring up the stack
#   make logs          # follow logs
#   make migrate       # alembic upgrade head
#   make revision m="init schema"
#   make help          # list targets

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Path to compose file
COMPOSE_DIR := deploy
COMPOSE := cd $(COMPOSE_DIR) && docker compose

# -----------------
# Core commands
# -----------------

## Bring up all services (with build)
up:
	$(COMPOSE) up -d --build

## Rebuild images without cache and bring up
rebuild:
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d

## Stop and remove containers (keep volumes)
down:
	$(COMPOSE) down

## Stop and remove containers + volumes
down-v:
	$(COMPOSE) down -v

## Restart entire stack
restart: down up

## Show current containers status
ps:
	$(COMPOSE) ps

## Follow logs for all services
logs:
	$(COMPOSE) logs -f

## Follow API logs
api-logs:
	$(COMPOSE) logs -f api

## Follow Web (nginx) logs
web-logs:
	$(COMPOSE) logs -f web

## Follow Celery worker logs
worker-logs:
	$(COMPOSE) logs -f worker

## Follow Celery beat logs
beat-logs:
	$(COMPOSE) logs -f beat

## Follow qBittorrent logs
qb-logs:
	$(COMPOSE) logs -f qbittorrent

## Follow Postgres logs
db-logs:
	$(COMPOSE) logs -f db

## Follow Redis logs
redis-logs:
	$(COMPOSE) logs -f redis

# -------------
# DB migrations
# -------------

revision:
	@if [ -z "$(m)" ]; then echo 'ERROR: provide message via m="..."'; exit 1; fi
	cd deploy && docker compose run --rm --no-deps \
		-e PYTHONPATH=/app \
		--entrypoint bash api -lc 'alembic revision --autogenerate -m "$(m)"'

migrate:
	cd deploy && docker compose run --rm --no-deps \
		-e PYTHONPATH=/app \
		--entrypoint bash api -lc 'alembic upgrade head'


# ---------------
# Shell helpers
# ---------------

## Enter shell in api container
api-sh:
	$(COMPOSE) exec api bash

## Enter shell in worker container
worker-sh:
	$(COMPOSE) exec worker bash

## Enter shell in web container (nginx)
web-sh:
	$(COMPOSE) exec web sh

## Open psql to Postgres (uses env inside container)
psql:
	$(COMPOSE) exec db bash -lc 'psql -U "$${POSTGRES_USER:-phelia}" -d "$${POSTGRES_DB:-phelia}"'

## Open redis-cli
redis-cli:
	$(COMPOSE) exec redis redis-cli

# ---------------
# Utilities
# ---------------

## Create admin user (defaults: email=admin@example.com, pass=admin)
seed-admin:
	cd deploy && docker compose exec api python -c "from app.db.session import SessionLocal; from app.db.models import User; from passlib.context import CryptContext; db=SessionLocal(); pwd=CryptContext(schemes=['bcrypt'], deprecated='auto'); email='admin@example.com'; password='admin'; u=db.query(User).filter(User.email==email).one_or_none(); \
if u: print('User already exists:', u.email); \
else: user=User(email=email, hashed_password=pwd.hash(password), role='admin'); db.add(user); db.commit(); print('Created admin:', user.id, user.email)"


## Check API /health
health:
	curl -fsS http://localhost:$${API_PORT:-8000}/api/v1/health >/dev/null && echo "OK" || (echo "FAILED"; exit 1)

## List available targets
help:
	@printf "\nTargets:\n\n"
	@grep -E '^[a-zA-Z0-9_.-]+:|^## ' $(MAKEFILE_LIST) | \
	awk 'BEGIN{FS=":|## "}{if($$0 ~ /:$$/){t=$$1}else if($$0 ~ /^## /){printf "  \033[36m%-16s\033[0m %s\n", t, $$2}}'

.PHONY: up rebuild down down-v restart ps logs api-logs web-logs worker-logs beat-logs qb-logs db-logs redis-logs \
        migrate revision api-sh worker-sh web-sh psql redis-cli seed-admin health help

