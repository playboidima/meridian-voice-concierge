# Bonus B5 Integrated Playground Design

## Goal

Embed a complete English-only LiveKit voice test experience in the existing Meridian React admin panel while keeping all LiveKit secrets on the backend.

## PRD coverage

- AP-13: the admin panel contains an embedded voice test.
- AP-14: each new session uses the current active voice and current FAQ data.
- AP-15: an administrator can start, conduct, and end a full voice conversation.
- AP-16: the screen is clearly labelled `Playground` and `Test Mode`.
- PG-1 through PG-5: browser access, microphone input, audio output, visible state, Start and End controls.

## Architecture

The existing React admin gains a fourth `Playground` view. It uses LiveKit's official React components and Session API to fetch short-lived room credentials, connect, dispatch `meridian-concierge`, publish microphone audio, render agent audio, and expose the agent lifecycle state.

FastAPI adds `POST /api/livekit/token`. The endpoint reads `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, and `AGENT_NAME` only on the server, accepts the standard LiveKit token request shape, generates unique default room and participant identities, preserves the requested agent dispatch configuration, and returns only `server_url` and a short-lived `participant_token`. The browser never receives API keys or the API secret.

The existing Nginx `/api/` proxy keeps frontend calls same-origin. No separate playground service, iframe, authentication system, or database table is introduced.

## User experience

- Navigation label: `Playground`.
- Page label: `Playground · Test Mode`.
- Primary controls: `Start conversation`, `End conversation`, and microphone mute/unmute.
- States: `Disconnected`, `Connecting`, `Listening`, `Thinking`, `Speaking`, and `Error`.
- The page displays the active voice returned by `GET /api/voice/active`.
- Agent audio is rendered in the browser and an explicit audio-unlock control appears when browser autoplay rules require it.
- Ending the session releases the microphone and room connection. Leaving the view also cleans up the session.
- Permission, configuration, connection, and media errors use short English messages and allow retrying.

## Session behavior

Each Start action creates a new room and dispatches the configured agent. The agent already loads the active voice at session start and queries the backend for every guest question, so no new voice or FAQ synchronization mechanism is required.

## Security and scope

- Real credentials remain only in local `.env`, which is ignored by Git.
- Tokens expire after 10 minutes and grant only room join, publish, and subscribe access to the generated room.
- Authentication remains out of scope as stated by the PRD; the token endpoint is intended for the local evaluation environment.
- Camera, screen sharing, recordings, text chat, and a separate guest site are out of scope.

## Verification

- Backend tests cover missing configuration, successful token response, unique defaults, grants, TTL, and accepted dispatch configuration.
- React tests cover English labels, states, Start/End behavior, microphone errors, retry, active voice display, and cleanup.
- Production build and all existing test suites must pass.
- Manual Chrome or Edge verification covers microphone permission, known FAQ, unknown question recording, agent audio, state changes, End, and reconnect.

