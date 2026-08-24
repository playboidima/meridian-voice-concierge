# Core acceptance checklist

Матриця звіряє реалізацію з обов'язковою частиною PRD. Позначка `manual`
означає, що критерій перевірено користувачем у LiveKit Playground.

| Критерій PRD | Статус | Доказ |
|---|---|---|
| VC-1: розмова через вебінтерфейс | Пройдено (manual) | LiveKit Agents Playground, нові сесії запускаються |
| VC-2: природна мова | Пройдено | Англійські semantic і paraphrase-тести |
| VC-3: пошук у базі знань | Пройдено | `POST /api/faq/search`, hybrid search |
| VC-4: озвучення знайденої відповіді | Пройдено (manual) | STT-LLM-TTS сесія в Playground |
| VC-5: fallback і запис unknown | Пройдено | Agent unit-тести, API/DB integration-тест і manual-перевірка |
| VC-6: теплий професійний тон | Пройдено (manual) | System prompt і голосові сценарії |
| KB-1: FAQ про комплекс | Пройдено | 47 seed FAQ з розділів 7.1-7.7 |
| KB-2: пошук за змістом | Пройдено | FastEmbed + pgvector, unseen paraphrase-тести |
| KB-3: unknown із timestamp | Пройдено | `first_seen_at`, `last_seen_at` у моделі та міграції |
| KB-4: frequency unknown | Пройдено | Atomic upsert; 50 паралельних запитів дають frequency 50 |
| KB-5: початкові дані | Пройдено | Clean-DB перевірка: 47 FAQ, 47 embeddings |
| API-1: FAQ search endpoint | Пройдено | `POST /api/faq/search` та API-тести |
| API-2: unanswered endpoint | Пройдено | `POST /api/unanswered` та API-тести |
| API-3: match/no-match контракт | Пройдено | Позитивні й негативні regression-тести |
| PG-1-PG-5: browser, mic, audio, status, Start/End | Пройдено (manual) | LiveKit Agents Playground |
| NF-1: розмовна голосова відповідь | Пройдено (manual) | Голосові сценарії; окремий latency benchmark PRD не задає |
| NF-2: локальний Docker-запуск | Пройдено | `docker compose up --build`; усі сервіси healthy |
| NF-4: преміальний тон | Пройдено (manual) | Prompt і голосова перевірка |
| Core deliverable: README | Пройдено | Налаштування, API, запуск, тести, clean start і обмеження |
| Core deliverable: технічні рішення | Пройдено | `TECHNICAL_DECISIONS.md` |
| Без вигаданих фактів | Пройдено | Unknown-набір, threshold tests і manual-перевірка |
| Секрети не в репозиторії | Пройдено | `.env` ignored; `.env.example` не містить ключів |

## Фінальні автоматичні команди

```powershell
docker compose up --build -d
docker compose ps
docker compose run --rm backend pytest -q
docker compose run --rm agent pytest -q
docker compose run --rm -e RUN_POSTGRES_INTEGRATION=1 backend pytest -q tests/test_postgres_concurrency.py
Invoke-RestMethod http://localhost:8000/health
```

## Межа приймання

Матриця охоплює лише Core. NF-3, NF-5, AP-* і VX-* належать до Bonus та не є
блокерами здачі основної частини.
