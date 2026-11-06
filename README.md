# Resume Builder

Приложение адаптирует резюме под вакансии. Пользователь загружает исходный PDF или DOCX один раз, затем добавляет вакансии полным текстом. Для каждой вакансии создаётся отдельная версия резюме; оригинальный файл сохраняется без изменений.

Адаптация проходит через Matcher → Tailor → Critic: анализ соответствия, переписывание с опорой на исходные факты и проверка результата. Результат — текст и замечания Critic, сохранённые в PostgreSQL. Скачать можно исходный документ, адаптированный текст — скопировать из интерфейса.

## Документация

- [Архитектура и движение данных](docs/architecture.md): сервисы, хранение, LLM, очередь и границы надёжности.
- [Контракты API](docs/api.md): авторизация, документы, адаптации, внутренние методы worker.
- [Frontend](frontend/README.md): страницы, сессия, черновики и браузерные проверки.
- [Worker и CLI](backend/worker/README.md): запуск по текстовым файлам и три сценария проверки реальной LLM.

Документация описывает текущую реализацию. Единого серверного списка адаптаций, экспорта результата в PDF/DOCX, редактирования и удаления документов пока нет.

## Пользовательский сценарий

1. Зарегистрироваться и войти.
2. Загрузить оригинал резюме в PDF или DOCX.
3. Открыть рабочее пространство, выбрать оригинал и вставить описание вакансии.
4. Нажать «Создать версию». Вакансия и задача сохраняются отдельно; браузер опрашивает статус задачи.
5. Прочитать результат и замечания Critic. При необходимости скопировать текст.
6. Для следующей вакансии использовать тот же оригинал.

**«Мои версии» — история текущей вкладки.** После перезагрузки страницы этот список очищается. Сами результаты остаются в БД и доступны по прямой ссылке `/my-versions/<id>`. Списки оригиналов и вакансий загружаются с сервера и сохраняются между посещениями.

## Стек и структура

| Часть | Реализация |
| --- | --- |
| Интерфейс | React, TypeScript, Vite, Mantine 8.3.18 |
| Авторизация | FastAPI, JWT, отдельная PostgreSQL |
| Документы и задачи | FastAPI, SQLAlchemy, Alembic, PostgreSQL |
| Оригинальные файлы | MinIO |
| Доставка событий | PostgreSQL Outbox → Redis |
| Обработка | Python worker, извлечение PDF/DOCX, embeddings, Matcher → Tailor → Critic |

```text
backend/auth/       Пользователи, вход, refresh, проверка роли сотрудника
backend/resume/     Резюме, вакансии, адаптации, Outbox, внутренний API
backend/worker/     Обработка очереди, извлечение текста, LLM, CLI
frontend/           Интерфейс и его тесты
docs/               Архитектура и API
docker-compose.yml Локальное окружение
```

Python-зависимости закреплены в `requirements.txt` каждого сервиса, npm-зависимости — в `frontend/package-lock.json`. Docker использует Python 3.11 и Node.js 22.

## Запуск с нуля

Нужны Docker с Compose v2 и доступ worker к API провайдера LLM. Для запуска всего приложения локальные Python и Node.js не обязательны. Команды ниже выполняются из корня репозитория в PowerShell.

### 1. Настроить окружение

Создать локальные файлы из примеров, сохранив уже существующие настройки:

```powershell
if (-not (Test-Path backend/auth/.env)) { Copy-Item backend/auth/.env.example backend/auth/.env }
if (-not (Test-Path backend/resume/.env)) { Copy-Item backend/resume/.env.example backend/resume/.env }
if (-not (Test-Path backend/worker/.env)) { Copy-Item backend/worker/.env.example backend/worker/.env }
```

В созданных файлах заполнить:

| Переменная | Где | Что указать |
| --- | --- | --- |
| `SECRET_KEY` | auth, resume | Одинаковая случайная строка для подписи и проверки JWT |
| `WORKER_API_TOKEN` | resume, worker | Другая одинаковая случайная строка для внутреннего API |
| `OPENAI_API_KEY` | worker | Действующий ключ провайдера |
| `DB_USER`, `DB_PASSWORD` | auth, resume | Для стандартного Compose — `admin` / `admin` |

Для генерации случайной строки при наличии Python можно использовать `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Значения ключей хранятся только в локальном окружении.

Необязательные настройки и значения по умолчанию:

| Переменная | Сервис | Значение |
| --- | --- | --- |
| `OPENAI_BASE_URL` | worker | `https://api.openai.com/v1` |
| `LLM_MODEL` | worker | `gpt-5-mini` |
| `HTTP_TIME_OUT` | worker | `90` секунд на HTTP-запрос |
| `EMBEDDING_MODEL` | worker | `text-embedding-3-small` |
| `REDIS_QUEUE_NAME` | resume, worker | `embedding_tasks`, должно совпадать |
| `MINIO_BUCKET` | resume, minio-init | `resumes` |
| `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` | resume, MinIO | `minioadmin` / `minioadmin` |

Compose передаёт `.env` через `env_file` и переопределяет адреса БД, Redis, MinIO и resume API на имена контейнеров. Примеры `.env.example` содержат адреса для запуска Python на хосте. Сервисы Python сами `.env` не читают.

Текущая конфигурация Compose предназначена для локальной разработки: порты опубликованы на хосте, БД и MinIO имеют стандартные учётные данные. Она не описывает готовое публичное развёртывание.

### 2. Поднять инфраструктуру и применить миграции

```powershell
docker compose config --quiet
docker compose build auth resume worker frontend
docker compose up -d --wait auth-postgres resume-postgres redis minio
docker compose run --rm --no-deps minio-init
docker compose run --rm --no-deps auth alembic upgrade head
docker compose run --rm --no-deps resume alembic upgrade head
docker compose up -d auth resume worker frontend
docker compose ps --all
```

Каждая команда должна завершиться успешно до следующей. `minio-init` создаёт bucket и штатно завершается с кодом 0. Остальные сервисы должны оставаться запущенными.

**Миграции выполняются отдельно для обеих БД.** Запуск контейнера и успешный `/health` не применяют их автоматически. Worker следует запускать после миграций. Без таблицы `adaptations` создание версии вернёт 500, даже если загрузка резюме и сохранение вакансий работают.

### 3. Открыть приложение

| Адрес | Назначение |
| --- | --- |
| [localhost:5173](http://localhost:5173/) | Интерфейс |
| [localhost:8001/docs](http://localhost:8001/docs) | Swagger auth |
| [localhost:8002/docs](http://localhost:8002/docs) | Swagger resume, включая внутренний API |
| [localhost:8002/health](http://localhost:8002/health) | Проверка ответа resume-сервиса |
| [localhost:9001](http://localhost:9001/) | Консоль MinIO |

Порты PostgreSQL на хосте: `5433` для auth и `5434` для resume. Redis — `16379`, MinIO S3 API — `9000`. Внутри контейнеров используются стандартные порты и имена сервисов из Compose.

## Обновление существующего окружения

Перед обновлением прекратить новые отправки и дождаться завершения текущих задач и обработки очереди. Остановка worker во время работы может оставить задачу в `running` и сообщение в processing; автоматического восстановления нет. После этого остановить обработку, пересобрать образы и применить миграции перед повторным запуском:

```powershell
docker compose stop worker resume auth
docker compose build auth resume worker frontend
docker compose run --rm --no-deps auth alembic upgrade head
docker compose run --rm --no-deps resume alembic upgrade head
docker compose up -d auth resume worker frontend
```

БД, Redis и MinIO должны оставаться запущенными. Для обычной остановки без удаления данных: `docker compose stop`. Данные находятся в именованных томах `pgdata_auth`, `pgdata_resume`, `minio_data`, `redisdata_resume`; удаление томов стирает соответствующие данные.

После изменения `.env` контейнер нужно пересоздать, например `docker compose up -d --force-recreate worker`. Обычный `restart` не перечитывает `env_file`. Изменения Python-файлов в bind mount auth/resume требуют перезапуска процессов; worker получает код при сборке образа.

Frontend хранит `node_modules` в отдельном томе. После изменения lockfile:

```powershell
docker compose exec -T frontend npm ci
docker compose restart frontend
```

## Разработка и проверки

### Frontend

Нужен Node.js 22. Из каталога `frontend`:

```powershell
npm ci
npm run dev
```

Vite проксирует API на `http://localhost:8001` и `http://localhost:8002`. Для других адресов задать `AUTH_API_URL` и `RESUME_API_URL` в окружении до запуска Vite.

```powershell
npm run lint
npm test
npm run build
npm run test:browser
```

Контрактные тесты подменяют `fetch`, браузерные — API. Для браузерных тестов нужен установленный Google Chrome; используются три размера экрана. Особенности Windows TEMP описаны в [frontend/README.md](frontend/README.md#проверки).

### Backend

Тесты используют pytest, pytest-asyncio и pytest-subtests. Запускать из каталога каждого Python-сервиса в отдельном окружении:

```powershell
python -m pip install -r requirements-test.txt
python -m pytest
```

Для локального запуска API/Alembic нужно предварительно экспортировать настройки в окружение процесса. У каждого сервиса свой пакет `app`, поэтому команды запускаются из соответствующего каталога.

В работающем Compose тесты auth и resume доступны через bind mount:

```powershell
docker compose exec -T auth python -m pip install -r requirements-test.txt
docker compose exec -T resume python -m pip install -r requirements-test.txt
docker compose exec -T auth python -m pytest
docker compose exec -T resume python -m pytest
```

Тесты репозитория resume требуют `TEST_DATABASE_URL`; без него они пропускаются. Для полной проверки использовать отдельную тестовую PostgreSQL, доступную из процесса тестов. На стандартном локальном Compose можно один раз создать тестовую БД:

```powershell
docker compose exec -T resume-postgres psql -U admin -d postgres -c 'CREATE DATABASE resume_test_db;'
docker compose exec -T -e TEST_DATABASE_URL=postgresql+asyncpg://admin:admin@resume-postgres:5432/resume_test_db resume python -m pytest
```

Тесты создают случайные схемы и удаляют их после выполнения. Не указывать рабочую БД для проверки нового или изменённого тестового кода.

Образ worker содержит только приложение. Для его тестов без установки Python на хост:

```powershell
docker compose run --rm --no-deps -v "${PWD}/backend/worker:/service:ro" worker sh -c "pip install -r requirements-test.txt && python -m pytest -p no:cacheprovider"
```

Эти тесты используют подставные ответы провайдера и не подтверждают качество адаптации реальной LLM. Ручные прогоны с подходящим опытом, отсутствующими навыками и намеренно ложным фактом описаны в [worker/README.md](backend/worker/README.md#три-ручных-сценария). Они вызывают платный API.

## Диагностика

Начать с состояния контейнеров и короткого фрагмента логов:

```powershell
docker compose ps --all
docker compose logs --tail 80 resume worker
docker compose exec -T resume alembic current
docker compose exec -T resume alembic heads
```

Состояния адаптаций и длины очередей можно проверить без чтения документов:

```powershell
docker compose exec -T resume-postgres psql -U admin -d resume_db -c 'SELECT status, count(*) FROM adaptations GROUP BY status;'
docker compose exec -T redis redis-cli LLEN embedding_tasks
docker compose exec -T redis redis-cli LLEN embedding_tasks:processing
```

Имена очередей выше соответствуют значению по умолчанию `REDIS_QUEUE_NAME`; при его изменении подставить свои. Непустая processing-очередь может содержать как активное, так и зависшее сообщение.

| Симптом | Что проверить |
| --- | --- |
| `POST /adaptations` → 500, в логах отсутствует таблица | Выполнить `docker compose exec -T resume alembic upgrade head`; затем `alembic check`. Миграция адаптаций — `d72e8a916b30` |
| Vite не находит `@mantine/core` | Обновить `node_modules` контейнера командой `npm ci` и перезапустить frontend |
| Внутренний API → 401 или 503 | Совпадение `WORKER_API_TOKEN` у resume/worker; после изменения env пересоздать контейнеры |
| Worker сообщает ошибку провайдера | Проверить доступность API, ключ, доступ к модели и лимиты аккаунта; `error` адаптации содержит только класс исключения |
| Задача остаётся `pending` | Проверить worker, Outbox dispatcher, Redis и совпадение имени очереди |
| Задача долго остаётся `running` | Проверить логи и processing-очередь; автоматического восстановления после аварии нет |
| Версии исчезли после перезагрузки | Список хранится в памяти вкладки; открыть сохранённую прямую ссылку |
| После 500 браузер блокирует повтор создания | Сначала проверить результат: сервер мог принять запрос. Сохранённая вакансия доступна в «Мои вакансии» |

После неопределённого ответа POST не повторять запрос автоматически: повторное создание адаптации с той же парой ID создаёт новую запись. Если подтверждено, что запись не создана, обновить страницу и запустить адаптацию для уже сохранённой вакансии.

## Текущие ограничения

- Резюме и вакансия обрабатываются целиком. Нет разбиения на профиль, поля и фрагменты, OCR, векторного поиска или подбора вакансий по embeddings.
- Полный текст документов передаётся внешнему провайдеру для embeddings и адаптации. Critic снижает риск выдуманных фактов, но не гарантирует их отсутствие; результат нужно сверять с оригиналом.
- Замечания Critic не запускают автоматическое переписывание. `done` означает завершение обработки, а одобрение определяется отдельно через `result.review.passed`.
- Очередь не имеет автоматического восстановления зависших `processing`/`running`, DLQ или гарантии exactly-once. Подробности — в [архитектуре](docs/architecture.md#доставка-событий-и-сбои).
- Общей истории адаптаций в API и экспорта адаптированного документа нет. Исходники и вакансии сохраняются, результат доступен по ID.
- Некорректный refresh token сейчас может приводить к 500 auth-сервиса. Интерфейс завершает сессию при неудачном refresh.
