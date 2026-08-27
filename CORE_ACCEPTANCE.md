# Core and Bonus acceptance checklist

## Повторне приймання — 27 August 2026

Цей розділ містить актуальні результати після виправлень аудиту; результати
24 August нижче залишені як історія, а не новий запуск тестів.

- Backend: **142 passed, 0 skipped**, включно з усіма opt-in PostgreSQL tests.
- Agent: **16 passed, 0 skipped**, включно з реальною взаємодією з тестовим API.
- Admin: **17 passed**; свіжий production build успішний. Vite попереджає про
  JS bundle 776.13 kB (gzip 213.34 kB); це не помилка збірки.
- Окремий Compose-проєкт `meridian-final-audit-20260827` з новим volume, без
  робочих даних і ключів: міграція `20260827_06`, 48 FAQ/embeddings, 4 голоси.
- Після CRUD, Convert, Dismiss і restart backend зміни та видалення збереглися;
  початкові FAQ не відновилися. Повторний `up` успішний.
- Робоча система: усі 4 контейнери healthy, backend health ok, admin HTTP 200,
  усі 4 різні preview доступні, рівно один активний голос. Живі записи не змінювалися.
- `.env` і `.venv` ignored; tracked `.env`/dump/key/pem не знайдено, staged list
  порожній. 104 tracked/unignored файли перевірено на збіги зі значеннями локальних
  секретів довжиною від 12 символів: збігів немає. Це не повний аудит історії Git.
- Користувач підтвердив етап 5: голосову сесію, перепідключення та зміну голосу.
  Нові розмови з кожним із чотирьох голосів автоматично не виконувались;
  після фінального етапу користувач окремо підтвердив їх ручну перевірку.
- Пошук консервативний: незнайомі перефразування можуть давати false negative;
  тести не є гарантією відсутності помилок для всіх можливих питань.
- Граничні тести 1000 символів покривають ASCII/англомовний сценарій. Питання з
  великою кількістю рідкісних багатобайтових Unicode-символів можуть перевищити
  байтовий ліміт UNIQUE B-tree індексу PostgreSQL і не зберегтися. Це відтворено
  окремо в тестовій транзакції; універсальна Unicode-підтримка потребує зміни
  індексу/валідації та не є підтвердженою властивістю цієї версії.
- Гілка виправлень: `codex/audit-fixes`. Користувач дозволив публікацію та
  злиття у `main`. Для запуску потрібен main із цими виправленнями;
  попередня версія main містить стару реалізацію seed.

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
| KB-1: FAQ про комплекс | Пройдено | 47 seed FAQ з розділів 7.1-7.7 PRD і 1 погоджений додатковий EV charging FAQ |
| KB-2: пошук за змістом | Пройдено | FastEmbed + pgvector, unseen paraphrase-тести |
| KB-3: unknown із timestamp | Пройдено | `first_seen_at`, `last_seen_at` у моделі та міграції |
| KB-4: frequency unknown | Пройдено | Atomic upsert; 50 паралельних запитів дають frequency 50 |
| KB-5: початкові дані | Пройдено | Clean-DB перевірка PRD: 47 FAQ/embeddings; після погодженого розширення каталог містить 48 FAQ |
| API-1: FAQ search endpoint | Пройдено | `POST /api/faq/search` та API-тести |
| API-2: unanswered endpoint | Пройдено | `POST /api/unanswered` та API-тести |
| API-3: match/no-match контракт | Пройдено | Позитивні й негативні regression-тести |
| AP-1: список FAQ для адміністратора | Пройдено | React `FAQ Library` використовує `GET /api/admin/faqs`; Backend і React component tests перевіряють список, пошук та відсутність embedding |
| AP-2: створення FAQ з пошуковим embedding | Пройдено | `POST /api/admin/faqs`; unit-тести перевіряють `201`, trimming, `422` і `409`, а opt-in PostgreSQL test перевіряє 384-вимірний embedding і пошук створеного FAQ |
| AP-3: оновлення FAQ та пошуку | Пройдено | `PUT /api/admin/faqs/{faq_id}`; unit-тести перевіряють `200`, recompute embedding, `404`, `409` і rollback, а opt-in PostgreSQL test знаходить оновлену відповідь |
| AP-4: видалення FAQ | Пройдено | `DELETE /api/admin/faqs/{faq_id}`; unit-тест перевіряє `204` без тіла та наступний `404`, а opt-in PostgreSQL lifecycle test видаляє створений FAQ і підтверджує cleanup |
| AP-5: перегляд черги unknown | Пройдено | `GET /api/admin/unanswered`; API-тест перевіряє лише відкриті записи та порядок за `frequency` |
| AP-6: відображення frequency | Пройдено | Відповідь черги містить `frequency`, timestamps і status; API-тест перевіряє значення та сортування |
| AP-7: перетворення unknown на FAQ | Пройдено | `POST /api/admin/unanswered/{id}/convert`; тест перевіряє FAQ, 384-вимірний embedding, статус `converted` і rollback при дублікаті |
| AP-8: відхилення unknown | Пройдено | `POST /api/admin/unanswered/{id}/dismiss`; тест перевіряє статус `dismissed`, зникнення з відкритої черги та `404` |
| AP-9: список чотирьох голосів | Пройдено | `GET /api/admin/voices`, API tests і Voice Studio показують James, Sofia, Marcus, Elena в PRD-порядку |
| AP-10: описи голосів | Пройдено | Фіксований каталог, API literal tests і чотири англомовні картки Voice Studio |
| AP-11: вибір активного голосу | Пройдено (manual) | Voice Studio переносить єдиний active badge; user-перевірка Sofia без restart |
| AP-12: preview голосів | Пройдено (manual) | Чотири distinct MP3, asset tests і user listening review |
| VX-1: чотири PRD-голоси | Пройдено (manual) | James, Sofia, Marcus, Elena з перевіреними LiveKit/Cartesia voice IDs |
| VX-2: адміністратор обирає голос | Пройдено (manual) | Voice Studio `Set active` і `POST /api/admin/voices/{id}/activate` |
| VX-3: зміна для нової розмови | Пройдено (manual) | Agent читає `/api/voice/active` на початку job; user-перевірка James → Sofia |
| VX-4: прослуховування preview | Пройдено (manual) | Preview/Stop preview, однаковий текст і автоматична зупинка попереднього audio |
| NF-3: desktop admin usability | Пройдено (manual) | Responsive React layout, component tests, browser QA і user review Voice Studio |
| NF-5: voice change without restart | Пройдено (manual) | PostgreSQL activation + нова LiveKit сесія Sofia без перезапуску Docker |
| AP-13: Playground у власній адмінпанелі | Пройдено | React `Playground`, navigation/component tests і production build |
| AP-14: активний голос та остання FAQ | Пройдено | `/api/voice/active`, LiveKit session messages і component tests |
| AP-15: повна голосова розмова | Пройдено (manual) | Користувач підтвердив успішну сесію у вбудованому Playground після lifecycle fix |
| AP-16: чіткий Test Mode | Пройдено | Заголовки `Playground` і `Test Mode`; component test |
| PG-1: запуск у браузері | Пройдено (manual) | `http://localhost:3000` → Playground |
| PG-2: доступ до мікрофона | Пройдено (manual) | Browser permission і успішний voice input |
| PG-3: відтворення відповіді | Пройдено (manual) | LiveKit remote audio у вбудованій сесії |
| PG-4: візуальні стани | Пройдено | Disconnected/Connecting/Listening/Thinking/Speaking UI та component tests |
| PG-5: Start/End | Пройдено (manual) | Start, End, cleanup, reconnect tests і ручна повторна сесія |
| NF-1: розмовна голосова відповідь | Пройдено (manual) | Голосові сценарії; окремий latency benchmark PRD не задає |
| NF-2: локальний Docker-запуск | Пройдено | `docker compose up --build`; усі сервіси healthy |
| NF-4: преміальний тон | Пройдено (manual) | Prompt і голосова перевірка |
| Core deliverable: README | Пройдено | Налаштування, API, запуск, тести, clean start і обмеження |
| Core deliverable: технічні рішення | Пройдено | `TECHNICAL_DECISIONS.md` |
| Без вигаданих фактів | Пройдено | Unknown-набір, threshold tests і manual-перевірка |
| Секрети не в репозиторії | Пройдено | `.env` ignored; `.env.example` не містить ключів |

## Фінальні автоматичні команди

Нижче лише unit/component перевірки для вже інтегрованої актуальної гілки.
Opt-in PostgreSQL тести змінюють дані: їх слід запускати **тільки на окремому
тестовому Compose-проєкті** з явними `INTEGRATION_BACKEND_URL`,
`INTEGRATION_DATABASE_URL`, `SEED_TEST_DATABASE_URL`, не на робочій БД.

```powershell
docker compose up --build -d
docker compose ps
docker compose run --rm backend pytest -q
docker compose run --rm agent pytest -q
docker compose build --no-cache admin
docker compose exec -T db psql -U meridian -d meridian -c "SELECT COUNT(*) AS voices, COUNT(*) FILTER (WHERE is_active) AS active FROM voice_configs;"
Invoke-RestMethod http://localhost:8000/health
```

## Bonus B4 final acceptance — 24 August 2026

- Користувач прослухав усі чотири preview у Voice Studio.
- Marcus активовано, і нова LiveKit-сесія почала розмову голосом Marcus.
- Elena активовано без перезапуску Docker, і наступна нова сесія почала
  розмову голосом Elena. PostgreSQL підтвердив Elena як єдиний active row.
- Відоме питання про poker room повернуло підтверджену відповідь `24/7`.
- Перша telescope rental перевірка виявила semantic false positive до
  helicopter tours. Після TDD-виправлення ambiguity margin точний regression
  повертає `matched: false`; Agent workflow записав unknown з
  `unanswered_recorded: true`, після чого тестовий запис `id 457` позначено
  `dismissed`, щоб він не засмічував відкриту чергу.
- Фінальні suites: Backend `49 passed, 3 skipped`, Agent `12 passed`, Admin
  `9 passed`; PostgreSQL voice concurrency `1 passed`; усі сервіси healthy.

## Bonus B5 final acceptance — 24 August 2026

- Вбудований англомовний Playground доступний з навігації адмінпанелі.
- Backend створює 10-хвилинний token для окремої кімнати без передачі secret у
  frontend; unit-тести перевіряють claims і помилки конфігурації.
- React-тести перевіряють Start/End, media UI, active voice, error/retry, cleanup
  та regression: rerender більше не завершує сесію під час підключення.
- Користувач вручну підтвердив, що після виправлення lifecycle голосова сесія
  успішно запускається і агент відповідає.
- Реальні browser media та provider calls залежать від локальних credentials,
  дозволу мікрофона, інтернету й LiveKit Cloud; unit-тести самі по собі не можуть
  довести роботу цих зовнішніх складових.

## Межа приймання

Матриця охоплює завершені Core і Bonus B1–B5. Бронювання, платежі,
авторизація та production deployment залишаються поза межами завдання.
