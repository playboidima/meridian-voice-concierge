# Bonus B4 Voice Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver four PRD voice personalities with real previews and immediate selection for new LiveKit sessions without restarting any service.

**Architecture:** PostgreSQL stores an immutable four-row voice catalog and exactly one active voice. FastAPI exposes admin list/activate/preview routes plus an internal active-voice route; the Python agent reads that route once per new session, while React adds an English Voice Studio using committed same-origin MP3 previews.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL, LiveKit Agents/Inference, React 18, Vitest, Docker Compose

**Spec:** `docs/superpowers/specs/2026-08-24-bonus-b4-voice-configuration-design.md`

## Global Constraints

- Keep Core FAQ and unanswered-question behavior unchanged.
- Keep the complete user-facing admin interface English.
- Use exactly James, Sofia, Marcus, and Elena; exactly one is active.
- A selection change affects the next LiveKit session without a Docker restart and never changes an existing session mid-conversation.
- Never store LiveKit/Cartesia secrets in PostgreSQL, preview metadata, frontend code, logs, or Git.
- Keep LiveKit Inference; do not require a separate Cartesia API key at runtime.
- Do not implement the integrated Playground, authentication, booking, payment, or multilingual behavior in B4.
- After every task, run its focused tests, the relevant regression suite, commit, and stop for the user's `ізі` checkpoint.

---

### Task 1: Validate the Four Provider Voices and Produce Real Preview Assets

**Files:**
- Create: `agent/scripts/generate_voice_previews.py`
- Modify: `agent/Dockerfile`
- Modify: `agent/requirements.txt`
- Create: `backend/app/static/voice-previews/james.mp3`
- Create: `backend/app/static/voice-previews/sofia.mp3`
- Create: `backend/app/static/voice-previews/marcus.mp3`
- Create: `backend/app/static/voice-previews/elena.mp3`
- Create: `backend/tests/test_voice_preview_assets.py`

**Interfaces:**
- Consumes: local `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`; candidate IDs from the B4 spec.
- Produces: four non-empty MP3 files containing exactly `Welcome to The Meridian. It is my pleasure to assist you today.` and a reproducible generation script that never prints credentials.

- [ ] **Step 1: Write the failing asset-contract test**

Create `backend/tests/test_voice_preview_assets.py`:

```python
from pathlib import Path


PREVIEW_DIR = Path(__file__).parents[1] / "app" / "static" / "voice-previews"


def test_all_four_real_voice_previews_are_committed() -> None:
    for name in ("james", "sofia", "marcus", "elena"):
        preview = PREVIEW_DIR / f"{name}.mp3"
        assert preview.exists(), name
        assert preview.stat().st_size > 1_000, name
        assert preview.read_bytes()[:3] == b"ID3" or preview.read_bytes()[:2] == b"\xff\xfb"
```

- [ ] **Step 2: Run the asset test and verify RED**

Run:

```powershell
docker compose run --rm --build backend pytest tests/test_voice_preview_assets.py -q
```

Expected: FAIL because the four MP3 files do not exist.

- [ ] **Step 3: Implement the credential-safe preview generator**

Create `agent/scripts/generate_voice_previews.py` with a fixed catalog:

```python
VOICE_IDS = {
    "james": "63ff761f-c1e8-414b-b969-d1833d1c870c",
    "sofia": "79a125e8-cd45-4c13-8a67-188112f4dd22",
    "marcus": "a167e0f3-df7e-4d52-a9c3-f949145efdab",
    "elena": "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
}
PREVIEW_TEXT = "Welcome to The Meridian. It is my pleasure to assist you today."
```

The script must use `livekit.agents.inference.TTS(model="cartesia/sonic-3", voice=voice_id, language="en")`, collect synthesized PCM frames through the supported LiveKit Agents TTS stream, and use pinned `lameenc==1.8.1` to encode one MP3 per catalog key. It writes only to an explicit `--output-dir` and prints only the output filename and byte count. It must fail nonzero if credentials are absent, a voice is rejected, or output is shorter than 1,000 bytes. Add `COPY scripts ./scripts` to the Agent Dockerfile. No generated `.env`, token, URL, or request header may be logged.

- [ ] **Step 4: Generate and listen-check all four previews**

Run from the repository root using the local ignored `.env`:

```powershell
docker compose build agent
docker compose run --rm -v "${PWD}/backend/app/static/voice-previews:/previews" agent python scripts/generate_voice_previews.py --output-dir /previews
```

The bind mount writes only the four resulting MP3 files into `backend/app/static/voice-previews/`. If a candidate ID fails or clearly violates its PRD personality, replace that ID with a compatible default Cartesia voice, update the B4 spec and the fixed catalog in the same commit, regenerate all four files, and repeat the listening check. Never use duplicated or mismatched audio.

- [ ] **Step 5: Verify GREEN and distinct assets**

Run:

```powershell
docker compose run --rm --build backend pytest tests/test_voice_preview_assets.py -q
Get-FileHash backend/app/static/voice-previews/*.mp3
```

Expected: test PASS; four distinct SHA-256 hashes.

- [ ] **Step 6: Commit and stop**

```powershell
git add agent/scripts/generate_voice_previews.py agent/Dockerfile agent/requirements.txt backend/app/static/voice-previews backend/tests/test_voice_preview_assets.py docs/superpowers/specs/2026-08-24-bonus-b4-voice-configuration-design.md
git commit -m "feat: add verified Meridian voice previews"
```

Stop for the user's listening check and `ізі`.

---

### Task 2: VoiceConfig Model, Seed, Migration, and Backend API

**Files:**
- Create: `backend/app/voice_catalog.py`
- Create: `backend/app/services/voice_admin.py`
- Create: `backend/migrations/versions/20260824_04_add_voice_configs.py`
- Create: `backend/tests/test_voice_admin_api.py`
- Create: `backend/tests/test_voice_admin_postgres.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/seed.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Consumes: the four verified IDs and preview files from Task 1.
- Produces: `VoiceConfig`, `VOICE_CATALOG`, `reconcile_voice_catalog(db)`, `list_voices(db)`, `activate_voice(db, voice_id)`, `get_active_voice(db)`, and the four HTTP routes from the spec.

- [ ] **Step 1: Write failing API behavior tests**

Create fixtures with four `VoiceConfig` rows and assert literal contracts:

```python
def test_admin_lists_four_voices_in_catalog_order(client):
    response = client.get("/api/admin/voices")
    assert response.status_code == 200
    assert [voice["name"] for voice in response.json()] == [
        "James", "Sofia", "Marcus", "Elena"
    ]
    assert sum(voice["is_active"] for voice in response.json()) == 1
    assert "provider_voice_id" not in response.json()[0]


def test_admin_activates_one_voice(client):
    voices = client.get("/api/admin/voices").json()
    sofia = next(voice for voice in voices if voice["name"] == "Sofia")
    response = client.post(f"/api/admin/voices/{sofia['id']}/activate")
    assert response.status_code == 200
    assert response.json()["name"] == "Sofia"
    assert response.json()["is_active"] is True
    assert sum(voice["is_active"] for voice in client.get("/api/admin/voices").json()) == 1


def test_internal_active_voice_exposes_only_agent_runtime_fields(client):
    response = client.get("/api/voice/active")
    assert response.status_code == 200
    assert set(response.json()) == {"name", "provider_voice_id", "updated_at"}


def test_voice_preview_streams_mp3(client):
    james = client.get("/api/admin/voices").json()[0]
    response = client.get(f"/api/admin/voices/{james['id']}/preview")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert len(response.content) > 1_000
```

Also assert literal `404` responses for missing activation and preview IDs.

- [ ] **Step 2: Run focused tests and verify RED**

```powershell
docker compose run --rm --build backend pytest tests/test_voice_admin_api.py -q
```

Expected: collection or request failures because `VoiceConfig` and routes do not exist.

- [ ] **Step 3: Add the fixed catalog, model, schemas, and migration**

Define `VOICE_CATALOG` in `voice_catalog.py` as four dictionaries with `name`, verified `provider_voice_id`, PRD `description`, `preview_path`, and James active by default. Add `VoiceConfig` to `models.py` with the exact spec fields. Create migration revision `20260824_04`, down revision `20260821_03`, the table constraints, and:

```python
op.create_index(
    "uq_voice_configs_one_active",
    "voice_configs",
    ["is_active"],
    unique=True,
    postgresql_where=sa.text("is_active"),
)
```

Define `VoiceAdminResponse` (without provider ID) and `ActiveVoiceResponse` (with provider ID) in `schemas.py`.

- [ ] **Step 4: Implement idempotent reconciliation and transactional services**

`reconcile_voice_catalog(db)` upserts by stable `name`, updates provider ID/description/preview path, deletes no user data, and guarantees James is active only when no row is active. `activate_voice` must select all voice rows with `with_for_update()`, return `VoiceNotFoundError` for an absent ID, set exactly one active flag, commit, and refresh the selected row. `get_active_voice` must require exactly one active row or raise `InvalidVoiceStateError`.

- [ ] **Step 5: Register routes and preview streaming**

Add the four spec routes to `main.py`. Use `FileResponse(path, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=3600"})`; resolve paths beneath the fixed Backend static directory and never accept a client-provided path. Map invalid active state to `503` and missing IDs/assets to `404`.

- [ ] **Step 6: Verify GREEN and PostgreSQL concurrency**

```powershell
docker compose run --rm --build backend pytest tests/test_voice_admin_api.py tests/test_voice_preview_assets.py -q
docker compose up --build -d backend
docker compose exec -T backend pytest tests/test_voice_admin_postgres.py -q
docker compose exec -T db psql -U meridian -d meridian -c "SELECT name, is_active FROM voice_configs ORDER BY id;"
```

Expected: four rows and exactly one `t`. The PostgreSQL test concurrently activates two different rows and asserts the committed database still contains one active row.

- [ ] **Step 7: Run Backend regression, commit, and stop**

```powershell
docker compose exec -T backend pytest -q
git add backend
git commit -m "feat: manage active concierge voice"
```

Stop for API/database review and `ізі`.

---

### Task 3: Use the Active Voice for Every New Agent Session

**Files:**
- Create: `agent/tests/test_voice_config.py`
- Modify: `agent/app/api.py`
- Modify: `agent/app/main.py`

**Interfaces:**
- Consumes: `GET /api/voice/active` from Task 2 and local `TTS_VOICE` fallback.
- Produces: `ConciergeAPI.get_active_voice() -> dict[str, Any]`, `resolve_voice_id(api, fallback) -> str`, and `build_tts(voice_id)` used once per new job.

- [ ] **Step 1: Write failing agent tests**

```python
@pytest.mark.asyncio
async def test_resolve_voice_uses_backend_provider_id(monkeypatch):
    class API:
        async def get_active_voice(self):
            return {"name": "Sofia", "provider_voice_id": "voice-sofia"}
    assert await resolve_voice_id(API(), "fallback") == "voice-sofia"


@pytest.mark.asyncio
async def test_resolve_voice_falls_back_when_backend_fails():
    class API:
        async def get_active_voice(self):
            raise httpx.ConnectError("offline")
    assert await resolve_voice_id(API(), "fallback") == "fallback"
```

Add a session-construction test that invokes the job/session factory twice with different mocked Backend results and asserts two different `inference.TTS` voice arguments.

- [ ] **Step 2: Run focused tests and verify RED**

```powershell
docker compose run --rm --build agent pytest tests/test_voice_config.py -q
```

Expected: FAIL because active-voice methods do not exist.

- [ ] **Step 3: Implement active-voice retrieval and fallback**

Add to `ConciergeAPI`:

```python
async def get_active_voice(self) -> dict[str, Any]:
    async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
        response = await client.get("/api/voice/active")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload.get("provider_voice_id"), str):
            raise ValueError("Invalid active voice response")
        return payload
```

In `main.py`, instantiate one `ConciergeAPI`, await `resolve_voice_id` before `AgentSession`, then call `build_tts(voice_id)`. Catch only `httpx.HTTPError` and `ValueError`; log the fallback event without the URL, credentials, or provider ID.

- [ ] **Step 4: Verify GREEN and regression**

```powershell
docker compose run --rm --build agent pytest -q
```

Expected: all agent tests PASS.

- [ ] **Step 5: Commit and stop**

```powershell
git add agent/app/api.py agent/app/main.py agent/tests/test_voice_config.py
git commit -m "feat: load active voice for new sessions"
```

Stop for the user's first real LiveKit voice-switch check and `ізі`.

---

### Task 4: Add the English React Voice Studio

**Files:**
- Modify: `admin/src/api.js`
- Modify: `admin/src/App.jsx`
- Modify: `admin/src/App.test.jsx`
- Modify: `admin/src/styles.css`

**Interfaces:**
- Consumes: admin voice list, activation, and preview endpoints from Task 2.
- Produces: `faqApi.listVoices()`, `faqApi.activateVoice(id)`, `faqApi.voicePreviewUrl(id)`, and the `Voice Studio` view.

- [ ] **Step 1: Write failing Voice Studio component tests**

Add a four-voice literal fixture and tests that:

```javascript
await user.click(screen.getByRole("button", { name: "Voice Studio" }));
expect(await screen.findByRole("heading", { name: "Voice Studio" })).toBeInTheDocument();
expect(screen.getAllByText("Active voice")).toHaveLength(1);
expect(screen.getByText("James")).toBeInTheDocument();
expect(screen.getByText("Sofia")).toBeInTheDocument();
expect(screen.getByText("Marcus")).toBeInTheDocument();
expect(screen.getByText("Elena")).toBeInTheDocument();
```

Activation test must assert `POST /api/admin/voices/{id}/activate`, the active badge moves, and `Voice changed to Sofia.` appears. Failure test must assert the old badge remains. Preview test must stub one `Audio` instance, assert its URL is `/api/admin/voices/{id}/preview`, and assert a second preview pauses the first.

- [ ] **Step 2: Run Vitest and verify RED**

```powershell
docker compose run --rm --build admin pnpm test --run
```

Expected: FAIL because `Voice Studio` does not exist.

- [ ] **Step 3: Add API methods and Voice Studio behavior**

Extend `faqApi`:

```javascript
listVoices: () => request("/api/admin/voices"),
activateVoice: (id) => request(`/api/admin/voices/${id}/activate`, { method: "POST" }),
voicePreviewUrl: (id) => `/api/admin/voices/${id}/preview`,
```

Add `Voice Studio` as the third navigation button. Load voices on entry. Render the fixed four cards, active badge, Preview/Stop preview, and Set active behavior specified in the design. Store the current `Audio` object in a React ref, pause/reset it before another preview and on component unmount, and translate media errors to `Voice preview is unavailable.` Disable all activation controls while a selection request is pending.

- [ ] **Step 4: Style desktop and responsive layouts**

Reuse the existing visual system. Add a two-column `.voice-grid`, an `.active-voice` card modifier, a compact waveform/play control, and a high-contrast active badge. At the existing narrow breakpoint, collapse to one column without horizontal overflow. Do not add a UI library.

- [ ] **Step 5: Verify GREEN, English copy, and production build**

```powershell
docker compose run --rm --build admin pnpm test --run
docker compose build --no-cache admin
```

Expected: all component tests PASS and Vite production build exits 0.

- [ ] **Step 6: Browser QA, commit, and stop**

Rebuild `admin`, open `http://localhost:3000`, and verify desktop plus the existing responsive breakpoint. Inspect the visible DOM for Cyrillic, preview each card, activate Sofia, and check console errors. Then:

```powershell
git add admin/src
git commit -m "feat: add concierge Voice Studio"
```

Stop for the user's UI/listening review and `ізі`.

---

### Task 5: Full B4 Integration, Documentation, and Acceptance Evidence

**Files:**
- Modify: `README.md`
- Modify: `TECHNICAL_DECISIONS.md`
- Modify: `TECHNICAL_PLAN.md`
- Modify: `CORE_ACCEPTANCE.md`
- Modify: `.env.example` only if the final verified model/default voice changed

**Interfaces:**
- Consumes: completed Tasks 1 through 4.
- Produces: reproducible B4 setup instructions, API examples, verification evidence, and an explicit B5 boundary.

- [ ] **Step 1: Document exact B4 behavior and requests**

Document the four personalities, Voice Studio URL, preview behavior, activation request/response, internal active-voice contract, `TTS_VOICE` fallback, and the rule that only new sessions change. State that preview files contain no secrets and that B5 Playground is not yet implemented.

- [ ] **Step 2: Run fresh complete verification**

```powershell
docker compose up --build -d
docker compose ps
docker compose exec -T backend pytest -q
docker compose exec -T agent pytest -q
docker compose build --no-cache admin
docker compose exec -T db psql -U meridian -d meridian -c "SELECT COUNT(*) AS voices, COUNT(*) FILTER (WHERE is_active) AS active FROM voice_configs;"
git diff --check
```

Expected: four healthy services; Backend and Agent suites have zero failures; admin tests/build pass; query returns `voices = 4`, `active = 1`; diff check exits 0.

- [ ] **Step 3: Perform live no-restart acceptance sequence**

1. Record `docker compose ps` and do not restart services afterward.
2. In Voice Studio, preview all four distinct voices.
3. Activate Marcus.
4. Start a new LiveKit session and confirm the greeting is Marcus.
5. Activate Elena without restarting Docker.
6. Start another new LiveKit session and confirm the greeting is Elena.
7. Ask one known FAQ and one unknown question to prove Core behavior remains intact.

Record manual results in `CORE_ACCEPTANCE.md` only after the user confirms each listening check.

- [ ] **Step 4: Secret and repository audit**

```powershell
git check-ignore -v .env
git ls-files .env
git diff --cached --name-only
rg -n "LIVEKIT_API_SECRET=.+|LIVEKIT_API_KEY=.+|sk_car_" --glob "!.env" --glob "!*.mp3" .
```

Expected: `.env` ignored and untracked; no real secret values in tracked text.

- [ ] **Step 5: Commit and stop**

```powershell
git add README.md TECHNICAL_DECISIONS.md TECHNICAL_PLAN.md CORE_ACCEPTANCE.md .env.example
git commit -m "docs: complete Bonus voice configuration"
```

Stop and report automated results, the user's manual listening evidence, known limitations, and that B5 integrated Playground is the next stage.
