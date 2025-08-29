up:
	cd deploy && docker compose up --build

down:
	cd deploy && docker compose down

logs:
	cd deploy && docker compose logs -f --tail=200

ps:
	cd deploy && docker compose ps

rebuild:
	cd deploy && docker compose build --no-cache
