# Core and Bonus Audit Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking. Stop after each stage for user confirmation; do not automatically dispatch subagents.

**Goal:** Виправити шість підтверджених проблем незалежного аудиту без втрати поточних даних і регресій Core/Bonus.

**Architecture:** Зберегти FastAPI/PostgreSQL/LiveKit/React. Відділити одноразове наповнення від звичайного запуску, індексувати актуальні FAQ, узгодити контракти backend/frontend. Не додавати нових сервісів чи платних залежностей.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL/pgvector, FastEmbed, LiveKit Agents, React, Vitest, Docker Compose.

**Spec:** PRD — `C:/Users/dmytr/OneDrive/Документи/Meridian_Voice_Concierge_PRD_UA.docx`; вихідні дефекти — незалежний аудит HEAD `100b8e0847850129b9d55bfca697a37b618f63f5` від 2026-08-27. Покриття: етап 1 — seed; 2 — embeddings; 3 — false matches/recording; 4 — stale UI/довжина; 5 — dispatch; 6 — приймання.

## Global Constraints

- Пояснення користувачу українською; UI та голосові відповіді англійською.
- Після кожного етапу зупинка; «ізі» означає підтвердження.
- Не видаляти volume, не змінювати живі записи заради тестів, не друкувати секрети.
- Не запускати старий backend entrypoint до виправлення seed: він може перезаписати FAQ.
- Регресійний тест має спочатку відтворити дефект, потім пройти після виправлення.
- PostgreSQL-перевірки виконувати на окремій тестовій БД/Compose-проєкті, без production volume і без живого агента.
- Коміти локальні після перевірки за погодженим workflow; push/PR/merge лише за окремою вказівкою.
- Нових функцій поза шістьма дефектами не додавати. Схвалений користувачем EV FAQ не видаляти.

## Stage 1 — Безпечне початкове наповнення

**Files:** `backend/app/seed.py`, `backend/app/models.py`, нова міграція в `backend/migrations/versions/`, новий `backend/tests/test_seed_persistence_postgres.py`, `README.md`.

**Interface:** зберегти `seed() -> None`; додати постійний маркер версії початкового наповнення, який не залежить від поточної кількості FAQ.

- [x] Зняти git/status і стан контейнерів; запустити лише DB без backend. Зберегти локальний backup поза Git до застосування міграцій; перевірити читабельність архіву.
- [x] У тестовій PostgreSQL відтворити послідовність: seed → edit answer/category → delete іншого FAQ → rename третього → seed. Assert: зміни збережено, видалений та старе ім'я не повернулися.
- [x] Покрити окремо порожню нову БД, існуючу інсталяцію з FAQ і існуючу інсталяцію з усіма видаленими FAQ. Не використовувати лише `COUNT(faqs)` для визначення першого запуску.
- [x] Реалізувати одноразове транзакційне наповнення. Для existing installation міграція позначає baseline застосованим без переписування контенту; для fresh database наповнення створює baseline і marker атомарно. Legacy-перетворення не виконувати на кожному старті.
- [x] Перевірити повторні/конкурентні запуски; оновити README щодо повторного запуску та окремих майбутніх змін контенту.
- [x] Запустити тест persistence на ізольованій PostgreSQL та звичайний Backend suite. Після backup і успішних тестів застосувати до робочої системи; показати користувачу результат і зупинитися.

**Приймання користувачем:** змінити тестовий FAQ, перезапустити Backend; зміна не зникає. Видалений тестовий FAQ не повертається.

## Stage 2 — Індекс актуальних відповідей

**Files:** `backend/app/services/embeddings.py`, `backend/app/services/semantic_passages.py`, `backend/tests/test_faq_admin_api.py`, новий `backend/tests/test_embedding_content.py`, новий `backend/app/reindex_faqs.py`.

**Interface:** зберегти `faq_embedding_text(question: str, answer: str, category: str) -> str`; текст має залежати від усіх актуальних полів.

- [ ] Написати й запустити регресійний тест:

```python
from app.seed_data import FAQS
from app.services.embeddings import faq_embedding_text

def test_seeded_answer_changes_embedding_input():
    faq = FAQS[0]
    before = faq_embedding_text(faq['question'], faq['answer'], faq['category'])
    after = faq_embedding_text(faq['question'], 'The service is permanently closed.', 'closed')
    assert before != after
    assert 'The service is permanently closed.' in after
```

- [ ] Будувати текст із поточних question/answer/category. Не включати застарілі hardcoded факти; зберігати лише безфактові aliases, що допомагають пошуку.
- [ ] Додати явний reindex: перерахувати тільки embedding усіх поточних рядків, без seed/зміни відповідей/відновлення видалених FAQ. У разі помилки відкотити транзакцію.
- [ ] Перевірити CRUD та PRD search scenarios до застосування reindex на робочій БД. Зупинитися для підтвердження.

**Приймання:** після зміни answer нові формулювання знаходяться; оновлення індексу не змінює контент FAQ.

## Stage 3 — Невідомі питання про відомі заклади

**Files:** `backend/app/services/faq_search.py`, `backend/tests/test_semantic_search_gaps.py`, `backend/tests/test_prd_scenarios.py`, `agent/tests/test_api.py`; за потреби `agent/app/api.py` та `agent/app/main.py` лише в межах контракту recording.

**Interface:** зберегти `/api/faq/search` і `search_and_record_unknown`; невідома політика не повинна ставати `matched=true` лише через назву закладу.

- [ ] Додати негативні API-сценарії: `Does Aurelia allow dogs?`, `Does Carbone have a wheelchair ramp?`, `What is Aurelia cancellation policy?`. Для кожного очікувати `matched=false`; у wrapper-тестах — один POST unanswered з оригінальним питанням.
- [ ] Зафіксувати позитивні сценарії: опис Aurelia, знижка Carbone, кухня/години ресторану. Вони мають продовжити знаходити правильні FAQ.
- [ ] Відтворити падіння; прибрати безумовний entity boost як доказ відповіді. Перевіряти достатність тематичного збігу, а не просто підвищувати загальний threshold чи додавати blacklist трьох прикладів.
- [ ] Перевірити нові перефразування, неоднозначні питання і повторення unknown (frequency зростає). Якщо локальні евристики не забезпечують потрібної точності, показати окремий вибір підходу до додавання LLM-перевірки, не вводити її мовчки.
- [ ] Запустити Backend/agent suites та isolated PostgreSQL search/recording. Зупинитися.

**Приймання:** користувач ставить голосом відоме і невідоме питання; невідоме з'являється у черзі без неправдивої відповіді.

## Stage 4 — Коректний Convert

**Files:** `admin/src/App.jsx`, `admin/src/App.test.jsx`, `backend/app/models.py`, `backend/app/schemas.py`, нова міграція `backend/migrations/versions/`, `backend/tests/test_unanswered_admin_api.py`, `backend/tests/test_faq_admin_postgres.py`.

**Interface:** FAQ.question та FAQAdminWrite.question підтримують до 1000 символів, як QuestionRequest; API шляхи незмінні.

- [ ] Додати UI-тест: Convert → FAQ Library → новий FAQ видно без перезавантаження. Показати падіння на старому коді.
- [ ] Після успішного conversion перечитувати FAQ або перечитувати бібліотеку при переході. Перевірити відображення помилки refresh окремо від факту успішного збереження.
- [ ] На PostgreSQL перевірити conversion довжин 500/501/1000; для API введення 1001 очікувати 422. SQLite не доводить підтримку varchar length.
- [ ] Розширити FAQ.question до String(1000) міграцією без обрізання даних; узгодити Pydantic і frontend-обмеження, якщо вони присутні. Не реалізовувати мовчазне обрізання при downgrade.
- [ ] Запустити frontend/backend suites і isolated PostgreSQL boundary tests; зупинитися.

**Приймання:** створений із черги FAQ відразу видно в бібліотеці; довге допустиме питання конвертується.

## Stage 5 — Єдина назва агента для Playground

**Files:** `backend/app/services/livekit_tokens.py`, `backend/tests/test_livekit_token_api.py`, `admin/src/Playground.jsx`, `admin/src/Playground.test.jsx`, `README.md`.

**Interface:** backend settings.agent_name є єдиним джерелом dispatch; формат token response лишається сумісним із TokenSource.endpoint.

- [ ] Тест із AGENT_NAME `meridian-audit-agent`: decoded тестовий JWT room configuration містить саме цю назву навіть якщо клієнт надіслав стару.
- [ ] Формувати agent dispatch на backend із settings.agent_name; прибрати hardcoded agentName з frontend. Перевірити фактичний контракт встановленого useSession перед зміною.
- [ ] Перевірити JWT TTL/room grants, відсутність дублікатів dispatch, default і custom name. Не друкувати справжні токени.
- [ ] Запустити token/frontend/agent suites; виконати ручний дзвінок з поточним голосом і повторне підключення. Зупинитися.

**Приймання:** Playground підключається, чує мікрофон та відповідає; нова сесія використовує вибраний голос без restart агента.

## Stage 6 — Повторне фінальне приймання

**Files:** `README.md`, `CORE_ACCEPTANCE.md`, цей checklist; код змінювати лише після окремо погодженого нового дефекту.

- [ ] Прогнати всі Backend/agent/frontend suites та production build. Поточний baseline аудиту: 54 Backend + 12 agent + 15 frontend; це історичний орієнтир, не майбутній результат.
- [ ] На окремому Compose-проєкті перевірити migrations/seed із порожньою БД, повторний запуск, persistence admin edits та PG integration. Використати окремий volume, не `down -v` робочого проєкту.
- [ ] Перевірити робочі `/health`, admin, FAQ CRUD, queue convert/dismiss/frequency, чотири preview та нові сесії з кожним голосом. Зазначити будь-які перевірки, що потребують чинних ключів/кредитів/мікрофона.
- [ ] Перевірити git diff, .env exclusion, відсутність backup/секретів у staged files. Оновити документацію лише фактичними результатами.
- [ ] Надати підсумок Core і Bonus окремо. За окремим погодженням користувача повторити незалежний аудит; не push/merge автоматично.

**Участь користувача:** Docker Desktop, дозвіл мікрофона, короткі голосові перевірки та підтвердження етапів. Писати код чи SQL не потрібно.


## Stage 1 execution — 2026-08-27

- Workspace: `C:/Users/dmytr/AppData/Local/Temp/meridian-audit-fixes`, branch `codex/audit-fixes`; main source unchanged.
- Baseline: 54 passed, 3 skipped. Regression red: 5 failed, 1 passed. Final backend suite with disposable PostgreSQL: 60 passed, 3 skipped (other opt-in integration suites).
- Backup: `C:/Users/dmytr/AppData/Local/Temp/meridian-before-seed-fix-20260827.dump`; restore to an isolated database succeeded.
- Migration 20260827_05 applied first to restored copy, then live database. Before/after/restart checksums identical for 49 FAQs, 2 unanswered records, 4 voices.
- Backend built from this worktree; all 4 live containers healthy; backend health JSON ok, admin health HTTP 200.
- Temporary PostgreSQL stopped. No pushes or merges; user acceptance pending. Do not rebuild from the original main checkout until changes are integrated: it still contains the old seed.

## Stage 2 checkpoint — incomplete, 2026-08-27

- User accepted Stage 1 and authorized Stage 2.
- Added 50 regression cases for current answer/category, stale spa facts and real persisted embeddings after an answer-only admin edit. Initial result: 49 failed, 1 passed; these now pass.
- Embedding text now uses current answer/question/category and English question aliases, not hardcoded semantic passages. Three topic aliases were added during regression investigation; no search thresholds or matching decisions changed.
- Full suite currently: 103 passed, 1 failed, 9 skipped. The failing loop stops on `Where can I eat near the hotel?`: the search chooses fitness instead of Carbone, so later cases in that loop have not been checked in this run.
- After three attempted adjustments, systematic-debugging requires a design checkpoint rather than another ad hoc tweak. Recommend reviewing Stage 2 together with Stage 3 retrieval acceptance logic; obtain user consent before expanding the current stage.
- No reindex command implemented or run; no working database data/index changes, no image build/deployment, no push/merge. Running system remains the verified Stage 1 image. Stage 2 working-copy changes are NOT ready to deploy.

## Combined Stages 2–3 completion — 2026-08-27

This checkpoint supersedes the incomplete Stage 2 checkpoint above. The user approved combining stages and the bounded design before implementation.

- Current answer/question/category form embeddings; only English question aliases supplement them. Static semantic passages are no longer imported by retrieval.
- Added `search_terms.py` for conservative topic coverage. Candidates must cover question topics in current FAQ question/answer; aliases only rank candidates. Each wording is scored separately. No venue-name bonus, new services, API keys or model dependencies.
- Added tests for unsupported venue policies, compound questions, added answers, answer-only edits, separate dog/cat rules, prices, hours, real vector persistence, transactional reindex rollback and exact unknown frequency increments.
- Reviewer identified basic pricing rejection; failing API tests confirmed it. Recognizing currency amounts and “how much” as price information fixed it.
- Final Backend suite with isolated PostgreSQL: **129 passed, 3 skipped** (other opt-in integration suites). Agent suite including real backend/queue: **16 passed**. No live voice session was automated; user voice acceptance remains pending.
- Integration tests now create a distinct temporary database per test, avoiding public-schema collisions with the separate API test database. Temporary API and database containers stopped after testing.
- New `python -m app.reindex_faqs` locks rows and rebuilds only vectors in one transaction. It neither runs seed nor changes content timestamps.
- Backup: `C:/Users/dmytr/AppData/Local/Temp/meridian-before-reindex-20260827.dump`. Restored copy successfully reindexed first; content hashes unchanged.
- Rebuilt working Backend from this worktree and reindexed 49 live FAQs. Content/timestamp hashes, 2 unanswered records and 4 voice records unchanged; all four containers healthy.
- Live API checks: nearby dining → Carbone; Deluxe price → Deluxe; Aurelia prices → Aurelia; Aurelia dogs / Carbone ramp / Aurelia cancellation → no match.
- Known limitation: deterministic conservative topic coverage is not universal entailment; unfamiliar paraphrases can produce false negatives. Changes are still uncommitted on `codex/audit-fixes`; main has old source, no push/merge. Do not rebuild from main before integration.
- Next checkpoint: user tests a new Playground session and queue frequency, then approves Stage 4 (Convert UI refresh and question length).

## Stage 4 completion — 2026-08-27

- User accepted Stages 2–3 and authorized Stage 4. Convert now uses the successful API response to insert the FAQ into local library state and remove the queue entry without a follow-up request. Failed conversion retains the draft.
- FAQ question limit is 1000 in the form, schema and model. Migration `20260827_06` expands PostgreSQL storage; downgrade refuses long existing values rather than truncating them.
- Regression RED: backend 3 failed / 1 passed (varchar 500); UI 2 failed / 15 passed (stale library and missing form limit).
- Final backend: 136 passed, 3 skipped (other opt-in integration suites); UI: 17 passed. Real PostgreSQL tests cover conversion/edit at 500/501/1000, preserved migration content, rejected lossy downgrade. API tests reject 1001. Docker images built successfully; existing Vite bundle-size warning remains.
- Backup: `C:/Users/dmytr/AppData/Local/Temp/meridian-before-stage4-20260827.dump`.
- Live migration is 20260827_06 and FAQ storage length is 1000. Before/after content hashes identical for 50 FAQs, 3 unanswered records, 4 voices. All four containers healthy; backend health ok and admin HTTP 200.
- No live test records created, no voice session performed, no push/merge. Original main source remains unchanged; do not rebuild from it before integration.
- Stopped for user acceptance: reload admin, Convert a question with a confirmed answer, switch to FAQ Library and verify it appears immediately. Stage 5 not started.

## Stage 5 implementation — 2026-08-27

- User accepted Stage 4. Verified installed useSession supports omitted options; removed the frontend hardcoded agentName.
- Backend always signs exactly one dispatch using settings.agent_name, overriding stale/duplicate client agent names. Other room configuration and first dispatch metadata remain compatible.
- Regression RED: 4 token tests failed / 3 passed; 5 Playground tests failed / 12 other UI tests passed. GREEN: backend 127 passed / 15 opt-in PostgreSQL tests skipped; agent 12 passed / 4 isolated API tests skipped; UI 17 passed. Token tests verify default/custom names, duplicate removal, TTL and room grants using fake credentials only.
- Backend/admin images built and local services updated. Existing Vite bundle-size warning remains. No database migration, live records edited, keys changed, push or merge.
- Manual acceptance pending: reload Playground, start/end/reconnect, then select another voice and start a new conversation without restarting the agent. Stage 6 not started.

## Stage 6 automated acceptance — 2026-08-27

- User accepted Stage 5. Fresh final suites: backend 142 passed, agent 16 passed, frontend 17 passed; no skipped tests. All three Docker images build; fresh frontend production build succeeds with existing bundle-size warning.
- Separate Compose project `meridian-final-audit-20260827`, newly created volume of the same prefix, no live keys/ports/worker. Fresh startup created revision 20260827_06, 48 FAQ vectors, four voices.
- Full PostgreSQL suites include 50 concurrent unknown requests, concurrent activation, admin CRUD/search/vector persistence, seed restart/race/upgrade safety, transactional reindex, length migration and boundaries. Agent integration checks known/unknown recording and frequency.
- Separate smoke confirmed CRUD, Convert, Dismiss, four distinct preview files and persistence after actual backend restart/repeated Compose up. No live records changed.
- Live read-only checks: four services healthy, health ok, admin HTTP 200, four distinct preview files and exactly one active voice. Voice/media/provider calls were not automated.
- Secret check: `.env`/`.venv` ignored, no tracked env/dump/key/pem files, no staged files; no matches against local secret values of length >=12 across 104 tracked/unignored files. Not a Git-history audit.
- README and CORE_ACCEPTANCE updated. Manual final check still requested for a new session with each of the four voices; Stage 5 session/reconnect/voice change already user-confirmed. No push/merge/commit; fixes remain in isolated worktree.

## Publication approval — 2026-08-27

- User confirmed the final four-voice manual check, then explicitly approved pushing and merging into GitHub main (not a separate production deployment).
- Fresh pre-publication verification: backend 142 passed, agent 16 passed, UI 17 passed; production build successful. Base origin/main unchanged at 100b8e0.
- Earlier uncommitted/pending entries above are historical checkpoints, superseded by this approval and the eventual Git commit history.
- Independent pre-merge reviewer found no blockers for approved English/local scope. Coordinator confirmed a separate Unicode boundary caveat: 1000 random four-byte characters exceed PostgreSQL UNIQUE B-tree byte limit. Documented in CORE_ACCEPTANCE, no new behavior change in publication stage.
