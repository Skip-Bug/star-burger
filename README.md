# Сайт доставки еды Star Burger

[![Репозиторий GitHub](https://img.shields.io/badge/Репозиторий-GitHub-blue?logo=github)](https://github.com/Skip-Bug/star-burger)
[![Зеркало на GitVers](https://img.shields.io/badge/Зеркало-GitVers-orange)](https://gitverse.ru/Skrip/star-burger)
[![Лицензия MIT](https://img.shields.io/badge/Лицензия-MIT-blue.svg)](LICENSE)
[![Демо сайта](https://img.shields.io/badge/Демо-сайт-brightgreen)](https://skip-project.githubpage.com/)

Это сайт сети ресторанов Star Burger. Здесь можно заказать превосходные бургеры с доставкой на дом.
<img style="max-width:50%; height:auto;" alt="Screenshot 2026-10-10 010603" src="https://github.com/user-attachments/assets/cb3c0911-e78a-4e9d-8fa1-6a6b9e88b013" />

Сеть Star Burger объединяет несколько ресторанов, действующих под единой франшизой. У всех ресторанов одинаковое меню и одинаковые цены. Просто выберите блюдо из меню на сайте и укажите место доставки. Мы сами найдём ближайший к вам ресторан, всё приготовим и привезём.

На сайте есть три независимых интерфейса. Первый — это публичная часть, где можно выбрать блюда из меню, и быстро оформить заказ без регистрации и SMS.

Второй интерфейс предназначен для менеджера. Здесь происходит обработка заказов. Менеджер видит поступившие новые заказы и первым делом созванивается с клиентом, чтобы подтвердить заказ. После оператор выбирает ближайший ресторан и передаёт туда заказ на исполнение. Там всё приготовят и сами доставят еду клиенту.

Третий интерфейс — это админка. Преимущественно им пользуются программисты при разработке сайта. Также сюда заходит менеджер, чтобы обновить меню ресторанов Star Burger.

## Как запустить dev-версию сайта

Проект докеризован: бэкенд и фронтенд собираются в отдельные образы, база
поднимается Docker Compose. Это основной способ запуска.

[Установите Docker](https://docs.docker.com/get-docker/) и Docker Compose, если
этого ещё не сделали.

Скачайте код (основной репозиторий — GitHub):

```sh
git clone https://github.com/Skip-Bug/star-burger.git
```

Перейдите в каталог проекта:

```sh
cd star-burger
```

Скопируйте шаблон окружения в `.env` в корне проекта:

```sh
cp .env.example .env
# Windows: copy .env.example .env
```

Для запуска через Docker в `.env` должны быть такие значения:

```sh
SECRET_KEY=django-insecure-0if40nf4nf93n4
YANDEX_API_KEY=ключ доступа к Yandex Geocoder API
DATABASE_URL=postgres://star_burger_user:ваш_пароль@db:5432/star_burger
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
POSTGRES_DB=star_burger
POSTGRES_USER=star_burger_user
POSTGRES_PASSWORD=ваш_пароль
# CSRF_TRUSTED_ORIGINS=https://your-domain.com
```

- `DATABASE_URL` указывает на сервис `db`: внутри сети Compose база доступна по имени сервиса, а не по `localhost`.
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` читает Docker Compose, когда создаёт базу. Значения должны совпадать с `DATABASE_URL`.
- `YANDEX_API_KEY` можно получить на https://developer.tech.yandex.ru/.
- Файл `.env` **не коммитится** в Git.

Запустите все сервисы:

```sh
docker compose --profile dev up
```

Поднимутся четыре контейнера: `db` (PostgreSQL), `web` (Django runserver),
`frontend` (Parcel watch) и `nginx` (реверс-прокси на `web`).

В другом терминале примените миграции и создайте суперпользователя:

```sh
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Откройте сайт в браузере по адресу [http://localhost/](http://localhost/).
Админка — [http://localhost/admin/](http://localhost/admin/), интерфейс
менеджера — [http://localhost/manager/](http://localhost/manager/).

Остановить стек:

```sh
docker compose --profile dev down
```

Данные базы лежат в docker volume `postgres_data`, загруженные
файлы — в `./media` на хосте (bind mount). И то, и другое переживает
остановку и пересоздание контейнеров. Не добавляйте к `down` флаг `-v` — он удалит вместе с
томами и базу данных.

Полезные команды:

```sh
docker compose --profile dev up -d              # запуск в фоне
docker compose --profile dev logs -f web        # логи Django
docker compose exec web python manage.py shell  # консоль Django
docker compose --profile dev build              # пересобрать образы
```

## Как запустить dev-версию без Docker

Тот же стек можно собрать вручную, без Docker. Понадобится одновременно запускать
бэкенд и фронтенд в двух терминалах.

### Как собрать бэкенд

[Установите Python](https://www.python.org/), если этого ещё не сделали.

Проверьте, что `python` установлен и корректно настроен. Запустите его в командной строке:

```sh
python --version
```

**Важно!** Версия Python должна быть не ниже 3.10.

Возможно, вместо команды `python` здесь и в остальных инструкциях этого README придётся использовать `python3`. Зависит это от операционной системы и от того, установлен ли у вас Python старой второй версии.

Перейдите в каталог back и создайте виртуальное окружение:

```sh
cd back
python -m venv venv
```

Активируйте его. На разных операционных системах это делается разными командами:

- Windows: `.\venv\Scripts\activate`
- MacOS/Linux: `source venv/bin/activate`

Установите зависимости в виртуальное окружение:

```sh
pip install -r requirements.txt
```

### База данных

В этом режиме база не поднимается автоматически — PostgreSQL нужно установить
самостоятельно и создать базу данных и пользователя:

```sql
CREATE DATABASE star_burger;
CREATE USER star_burger_user WITH PASSWORD 'ваш_пароль';
GRANT ALL PRIVILEGES ON DATABASE star_burger TO star_burger_user;
ALTER DATABASE star_burger OWNER TO star_burger_user;
```

#### Быстрый fallback на SQLite

Если не хотите поднимать Postgres для отладки, не указывайте `DATABASE_URL`
в `.env` — проект откатится на SQLite.

### Файл `.env`

В отличие от Docker-режима, здесь база живёт на хосте, поэтому в `DATABASE_URL`
указан `localhost`, и переменные `POSTGRES_*` не нужны:

```sh
SECRET_KEY=django-insecure-0if40nf4nf93n4
YANDEX_API_KEY=ключ доступа к Yandex Geocoder API
ROLLBAR_ACCESS_TOKEN='ваш_токен' # если хотите подключить ROLLBAR
ROLLBAR_ENVIRONMENT=development # production или development
DATABASE_URL=postgres://star_burger_user:ваш_пароль@localhost:5432/star_burger
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

- `YANDEX_API_KEY` можно получить на https://developer.tech.yandex.ru/.
- `ROLLBAR_ACCESS_TOKEN` можно получить на https://rollbar.com/.
- Файл `.env` **не коммитится** в Git.

Примените миграции:

```sh
python manage.py migrate
```

(Опционально) создайте суперпользователя для доступа в админку:

```sh
python manage.py createsuperuser
```

Запустите сервер:

```sh
python manage.py runserver
```

Откройте сайт в браузере по адресу [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Если вы увидели пустую белую страницу, то не пугайтесь, выдохните. Просто фронтенд пока ещё не собран. Переходите к следующему разделу README.

### Собрать фронтенд

**Откройте новый терминал**. Для работы сайта в dev-режиме необходима одновременная работа сразу двух программ `runserver` и `parcel`. Каждая требует себе отдельного терминала. Чтобы не выключать `runserver` откройте для фронтенда новый терминал и все нижеследующие инструкции выполняйте там.

[Установите Node.js](https://nodejs.org/en/), если у вас его ещё нет.

Проверьте, что Node.js и его пакетный менеджер корректно установлены. Если всё исправно, то терминал выведет их версии:

```sh
nodejs --version
# v16.16.0
# Если ошибка, попробуйте node:
node --version
# v16.16.0

npm --version
# 8.11.0
```

Версия `nodejs` должна быть не младше `10.0` и не старше `16.16`. Лучше ставьте `16.16.0`, её мы тестировали. Версия `npm` не важна. На macOS версия 16 может не запуститься с ошибкой `version 'GLIBC_2.29' not found` — тогда берите `17.6.0` или новее.

Перейдите в каталог front и установите пакеты Node.js:

```sh
cd front
npm ci
```

Команда `npm ci` создаст каталог `node_modules` и установит туда пакеты Node.js. Получится аналог виртуального окружения как для Python, но для Node.js.

Помимо прочего будет установлен [Parcel](https://parceljs.org/) — это упаковщик веб-приложений, похожий на [Webpack](https://webpack.js.org/). В отличии от Webpack он прост в использовании и совсем не требует настроек.

Теперь запустите сборку фронтенда и не выключайте. Parcel будет работать в фоне и следить за изменениями в JS-коде:

```sh
./node_modules/.bin/parcel watch bundles-src/index.js --dist-dir ../back/bundles --public-url="./"
```

Если вы на Windows, то вам нужна та же команда, только с другими слешами в путях:

```sh
.\node_modules\.bin\parcel watch bundles-src/index.js --dist-dir ../back/bundles --public-url="./"
```

Дождитесь завершения первичной сборки. Это вполне может занять 10 и более секунд. О готовности вы узнаете по сообщению в консоли:

```
✨  Built in 10.89s
```

Parcel будет следить за файлами в каталоге `bundles-src`. Сначала он прочитает содержимое `index.js` и узнает какие другие файлы он импортирует. Затем Parcel перейдёт в каждый из этих подключенных файлов и узнает что импортируют они. И так далее, пока не закончатся файлы. В итоге Parcel получит полный список зависимостей. Дальше он соберёт все эти сотни мелких файлов в большие бандлы `bundles/index.js` и `bundles/index.css`. Они полностью самодостаточны, и потому пригодны для запуска в браузере. Именно эти бандлы сервер отправит клиенту.

Теперь если зайти на страницу [http://127.0.0.1:8000/](http://127.0.0.1:8000/), то вместо пустой страницы вы увидите:

![](https://dvmn.org/filer/canonical/1594651900/687/)

Каталог `bundles` в репозитории особенный — туда Parcel складывает результаты своей работы. Эта директория предназначена исключительно для результатов сборки фронтенда и потому исключёна из репозитория с помощью `.gitignore`.

**Сбросьте кэш браузера <kbd>Ctrl-F5</kbd>.** Браузер при любой возможности старается кэшировать файлы статики: CSS, картинки и js-код. Порой это приводит к странному поведению сайта, когда код уже давно изменился, но браузер этого не замечает и продолжает использовать старую закэшированную версию. В норме Parcel решает эту проблему самостоятельно. Он следит за пересборкой фронтенда и предупреждает JS-код в браузере о необходимости подтянуть свежий код. Но если вдруг что-то у вас идёт не так, то начните ремонт со сброса браузерного кэша, жмите <kbd>Ctrl-F5</kbd>.

## Как запустить prod-версию сайта

Инструкция по развёртыванию на сервере (production): настройка PostgreSQL,
Nginx, `.env` для прода, сборка образов и запуск `deploy.sh` — в отдельном файле:

- [DEPLOY.md](DEPLOY.md)

## Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org). За основу был взят код проекта [FoodCart](https://github.com/Saibharath79/FoodCart).

Где используется репозиторий:

- Второй и третий урок [учебного курса Django](https://dvmn.org/modules/django/)
- Второй урок [учебного курса по докеру](https://dvmn.org/modules/docker-v2/lesson/dockerize-django/)
