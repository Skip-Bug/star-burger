# Инструкция по деплою Star Burger

Документ описывает развёртывание проекта на сервере (production) и на локальной машине.
Локальная разработка подробно описана в [README.md](README.md), здесь приведены только
серверные сценарии и резервные варианты.

---

## 🖥️ Развёртывание на сервере (production)

### Требования

- Ubuntu 22.04+
- Python 3.10+
- PostgreSQL 14+
- Nginx
- Git

### Подготовка сервера

```bash
apt update
apt install python3-pip python3-venv postgresql postgresql-contrib nginx git -y
```

### Создание базы данных

Заходим в Postgres от суперпользователя:

```bash
sudo -u postgres psql
```

Создаём роль и базу. Пользователь сразу становится владельцем базы — этого
достаточно для всех операций (миграции, CRUD, тесты), никаких дополнительных
`GRANT` не требуется:

```sql
CREATE USER star_burger_user WITH PASSWORD 'надёжный_пароль';
CREATE DATABASE star_burger OWNER star_burger_user;
```

Настраиваем параметры сессии по умолчанию:

```sql
ALTER ROLE star_burger_user SET client_encoding TO 'utf8';
ALTER ROLE star_burger_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE star_burger_user SET timezone TO 'UTC';
\q
```

Или, если создаёте базу отдельно:

```sql
CREATE DATABASE star_burger;
CREATE USER star_burger_user WITH PASSWORD 'надёжный_пароль';
GRANT ALL PRIVILEGES ON DATABASE star_burger TO star_burger_user;
ALTER DATABASE star_burger OWNER TO star_burger_user;
\q
```

> ⚠️ Пароль не должен быть дефолтным (`postgres`/`postgres`) и не должен
> совпадать с локальным.

### Клонирование проекта

```bash
cd /opt
git clone git@gitverse.ru:Skrip/star-burger.git
cd star-burger
git checkout deploy
```

### Виртуальное окружение и зависимости

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Файл `.env`

Создай `/opt/star-burger/.env` со следующим содержимым:

```
SECRET_KEY=...
YANDEX_API_KEY=...
DATABASE_URL=postgres://star_burger_user:надёжный_пароль@localhost:5432/star_burger
ROLLBAR_ACCESS_TOKEN=...
ROLLBAR_ENVIRONMENT=production
ALLOWED_HOSTS=5.101.50.139 # поставте свой айпи сервера
DEBUG=False #Для прода, для разработки True
```

> Файл `.env` **не коммитится** в Git. Он должен быть в `.gitignore`.

### Миграции, статика, суперпользователь

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### Systemd-сервис

Обязательно создай юнит.
Создай `/etc/systemd/system/star-burger.service`:

```ini
[Unit]
Description=Star Burger

[Service]
Type=simple
User=root
WorkingDirectory=/opt/star-burger
EnvironmentFile=/opt/star-burger/.env
Environment="DEBUG=False" # если добавить тут, можно легко менять для дебага
ExecStart=/opt/star-burger/venv/bin/gunicorn -w 3 -b 127.0.0.1:8000 star_burger.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

**Зависимость от Postgres**

**Вариант 1. Postgres на том же сервере** — добавь в `star-burger.service`:

```ini
[Unit]
After=network.target postgresql.service
Requires=postgresql.service
```

И для надёжности — проверку готовности:

```ini
[Service]
ExecStartPre=/bin/bash -c 'until pg_isready -h localhost -p 5432; do sleep 1; done'
```

**Вариант 2. Postgres на другом сервере** — `After`/`Requires` не сработают,
используй проверку по сети:

```ini
[Service]
ExecStartPre=/bin/bash -c 'until pg_isready -h <адрес_бд> -p 5432; do sleep 2; done'
Restart=always
RestartSec=5
```

Активируй:

```bash
systemctl daemon-reload
systemctl enable star-burger
systemctl start star-burger
systemctl status star-burger
```

### Nginx

Создай `/etc/nginx/sites-available/star-burger`:

```nginx
server {
    listen 80;
    server_name 5.101.50.139; # айпи вашего сервера

    location /static/ {
        alias /opt/star-burger/staticfiles/;
    }
    location /media/ {
        alias /opt/star-burger/media/;
    }
    location / {
        include /etc/nginx/proxy_params;
        proxy_pass http://127.0.0.1:8000/;
    }
}
```

Активируй:

```bash
ln -s /etc/nginx/sites-available/star-burger /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
```

### Проверка

Открой `ip_вашего_сервера` — сайт должен работать, статика и медиа
отдаваться, а админка открываться.

---

## 🔄 Обновление проекта на сервере

### На локальной машине

```bash
git checkout master
git add .
git commit -m "Описание изменений"
git push origin master
```

### На сервере

```bash
cd /opt/star-burger
git checkout deploy
git fetch
git merge origin/master       # при конфликтах — разрешить вручную
git push origin deploy

source venv/bin/activate
pip install -r requirements.txt          # если менялся requirements.txt
python manage.py migrate                 # если есть новые миграции
python manage.py collectstatic --noinput # если менялась статика
systemctl restart star-burger
```

---

## ⚡ Быстрый деплой одной командой

Создайте скрипт в корне проекта:

```bash
nano deploy.sh
```

Скопируйте туда:

````
#!/bin/bash
set -euo pipefail
cd /opt/star-burger
echo "Обновляем ветку deploy из origin/master"
git checkout deploy
git fetch
git merge origin/master --no-edit
echo "Активируем виртуальное окружение"
source venv/bin/activate
echo "Устанавливаем зависимости"
pip install -r requirements.txt
echo "Устанавливаем Node.js-зависимости"
npm install --silent
echo "Пересобираем JS"
./node_modules/.bin/parcel build bundles-src/index.js --dist-dir bundles --public-url="./"
echo "Применяем миграции"
python manage.py migrate --noinput
echo "Собираем статику"
python manage.py collectstatic --noinput
echo "Перезапускаем сервис"
systemctl restart star-burger
echo "Сообщаем Rollbar о деплое"
COMMIT_HASH=$(git rev-parse origin/master)
ACCESS_TOKEN=$(grep -E '^ROLLBAR_ACCESS_TOKEN=' .env | cut -d= -f2- | tr -d "'\"")
ROLLBAR_ENV=$(grep -E '^ROLLBAR_ENVIRONMENT=' .env | cut -d= -f2- | tr -d "'\"")
AUTHOR=$(git log -1 --pretty=format:'%an' origin/master)
COMMENT=$(git log -1 --pretty=format:'%s' origin/master)
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
echo "Готово!"


```bash
chmod u+x deploy.sh # Сделать скрипт исполняемым

./deploy.sh # запуск скрипта
````

Скрипт:

1. Обновляет код из `origin/master` в ветку `deploy`.
2. Устанавливает Python- и Node.js-зависимости.
3. Пересобирает JS (`npm run build`).
4. Применяет миграции.
5. Собирает статику.
6. Перезапускает Gunicorn.
7. Сообщает Rollbar о деплое

---

## 💻 Развёртывание локально (для разработки)

Подробная инструкция — в [README.md](README.md). Кратко:

### Клонирование

```bash
git clone git@gitverse.ru:Skrip/star-burger.git
cd star-burger
```

### Виртуальное окружение

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

### Зависимости

```bash
pip install -r requirements.txt
```

### PostgreSQL

Создай базу и пользователя (см. раздел сервера, «Создание базы данных»).

Если Postgres поднимать не хочется, оставь `DATABASE_URL` пустым — проект
откатится на SQLite.

### Файл `.env`

Создай в корне проекта:

```
SECRET_KEY=...
YANDEX_API_KEY=...
DATABASE_URL=postgres://star_burger_user:локальный_пароль@localhost:5432/star_burger
ROLLBAR_ACCESS_TOKEN=...
ROLLBAR_ENVIRONMENT=development
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

### Миграции и запуск

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## 🌐 Домен и HTTPS (необязательно, но рекомендуется)

### Домен

Для продакшена желательно купить домен — так сайт будет выглядеть профессиональнее,
а Let's Encrypt сможет выдать сертификат.
[бесплатно можно тут](https://localhost.cc/)

В DNS нужно добавить A-запись, указывающую на IP-адрес вашего сервера:

![Добавление DNS-записи: тип A, поддомен, IP сервера](assets/dns-record.png)

### Указать домен в настройках

**`.env`** (`/opt/star-burger/.env`):

```env
ALLOWED_HOSTS=ваш-домен.ru,www.ваш-домен.ru
CSRF_TRUSTED_ORIGINS=https://ваш-домен.ru,https://www.ваш-домен.ru
```

**Nginx** (`/etc/nginx/sites-available/star-burger`) — заменить `server_name`:

```nginx
server_name ваш-домен.ru www.ваш-домен.ru;
```

Применить:

```bash
nginx -t && systemctl reload nginx
systemctl restart star-burger
```

### Сертификат Let's Encrypt

```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d ваш-домен.ru -d www.ваш-домен.ru
```

Certbot сам настроит HTTPS и редирект с HTTP. Продление — автоматическое.

Проверка:

```bash
certbot renew --dry-run
```

- [Certbot — официальный сайт](https://certbot.eff.org/)
- [Let's Encrypt — официальный сайт](https://letsencrypt.org/)

После изменений:

```bash
systemctl restart star-burger
```

## 📌 Полезные команды

| Действие               | Команда                                       |
| ---------------------- | --------------------------------------------- |
| Логи Gunicorn          | `journalctl -u star-burger -n 50`             |
| Логи Nginx             | `journalctl -u nginx -n 50`                   |
| Перезапуск сервиса     | `systemctl restart star-burger`               |
| Проверка конфига Nginx | `nginx -t`                                    |
| Перезагрузка Nginx     | `systemctl reload nginx`                      |
| Подключение к БД       | `sudo -u postgres psql -d star_burger`        |
| Дамп БД                | `python manage.py dumpdata -o /tmp/dump.json` |
| Загрузка дампа         | `python manage.py loaddata /tmp/dump.json`    |

---

## 🔐 Безопасность

- Файл `.env` **никогда** не коммитится.
- Пароль к БД — не дефолтный.
- `DEBUG=False` на проде.
- Токены Rollbar и Яндекс.API хранятся в `.env`, а не в коде.
- Postgres слушает только `localhost`, не открыт в интернет.
