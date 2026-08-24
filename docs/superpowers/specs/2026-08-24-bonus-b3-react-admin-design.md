# Bonus B3: React Admin Panel Design

## Goal

Add a beginner-friendly desktop React admin panel for the already implemented
FAQ CRUD (AP-1–AP-4) and unanswered queue (AP-5–AP-8), while preserving all
Core, B1, and B2 API contracts.

## Scope

The panel has two views:

1. **FAQ** — list, client-side search, create, edit, and confirmed delete.
2. **Unanswered Queue** — open questions with frequency and last-seen time,
   convert to FAQ with answer/category input, and confirmed dismiss.

Voice configuration, voice preview, authentication, pagination, routing,
integrated Playground, booking, and payments are outside B3.

## Architecture

- `admin/` is a Vite React application using JavaScript, native `fetch`, and
  plain CSS. No state-management or component-library dependency is needed.
- A small API module owns HTTP requests and translates Backend error payloads.
- The main application owns view selection, loading, refresh, and user-visible
  errors. Focused form components own their draft values and validation.
- A production multi-stage Dockerfile builds the Vite assets and serves them
  with Nginx.
- Nginx serves the SPA and proxies `/api/` to `http://backend:8000`, avoiding
  CORS changes and keeping Backend URLs out of the browser configuration.
- Docker Compose adds `admin`, exposes port `3000`, and waits for the healthy
  Backend. Existing services and environment variables remain unchanged.

## User Experience

### FAQ view

- A search input filters question, answer, and category without another API
  request.
- `Add FAQ` opens a simple form with question, answer, and category.
- `Edit` pre-fills the same form.
- `Delete` requires explicit confirmation.
- Successful mutations close/reset the form and refresh the list.

### Unanswered view

- Cards/rows show original question, frequency, and last-seen timestamp.
- `Convert` opens answer/category fields and calls the B2 convert endpoint.
- `Dismiss` requires explicit confirmation.
- Processed entries disappear after the queue refresh.

Both views show loading, empty, success, and error states. The layout must be
usable in common desktop browser widths and remain readable on a narrow window.

## API Contracts Used

- `GET/POST /api/admin/faqs`
- `PUT/DELETE /api/admin/faqs/{faq_id}`
- `GET /api/admin/unanswered`
- `POST /api/admin/unanswered/{id}/convert`
- `POST /api/admin/unanswered/{id}/dismiss`

The UI displays useful messages for `404`, `409`, `422`, network errors, and
unexpected server errors. It never receives or renders FAQ embeddings and never
contains API keys or LiveKit credentials.

## Testing

- Vitest and React Testing Library cover view loading, FAQ filtering, create
  submission, unanswered conversion, dismiss confirmation, and visible errors.
- `npm run build` proves the production bundle builds.
- Docker verification checks the Nginx page and proxied Backend health/API.
- Existing Backend, Agent, and PostgreSQL suites remain green.
- Manual acceptance covers one FAQ lifecycle and one unanswered action in the
  browser.

## Acceptance

- `docker compose up --build` starts `db`, `backend`, `agent`, and `admin`.
- The panel is available at `http://localhost:3000`.
- AP-1–AP-8 can be demonstrated without direct database access.
- No B4 voice or Playground functionality is claimed or started.
