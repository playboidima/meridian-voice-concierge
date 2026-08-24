# Bonus B3 React Admin Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Dockerized React admin panel that demonstrates AP-1–AP-8 through the existing B1/B2 APIs.

**Architecture:** A Vite React SPA uses a focused native-fetch API module and small form/view components. A multi-stage Dockerfile builds static assets; Nginx serves them and proxies `/api` to the healthy Backend.

**Tech Stack:** React 18, Vite, Vitest, React Testing Library, plain CSS, Nginx, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-08-24-bonus-b3-react-admin-design.md`

## Global Constraints

- Preserve every Core, B1, and B2 Backend contract.
- Do not add authentication, voice configuration, Playground, routing, pagination, Redux, or a UI component library.
- Do not expose embeddings or include secrets in frontend source/bundles.
- `docker compose up --build` must start the new `admin` service with the existing stack.

---

### Task 1: React behavior and API client

**Files:**
- Create: `admin/package.json`, `admin/index.html`, `admin/src/api.js`, `admin/src/App.jsx`, `admin/src/main.jsx`, `admin/src/styles.css`
- Create: `admin/src/App.test.jsx`, `admin/src/test/setup.js`, `admin/vite.config.js`

**Interfaces:**
- Consumes: B1/B2 endpoints under relative `/api/admin/...` paths.
- Produces: `faqApi` request methods and a two-view `App` component.

- [ ] Write Vitest/Testing Library tests that mock `fetch` at the HTTP boundary and verify: initial FAQ loading/filtering; create form submission; unanswered view loading; convert submission; dismiss confirmation; visible server error.
- [ ] Run `npm test -- --run` in the admin test container/environment and confirm RED because the app/API modules are absent.
- [ ] Implement `api.js` with one request helper that parses JSON, extracts FastAPI `detail`, and exposes list/create/update/delete/convert/dismiss methods.
- [ ] Implement the accessible two-view React UI with controlled forms, loading/empty/error/success states, refresh after mutations, client-side FAQ filtering, and native delete/dismiss confirmation.
- [ ] Add responsive premium-styled plain CSS without external assets or fonts.
- [ ] Run `npm test -- --run` and confirm GREEN.

### Task 2: Production container and Compose integration

**Files:**
- Create: `admin/Dockerfile`, `admin/nginx.conf`, `admin/.dockerignore`
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: Vite `dist/` and Compose Backend service.
- Produces: healthy `admin` at port `3000`, with `/api/` proxied to Backend.

- [ ] Add an Nginx configuration with SPA fallback, `/api/` proxy preserving the path, and `/health` returning `200 ok`.
- [ ] Add a multi-stage Dockerfile: Node installs locked dependencies and runs tests/build; Nginx serves `dist`.
- [ ] Add Compose `admin`, port `3000:80`, Backend health dependency, and HTTP health check.
- [ ] Run `docker compose config --quiet`, then `docker compose up --build -d admin`.
- [ ] Verify `http://localhost:3000`, `http://localhost:3000/health`, and proxied `http://localhost:3000/api/admin/faqs` return successful responses.

### Task 3: Documentation and full acceptance

**Files:**
- Modify: `README.md`, `CORE_ACCEPTANCE.md`, `TECHNICAL_PLAN.md`

**Interfaces:**
- Consumes: final admin URL, commands, and automated evidence.
- Produces: beginner-friendly B3 launch/test instructions and AP/NF-3 evidence.

- [ ] Document `http://localhost:3000`, the two views, Docker launch, frontend test/build commands, and current B3 boundaries.
- [ ] Mark AP-1–AP-8 demonstrable through React and `Bonus B3 — ready for manual review`; do not mark voices or Playground complete.
- [ ] Run `docker compose config --quiet`; frontend tests/build; full Backend suite; Agent suite; opt-in PostgreSQL suites; `docker compose ps`; secret scan; `git diff --check`.
- [ ] Confirm all four services are healthy and no keys occur in frontend source or built assets.
- [ ] Commit the B3 implementation and stop at the browser manual checkpoint.
