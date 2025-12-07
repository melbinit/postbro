Every time you change backend code:

docker-compose down && docker-compose build && docker-compose up -d

That's it. Migrations run automatically.

docker-compose restart backend &&
docker-compose restart celery-worker

To check if it worked:

docker-compose logs backend


docker-compose build --no-cache celery-worker && docker-compose up -d celery-worker