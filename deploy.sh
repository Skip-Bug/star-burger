#!/bin/bash
set -euo pipefail

cd /opt/star-burger

echo "=== 1. Обновляем код ==="
git pull gitverse master

echo "=== 2. Собираем frontend ==="
docker build -f Dockerfile.frontend -t star-burger-frontend .

echo "=== 3. Собираем web (collectstatic внутри) ==="
docker build -t star-burger-web .

echo "=== 4. Bundles → ./staticfiles/ ==="
docker run --rm -v "$(pwd)/staticfiles:/out" star-burger-frontend \
    sh -c "cp -r /app/bundles/. /out/"

echo "=== 5. Django-статика → ./staticfiles/ ==="
docker run --rm -v "$(pwd)/staticfiles:/out" star-burger-web \
    sh -c "cp -r /app/staticfiles/. /out/"

echo "=== 6. Применяем миграции ==="
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    run --rm web python manage.py migrate --noinput

echo "=== 7. Запускаем контейнеры ==="
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

echo "=== 8. Сообщаем Rollbar ==="
COMMIT_HASH=$(git rev-parse HEAD)
ACCESS_TOKEN=$(grep -E '^ROLLBAR_ACCESS_TOKEN=' .env | cut -d= -f2- | tr -d "'\"")
ROLLBAR_ENV=$(grep -E '^ROLLBAR_ENVIRONMENT=' .env | cut -d= -f2- | tr -d "'\"")
AUTHOR=$(git log -1 --pretty=format:'%an')
COMMENT=$(git log -1 --pretty=format:'%s')

curl -sS -X POST https://api.rollbar.com/api/1/deploy/ \
  -H "Content-Type: application/json" \
  -d "{
    \"access_token\": \"$ACCESS_TOKEN\",
    \"environment\": \"$ROLLBAR_ENV\",
    \"revision\": \"$COMMIT_HASH\",
    \"local_username\": \"$AUTHOR\",
    \"comment\": \"$COMMENT\"
  }" || true

echo ""
echo "✅ Готово!"