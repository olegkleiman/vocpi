# End Session Specification

## 1. Overview
- **Goal**: Enable the mobile frontend to stop an active charging session and retrieve the final Charge Detail Record (CDR) containing total energy, cost, and duration — using long-polling to await the CPO callback.
- **User Story**: As a mobile app user, I want to stop my charging session and immediately receive my final receipt so that I know exactly what I was charged.

---

## 2. Functional Requirements

- [ ] **Stop session**: Frontend calls `POST /api/end_session` with the `session_id` (which is the `session_request_id` issued at session start). The server resolves the CPO `session_id` and sends a `STOP_SESSION` command.
- [ ] **Unknown session handling**: If the `session_request_id` cannot be resolved to a CPO `session_id`, the server returns an OCPI `UNKNOWN_SESSION` response without calling the CPO.
- [ ] **CPO command**: The server sends a `STOP_SESSION` command to the CPO over OCPI 2.2.1 with a `response_url` callback and the CPO `session_id`.
- [ ] **Session cleanup**: After the stop command is dispatched, the server marks the session request as inactive (`is_active = false`) in `sessions_requests`.
- [ ] **CDR receipt — long-polling**: Frontend calls `GET /api/cdrs/updates/{session_request_id}`. If the CDR is already in the DB it is returned immediately; otherwise the server parks the request using an `asyncio.Event` and waits up to `timeout` seconds.
- [ ] **CDR callback**: When the CPO posts `POST /ocpi/2.2.1/cdrs`, the server saves the CDR and signals any parked long-poll waiter via the `asyncio.Event`.
- [ ] **Data persistence**: The CDR is saved to the `cdrs` table linked by both `session_id` and `session_request_id`. The full OCPI CDR JSON is stored as `cdr_json`.
- [ ] **UI/UX**: The frontend receives a `CDRResponse` with `session_id`, `cdr_id`, `currency`, `total_energy_kwh`, `total_cost`, `duration` (formatted as `HH:MM`), `started_at`, `ended_at`, and `location` (name or address string).

---

## 3. Technical Constraints

- **Tech Stack**: FastAPI, SQLAlchemy async (psycopg3), `httpx.AsyncClient` for all outbound HTTP, `asyncio.Event` for long-poll synchronisation, `aiocache` with `PickleSerializer` for partner data caching (TTL 600 s).
- **Architecture**: Dual-router pattern — `api_router` for frontend-facing routes (`/api/...`), `router` for OCPI standard routes (`/ocpi/2.2.1/...`). Business logic in `SessionService` and `CDRService`, injected via `Depends()`. `cdr_waiters: dict[str, asyncio.Event]` is a module-level dict in `cdrs.py` shared across the two CDR endpoints in the same process.
- **Long-poll mechanism**: `cdr_waiters` maps `session_request_id → asyncio.Event`. `get_receipt` creates the event and calls `asyncio.wait_for(event.wait(), timeout=timeout)`. `receive_cdr` calls `event.set()` after saving. The `finally` block in `get_receipt` always removes the entry from `cdr_waiters`.
- **Timeout**: Default long-poll wait is **10 seconds**, overridden by the `timeout` value parsed from the client's `Keep-Alive` header (`timeout=N, max=...` format) if present.
- **CDR response transformation**: `CDRResponse` uses a `model_validator` to flatten the OCPI `location` object to a name/address string, and to convert `total_time` (float hours) to `HH:MM` duration string.
- **Boundaries**: Do not modify `database.py` partner caching logic. Do not instantiate `httpx.AsyncClient` globally — always use `async with` per request. Do not bypass `Depends()` for DB sessions or services. Do not use `asyncio.Event` across processes — long-polling only works within a single server instance.

---

## 4. Edge Cases & Error Handling

- **Unknown session**: If `get_session_id(session_request_id)` returns `None`, `end_session` returns `HTTP 202` with OCPI status `3000 SERVER_ERROR` and command result `UNKNOWN_SESSION` — no CPO call is made.
- **Partner not found**: `get_partner()` raises `PartnerNotFoundError` if no CPO is mapped to the session's `(location_id, evse_id)`. Propagates as `HTTP 500` from `stop_session`.
- **CPO HTTP error**: `httpx.HTTPStatusError` is caught; the CPO response body (or reason phrase, or standard HTTP reason) is forwarded as the detail of an `HTTPException` with the CPO's status code.
- **CPO command timeout**: `httpx.AsyncClient` enforces a **30-second** timeout on the `STOP_SESSION` POST.
- **CDR long-poll timeout**: If the CPO does not post the CDR within `timeout` seconds, `get_receipt` raises `HTTP 408 Request Timeout`.
- **CDR event triggered but DB miss**: If `asyncio.Event` is set but `get_cdr()` still returns `None` (race condition), `get_receipt` raises `HTTP 404`.
- **CDR already present**: If the CDR exists in the DB before the client calls `get_receipt`, it is returned immediately without creating a waiter.
- **Missing `CALLBACK_BASE_URL`**: `stop_session` raises `HTTP 500` with a descriptive configuration error message.
- **Logging**: All errors logged via `logger.error(...)` with full exception detail. CDR waiter notifications logged at `DEBUG` level.

---

## 5. Acceptance Criteria (Success)

- [ ] `POST /api/end_session` returns `HTTP 202` when called with a valid `session_request_id` that maps to an active CPO session.
- [ ] After `end_session`, the `sessions_requests` row has `is_active = false`.
- [ ] `GET /api/cdrs/updates/{session_request_id}` returns the `CDRResponse` immediately if the CDR is already in the DB.
- [ ] `GET /api/cdrs/updates/{session_request_id}` blocks and returns the `CDRResponse` within 1 second of the CPO posting `POST /ocpi/2.2.1/cdrs`.
- [ ] `CDRResponse.duration` is formatted as `HH:MM` derived from `total_time` (hours float).
- [ ] `CDRResponse.location` is a plain string (name or address), not an object.
- [ ] `GET /api/cdrs/updates/{session_request_id}` returns `HTTP 408` if no CDR arrives within the timeout window.
- [ ] Calling `end_session` with an unknown `session_request_id` returns `HTTP 202` with `UNKNOWN_SESSION` result and does not call the CPO.
- [ ] CPO returning a non-2xx response causes `end_session` to return `HTTP` matching the CPO status code.

---

## 6. Implementation Plan (Phased)

1. **Phase 1 — Setup**: Confirm `cdrs` table schema has `session_id`, `session_request_id`, `cdr_id`, `cdr_json`. Confirm `CALLBACK_BASE_URL` is set in `.env`.
2. **Phase 2 — Stop session**: Implement `POST /api/end_session` → resolve CPO `session_id` via `SessionService.get_session_id()` → unknown session guard → call `stop_session()` → `delete_session_request()` → return response.
3. **Phase 3 — CPO command**: Implement `POST /ocpi/2.2.1/commands/stop_session` → resolve `(location_id, evse_id)` via `get_location_from_session_id()` → partner lookup (cached) → `httpx` POST to CPO with timeout → validate and return `OCPIResponse`.
4. **Phase 4 — CDR long-polling**: Implement `GET /api/cdrs/updates/{session_request_id}` → immediate DB check → create `asyncio.Event` in `cdr_waiters` → `asyncio.wait_for(event.wait(), timeout)` → re-fetch CDR → cleanup in `finally`.
5. **Phase 5 — CPO CDR callback**: Implement `POST /ocpi/2.2.1/cdrs` → resolve `session_request_id` via `get_request_id_by_session_id()` → `CDRService.save_cdr()` → signal `cdr_waiters` event if waiter exists → return `OCPIResponse`.
6. **Phase 6 — CDR response shaping**: Validate `CDRResponse` model_validator correctly maps `location` object → string and `total_time` → `HH:MM` duration from the stored `cdr_json`.