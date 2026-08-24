# Meridian Voice Concierge

Core Voice Concierge: Backend API, PostgreSQL, 47 FAQ та окремий англомовний голосовий агент LiveKit із STT–LLM–TTS pipeline. Агент відповідає лише за даними FAQ, а невідомі питання записує для подальшого опрацювання.

Детальні обґрунтування архітектури наведені в `TECHNICAL_DECISIONS.md`, а
звірка з обов'язковими критеріями PRD — у `CORE_ACCEPTANCE.md`.

## Архітектура

```text
LiveKit Agent -> FastAPI -> service пошуку -> PostgreSQL
                         -> unanswered questions
Browser -> React Admin (Nginx) -> FastAPI admin API
```

FAQ-пошук гібридний. Backend створює локальні англійські embeddings моделлю `BAAI/bge-small-en-v1.5`, зберігає їх у PostgreSQL через `pgvector` і виконує cosine similarity search. Сильні точні та перевірені lexical-збіги мають пріоритет, а semantic retrieval обробляє нові природні перефразування. Якщо обидва механізми нижче відповідного порога, API повертає `matched: false`. Embedding-модель працює локально на CPU і не потребує API-ключа.

Для semantic результату також перевіряється відрив від другого кандидата. Якщо
два FAQ мають майже однакову оцінку, результат вважається неоднозначним і
повертається `matched: false`, щоб Agent не озвучував випадковий близький факт.

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

Під час першого Docker build завантажується локальна embedding-модель. Backend автоматично застосує Alembic-міграції, увімкне `pgvector` і безпечно повторить seed разом з embeddings. API буде доступний на `http://localhost:8000`, Swagger — на `http://localhost:8000/docs`, React-адмінпанель — на `http://localhost:3000`.

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
  "best_match": "When is the poker room open, and what games are available?",
  "answer": "The poker room is open 24/7...",
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

### Адміністрування FAQ (Bonus B1)

Ці endpoint-и дають змогу керувати записами FAQ без прямого доступу до бази
даних. Усі приклади нижче можна скопіювати до PowerShell після запуску
`docker compose up --build -d`. Поля `question`, `answer` і `category` є
обов'язковими: після обрізання пробілів кожне повинно містити щонайменше два
символи. API автоматично оновлює пошуковий embedding, тому не передавайте його
у JSON.

#### `GET /api/admin/faqs` — переглянути FAQ

```powershell
Invoke-RestMethod -Method Get `
  -Uri "http://localhost:8000/api/admin/faqs"
```

Приклад відповіді (масив відсортовано за `id`):

```json
[
  {
    "id": 48,
    "question": "Is late checkout available?",
    "answer": "Late checkout is subject to availability.",
    "category": "hotel",
    "created_at": "2026-08-24T12:00:00Z",
    "updated_at": "2026-08-24T12:00:00Z"
  }
]
```

#### `POST /api/admin/faqs` — створити FAQ

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/api/admin/faqs" `
  -ContentType "application/json" `
  -Body '{"question":"Is late checkout available?","answer":"Late checkout is subject to availability.","category":"hotel"}'
```

Успішне створення повертає `201 Created` і створений запис:

```json
{
  "id": 48,
  "question": "Is late checkout available?",
  "answer": "Late checkout is subject to availability.",
  "category": "hotel",
  "created_at": "2026-08-24T12:00:00Z",
  "updated_at": "2026-08-24T12:00:00Z"
}
```

#### `PUT /api/admin/faqs/{faq_id}` — оновити FAQ

Підставте фактичний `id` зі створеного або отриманого запису (у прикладі —
`48`). Запит замінює всі три текстові поля FAQ.

```powershell
Invoke-RestMethod -Method Put `
  -Uri "http://localhost:8000/api/admin/faqs/48" `
  -ContentType "application/json" `
  -Body '{"question":"Is late checkout available?","answer":"Late checkout is available on request, subject to availability.","category":"hotel"}'
```

Успішне оновлення повертає `200 OK` і запис з оновленим `updated_at`:

```json
{
  "id": 48,
  "question": "Is late checkout available?",
  "answer": "Late checkout is available on request, subject to availability.",
  "category": "hotel",
  "created_at": "2026-08-24T12:00:00Z",
  "updated_at": "2026-08-24T12:05:00Z"
}
```

#### `DELETE /api/admin/faqs/{faq_id}` — видалити FAQ

```powershell
Invoke-WebRequest -Method Delete `
  -Uri "http://localhost:8000/api/admin/faqs/48"
```

Успішне видалення повертає `204 No Content`, тобто тіло відповіді відсутнє.

#### Помилки адміністрування FAQ

- `404 Not Found` — FAQ з таким `faq_id` не існує. Відповідь:
  `{"detail":"FAQ not found"}`.
- `409 Conflict` — `question` уже є в іншому FAQ; дублікати питань не
  створюються. Відповідь: `{"detail":"FAQ question already exists"}`.
- `422 Unprocessable Entity` — JSON не відповідає правилам полів, наприклад
  поле пропущене, після обрізання пробілів закоротке, або `question` довше
  500 символів. Відповідь містить стандартний масив FastAPI `detail` з
  описом полів, які треба виправити.

### Черга запитань без відповіді (Bonus B2)

Переглянути відкриту чергу, відсортовану від найчастіших запитань:

```powershell
Invoke-RestMethod -Method Get `
  -Uri "http://localhost:8000/api/admin/unanswered"
```

Перетворити запитання на FAQ (підставте його фактичний `id`):

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/api/admin/unanswered/1/convert" `
  -ContentType "application/json" `
  -Body '{"answer":"Airport transfers can be arranged through the concierge.","category":"hotel"}'
```

Успішний convert повертає `201 Created`, створює пошуковий embedding і змінює
статус вихідного запитання на `converted`. Відхилити нерелевантне запитання:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/api/admin/unanswered/1/dismiss"
```

Dismiss повертає запис зі статусом `dismissed`. Оброблені записи більше не
показуються у відкритій черзі. Відсутній або вже оброблений запис повертає
`404`; спроба створити FAQ з наявним питанням повертає `409` і залишає запис
черги відкритим.

## React-адмінпанель (Bonus B3)

Після `docker compose up --build -d` відкрийте `http://localhost:3000`.

- **FAQ Library**: пошук, додавання, редагування та видалення FAQ.
- **Unanswered Queue**: частота невідомих запитань, Convert і Dismiss.
- **Voice Studio**: чотири голоси, прослуховування preview та вибір активного
  голосу для нових розмов.

Nginx усередині `admin` проксіює `/api` до Backend, тому frontend не містить
ключів або окремої адреси API. Production build автоматично запускає 15
компонентних тестів перед створенням статичних файлів. Окрема перевірка:

```powershell
docker compose build admin
Invoke-WebRequest http://localhost:3000/health
Invoke-RestMethod http://localhost:3000/api/admin/faqs
```

Вбудований Playground описаний нижче в розділі Bonus B5.

## Налаштування голосу (Bonus B4)

Voice Studio доступний на `http://localhost:3000`. Каталог фіксований вимогами
PRD і не потребує окремого Cartesia API-ключа:

- **James** — mature, warm British male; professional and refined;
- **Sofia** — friendly, elegant female with a light European accent;
- **Marcus** — confident, energetic, modern American male;
- **Elena** — calm, reassuring, clear American female.

Кнопка **Preview** відтворює однакове коротке речення попередньо згенерованим
MP3. Preview-файли зберігаються в репозиторії, не містять credentials і
віддаються Backend без runtime TTS-виклику. **Set active** змінює голос без
перезапуску сервісів. Нова настройка застосовується лише до нових LiveKit
сесій; уже відкрита розмова зберігає свій голос до завершення.

Переглянути каталог:

```powershell
Invoke-RestMethod "http://localhost:8000/api/admin/voices"
```

Активувати голос, використовуючи його фактичний `id`:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8000/api/admin/voices/3/activate"
```

Приклад відповіді браузерного API — без provider voice ID:

```json
{
  "id": 3,
  "name": "Marcus",
  "description": "Confident, energetic, modern American male.",
  "is_active": true,
  "preview_url": "/api/admin/voices/3/preview",
  "updated_at": "2026-08-24T12:00:00Z"
}
```

Agent отримує runtime-конфігурацію окремим внутрішнім маршрутом:

```powershell
Invoke-RestMethod "http://localhost:8000/api/voice/active"
```

```json
{
  "name": "Marcus",
  "provider_voice_id": "a167e0f3-df7e-4d52-a9c3-f949145efdab",
  "updated_at": "2026-08-24T12:00:00Z"
}
```

Якщо Backend тимчасово недоступний на початку нової сесії, Agent використовує
локальний `TTS_VOICE` з `.env` як fallback. Інтегрований у власний frontend
Voice Studio керує голосом, який використовуватимуть нові сесії у вбудованому
Playground.

## Інтегрований Playground (Bonus B5)

Після `docker compose up --build -d` відкрийте `http://localhost:3000` і
виберіть **Playground**. Це чітко позначений тестовий режим адміністратора, а
не гостьовий інтерфейс.

1. Натисніть **Start session** і дозвольте браузеру доступ до мікрофона.
2. Дочекайтеся стану **Listening** та поставте питання англійською.
3. Під час розмови інтерфейс показує **Listening**, **Thinking** або
   **Speaking**, активний голос і останню знайдену FAQ-відповідь.
4. Натисніть **End session** для завершення. Нову сесію можна почати без
   перезавантаження сторінки.

Frontend запитує у Backend короткочасний, прив'язаний до окремої кімнати
LiveKit token. `LIVEKIT_API_SECRET` ніколи не передається у React bundle і не
зберігається у браузері.

Якщо сесія не починається:

- перевірте, що локальний `.env` містить `LIVEKIT_URL`, `LIVEKIT_API_KEY` і
  `LIVEKIT_API_SECRET`, а всі сервіси в `docker compose ps` мають стан healthy;
- для помилки мікрофона дозвольте доступ у налаштуваннях сайту браузера та
  натисніть Start ще раз;
- якщо браузер блокує звук, взаємодійте зі сторінкою і дозвольте autoplay/audio;
- якщо з'єднання є, але агент не відповідає, перевірте
  `docker compose logs --tail 100 agent` і доступність LiveKit Cloud/Inference.

## Корисні команди

```powershell
docker compose config
docker compose run --rm backend pytest -q
docker compose run --rm agent pytest -q
docker compose build admin
docker compose exec -T db psql -U meridian -d meridian -c "SELECT name, is_active FROM voice_configs ORDER BY id;"
docker compose run --rm -e RUN_POSTGRES_INTEGRATION=1 backend pytest -q tests/test_postgres_concurrency.py
docker compose run --rm -e RUN_POSTGRES_INTEGRATION=1 backend pytest -q tests/test_faq_admin_postgres.py
docker compose down
docker compose down -v  # також видаляє локальні дані PostgreSQL
```

Справжні LiveKit credentials потрібні лише для голосового запуску й не повинні потрапляти до Git. Окремі ключі провайдерів STT/LLM/TTS не потрібні при використанні LiveKit Inference.

## Голосовий агент

1. Вкажіть `LIVEKIT_URL`, `LIVEKIT_API_KEY` і `LIVEKIT_API_SECRET` у локальному `.env`.
2. Запустіть весь Core: `docker compose up --build`.
3. У LiveKit Agent Console почніть сесію з агентом `meridian-concierge`.

Агент приймає та озвучує лише англійську мову. Якщо гість говорить іншою мовою, агент просить повторити питання англійською. Вбудовані FAQ та весь контент React-адмінпанелі зберігаються і відображаються англійською.

Моделі можна змінити через `STT_MODEL`, `LLM_MODEL` і `TTS_MODEL` без
редагування коду. `TTS_VOICE` тепер є лише локальним fallback: за нормальної
роботи активний голос читається з Backend для кожної нової сесії. Для
локального текстового запуску агента використайте `python -m app.main console`
з каталогу `agent`.

## Перевірка чистого запуску

Увага: `down -v` безповоротно видаляє локальну базу та всі записані невідомі питання.

```powershell
docker compose down -v --remove-orphans
docker compose up --build -d
docker compose ps
docker compose exec db psql -U meridian -d meridian -c "SELECT COUNT(*) FROM faqs;"
```

Усі чотири сервіси мають бути `healthy`, а кількість FAQ — `47`.

Команду `docker compose down -v` використовуйте лише коли записані unknown-питання
більше не потрібні. Для звичайного перезапуску достатньо `docker compose down`,
який зберігає PostgreSQL volume.

## Відомі обмеження Core

- Голосова сесія потребує інтернету, LiveKit Cloud credentials і доступності LiveKit Inference.
- Semantic threshold відкалібровано на контрольному наборі Core; перед суттєвим розширенням бази FAQ його потрібно повторно перевірити на позитивних і негативних сценаріях.
- Частота невідомих питань об'єднується за однаковим нормалізованим текстом; різні за формулюванням питання про одну тему можуть залишитися окремими записами.
- Бронювання, оплата й авторизація не входять до завдання. Playground є
  локальним адміністративним Test Mode і навмисно не має авторизації в межах PRD.
