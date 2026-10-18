# Operations Under Pressure: Build Plan

One-day full-stack challenge (Newtonite). Goal: a small system with well-considered behaviour, not a big system with half-done features.

---

## 1. Problem in one line

Teams lose track of operational work in chats and spreadsheets. We need one place where every request has **one owner, one state, one history**, and where concurrent users can't corrupt each other's work.

This is a **coordination and correctness problem**, not a task-list problem. Every design choice below maps to a pain point in the brief.

---

## 2. Assumptions (also goes into README)

1. A request belongs to **exactly one team**. Cross-team work is done by re-assigning the team (logged as an event).
2. A user can be in many teams with a **different role per team**. No global roles.
3. A request has **at most one owner** at a time. Unowned requests sit in a visible inbox.
4. Approval requirements depend on the **request type** (`approval_mode`: none / before / after / both).
5. The person who did the work **cannot** approve completion of that same work.
6. History is **append-only**. Nothing is edited or deleted from the event log.
7. Auth is simple (seeded users + JWT login). SSO is out of scope.
8. Notifications are in-app only. Email/Slack are pluggable later.
9. Polling (not WebSockets) is acceptable for freshness in v1.

---

## 3. Tech stack and why

| Layer | Choice | Reason |
|---|---|---|
| Backend | **FastAPI** (Python) | Fast to build, typed, clean dependency injection for authz |
| DB | **PostgreSQL** | Transactions, row locks, `SKIP LOCKED`, partial indexes, full-text search |
| ORM / migrations | SQLAlchemy 2 + Alembic | Explicit control over SQL where correctness matters |
| Worker | Same codebase, separate process | Outbox consumer; no extra infra (no Redis/Kafka) |
| Frontend | **React + Vite + TanStack Query** | Server-state caching, optimistic updates, rollback |
| Run | `docker compose up` | One command for reviewers |
| Tests | pytest (+ real Postgres in compose) | Concurrency tests need a real DB, not mocks |

---

## 4. Architecture

```
 React (Vite + TanStack Query)
        |  REST/JSON, JWT, Idempotency-Key, If-Match-style version
        v
 FastAPI app
   |- auth dependency (who is the user)
   |- authz layer (user + team + role + resource -> allow/deny)
   |- service layer (state machine, claim, transitions, comments)
   |       one DB transaction = state change + event row + outbox row
   v
 PostgreSQL
   users, teams, team_memberships, request_types,
   requests, request_events, comments,
   idempotency_keys, outbox, notifications
   ^
   |  poll with FOR UPDATE SKIP LOCKED
 Worker process
   reads outbox -> creates notifications (idempotent) -> retries / dead-letter
```

Key principle: **the service layer is the only place that changes state.** Routes are thin. The UI is never trusted.

---

## 5. Data model

```
users(id, email, name, password_hash, created_at)
teams(id, name)
team_memberships(user_id, team_id, role)          -- PK(user_id, team_id)
                                                  -- role: member | approver | lead
request_types(id, team_id, name, approval_mode, sla_hours)
                                                  -- approval_mode: none|before|after|both

requests(
  id, team_id, type_id, title, description,
  status, priority,                               -- low|medium|high|urgent
  owner_id NULL, created_by,
  version INT NOT NULL DEFAULT 1,                 -- optimistic locking
  due_at, last_activity_at,
  created_at, updated_at,
  search_tsv tsvector                             -- full-text search
)

request_events(                                   -- APPEND-ONLY
  id BIGSERIAL, request_id, actor_id,
  type,                                           -- created|status_changed|owner_changed|
                                                  -- priority_changed|commented|approved|rejected|...
  from_value JSONB, to_value JSONB, reason,
  created_at
)

comments(id, request_id, author_id, body, created_at)

idempotency_keys(
  user_id, key, endpoint, request_hash,
  response_status, response_body, created_at      -- PK(user_id, key)
)

outbox(
  id, event_id, topic, payload JSONB,
  status,                                         -- pending|processing|done|dead
  attempts, next_attempt_at, last_error, created_at
)

notifications(
  id, user_id, request_id, kind, body, read_at,
  dedupe_key UNIQUE                               -- makes the consumer idempotent
)
```

### Indexes (for scale: tens of thousands of active items, huge history)

- `requests(team_id, status, last_activity_at DESC, id DESC)` for list + keyset pagination
- `requests(owner_id, status)` for "my work"
- Partial: `requests(team_id, last_activity_at) WHERE status NOT IN ('done','cancelled')` for stale/attention queries
- Partial: `requests(team_id, created_at) WHERE owner_id IS NULL AND status IN ('new','triage')` for the unowned inbox
- GIN on `requests.search_tsv`
- `request_events(request_id, id DESC)` for timeline
- `outbox(next_attempt_at) WHERE status='pending'`

---

## 6. Workflow (state machine)

```
New -> Triage -> [Awaiting start approval] -> In progress -> [Awaiting completion approval] -> Done
                                                   \-> Cancelled (from any non-terminal state)
```
Brackets = only if the request type's `approval_mode` requires it.

| approval_mode | Path |
|---|---|
| none | Triage -> In progress -> Done |
| before | Triage -> Awaiting start approval -> In progress -> Done |
| after | Triage -> In progress -> Awaiting completion approval -> Done |
| both | full chain |

### Allowed transitions

| From | To | Who | Guard |
|---|---|---|---|
| New | Triage | member+ | none |
| Triage | Awaiting start approval | owner or lead | owner + priority set; mode is before/both |
| Triage | In progress | owner or lead | owner + priority set; mode is none/after |
| Awaiting start approval | In progress | **approver** | approver != requester/owner; reason logged |
| Awaiting start approval | Triage | **approver** | rejection, reason required |
| In progress | Awaiting completion approval | owner | mode is after/both |
| In progress | Done | owner | mode is none/before |
| Awaiting completion approval | Done | **approver** | approver != owner |
| Awaiting completion approval | In progress | **approver** | rejection, reason required |
| any non-terminal | Cancelled | lead (or creator while New) | reason required |

Implementation: one `TRANSITIONS` table in code, plus `validate_transition(request, target, actor)`. Illegal move returns `409` (state conflict) or `403` (not allowed). The workflow lives in **one module** so it is easy to explain and test.

---

## 7. Authorization

Permission = **(user, team, role) checked against the specific resource**, never just a global flag.

| Action | member | approver | lead |
|---|---|---|---|
| Create request, comment, view team's requests | yes | yes | yes |
| Claim unowned request | yes | yes | yes |
| Work own request (transition as owner) | yes | yes | yes |
| Approve / reject | no | yes (not own work) | yes (not own work) |
| Reassign, change priority, cancel | no | no | yes |
| Attention (manager) view | no | no | yes |

Rules:
- Every endpoint loads the request, finds the user's membership **for that request's team**, and checks the role. No membership = `404` (don't leak existence).
- Implemented as a FastAPI dependency: `require_permission("approve")`, used by every mutating route.
- Separation of duties: approver of the completion step cannot be the owner.
- List endpoints are scoped in SQL to the user's teams. Never filter after loading.

---

## 8. The five critical behaviours (correctness beyond CRUD)

### 8.1 Atomic claim (two users take the same work)
```sql
UPDATE requests
SET owner_id = :me, version = version + 1, last_activity_at = now()
WHERE id = :id AND owner_id IS NULL
RETURNING *;
```
0 rows updated -> `409 already claimed by <name>`. The database arbitrates, not the app.

### 8.2 Optimistic locking (stale information)
- Client sends the `version` it last saw.
- `UPDATE ... WHERE id = :id AND version = :v` then `version = version + 1`.
- 0 rows -> `409` with the **current** state plus the **events since that version**.
- UI shows "this request changed while you were editing" with a diff and a choice: reload or reapply.

### 8.3 Idempotent operations (user retries)
- Mutating endpoints accept `Idempotency-Key`.
- On first use: run the action, store `(user, key, request_hash, response)` in the same transaction.
- Same key again: return the **stored response**, no second effect.
- Same key with a different payload: `422`.
- Concurrent duplicates: unique PK on `(user_id, key)` makes the second one wait or fail cleanly.

### 8.4 Workflow enforcement + resource-level authz
- Backend rejects skipped steps and wrong-role actions regardless of the UI.
- Tested by calling the API directly as the "wrong" user.

### 8.5 Reliable async processing (transactional outbox)
- In the **same transaction** as the state change: insert `request_events` row + `outbox` row. Either both exist or neither does.
- Worker loop: `SELECT ... FROM outbox WHERE status='pending' AND next_attempt_at <= now() FOR UPDATE SKIP LOCKED LIMIT n`.
- Handler creates a notification with a **unique `dedupe_key`** (`event_id:user_id:kind`). Running twice has no extra effect (at-least-once delivery + idempotent consumer).
- Failure: `attempts++`, exponential backoff in `next_attempt_at`. After N attempts -> `dead` with `last_error`, visible for inspection.
- Delay is harmless: the primary action never waits on notifications.

---

## 9. API design

REST, JSON, cursor pagination, consistent error shape `{code, message, details}`.

```
POST   /auth/login
GET    /me                                   -> user, teams, roles

GET    /requests                             -> list (filters, search, cursor)
POST   /requests                             -> create          [Idempotency-Key]
GET    /requests/{id}                        -> detail + version
PATCH  /requests/{id}                        -> edit fields     [version required]
POST   /requests/{id}/claim                  -> atomic claim    [Idempotency-Key]
POST   /requests/{id}/transition             -> {to, reason, version}
POST   /requests/{id}/assign                 -> lead reassigns  [version]
GET    /requests/{id}/events                 -> timeline (cursor)
POST   /requests/{id}/comments               -> comment         [Idempotency-Key]

GET    /approvals/queue                      -> awaiting my approval
GET    /attention                            -> manager "needs attention" buckets
GET    /notifications                        -> my notifications (cursor)
POST   /notifications/{id}/read
```

List query params: `team`, `status`, `owner` (`me`/`none`/id), `priority`, `type`, `q` (full-text), `cursor`, `limit` (max 50).

**Keyset pagination:** order by `(last_activity_at DESC, id DESC)`, cursor = last row's pair. No `OFFSET`, so it stays fast with large tables.

Error semantics: `401` unauthenticated, `403` role insufficient, `404` no access/not found, `409` version/claim/state conflict, `422` validation / idempotency mismatch.

---

## 10. "Needs attention" view (manager)

Computed in SQL, scoped to teams the user leads, each bucket paginated/limited with counts:

| Bucket | Rule |
|---|---|
| Unowned | status in (new, triage) and owner is null, older than X hrs |
| Stale | active status and `last_activity_at` older than 24h |
| Overdue | `due_at < now()` and not terminal (due_at = created_at + type SLA by default) |
| Stuck in approval | awaiting approval for more than 8h |
| Urgent | priority = urgent and not terminal |

Thresholds are constants in one config file. No charts needed; a prioritized list is more useful.

---

## 11. Frontend

Pages:
1. **Login** (seeded demo users)
2. **Work list**: filters (status, owner, priority, team), search box, infinite scroll via cursor, "My work" shortcut
3. **Request detail**: header (status, priority, owner, version), action buttons shown **only if allowed** (but backend enforces), comments, **"Why?" timeline** from `request_events`
4. **Approval queue** (approvers)
5. **Attention** (leads)
6. **Notifications** dropdown (polling every ~15s)

State management:
- TanStack Query for server state; list and detail are separate query keys.
- **Optimistic updates** for claim, comment, and transitions.
- On server rejection: roll back, show toast with reason. On `409`: refetch and open the conflict dialog with what changed.
- Every mutation generates one `Idempotency-Key` per user intent (reused on retry, new on a new click).
- Buttons disable while a mutation is in flight; unclear network failures can be retried safely.

---

## 12. Testing strategy (test what would be dangerous if wrong)

Run against real Postgres.

| Risk | Test |
|---|---|
| Two people claim the same work | Fire N concurrent claims -> exactly one succeeds, others get 409 |
| Stale edit overwrites newer change | Two clients, same version -> second gets 409, data unchanged |
| Retry causes double effect | Same `Idempotency-Key` twice -> one event, identical response |
| Approval skipped | Try New -> Done, Triage -> Done on a `before` type -> rejected |
| Wrong role acts | Employee calls approve directly -> 403; non-member -> 404 |
| Owner approves own work | Rejected |
| Event log integrity | Every transition creates exactly one event; failed action creates none |
| Outbox reliability | Handler fails twice then succeeds -> one notification; run twice -> still one |
| Dead-letter | Handler always fails -> status `dead` after N attempts |
| Pagination | No duplicates/skips across pages while new rows are inserted |

---

## 13. Step-by-step build process

Target: one working day (~9-10h). Do steps in order; each ends in something runnable.

### Step 1: Project skeleton + schema (1h 30m)
- Repo layout: `backend/`, `frontend/`, `docker-compose.yml`, `docs/`.
- Compose: postgres, api, worker, web.
- SQLAlchemy models + Alembic migration for all tables and indexes in section 5.
- `seed` command: 3 teams, ~12 users with mixed roles, request types (none/before/after/both), ~200 requests with events (enough to feel pagination).
- Done when: `docker compose up` gives a migrated, seeded DB.

### Step 2: Auth + authorization layer (1h)
- Login, JWT, `get_current_user` dependency.
- Membership lookup + `require_permission(action)` dependency.
- Done when: a route returns 403/404 correctly for wrong role / non-member.

### Step 3: Core service layer (2h 30m) (most important)
- `workflow.py`: transitions table + validators.
- `services/requests.py`: create, edit (version check), claim (atomic), transition, assign, comment.
- Each service call = **one transaction**: state change + `request_events` + `outbox`.
- Idempotency middleware/helper.
- Done when: all Section 8.1 to 8.4 behaviours work via API.

### Step 4: Tests for the core (45m, write now, not at the end)
- Concurrency, locking, idempotency, workflow, authz tests from Section 12.
- Done when: they pass and fail when you deliberately break the logic.

### Step 5: Outbox + worker (1h)
- Worker loop with `SKIP LOCKED`, backoff, dead-letter, idempotent notification creation.
- Add outbox tests.
- Done when: kill/fail handler mid-way and nothing is lost or duplicated.

### Step 6: Read APIs (1h)
- `GET /requests` with filters, full-text search, keyset pagination.
- `/events`, `/approvals/queue`, `/attention`, `/notifications`.
- Check `EXPLAIN` on the main list and attention queries against the seeded data.

### Step 7: Frontend (2h)
- Order: list -> detail + timeline -> actions with optimistic updates -> conflict dialog -> approval queue -> attention -> notifications.
- Done when: the demo scenario in Section 14 works end to end.

### Step 8: Docs (45m)
- `README.md`: run instructions, seeded logins, assumptions, known limitations.
- `ENGINEERING_DECISIONS.md` (Section 15).
- Optional: architecture diagram (the one in Section 4).

### Step 9: Polish + rehearsal (remaining time)
- Run the demo script twice. Fix rough edges. Re-read the brief's checklist.

### If time is short, cut in this order
1. AI features, 2. duplicate detection, 3. presence badge, 4. notifications UI polish. **Never cut** the tests, the five critical behaviours, or the docs.

---

## 14. Demo script (final discussion)

1. Log in as a member, create a request (show idempotent retry: double-click creates one).
2. Two browser windows: both claim the same request -> one wins, other sees "already claimed by X".
3. Two windows edit the same request -> second save hits 409 and shows what changed.
4. Try to skip approval via curl as the wrong user -> 403, show it in the timeline that nothing changed.
5. Approver rejects with a reason -> request goes back, timeline tells the story.
6. Kill the worker, make changes, restart -> notifications still arrive, no duplicates.
7. Manager opens Attention view -> stale/unowned/overdue buckets.
8. Show the list with thousands of rows paginating and searching quickly.

---

## 15. ENGINEERING_DECISIONS.md: five decisions to write up

1. **State + append-only events in one transaction.** Why: audit trail comes from the design; trade-off: more writes, simpler than full event sourcing.
2. **Optimistic locking + atomic claim in SQL.** Why: DB is the arbiter under concurrency; trade-off: users see conflicts, but never silent overwrites.
3. **Idempotency keys for mutations.** Why: retries are normal on bad networks; trade-off: extra table and cleanup job.
4. **Transactional outbox + Postgres-backed worker.** Why: reliable at-least-once without new infrastructure; trade-off: Postgres polling won't scale forever (next: a queue).
5. **Per-team roles checked at resource level, enforced in backend.** Why: matches multi-team reality; trade-off: more checks per request, cached per request.

Also list what was **intentionally not built**: SSO, email/Slack delivery, WebSocket presence, file attachments, full audit export.

---

## 16. Known limitations (to state honestly)

- Polling instead of push; data can be up to ~15s stale on screen (writes are still safe via versioning).
- Postgres full-text search, not a dedicated search engine.
- Single worker design; fine for this scale, would move to a real queue later.
- No rate limiting, no email delivery, simple JWT auth.
- Idempotency keys and old outbox rows need a cleanup job (not implemented).
- History table will need partitioning by time at very large volume.

## 17. If the app grew / next week

- WebSocket or SSE for live updates and presence.
- Partition `request_events`; archive old history.
- Move outbox to a managed queue (SQS/Kafka); keep the outbox pattern.
- Dedicated search (OpenSearch) if filtering gets complex.
- SLA engine, escalation rules, blocked state, duplicate detection, email/Slack notifications.
- AI assist (categorize, suggest owner, summarize) behind a feature flag, always optional.
