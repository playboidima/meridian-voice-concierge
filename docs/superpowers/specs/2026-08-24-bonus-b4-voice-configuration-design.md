# Bonus B4: Voice Configuration Design

## Goal

Add the PRD voice-configuration bonus to the existing Meridian admin system:
four named voice personalities, preview audio, one clearly active voice, and
application of a changed voice to every new LiveKit conversation without a
service restart.

This stage covers PRD criteria VX-1 through VX-4, AP-9 through AP-12, and
NF-5. The integrated admin Playground (AP-13 through AP-16) remains B5.

## Constraints

- The user-facing admin interface remains entirely English.
- Voice selection must not require restarting Docker services.
- A voice change affects new conversations; an already running conversation
  keeps the voice with which it started.
- No LiveKit, Cartesia, or other secret may be stored in PostgreSQL, frontend
  code, preview assets, logs, or Git.
- The system continues to start with `docker compose up`.
- LiveKit Inference remains the TTS integration, so no separate Cartesia API
  key becomes a runtime requirement.
- B4 does not embed a Playground or add authentication, booking, payment, or
  multilingual behavior.

## Voice Catalog

The admin UI uses the four names and target personalities specified by the
PRD. Provider catalog names remain an implementation detail.

| UI name | PRD personality | Cartesia catalog voice | Candidate voice ID |
| --- | --- | --- | --- |
| James | Mature, warm British male; professional and refined | Confident British Man | `63ff761f-c1e8-414b-b969-d1833d1c870c` |
| Sofia | Friendly, elegant female with a light European accent | British Lady | `79a125e8-cd45-4c13-8a67-188112f4dd22` |
| Marcus | Confident, energetic, modern American male | Blake | `a167e0f3-df7e-4d52-a9c3-f949145efdab` |
| Elena | Calm, reassuring, clear American female | Jacqueline | `9626c31c-bec5-4cca-baa8-f8ba9e84c8bc` |

The IDs are candidate defaults until each one passes a real LiveKit Inference
generation check. A failing or unavailable candidate must be replaced by a
default Cartesia voice with the same PRD gender/accent/personality; the UI name
and PRD description do not change. James is initially active.

Every preview uses the same sentence so differences are easy to compare:

> Welcome to The Meridian. It is my pleasure to assist you today.

## Data Model

Add `VoiceConfig` with these fields:

- `id`: integer primary key;
- `name`: unique stable UI name (`James`, `Sofia`, `Marcus`, or `Elena`);
- `provider_voice_id`: unique Cartesia voice UUID;
- `description`: PRD personality text shown in the admin UI;
- `preview_path`: repository-controlled relative preview path;
- `is_active`: boolean;
- `updated_at`: timezone-aware timestamp.

An Alembic migration creates the table, seeds exactly four rows, and creates a
PostgreSQL partial unique index that permits only one `is_active = true` row.
The regular startup seed also reconciles the four built-in rows by stable
`name`, allowing descriptions, provider IDs, and preview paths to be updated
idempotently without creating duplicates. It never creates arbitrary voices
from client input.

## Backend API

### `GET /api/admin/voices`

Returns the four voices ordered James, Sofia, Marcus, Elena. Each response
contains `id`, `name`, `description`, `is_active`, `preview_url`, and
`updated_at`. It does not expose provider credentials. `provider_voice_id` is
not needed by the browser and is omitted.

### `POST /api/admin/voices/{voice_id}/activate`

Within one transaction, lock the relevant voice rows, clear the previous
active flag, activate the requested row, and commit. Return the newly active
voice. An unknown ID returns `404` with `Voice not found`. Concurrent requests
must finish with exactly one active row.

### `GET /api/admin/voices/{voice_id}/preview`

Return the matching committed MP3 asset with `audio/mpeg` and cache headers.
An unknown voice or missing asset returns `404`; no runtime TTS call and no
secret is required.

### `GET /api/voice/active`

Internal runtime endpoint used by the agent. Return `name`,
`provider_voice_id`, and `updated_at` for the single active voice. If database
state is unexpectedly invalid, log an error without secrets and return `503`
rather than selecting an arbitrary database row.

## Preview Assets

Store four short MP3 files under the Backend-owned static asset directory.
Each file must be generated using its configured provider voice and the common
preview sentence. Generated audio contains no credential metadata and is safe
to commit.

The Backend streams these files so the React app uses same-origin `/api`
requests through the existing Nginx proxy. The frontend bundle contains no
provider URL, key, or voice UUID.

If real preview generation cannot run automatically through the current
LiveKit account, the stage is not marked complete: the exact missing manual
generation step is reported, and placeholder or mismatched audio is not used.

## Agent Runtime Flow

At the start of each `meridian_agent` job, before constructing
`AgentSession`, the agent requests `/api/voice/active` through its existing
Backend client:

1. If the response is valid, construct `inference.TTS` with the returned
   `provider_voice_id`.
2. If the request times out, fails, or returns invalid data, log a concise
   warning and use local `TTS_VOICE` as the fallback.
3. Keep that TTS object for the lifetime of the current session.

The next job performs a fresh lookup, so an admin change applies immediately
to new conversations without restarting the agent. No polling is needed, and
an in-progress conversation cannot change voice mid-sentence.

## React Admin Experience

Add a third sidebar destination named `Voice Studio`. Its header reads
`Voice Studio` with the description `Choose how The Meridian greets every
guest.`

The page displays four voice cards. Each card includes:

- voice name;
- PRD personality description;
- gender/accent summary derived from the fixed catalog;
- `Preview` / `Stop preview` control;
- `Set active` action for inactive voices;
- a prominent `Active voice` badge for the selected voice.

Only one preview can play at a time. Starting another preview stops the first.
Audio completion and manual stopping return the button to `Preview`. A failed
audio request displays an English error and does not change the active voice.

After successful activation, React reloads the voice list (or replaces it with
the returned canonical state), shows `Voice changed to <name>.`, and moves the
active badge immediately. While activation is pending, selection controls are
disabled to avoid duplicate requests.

## Failure Handling

- List failure: retain the page shell and show an English retryable error.
- Activation `404`: show `Voice not found.` and reload the catalog.
- Activation network/server error: keep the previous active state and show the
  Backend error.
- Preview `404` or media failure: stop playback and show
  `Voice preview is unavailable.`
- Agent active-voice lookup failure: use `TTS_VOICE`; do not fail the voice
  session solely because admin configuration is unavailable.
- Invalid multiple-active database state: internal endpoint returns `503` and
  emits a structured error; the admin list remains inspectable for diagnosis.

## Testing

### Backend

- migration/seed produces exactly four catalog rows and one active row;
- list ordering and response contract;
- activation changes the active row;
- unknown activation and preview return `404`;
- preview returns non-empty `audio/mpeg` data;
- repeated seed is idempotent;
- PostgreSQL concurrency test proves exactly one active row after simultaneous
  activation requests.

### Agent

- active voice is requested before `AgentSession` construction;
- returned provider ID is passed to `inference.TTS`;
- Backend failure falls back to `TTS_VOICE`;
- separate new sessions can receive different active voice IDs.

### React

- four cards and one active badge render;
- Preview plays and stopping/second preview enforces one audio instance;
- successful activation updates the badge and notice;
- failed activation preserves the previous active selection;
- all B4 UI copy is English.

### Integrated verification

- full Backend, Agent, and React suites pass;
- `docker compose up --build -d` leaves all services healthy;
- all four preview controls play distinct, matching samples;
- select a different voice, start a new LiveKit session, and confirm the new
  greeting uses that voice without restarting Docker;
- start another new session after switching back and confirm the voice changes
  again;
- existing Core FAQ and unanswered-question behavior remains unchanged.

## Acceptance Boundary

B4 is complete only when all VX-1 through VX-4, AP-9 through AP-12, and NF-5
are demonstrated. The final handoff clearly separates automated evidence from
the user's required listening checks in the admin UI and LiveKit.

The integrated Playground is explicitly deferred to B5.
