# Bonus B1 FAQ Admin CRUD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Додати перевірений admin CRUD для FAQ, який автоматично підтримує embeddings і не змінює Core API.

**Architecture:** Тонкі FastAPI handlers викликають окремий `faq_admin` service. Service володіє SQLAlchemy-транзакціями, обчисленням embedding і domain-помилками; Pydantic schemas виконують trimming та валідацію. Швидкі API-тести використовують SQLite, а окремий opt-in integration-тест перевіряє повний lifecycle у PostgreSQL і Core search.

**Tech Stack:** Python 3.12, FastAPI 0.116.1, SQLAlchemy 2.0.43, Pydantic v2, PostgreSQL 16, pgvector, FastEmbed, pytest, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-08-24-bonus-b1-faq-crud-design.md`

## Global Constraints

- Не змінювати контракти `GET /health`, `POST /api/faq/search` або `POST /api/unanswered`.
- Не додавати авторизацію, React, pagination, unanswered admin API або voice configuration у B1.
- Не повертати поле `embedding` в HTTP response.
- Create/update завжди зберігають 384-вимірний embedding до commit.
- Duplicate question повертає `409`; невідомий ID — `404`; невалідний body — `422`.
- Кожен implementation task виконується red-green-refactor і завершується окремим комітом.
- `.env` та LiveKit credentials не додаються до Git.

---

### Task 1: Admin schemas і read-only FAQ list

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_faq_admin_api.py`

**Interfaces:**
- Consumes: SQLAlchemy model `app.models.FAQ`, dependency `app.db.get_db`.
- Produces: `FAQAdminWrite`, `FAQAdminResponse`, `GET /api/admin/faqs`.

- [ ] **Step 1: Написати failing tests для list і validation schema**

```python
from app.schemas import FAQAdminWrite


def test_admin_faq_list_is_sorted_and_hides_embedding(client):
    response = client.get("/api/admin/faqs")
    body = response.json()

    assert response.status_code == 200
    assert [item["id"] for item in body] == sorted(item["id"] for item in body)
    assert body
    assert "embedding" not in body[0]
    assert set(body[0]) == {
        "id", "question", "answer", "category", "created_at", "updated_at"
    }


def test_admin_faq_write_strips_fields_and_rejects_blank_values():
    payload = FAQAdminWrite(
        question="  Is breakfast available?  ",
        answer="  Breakfast is served daily.  ",
        category="  dining  ",
    )
    assert payload.question == "Is breakfast available?"
    assert payload.answer == "Breakfast is served daily."
    assert payload.category == "dining"
```

Task 2 extends this file with the following exact validation cases after the
POST route exists:

```python
@pytest.mark.parametrize(
    "payload",
    [
        {"question": " ", "answer": "Valid answer", "category": "hotel"},
        {"question": "Valid question", "answer": " ", "category": "hotel"},
        {"question": "Valid question", "answer": "Valid answer", "category": " "},
    ],
)
def test_admin_faq_rejects_blank_fields(client, payload):
    response = client.post("/api/admin/faqs", json=payload)
    assert response.status_code == 422
```

- [ ] **Step 2: Запустити тести й підтвердити правильний RED**

Run:

```powershell
docker compose run --rm backend pytest -q tests/test_faq_admin_api.py
```

Expected: collection fails because `FAQAdminWrite` is not defined or list route returns `404`.

- [ ] **Step 3: Додати schemas**

```python
class FAQAdminWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=2, max_length=500)
    answer: str = Field(min_length=2)
    category: str = Field(min_length=2, max_length=100)


class FAQAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    answer: str
    category: str
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 4: Додати list handler**

```python
@app.get("/api/admin/faqs", response_model=list[FAQAdminResponse])
def list_admin_faqs(db: Session = Depends(get_db)) -> list[FAQ]:
    return list(db.scalars(select(FAQ).order_by(FAQ.id)))
```

Import `FAQ`, `select`, and the two admin schemas explicitly.

- [ ] **Step 5: Запустити focused і Core API tests**

```powershell
docker compose build backend
docker compose run --rm backend pytest -q tests/test_faq_admin_api.py tests/test_api.py
```

Expected: list/schema tests pass; existing Core API tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/schemas.py backend/app/main.py backend/tests/test_faq_admin_api.py
git commit -m "feat: add FAQ admin list contract"
```

---

### Task 2: FAQ create service і endpoint

**Files:**
- Create: `backend/app/services/faq_admin.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_faq_admin_api.py`

**Interfaces:**
- Consumes: `FAQAdminWrite`, `FAQ`, `embed_passage(text)`, `faq_embedding_text(question, answer, category)`.
- Produces: `FAQConflictError`, `create_faq(db, payload) -> FAQ`, `POST /api/admin/faqs`.

- [ ] **Step 1: Написати failing create, validation і duplicate tests**

```python
def test_admin_can_create_faq(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.faq_admin.embed_passage", lambda text: [0.25] * 384
    )
    response = client.post(
        "/api/admin/faqs",
        json={
            "question": "  Is breakfast available?  ",
            "answer": "  Breakfast is served daily.  ",
            "category": "  dining  ",
        },
    )
    body = response.json()

    assert response.status_code == 201
    assert body["question"] == "Is breakfast available?"
    assert body["answer"] == "Breakfast is served daily."
    assert body["category"] == "dining"
    assert "embedding" not in body


def test_duplicate_admin_faq_returns_409(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.faq_admin.embed_passage", lambda text: [0.25] * 384
    )
    payload = {
        "question": "Is breakfast available?",
        "answer": "Breakfast is served daily.",
        "category": "dining",
    }
    assert client.post("/api/admin/faqs", json=payload).status_code == 201
    response = client.post("/api/admin/faqs", json=payload)
    assert response.status_code == 409
    assert response.json() == {"detail": "FAQ question already exists"}
```

Add the `test_admin_faq_rejects_blank_fields` parametrized test defined in
Task 1 and import `pytest` at the top of the file.

- [ ] **Step 2: Запустити create tests і підтвердити RED**

```powershell
docker compose run --rm backend pytest -q tests/test_faq_admin_api.py -k "create or duplicate or blank"
```

Expected: fail because POST route/service does not exist.

- [ ] **Step 3: Реалізувати service create**

```python
class FAQConflictError(Exception):
    pass


def create_faq(db: Session, payload: FAQAdminWrite) -> FAQ:
    item = FAQ(
        question=payload.question,
        answer=payload.answer,
        category=payload.category,
        embedding=embed_passage(
            faq_embedding_text(payload.question, payload.answer, payload.category)
        ),
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise FAQConflictError from exc
    db.refresh(item)
    return item
```

- [ ] **Step 4: Реалізувати POST handler**

```python
@app.post(
    "/api/admin/faqs",
    response_model=FAQAdminResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_faq(
    payload: FAQAdminWrite,
    db: Session = Depends(get_db),
) -> FAQ:
    try:
        return create_faq(db, payload)
    except FAQConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="FAQ question already exists",
        ) from exc
```

- [ ] **Step 5: Запустити focused tests**

```powershell
docker compose build backend
docker compose run --rm backend pytest -q tests/test_faq_admin_api.py
```

Expected: list/create/duplicate/validation tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/faq_admin.py backend/app/main.py backend/tests/test_faq_admin_api.py
git commit -m "feat: create FAQ through admin API"
```

---

### Task 3: FAQ update і delete lifecycle

**Files:**
- Modify: `backend/app/services/faq_admin.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_faq_admin_api.py`

**Interfaces:**
- Consumes: `FAQAdminWrite`, `FAQConflictError`, `FAQ`.
- Produces: `FAQNotFoundError`, `update_faq(db, faq_id, payload) -> FAQ`, `delete_faq(db, faq_id) -> None`, PUT/DELETE routes.

- [ ] **Step 1: Написати failing update/delete/not-found tests**

```python
def test_admin_can_update_faq(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.faq_admin.embed_passage", lambda text: [0.5] * 384
    )
    created = client.post(
        "/api/admin/faqs",
        json={"question": "Old question", "answer": "Old answer", "category": "old"},
    ).json()
    response = client.put(
        f"/api/admin/faqs/{created['id']}",
        json={"question": "New question", "answer": "New answer", "category": "new"},
    )

    assert response.status_code == 200
    assert response.json()["question"] == "New question"
    assert response.json()["answer"] == "New answer"


def test_admin_can_delete_faq(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.faq_admin.embed_passage", lambda text: [0.5] * 384
    )
    created = client.post(
        "/api/admin/faqs",
        json={"question": "Delete me", "answer": "Temporary", "category": "test"},
    ).json()
    response = client.delete(f"/api/admin/faqs/{created['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.delete(f"/api/admin/faqs/{created['id']}").status_code == 404
```

Add these not-found and conflict assertions:

```python
def test_admin_update_missing_faq_returns_404(client):
    response = client.put(
        "/api/admin/faqs/999999",
        json={"question": "Valid question", "answer": "Valid answer", "category": "hotel"},
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "FAQ not found"}


def test_admin_update_duplicate_question_returns_409(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.faq_admin.embed_passage", lambda text: [0.5] * 384
    )
    first = client.post(
        "/api/admin/faqs",
        json={"question": "First unique question", "answer": "First answer", "category": "test"},
    ).json()
    second = client.post(
        "/api/admin/faqs",
        json={"question": "Second unique question", "answer": "Second answer", "category": "test"},
    ).json()
    response = client.put(
        f"/api/admin/faqs/{second['id']}",
        json={"question": first["question"], "answer": "Changed", "category": "test"},
    )
    assert response.status_code == 409
    rows = client.get("/api/admin/faqs").json()
    by_id = {row["id"]: row for row in rows}
    assert by_id[first["id"]]["question"] == "First unique question"
    assert by_id[second["id"]]["question"] == "Second unique question"
```

- [ ] **Step 2: Запустити lifecycle tests і підтвердити RED**

```powershell
docker compose run --rm backend pytest -q tests/test_faq_admin_api.py -k "update or delete or not_found"
```

Expected: `405 Method Not Allowed` because PUT/DELETE routes are absent.

- [ ] **Step 3: Реалізувати service update/delete**

```python
class FAQNotFoundError(Exception):
    pass


def update_faq(db: Session, faq_id: int, payload: FAQAdminWrite) -> FAQ:
    item = db.get(FAQ, faq_id)
    if item is None:
        raise FAQNotFoundError
    item.question = payload.question
    item.answer = payload.answer
    item.category = payload.category
    item.embedding = embed_passage(
        faq_embedding_text(payload.question, payload.answer, payload.category)
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise FAQConflictError from exc
    db.refresh(item)
    return item


def delete_faq(db: Session, faq_id: int) -> None:
    item = db.get(FAQ, faq_id)
    if item is None:
        raise FAQNotFoundError
    db.delete(item)
    db.commit()
```

- [ ] **Step 4: Реалізувати PUT/DELETE handlers**

Use these handlers and a shared translator:

```python
def _raise_admin_faq_error(exc: Exception) -> None:
    if isinstance(exc, FAQNotFoundError):
        raise HTTPException(status_code=404, detail="FAQ not found") from exc
    raise HTTPException(status_code=409, detail="FAQ question already exists") from exc


@app.put("/api/admin/faqs/{faq_id}", response_model=FAQAdminResponse)
def update_admin_faq(
    faq_id: int,
    payload: FAQAdminWrite,
    db: Session = Depends(get_db),
) -> FAQ:
    try:
        return update_faq(db, faq_id, payload)
    except (FAQNotFoundError, FAQConflictError) as exc:
        _raise_admin_faq_error(exc)


@app.delete("/api/admin/faqs/{faq_id}", status_code=204)
def delete_admin_faq(faq_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        delete_faq(db, faq_id)
    except FAQNotFoundError as exc:
        _raise_admin_faq_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 5: Запустити весь admin API test file**

```powershell
docker compose build backend
docker compose run --rm backend pytest -q tests/test_faq_admin_api.py
```

Expected: every admin CRUD test passes.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/faq_admin.py backend/app/main.py backend/tests/test_faq_admin_api.py
git commit -m "feat: update and delete FAQ through admin API"
```

---

### Task 4: PostgreSQL CRUD-to-search integration

**Files:**
- Create: `backend/tests/test_faq_admin_postgres.py`
- Modify: `backend/pytest.ini`

**Interfaces:**
- Consumes: running Backend at `INTEGRATION_BACKEND_URL`, PostgreSQL at `INTEGRATION_DATABASE_URL`.
- Produces: opt-in test gated by `RUN_POSTGRES_INTEGRATION=1` with guaranteed cleanup.

- [ ] **Step 1: Написати PostgreSQL lifecycle test**

Use a UUID in both question versions. The test must:

```python
def test_admin_crud_updates_live_core_search():
    token = uuid4().hex
    original = f"What is the zzzmeridian{token} service?"
    updated = f"Where is the zzzmeridian{token} desk?"
    faq_id = None
    try:
        created = httpx.post(
            f"{BACKEND_URL}/api/admin/faqs",
            json={"question": original, "answer": "Original verified answer.", "category": "test"},
            timeout=20,
        )
        assert created.status_code == 201
        faq_id = created.json()["id"]

        found = httpx.post(
            f"{BACKEND_URL}/api/faq/search",
            json={"question": original},
            timeout=20,
        ).json()
        assert found["matched"] is True
        assert found["answer"] == "Original verified answer."

        changed = httpx.put(
            f"{BACKEND_URL}/api/admin/faqs/{faq_id}",
            json={"question": updated, "answer": "Updated verified answer.", "category": "test"},
            timeout=20,
        )
        assert changed.status_code == 200

        found_again = httpx.post(
            f"{BACKEND_URL}/api/faq/search",
            json={"question": updated},
            timeout=20,
        ).json()
        assert found_again["matched"] is True
        assert found_again["answer"] == "Updated verified answer."
    finally:
        if faq_id is not None:
            httpx.delete(f"{BACKEND_URL}/api/admin/faqs/{faq_id}", timeout=20)
```

Use SQLAlchemy helpers in the same test file:

```python
engine = create_engine(DATABASE_URL)


def embedding_dimensions(faq_id: int) -> int | None:
    with engine.connect() as connection:
        return connection.scalar(
            text("SELECT vector_dims(embedding) FROM faqs WHERE id = :faq_id"),
            {"faq_id": faq_id},
        )


def faq_exists(faq_id: int) -> bool:
    with engine.connect() as connection:
        return bool(
            connection.scalar(
                text("SELECT EXISTS(SELECT 1 FROM faqs WHERE id = :faq_id)"),
                {"faq_id": faq_id},
            )
        )
```

Assert `embedding_dimensions(faq_id) == 384` after create and update. In
`finally`, call DELETE when needed, assert `faq_exists(faq_id) is False`, and
call `engine.dispose()`.

- [ ] **Step 2: Запустити test до rebuild і підтвердити контрольований failure**

```powershell
docker compose run --rm -e RUN_POSTGRES_INTEGRATION=1 backend pytest -q tests/test_faq_admin_postgres.py
```

Expected before rebuilt Backend: `404` for `/api/admin/faqs` because the running
container still uses the previous image. This proves the integration test reaches
the real stack rather than TestClient.

- [ ] **Step 3: Rebuild/recreate Backend і повторити test**

```powershell
docker compose up --build -d backend
docker compose run --rm -e RUN_POSTGRES_INTEGRATION=1 backend pytest -q tests/test_faq_admin_postgres.py
```

Expected: `1 passed`; test FAQ is removed in `finally`.

- [ ] **Step 4: Commit**

```powershell
git add backend/tests/test_faq_admin_postgres.py backend/pytest.ini
git commit -m "test: cover FAQ admin lifecycle in PostgreSQL"
```

---

### Task 5: README, full regression і B1 acceptance

**Files:**
- Modify: `README.md`
- Modify: `CORE_ACCEPTANCE.md`
- Modify: `TECHNICAL_PLAN.md`

**Interfaces:**
- Consumes: final B1 API contract and test commands.
- Produces: copy-paste PowerShell examples and recorded Bonus B1 evidence.

- [ ] **Step 1: Додати README API examples**

Document GET/POST/PUT/DELETE with `Invoke-RestMethod`, example JSON responses,
HTTP error meanings, and this integration command:

```powershell
docker compose run --rm -e RUN_POSTGRES_INTEGRATION=1 backend pytest -q tests/test_faq_admin_postgres.py
```

- [ ] **Step 2: Оновити acceptance і technical plan**

Add AP-1, AP-2, AP-3, AP-4 rows to `CORE_ACCEPTANCE.md`, each linked to the
implemented endpoint and automated evidence. Add `Bonus B1 — ready for manual
review` to `TECHNICAL_PLAN.md`; do not mark later Bonus stages complete.

- [ ] **Step 3: Запустити full verification**

```powershell
docker compose config --quiet
docker compose run --rm backend pytest -q
docker compose run --rm agent pytest -q
docker compose run --rm -e RUN_POSTGRES_INTEGRATION=1 backend pytest -q tests/test_postgres_concurrency.py tests/test_faq_admin_postgres.py
docker compose ps
git diff --check
```

Expected: all test processes exit `0`; all three long-running services are
healthy; diff check exits `0`.

- [ ] **Step 4: Перевірити secrets і test cleanup**

```powershell
git check-ignore -q .env
git grep -n -I -E "sk-[A-Za-z0-9_-]{16,}" -- .
docker compose exec -T db psql -U meridian -d meridian -c "SELECT COUNT(*) FROM faqs WHERE category = 'test';"
```

Expected: `.env` is ignored; no real key matches; count for B1 integration test
records is `0`.

- [ ] **Step 5: Commit documentation**

```powershell
git add README.md CORE_ACCEPTANCE.md TECHNICAL_PLAN.md
git commit -m "docs: document Bonus FAQ administration"
```

- [ ] **Step 6: Stop at B1 checkpoint**

Ask the user to create, edit, search, and delete one harmless FAQ through the
documented PowerShell commands. Do not start B2 until the user confirms the
manual lifecycle.
