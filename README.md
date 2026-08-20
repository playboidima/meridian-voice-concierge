# Meridian Voice Concierge

Core Voice Concierge: Backend API, PostgreSQL, 47 FAQ та окремий голосовий агент LiveKit із STT–LLM–TTS pipeline. Агент відповідає лише за даними FAQ, а невідомі питання записує для подальшого опрацювання.

## Архітектура

```text
LiveKit Agent -> FastAPI -> service пошуку -> PostgreSQL
                         -> unanswered questions
```

Пошук зараз локальний і детермінований: текст нормалізується, поширені слова-синоніми зводяться до спільних понять, після чого оцінюється перетин слів і схожість фраз. Якщо оцінка нижча за поріг, API повертає `matched: false`. Це дозволяє працювати без зовнішніх ключів; пізніше реалізацію можна замінити на embeddings без зміни API.

## Запуск

1. Скопіюйте `.env.example` у `.env` (для локального демо можна залишити наведені тестові значення PostgreSQL).
2. Запустіть:

```bash
docker compose up --build
```

Під час старту Backend автоматично застосує Alembic-міграції та безпечно повторить seed. API буде доступний на `http://localhost:8000`, Swagger — на `http://localhost:8000/docs`.

Перевірка:

```bash
curl http://localhost:8000/health
docker compose run --rm backend pytest
```

## API

### `GET /health`

Запит:

```bash
curl http://localhost:8000/health
```

Відповідь:

```json
{"status":"ok","database":"ok"}
```

### `POST /api/faq/search`

Запит:

```bash
curl -X POST http://localhost:8000/api/faq/search \
  -H "Content-Type: application/json" \
  -d '{"question":"Покерна кімната зараз відкрита?"}'
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

```bash
curl -X POST http://localhost:8000/api/unanswered \
  -H "Content-Type: application/json" \
  -d '{"question":"Чи можна приїхати із собакою?"}'
```

Відповідь (повторний нормалізований запит збільшує `frequency`):

```json
{
  "id": 1,
  "original_question": "Чи можна приїхати із собакою?",
  "normalized_question": "можна приїхати із собакою",
  "frequency": 1,
  "status": "open",
  "first_seen_at": "2026-08-20T12:00:00Z",
  "last_seen_at": "2026-08-20T12:00:00Z"
}
```

## Корисні команди

```bash
docker compose config
docker compose down
docker compose down -v  # також видаляє локальні дані PostgreSQL
```

Справжні LiveKit credentials потрібні лише для голосового запуску й не повинні потрапляти до Git. Окремі ключі провайдерів STT/LLM/TTS не потрібні при використанні LiveKit Inference.

## Голосовий агент

1. Вкажіть `LIVEKIT_URL`, `LIVEKIT_API_KEY` і `LIVEKIT_API_SECRET` у локальному `.env`.
2. Запустіть весь Core: `docker compose up --build`.
3. У LiveKit Agent Console почніть сесію з агентом `meridian-concierge`.

Моделі можна змінити через `STT_MODEL`, `LLM_MODEL`, `TTS_MODEL` і `TTS_VOICE` без редагування коду. Для локального текстового запуску агента використайте `python -m app.main console` з каталогу `agent`.
