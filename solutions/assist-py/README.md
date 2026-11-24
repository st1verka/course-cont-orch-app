# Assistant

Персональный ассистент на FastAPI для лабораторных работ по Docker и Kubernetes.

Автор: Ивановский Роман Евгеньевич
ИСУ: 466021
Группа: К3320
Персональный префикс: ivanovsky
Персональный порт: 5451

Исходное приложение: https://github.com/FilBTi/assist-py

## Как собрать

Базовый образ:

    docker build -t ivanovsky-assistant:v1 .

Финальный образ:

    docker build -t ivanovsky-assistant:final -f Dockerfile.optimized .

## Как запустить

Введите учебный секрет и нажмите Enter (ввод скрыт):

    read -s APP_SECRET
    export APP_SECRET

Создайте контейнер:

    docker run -d --name ivanovsky-assistant-final -p 5451:5451 -e APP_OWNER=ivanovsky -e APP_SECRET ivanovsky-assistant:final

Если контейнер уже существует и остановлен:

    docker start ivanovsky-assistant-final

## Переменные окружения

| Переменная | Назначение | Значение |
| --- | --- | --- |
| APP_OWNER | Владелец приложения | ivanovsky |
| APP_SECRET | Учебный ключ секретного эндпоинта | Передаётся при запуске |
| PORT | Порт приложения внутри контейнера | 5451 |

PORT задан в Dockerfile. При изменении порта нужно изменить и проброс порта.
Секрет не записывается в Dockerfile. Файл .env исключён из Git и контекста сборки.

## Как проверить

    curl http://localhost:5451/
    curl http://localhost:5451/me
    curl http://localhost:5451/health
    curl -X POST http://localhost:5451/notes -H "Content-Type: application/json" -d '{"text":"ЛР2: сборка образа"}'
    curl http://localhost:5451/notes
    curl "http://localhost:5451/secret/${APP_SECRET}"

Проверка здоровья контейнера:

    docker ps --filter "name=ivanovsky-assistant-final" --format "table {{.Names}}\t{{.Status}}"

Ожидаемый статус: (healthy).
Заметки хранятся в памяти и теряются при перезапуске приложения.

## Результаты лабораторной работы №2

Размеры по столбцу DISK USAGE команды docker images:

| Тег | Вариант | Размер |
| --- | --- | --- |
| v1 | Базовая сборка | 313 МБ |
| v2 | Установка зависимостей без кеша pip | 287 МБ |
| ms | Multi-stage с виртуальным окружением | 307 МБ |
| v3 | Базовая сборка с .dockerignore | 313 МБ |
| final | Multi-stage с curl и HEALTHCHECK | 327 МБ |

Размеры округлены Docker.
Отключение кеша pip уменьшило размер на 26 МБ.
Вариант ms оказался на 20 МБ больше v2 из-за переноса отдельного виртуального окружения.
Установка curl добавила около 20 МБ относительно ms.

Отдельное копирование requirements.txt позволяет использовать кеш установки зависимостей при изменении только кода приложения.

.dockerignore исключает служебные файлы из контекста сборки.
Размер v3 совпал с v1, поскольку Dockerfile копирует только requirements.txt и app/.

Healthcheck проверяет /health каждые 30 секунд.
Таймаут: 5 секунд, стартовый период: 10 секунд, число неудач: 3.
Вместо curl можно использовать стандартный модуль Python urllib.request.

Текущий Dockerfile.optimized соответствует final.
Образы v2 и ms были собраны на промежуточных этапах.

## Тегирование

    docker tag ivanovsky-assistant:final ivanovsky-assistant:1.0.0
    docker tag ivanovsky-assistant:final ivanovsky-assistant:$(date +%Y%m%d)

Теги final, 1.0.0 и дата сборки ссылаются на один итоговый образ.

## Хранение данных

В лабораторной работе № 3 я подключил PostgreSQL к приложению на FastAPI. При заданной переменной `DATABASE_URL` приложение сохраняет заметки в базе данных, а эндпоинт `/health` проверяет доступность PostgreSQL.

Для хранения файлов базы данных я создал именованный том `ivanovsky-pgdata` и подключил его к каталогу `/var/lib/postgresql/data` внутри контейнера. На первом этапе я опубликовал порт PostgreSQL на хосте как `5451`. Ассистент обращается к базе `ivanovsky21` по адресу `host.docker.internal:5451` и принимает HTTP-запросы на порту `8021`.

Перед запуском необходимо задать и экспортировать переменные `POSTGRES_PASSWORD` и `APP_SECRET`. Команды выполняются из каталога `solutions/assist-py`.

```bash
docker volume create ivanovsky-pgdata

docker run -d --name ivanovsky-postgres \
  -e POSTGRES_USER=user_21 -e POSTGRES_PASSWORD -e POSTGRES_DB=ivanovsky21 \
  -v ivanovsky-pgdata:/var/lib/postgresql/data -p 5451:5432 postgres:15

docker build -f Dockerfile.optimized -t ivanovsky-assistant:v3 .

docker run -d --name ivanovsky-assistant -p 8021:8021 \
  -e PORT=8021 -e APP_OWNER=ivanovsky -e APP_SECRET \
  -e DATABASE_URL="postgresql://user_21:${POSTGRES_PASSWORD}@host.docker.internal:5451/ivanovsky21" \
  ivanovsky-assistant:v3
```

Для проверки я отправил четыре HTTP-запроса. Главная страница вернула приветствие, а `/health` подтвердил подключение к PostgreSQL. Затем я создал заметку «ЛР3: данные в БД» запросом `POST /notes` и проверил её наличие в ответе `GET /notes`.

[Скриншот проверки](../reports/lab-3/images/step-1-5.png)
### Проверка сохранности данных

Я остановил и удалил контейнер ассистента, затем заново создал его из того же образа. Контейнер PostgreSQL с томом `ivanovsky-pgdata` продолжал работать. Запрос `GET /notes` вернул заметку «ЛР3: данные в БД», созданную до пересоздания ассистента.

[Скриншот проверки](../reports/lab-3/images/step-2-4.png)

### Подключение файла конфигурации

Я подключил каталог `config` с хоста к `/app/config` в контейнере в режиме только для чтения. Командой `docker exec` я проверил содержимое `app.conf`. После изменения `maintenance_mode` на хосте и перезапуска контейнера файл внутри контейнера содержал новое значение `true`. Образ я не пересобирал.

[Скриншот проверки](../reports/lab-3/images/step-3-3.png)

### Пользовательская сеть Docker

Я создал сеть `ivanovsky-backend` и подключил к ней PostgreSQL и ассистента. Порт PostgreSQL не опубликован на хосте. Ассистент обращается к базе по имени контейнера `ivanovsky-postgres` и порту `5432`. Для HTTP-запросов к ассистенту на хосте опубликован порт `8021`.

Команды ниже используют ранее созданный том `ivanovsky-pgdata` и переменные окружения `POSTGRES_PASSWORD` и `APP_SECRET`. Ассистент запускается после того, как `pg_isready` подтвердит готовность базы.

```bash
docker network create ivanovsky-backend

docker run -d --name ivanovsky-postgres \
  --network ivanovsky-backend \
  -e POSTGRES_USER=user_21 -e POSTGRES_PASSWORD -e POSTGRES_DB=ivanovsky21 \
  -v ivanovsky-pgdata:/var/lib/postgresql/data postgres:15

docker exec ivanovsky-postgres \
  pg_isready -h 127.0.0.1 -U user_21 -d ivanovsky21

docker run -d --name ivanovsky-assistant \
  --network ivanovsky-backend -p 8021:8021 \
  -e PORT=8021 -e APP_OWNER=ivanovsky -e APP_SECRET \
  -e DATABASE_URL="postgresql://user_21:${POSTGRES_PASSWORD}@ivanovsky-postgres:5432/ivanovsky21" \
  -v "$PWD/config:/app/config:ro" \
  ivanovsky-assistant:v3
```

Я проверил разрешение имени `ivanovsky-postgres` из двух контейнеров Alpine. Вне сети `ivanovsky-backend` имя не разрешилось. Внутри сети я получил два ответа на `ping` без потерь. Запрос `GET /notes` вернул заметку, созданную до переноса, и новую заметку «ЛР3: сеть работает!».

- [Проверка вне сети](../reports/lab-3/images/step-4-4-outside.png)
- [Проверка внутри сети](../reports/lab-3/images/step-4-4-inside.png)
