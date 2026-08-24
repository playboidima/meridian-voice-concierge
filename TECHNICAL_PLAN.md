# Технічний план Core

## Етап 1 — готово

- FastAPI Backend із `GET /health`, `POST /api/faq/search` і `POST /api/unanswered`.
- PostgreSQL у Docker Compose, SQLAlchemy-моделі та Alembic-міграція.
- Повторно безпечний seed із 47 FAQ з розділів 7.1–7.7 PRD та одним
  погодженим додатковим FAQ про EV charging.
- Локальний пошук із порогом та стабільним JSON-контрактом.
- Тести health, валідації, match/no-match, нормалізації, агрегації та сценаріїв PRD.

## Етап 2 — готово

- Додано окремий Python-сервіс `agent` на LiveKit Agents.
- STT, LLM і TTS працюють через LiveKit Inference та налаштовуються змінними середовища.
- Агент має один інструмент: пошук FAQ, який автоматично записує питання лише
  тоді, коли надійної відповіді немає. Це не дозволяє мовній моделі забути
  записати unknown-запит або записати відоме питання.
- Agent Console підключається до агента з ім'ям `meridian-concierge`.
- Голосові сценарії перевірені через LiveKit Playground після додавання
  користувачем власних credentials у локальний `.env`.

## Етап 3 — готово

- Додано тайм-аут Backend API та безпечну обробку його недоступності: агент
  не вигадує відповідь і не стверджує, що unknown-запит записано, якщо запис не вдався.
- Агент працює лише англійською і передає до пошуку оригінальне англійське
  формулювання без перекладу.
- Невідоме питання записується детерміновано одним Backend workflow.

## Етап 4 — готово

- Локальний semantic search використовує FastEmbed і `pgvector`, не потребує
  зовнішнього API-ключа та зберігає поточний API-контракт.
- Hybrid search поєднує перевірені lexical-збіги із semantic retrieval.
- `frequency` для однакових unknown-запитів оновлюється атомарно в PostgreSQL.
- Конкурентний integration-тест перевіряє 50 одночасних однакових запитів.

## Етап 5 — готово

- Перевірити міграції та seed на окремій порожній PostgreSQL-базі без видалення
  робочих даних користувача.
- Перебудувати та запустити систему через Docker Compose.
- Запустити Backend, Agent та PostgreSQL integration-тести.
- Перевірити health-check, кількість FAQ, embeddings і основні API-сценарії.

## Етап 6 — готово

- Повторно звірити реалізацію з обов'язковими критеріями PRD.
- Додати окремий документ ключових технічних рішень.
- Додати Core acceptance checklist із доказами автоматичних і ручних перевірок.
- Перевірити відсутність секретів та виконати фінальну регресію.

Bonus почався лише після проходження всіх Core-критеріїв.

## Bonus B1 — ready for manual review

## Bonus B2 — ready for manual review

- Відкрита черга unknown-запитань сортується за частотою та останньою появою.
- Запитання можна атомарно перетворити на FAQ з новим пошуковим embedding.
- Нерелевантне запитання можна позначити як `dismissed`.
- Для відсутніх записів і дублікатів FAQ повертаються стабільні `404`/`409`.

## Bonus B3 — ready for manual review

- React-панель на `http://localhost:3000` керує FAQ та unanswered queue.
- Nginx віддає production bundle і без CORS-змін проксіює `/api` до Backend.
- FAQ підтримують пошук, create, edit і підтверджене delete.
- Queue підтримує frequency, Convert і підтверджене Dismiss.
- П'ять component tests запускаються під час Docker build; desktop і narrow
  layouts перевірені в браузері.

## Bonus B4 — complete

- Додано чотири перевірені PRD-голоси та реальні MP3 preview.
- PostgreSQL і Backend API гарантують рівно один активний голос.
- Agent читає активний голос для кожної нової LiveKit-сесії без перезапуску.
- Англомовний Voice Studio відтворює preview та перемикає активний голос.
- Дев'ять component tests запускаються під час Admin Docker build; desktop і
  mobile layouts перевірені в браузері без overflow та console errors.
- Фінальний no-restart acceptance підтвердив Marcus → Elena для нових LiveKit
  сесій, усі чотири preview, known FAQ та безпечний unknown-flow.
- Доданий semantic ambiguity guard і regression-тест не дозволяють telescope
  rental помилково збігатися з FAQ про helicopter tours.

## Bonus B5 — complete

- Backend безпечно видає короткочасні room-scoped LiveKit tokens.
- Англомовний Playground в адмінпанелі має Start/End, мікрофон, remote audio,
  стани з'єднання й агента, активний голос та останню FAQ-відповідь.
- Повторний старт працює без перезавантаження, а unmount завершує сесію.
- Component tests перевіряють UI, token/start/end/error flow і regression для
  передчасного disconnect під час rerender.
- Ручна браузерна перевірка підтвердила успішну голосову сесію після виправлення
  session lifecycle.
