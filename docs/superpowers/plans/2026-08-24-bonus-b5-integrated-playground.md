# Bonus B5 Integrated Playground Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a complete LiveKit voice playground inside the existing Meridian React admin panel.

**Architecture:** FastAPI generates short-lived, room-scoped LiveKit credentials without exposing secrets. The existing React application uses LiveKit Session APIs and React components for connection lifecycle, microphone input, agent audio, and state rendering through the existing same-origin Nginx proxy.

**Tech Stack:** Python, FastAPI, `livekit-api`, React 18, `@livekit/components-react`, `@livekit/components-styles`, `livekit-client`, Vitest, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-08-24-bonus-b5-integrated-playground-design.md`

## Global Constraints

- All interface copy is English.
- `LIVEKIT_API_SECRET` must never be returned to or bundled into the frontend.
- Each token expires after 10 minutes and is scoped to one generated room.
- The agent name defaults to `meridian-concierge`.
- Camera, screen sharing, recording, text chat, authentication, and a separate guest site remain out of scope.
- `docker compose up` remains the single system startup command.

---

### Task 1: FastAPI LiveKit token endpoint

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`
- Create: `backend/app/services/livekit_tokens.py`
- Create: `backend/tests/test_livekit_token_api.py`
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, and `AGENT_NAME` environment variables.
- Produces: `POST /api/livekit/token` accepting LiveKit's standard token-source JSON fields and returning HTTP 201 with `{ "server_url": string, "participant_token": string }`.

- [x] **Step 1: Write failing API tests**

Add tests that override token settings and assert: missing credentials return HTTP 503 without naming secret values; configured requests return HTTP 201; two empty requests create different room/participant identities; supplied `room_config` is retained for agent dispatch; decoded grants allow join/publish/subscribe only in the generated room and expire in at most 10 minutes.

- [x] **Step 2: Run the focused test and confirm failure**

Run: `docker compose run --rm backend pytest tests/test_livekit_token_api.py -q`

Expected: FAIL because `/api/livekit/token` does not exist.

- [x] **Step 3: Add the minimal token service and endpoint**

Add `livekit-api` to backend dependencies. Define optional token-source request fields in Pydantic, generate `playground-<uuid>` and `tester-<uuid>` defaults, build an `api.AccessToken` with a 10-minute TTL and `VideoGrants(room_join=True, room=<room>, can_publish=True, can_subscribe=True)`, apply `room_config` when supplied, and return the configured server URL plus JWT. Raise HTTP 503 when server credentials are incomplete.

- [x] **Step 4: Pass LiveKit configuration through Compose**

Add the four LiveKit variables to the backend service environment using the same `.env` values already passed to the agent. Do not add any real values or frontend build arguments.

- [x] **Step 5: Run focused and backend regression tests**

Run: `docker compose build backend`

Run: `docker compose run --rm backend pytest tests/test_livekit_token_api.py -q`

Run: `docker compose run --rm backend pytest -q`

Expected: token tests and the complete backend suite PASS.

- [x] **Step 6: Commit the endpoint**

```bash
git add backend docker-compose.yml
git commit -m "feat: issue LiveKit playground tokens"
```

### Task 2: React LiveKit playground

**Files:**
- Modify: `admin/package.json`
- Modify: `admin/pnpm-lock.yaml`
- Modify: `admin/src/api.js`
- Modify: `admin/src/App.jsx`
- Create: `admin/src/Playground.jsx`
- Create: `admin/src/Playground.test.jsx`
- Modify: `admin/src/styles.css`
- Modify: `admin/src/App.test.jsx`

**Interfaces:**
- Consumes: `POST /api/livekit/token`, `GET /api/voice/active`, and agent name `meridian-concierge`.
- Produces: a `Playground` admin view with Start, End, microphone, audio rendering, active voice, and lifecycle status.

- [ ] **Step 1: Install official LiveKit browser packages**

Run from `admin`: `pnpm add @livekit/components-react @livekit/components-styles livekit-client`

Expected: `package.json` and `pnpm-lock.yaml` contain the three direct dependencies.

- [ ] **Step 2: Write failing component tests**

Mock the LiveKit session boundary and test that the component renders `Playground`, `Test Mode`, `Disconnected`, and the active voice; Start invokes `session.start()` and shows connection progress; End invokes `session.end()`; a rejected Start renders an English retryable error; unmount invokes cleanup. Extend the app navigation test to require the fourth `Playground` item.

- [ ] **Step 3: Run the focused frontend tests and confirm failure**

Run: `docker compose run --rm admin pnpm test -- --run src/Playground.test.jsx src/App.test.jsx`

Expected: FAIL because the view and component do not exist.

- [ ] **Step 4: Implement the session boundary**

Create a module-level `TokenSource.endpoint('/api/livekit/token')`. Use `useSession(tokenSource, { agentName: 'meridian-concierge' })` and `SessionProvider`. Keep session start user-initiated, call `session.end()` on End and unmount, and use LiveKit agent/session state to map internal values to the six approved English display states.

- [ ] **Step 5: Implement voice audio and controls**

Render `RoomAudioRenderer`, an audio-unlock control for autoplay restrictions, a microphone toggle, Start/End controls, and an agent audio visualizer. Disable impossible actions during transitions and keep camera/screen-share controls absent.

- [ ] **Step 6: Integrate the view into the admin shell**

Add `Playground` to the sidebar and page heading switch. Fetch `/api/voice/active` on entry and show `Testing with <name>`. Keep all copy English and preserve the FAQ, Queue, and Voice Studio behavior.

- [ ] **Step 7: Style desktop and narrow layouts**

Add styles consistent with the existing Meridian cards: visible Test Mode badge, central status/visualizer, readable controls, clear error panel, and usable layout down to 768px width. Do not create a new global design system.

- [ ] **Step 8: Run frontend tests and production build**

Run: `docker compose run --rm admin pnpm test -- --run`

Run: `docker compose build admin`

Expected: all frontend tests PASS and Vite production build succeeds.

- [ ] **Step 9: Commit the integrated interface**

```bash
git add admin
git commit -m "feat: integrate LiveKit admin playground"
```

### Task 3: Full-system acceptance and documentation

**Files:**
- Modify: `README.md`
- Modify: `TECHNICAL_DECISIONS.md`
- Modify: `TECHNICAL_PLAN.md`
- Modify: `CORE_ACCEPTANCE.md`

**Interfaces:**
- Consumes: completed token endpoint and Playground UI.
- Produces: reproducible evaluator instructions and recorded AP-13 through AP-16 acceptance evidence.

- [ ] **Step 1: Document setup and operation**

Document `http://localhost:3000` → `Playground`, microphone permission, Start/End, expected states, active-voice behavior, reconnect, and the fact that tokens are server-generated and short-lived. Add troubleshooting for missing LiveKit variables, microphone denial, autoplay blocking, and an unavailable agent.

- [ ] **Step 2: Run all automated verification**

Run: `docker compose up -d --build`

Run: `docker compose run --rm backend pytest -q`

Run: `docker compose run --rm agent pytest -q`

Run: `docker compose run --rm admin pnpm test -- --run`

Run: `docker compose ps`

Expected: all suites PASS; `db`, `backend`, `agent`, and `admin` are running and healthy.

- [ ] **Step 3: Run repository safety checks**

Run: `git check-ignore -v .env`

Run: `git ls-files .env`

Run: `git diff --check`

Expected: `.env` is ignored, `git ls-files .env` prints nothing, and `git diff --check` prints nothing.

- [ ] **Step 4: Perform the manual browser gate**

In Chrome or Edge, open `http://localhost:3000`, choose Playground, grant microphone access, start a conversation, ask one known FAQ and confirm the correct spoken response, ask one unknown question and confirm the safe fallback plus queue record, verify visible Listening/Thinking/Speaking transitions, end the call, start a second call, and confirm the active voice is used. Repeat once with microphone permission denied and confirm the retryable English error.

- [ ] **Step 5: Record acceptance status**

Mark AP-13 through AP-16 and PG-1 through PG-5 with automated/manual evidence. State explicitly that browser media and real provider calls require valid local credentials and cannot be fully proven by unit tests alone.

- [ ] **Step 6: Commit B5 documentation**

```bash
git add README.md TECHNICAL_DECISIONS.md TECHNICAL_PLAN.md CORE_ACCEPTANCE.md
git commit -m "docs: complete integrated playground"
```
