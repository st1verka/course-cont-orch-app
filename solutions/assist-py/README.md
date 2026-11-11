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
