# Start Session Specification

## 1. Overview
- **Goal**: Enable the mobile frontend to initiate an EV charging session at a specific connector, receive a stable session identifier, and stream real-time session progress via SSE throughout the charging lifecycle.
- **User Story**: As a mobile app user, I want to start a charging session at a selected connector so that I can monitor energy delivery and cost in real time without polling.

---

## 2. Functional Requirements

- [ ] **Initiate session**: Frontend calls `POST /api/begin_session` with `location_id`, `evse_uid`, and `connector_id`. The server generates a stable `session_request_id` and returns it immediately.
- [ ] **Idempotency**: If an active session request already exists for the same `(location_id, evse_uid, connector_id)` triple, the existing `session_request_id` is reused — no duplicate is created.
- [ ] **CPO command**: The server sends a `START_SESSION` command to the CPO over OCPI 2.2.1, including the RFID token (loaded from `RFID_FAKE_TOKEN_FILE_PATH`) and a `response_url` callback.
- [ ] **Session correlation**: When the CPO calls back `POST /ocpi/2.2.1/sessions/`, the server maps the CPO-assigned `session_id` to the existing `session_request_id` via the `sessions_requests` table.
- [ ] **Real-time updates**: After the CPO callback, session updates (`kwh`, `total_cost`, `currency`, `updated_at`) are streamed to the frontend over SSE on topic `{session_request_id}`.
- [ ] **Ongoing updates**: Subsequent CPO `PUT /ocpi/2.2.1/sessions/{session_id}` calls are saved and published to both the session SSE topic and the location SSE topic `{location_id}:{evse_id}`.
- [ ] **Data persistence**: Each session update is saved to `ocpi_sessions_updates`; the session itself is saved to `ocpi_sessions`.
- [ ] **UI/UX**: The frontend receives a single `session_id` field on success and opens an SSE connection using it. Each SSE `update` event carries the fields needed to refresh the charging progress UI (`kwh`, `total_cost`, `currency`).

---

## 3. Technical Constraints

- **Tech Stack**: FastAPI, SQLAlchemy async (psycopg3), `sse-starlette` for SSE, `httpx.AsyncClient` for all outbound HTTP, `aiocache` with `PickleSerializer` for partner data caching (TTL 600 s).
- **Architecture**: Dual-router pattern — `api_router` for frontend-facing routes (`/api/...`), `router` for OCPI standard routes (`/ocpi/2.2.1/...`). All business logic goes through service classes injected via `Depends()`. The pub/sub singleton (`OCPIPubSub`) is instantiated once in `dependencies.py` and shared across all requests.
- **Pub/Sub internals**: `OCPIPubSub` holds `dict[str, list[asyncio.Queue]]`. Each SSE subscriber gets its own `asyncio.Queue(maxsize=100)`. `publish()` iterates a copy of the subscriber list and uses `put_nowait` — slow subscribers have messages dropped silently. `unsubscribe()` removes the queue and deletes the topic key when the last subscriber leaves.
- **Boundaries**: Do not modify `database.py` partner caching logic. Do not instantiate `httpx.AsyncClient` globally — always use `async with` per request. Do not bypass `Depends()` for DB sessions or services.

---

## 4. Edge Cases & Error Handling

- **Missing Authorization header**: `auth_required` dependency raises `HTTP 401` with OCPI status `2001 INVALID_PARAMETERS` and message `"Missing Authorization header"`.
- **Missing env config**: If `RFID_FAKE_TOKEN_FILE_PATH` or `CALLBACK_BASE_URL` is not set, `start_session` raises `HTTP 500` with a descriptive configuration error message.
- **Partner not found**: `get_partner()` raises `PartnerNotFoundError` if no CPO partner is mapped to the given `(location_id, evse_id)`. Propagates as `HTTP 500` from `begin_session`.
- **CPO HTTP error**: `httpx.HTTPStatusError` is caught; the CPO response body (or reason phrase, or standard HTTP reason) is forwarded as the detail of an `HTTPException` with the CPO's status code.
- **CPO command timeout**: `httpx.AsyncClient` enforces a **30-second** timeout on the `START_SESSION` POST.
- **Duplicate session request**: Handled by the idempotency check in `get_request_id()` — no error, existing `session_request_id` is returned.
- **Slow SSE subscriber**: Queue is bounded to 100 messages; overflow messages are dropped via `put_nowait` without raising an error.
- **Disconnect detection**: Checked at the top of each `event_generator` loop iteration — disconnect is only acted upon after the next `queue.get()` unblocks.
- **Logging**: All errors logged via `logger.error(...)` with full exception detail. CPO command response logged at `DEBUG` level.

---

## 5. Acceptance Criteria (Success)

- [ ] `POST /api/begin_session` returns `HTTP 200` with `{"session_id": "<16-char hex>"}` when called with valid location/evse/connector identifiers.
- [ ] A second identical call to `POST /api/begin_session` before session completion returns the **same** `session_id`.
- [ ] `GET /ocpi/2.2.1/sessions/updates/{session_request_id}` returns `Content-Type: text/event-stream` and delivers an `update` event within 1 second of the CPO posting to `POST /ocpi/2.2.1/sessions/`.
- [ ] SSE event `data` contains valid JSON with fields `session_id`, `kwh`, `total_cost`, `currency`, `updated_at`.
- [ ] After CPO `PUT` update, both the session SSE topic and the location SSE topic receive the published message.
- [ ] On client SSE disconnect, the subscriber queue is removed from `_topics` and the topic key is deleted if empty.
- [ ] Missing `Authorization` header returns `HTTP 401`.
- [ ] CPO returning a non-2xx response causes `begin_session` to return `HTTP` matching the CPO status code.

---

## 6. Implementation Plan (Phased)

1. **Phase 1 — Setup**: Ensure `sessions_requests` table schema has `request_id`, `location_id`, `evse_id`, `connector_id`, `session_id` (nullable), `is_active`. Confirm `RFID_FAKE_TOKEN_FILE_PATH` and `CALLBACK_BASE_URL` are set in `.env`.
2. **Phase 2 — Session initiation**: Implement `POST /api/begin_session` → idempotency check → `session_request_id` generation → `save_session_request()` → forward to `start_session()` → return `BeginSessionResponse`.
3. **Phase 3 — CPO command**: Implement `POST /ocpi/2.2.1/commands/START_SESSION` → partner lookup (cached) → RFID token load → `httpx` POST to CPO with timeout → pass-through response.
4. **Phase 4 — CPO callback & pub/sub**: Implement `POST /ocpi/2.2.1/sessions/` → correlate IDs → `save_session()` → `create_and_save_session_update()` → `pubsub.publish(session_request_id, session_update)`.
5. **Phase 5 — SSE endpoint**: Implement `GET /ocpi/2.2.1/sessions/updates/{session_request_id}` → `pubsub.subscribe()` → `event_generator` loop → disconnect handling → `pubsub.unsubscribe()`.
6. **Phase 6 — Ongoing updates**: Implement `PUT /ocpi/2.2.1/sessions/{session_id}` → fallback to create path if no existing session → publish to both session and location topics.
