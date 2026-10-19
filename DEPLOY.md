# Деплой Star Burger (Docker Compose)

## Требования

- Ubuntu 22.04+
- Docker + Docker Compose (v2)
- Git
- Сервер с публичным IP (для HTTPS и Nginx)

## Подготовка сервера

### 1. Docker

```bash
apt update
apt install -y docker.io docker-compose-plugin
usermod -aG docker $USER
```

Перелогиньтесь, чтобы изменения группы вступили в силу.

Проверьте:

```bash
docker compose version
```

### 2. Nginx (хостовый, не в контейнере)

Nginx на сервере **не докеризирован** — он общий на все сайты и нужен для HTTPS.

```bash
apt install -y nginx
systemctl enable nginx
```

### 3. Клонирование репозитория

```bash
cd /opt
git clone git@github.com:Skip-Bug/star-burger.git
cd star-burger
```

> Ветка `master` — для разработки. Сервер работает из ветки `deploy`,
> но при первом клонировании вы получите `master` — это нормально,
> `deploy.sh` сам переключится на `deploy`.

### 4. Файл `.env`

Скопируйте шаблон из репозитория:

```bash
cp .env.example .env
```

Заполните значения под продакшен — `/opt/star-burger/.env` должен выглядеть так:

```env
SECRET_KEY=django-insecure-0if40nf4nf93n4
YANDEX_API_KEY=ключ_из_https://developer.tech.yandex.ru/
DATABASE_URL=postgres://star_burger_user:пароль@db:5432/star_burger
DEBUG=False
ALLOWED_HOSTS=ip_вашего_сервера
CSRF_TRUSTED_ORIGINS=https://ваш_домен
POSTGRES_DB=star_burger
POSTGRES_USER=star_burger_user
POSTGRES_PASSWORD=пароль
ROLLBAR_ACCESS_TOKEN=токен_из_rollbar.com
ROLLBAR_ENVIRONMENT=production
```

**Важно:**

- `DATABASE_URL` указывает на сервис `db` внутри Docker Compose (`host:port` = `db:5432`).
- `POSTGRES_*` — переменные, которые Docker Compose передаёт контейнеру PostgreSQL. Они должны совпадать с `DATABASE_URL`.
- `ALLOWED_HOSTS` — IP-адрес вашего сервера (или домен).
- `CSRF_TRUSTED_ORIGINS` обязателен для HTTPS. Указывайте полный origin с протоколом: `https://skip-project.githubpage.com`.

## Первый запуск

### 1. Применить миграции

```bash
docker compose -f docker-compose.prod.yml \
    run --rm web python manage.py migrate --noinput

docker compose -f docker-compose.prod.yml \
    run --rm web python manage.py createsuperuser
```

### 2. Запустить контейнеры

```bash
docker compose -f docker-compose.prod.yml up -d
```

Проверьте:

```bash
docker compose -f docker-compose.prod.yml ps
```

Должно быть:

| Сервис | Статус |
| ------ | ------ |
| db     | Up     |
| web    | Up     |

> `frontend` в prod не запускается — он нужен только в dev для `parcel watch`.
> На сервере фронтенд собирается `deploy.sh` и копируется через `docker run --rm`.

### 3. Проверить сайт

```bash
curl -s http://localhost:8000/ | head -5
```

Если видите HTML — Django запущен и отдаёт главную страницу.

---

## Nginx (хостовый веб-сервер)

### Базовая конфигурация

Создайте `/etc/nginx/sites-available/star-burger`:

```nginx
server {
    listen 80;
    server_name ваш_домен;  # или IP-адрес

    location /static/ {
        alias /opt/star-burger/back/staticfiles/;
    }

    location /media/ {
        alias /opt/star-burger/back/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Активируйте:

```bash
ln -s /etc/nginx/sites-available/star-burger /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

> **Как работает статика:** `deploy.sh` собирает образы, извлекает бандлы и
> collectstatic в `/opt/star-burger/back/staticfiles/`. Nginx отдаёт их напрямую.
> Django-контейнер тоже читает статику из образа, но nginx — основной источник.

---

## HTTPS (Let's Encrypt)

### 1. Установить Certbot

```bash
apt install -y certbot python3-certbot-nginx
```

### 2. Получить сертификат

```bash
certbot --nginx -d ваш_домен
```

Certbot сам:

- получит SSL-сертификат
- перенастроит Nginx на HTTPS
- настроит автоперенаправление с HTTP на HTTPS

> После настройки HTTPS убедитесь, что домен в `CSRF_TRUSTED_ORIGINS` в
> `.env` совпадает с доменом сертификата. Иначе POST-запросы (оформление заказа, вход в админку) будут падать с ошибкой CSRF 403.

### 3. Автопродление

```bash
certbot renew --dry-run
```

Проверьте, что Cron стоит на автообновлении сертификатов.

---

## Обновление кода

Основной способ — скрипт `deploy.sh`. Он:

1. Переключается на ветку `deploy`.
2. Забирает изменения из `fork/master`.
3. Собирает Docker-образы (frontend и web).
4. Копирует статику (bundles + collectstatic) в `./staticfiles/`.
5. Применяет миграции.
6. Запускает контейнеры.
7. Сообщает Rollbar (пропускается, если `ROLLBAR_ACCESS_TOKEN` не задан).
8. Пушит снимок состояния в `fork/deploy`.

```bash
cd /opt/star-burger
./deploy.sh
```

**Если что-то пошло не так — откатитесь:**

```bash
cd /opt/star-burger
git log --oneline -5                # найти предыдущий рабочий коммит
git reset --hard <hash>             # откатиться к нему
./deploy.sh
```

> Ветка `deploy` хранит предыдущее рабочее состояние. `master` — всегда
> экспериментальный.

---

## Полезные команды

| Действие          | Команда                                                                                                     |
| ----------------- | ----------------------------------------------------------------------------------------------------------- |
| Запуск            | `docker compose -f docker-compose.prod.yml up -d`                                                           |
| Остановка         | `docker compose -f docker-compose.prod.yml down`                                                            |
| Логи              | `docker compose -f docker-compose.prod.yml logs -f web`                                                     |
| Консоль Django    | `docker compose -f docker-compose.prod.yml exec web python manage.py shell`                                 |
| Миграции          | `docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate`                           |
| Пересобрать образ | `docker compose -f docker-compose.prod.yml build`                                                           |
| Дамп БД           | `docker compose -f docker-compose.prod.yml exec db pg_dump star_burger -U star_burger_user > /tmp/dump.sql` |
| Загрузить дамп    | `docker compose -f docker-compose.prod.yml exec db psql star_burger -U star_burger_user < /tmp/dump.sql`    |

---

## Сохранность данных

| Что                          | Где                                                 | Переживает `docker compose down`?        |
| ---------------------------- | ----------------------------------------------------| ---------------------------------------- |
| База данных                  | Docker volume `postgres_data`                       | ✅ да                                    |
| Загруженные файлы (`media/`) | Bind mount `./back/media`                           | ✅ да                                    |
| Статика (`staticfiles/`)     | Хостовая папка `/opt/star-burger/back/staticfiles/` | ✅ да                                    |
| Образы                       | Локальный Docker cache                              | ❌ нет (но пересобираются за 1–2 минуты) |

> Не запускайте `docker compose down -v` — он удалит volume `postgres_data`
> и базу данных.

---

## Безопасность

- Файл `.env` **никогда** не коммитится в Git.
- Пароль к БД — не дефолтный.
- `DEBUG=False` на проде.
- Токены Rollbar и Яндекс API хранятся в `.env`, а не в коде.
- Docker-контейнеры не слушают внешние порты (кроме 8000 на `127.0.0.1`).

---

## Развёртывание на локальной машине (для разработки)

Подробная инструкция — в [README.md](README.md). Кратко:

```bash
# В папке проекта
docker compose --profile dev up
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
# Открыть http://localhost
```

Бэкенд и фронтенд запускаются в отдельных контейнерах: `web`, `frontend`,
`db`, `nginx`.
