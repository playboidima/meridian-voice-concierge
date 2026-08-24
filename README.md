# Meridian Voice Concierge

Core Voice Concierge: Backend API, PostgreSQL, 47 FAQ та окремий англомовний голосовий агент LiveKit із STT–LLM–TTS pipeline. Агент відповідає лише за даними FAQ, а невідомі питання записує для подальшого опрацювання.

Детальні обґрунтування архітектури наведені в `TECHNICAL_DECISIONS.md`, а
звірка з обов'язковими критеріями PRD — у `CORE_ACCEPTANCE.md`.

## Архітектура

```text
LiveKit Agent -> FastAPI -> service пошуку -> PostgreSQL
                         -> unanswered questions
```

FAQ-пошук гібридний. Backend створює локальні англійські embeddings моделлю `BAAI/bge-small-en-v1.5`, зберігає їх у PostgreSQL через `pgvector` і виконує cosine similarity search. Сильні точні та перевірені lexical-збіги мають пріоритет, а semantic retrieval обробляє нові природні перефразування. Якщо обидва механізми нижче відповідного порога, API повертає `matched: false`. Embedding-модель працює локально на CPU і не потребує API-ключа.

## Запуск

1. Скопіюйте `.env.example` у `.env`:

```powershell
Copy-Item .env.example .env
```

2. Додайте до локального `.env` власні `LIVEKIT_URL`, `LIVEKIT_API_KEY` і `LIVEKIT_API_SECRET`. Не додавайте цей файл до Git.
3. Запустіть:

```powershell
docker compose up --build -d
```

Під час першого Docker build завантажується локальна embedding-модель. Backend автоматично застосує Alembic-міграції, увімкне `pgvector` і безпечно повторить seed разом з embeddings. API буде доступний на `http://localhost:8000`, Swagger — на `http://localhost:8000/docs`.

Перевірка:

```powershell
Invoke-RestMethod http://localhost:8000/health
docker compose ps
```

## API

### `GET /health`

Запит:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Відповідь:

```json
{"status":"ok","database":"ok"}
```

### `POST /api/faq/search`

Запит:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/api/faq/search" `
  -ContentType "application/json" `
  -Body '{"question":"Is the poker room open right now?"}'
```

Приклад успішної відповіді:

```json
{
  "matched": true,
  "score": 0.82,
  "best_match": "Коли працює покерна кімната і які ігри доступні?",
  "answer": "Покерна кімната працює 24/7...",
  "category": "casino"
}
```

Якщо надійного збігу немає:

```json
{"matched":false,"score":0.12,"best_match":null,"answer":null,"category":null}
```

### `POST /api/unanswered`

Запит:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/api/unanswered" `
  -ContentType "application/json" `
  -Body '{"question":"Are dogs allowed at the hotel?"}'
```

Відповідь (повторний нормалізований запит збільшує `frequency`):

```json
{
  "id": 1,
  "original_question": "Are dogs allowed at the hotel?",
  "normalized_question": "dogs allowed hotel",
  "frequency": 1,
  "status": "open",
  "first_seen_at": "2026-08-20T12:00:00Z",
  "last_seen_at": "2026-08-20T12:00:00Z"
}
```

## Корисні команди

```powershell
docker compose config
docker compose run --rm backend pytest -q
docker compose run --rm agent pytest -q
docker compose run --rm -e RUN_POSTGRES_INTEGRATION=1 backend pytest -q tests/test_postgres_concurrency.py
docker compose down
docker compose down -v  # також видаляє локальні дані PostgreSQL
```

Справжні LiveKit credentials потрібні лише для голосового запуску й не повинні потрапляти до Git. Окремі ключі провайдерів STT/LLM/TTS не потрібні при використанні LiveKit Inference.

## Голосовий агент

1. Вкажіть `LIVEKIT_URL`, `LIVEKIT_API_KEY` і `LIVEKIT_API_SECRET` у локальному `.env`.
2. Запустіть весь Core: `docker compose up --build`.
3. У LiveKit Agent Console почніть сесію з агентом `meridian-concierge`.

Агент приймає та озвучує лише англійську мову. Якщо гість говорить іншою мовою, агент просить повторити питання англійською. Внутрішні FAQ зберігаються українською, але гостю озвучується англійський переклад лише перевіреної відповіді.

Моделі можна змінити через `STT_MODEL`, `LLM_MODEL`, `TTS_MODEL` і `TTS_VOICE` без редагування коду. Для локального текстового запуску агента використайте `python -m app.main console` з каталогу `agent`.

## Перевірка чистого запуску

Увага: `down -v` безповоротно видаляє локальну базу та всі записані невідомі питання.

```powershell
docker compose down -v --remove-orphans
docker compose up --build -d
docker compose ps
docker compose exec db psql -U meridian -d meridian -c "SELECT COUNT(*) FROM faqs;"
```

Усі три сервіси мають бути `healthy`, а кількість FAQ — `47`.

Команду `docker compose down -v` використовуйте лише коли записані unknown-питання
більше не потрібні. Для звичайного перезапуску достатньо `docker compose down`,
який зберігає PostgreSQL volume.

## Відомі обмеження Core

- Голосова сесія потребує інтернету, LiveKit Cloud credentials і доступності LiveKit Inference.
- Semantic threshold відкалібровано на контрольному наборі Core; перед суттєвим розширенням бази FAQ його потрібно повторно перевірити на позитивних і негативних сценаріях.
- Частота невідомих питань об'єднується за однаковим нормалізованим текстом; різні за формулюванням питання про одну тему можуть залишитися окремими записами.
- Бронювання, оплата, авторизація, React-адмінпанель і бонусні функції не входять до поточного Core.
