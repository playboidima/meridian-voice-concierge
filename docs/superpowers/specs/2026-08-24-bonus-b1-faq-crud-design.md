# Bonus B1: FAQ Admin CRUD Design

## Мета

Додати до чинного FastAPI Backend адміністративні CRUD-ендпоїнти для FAQ,
не змінюючи контракти Core API або поведінку голосового агента. Створені чи
оновлені FAQ мають одразу отримувати embedding і брати участь у hybrid search.

## Межі етапу

Етап включає:

- список усіх FAQ;
- створення FAQ;
- повне оновлення FAQ;
- видалення FAQ;
- автоматичний перерахунок embedding після create/update;
- unit/API та PostgreSQL integration-тести;
- документацію API.

Етап не включає React UI, авторизацію, pagination, unanswered queue, voice
configuration або Playground. Ці можливості належать наступним Bonus-етапам.

## API-контракт

### `GET /api/admin/faqs`

Повертає масив FAQ, відсортований за `id` за зростанням. Для поточного обсягу
в 47 записів pagination не додається.

Успішна відповідь: `200 OK`.

### `POST /api/admin/faqs`

Приймає:

```json
{
  "question": "Do you provide airport transportation?",
  "answer": "The Meridian does not currently provide an airport shuttle.",
  "category": "hotel"
}
```

Перед збереженням текстові поля обрізаються по краях. Порожні поля не
допускаються. Після валідації Backend обчислює embedding через наявний
FastEmbed service і зберігає FAQ однією транзакцією.

Успішна відповідь: `201 Created`. Якщо `question` уже існує: `409 Conflict`.

### `PUT /api/admin/faqs/{faq_id}`

Виконує повну заміну `question`, `answer` і `category`. Backend завжди
перераховує embedding, оскільки будь-яке з цих полів впливає на semantic
passage. `updated_at` оновлюється під час транзакції.

Успішна відповідь: `200 OK`. Невідомий `faq_id`: `404 Not Found`. Конфлікт
із питанням іншого FAQ: `409 Conflict`.

### `DELETE /api/admin/faqs/{faq_id}`

Видаляє FAQ і його embedding тією самою транзакцією.

Успішна відповідь: `204 No Content`. Невідомий `faq_id`: `404 Not Found`.

### Response model

```json
{
  "id": 48,
  "question": "Do you provide airport transportation?",
  "answer": "The Meridian does not currently provide an airport shuttle.",
  "category": "hotel",
  "created_at": "2026-08-24T12:00:00Z",
  "updated_at": "2026-08-24T12:00:00Z"
}
```

Внутрішнє поле `embedding` до API-відповіді не входить.

## Структура коду

- `backend/app/schemas.py`: `FAQAdminWrite` та `FAQAdminResponse`.
- `backend/app/services/faq_admin.py`: CRUD-операції, embedding і перетворення
  database conflicts на окрему service-помилку.
- `backend/app/main.py`: тонкі HTTP handlers для `/api/admin/faqs`.
- `backend/tests/test_faq_admin_api.py`: швидкі API-тести через SQLite й
  dependency override.
- `backend/tests/test_faq_admin_postgres.py`: opt-in integration-тест проти
  запущеного PostgreSQL Backend з автоматичним очищенням тестових записів.

Окремий router поки не додається: чотири handlers не роблять `main.py`
надмірним. Якщо наступні Bonus-етапи суттєво збільшать admin API, маршрути
будуть винесені в router окремим затвердженим рефакторингом.

## Data flow

```text
Admin request
    -> Pydantic validation and trimming
    -> faq_admin service
    -> FastEmbed embedding calculation
    -> SQLAlchemy transaction
    -> FAQAdminResponse without embedding
```

Після commit чинний `/api/faq/search` читає той самий PostgreSQL row, тому
новий або оновлений FAQ доступний агенту без перезапуску чи окремої індексації.

## Обробка помилок

- Pydantic повертає `422` для коротких або порожніх значень.
- Service перевіряє наявність `faq_id` і повертає контрольований not-found
  результат, який handler перетворює на `404`.
- PostgreSQL/SQLite unique conflict робить rollback і перетворюється на `409`.
- Неочікувані database або embedding-помилки не маскуються як успіх;
  транзакція відкочується, а FastAPI повертає server error.

## Тестування

Реалізація виконується через TDD:

1. API-тести спочатку підтверджують відсутність маршрутів.
2. Create-тест перевіряє `201`, trimming і response без embedding.
3. Duplicate-тест перевіряє `409` та відсутність другого row.
4. Update-тест перевіряє зміну даних і embedding.
5. Delete-тест перевіряє `204` та подальший `404`.
6. PostgreSQL integration створює унікальний FAQ, знаходить його через Core
   search, оновлює, повторно знаходить і видаляє у `finally`.
7. Після B1 запускаються повні Backend, Agent і concurrency regression suites.

## Критерії завершення B1

- чотири admin CRUD endpoints відповідають описаному контракту;
- create/update автоматично зберігають 384-вимірний embedding;
- зміни доступні Core search без перезапуску;
- помилки мають стабільні HTTP-коди `404`, `409`, `422`;
- integration-тести не залишають службових FAQ у базі;
- Core test suites залишаються зеленими;
- README містить приклади нових API-викликів.
