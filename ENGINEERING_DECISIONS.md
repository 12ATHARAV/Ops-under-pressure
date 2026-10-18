# Engineering Decisions

Five key architectural decisions and the trade-offs behind them.

---

## 1. Current State + Append-Only Event Log (Not Full Event Sourcing)

### Decision
Every `requests` row stores the **current state** directly (status, owner, priority, version). Every mutation also appends an immutable row to `request_events` in the **same transaction**.

### Why
- **Reads are simple**: `SELECT * FROM requests WHERE ...` gives the current state without replaying events.
- **Audit trail is automatic**: the event log captures who changed what, when, and why — driven by the design, not by bolted-on logging.
- **Atomic consistency**: state change + event are in one transaction, so they can never diverge.

### Trade-off
- More writes per mutation (update request + insert event + insert outbox).
- If we ever need to rebuild state from events, we'd have to migrate to full event sourcing.
- We accepted this because reads vastly outnumber writes, and the simplicity of direct-state reads is worth the extra write cost.

### What we avoided
Full event sourcing would require replaying potentially thousands of events to render a single request detail page. At our scale, this adds complexity without clear benefit.

---

## 2. Optimistic Locking + Atomic Claim via Conditional SQL

### Decision
Every request has a `version` column. Mutations send the version the client last saw and use `UPDATE ... WHERE id = :id AND version = :v`. For claims, we use `UPDATE ... WHERE owner_id IS NULL`. The database is the arbiter.

### Why
- **No lost updates**: if two users edit the same request, the second one is rejected with a 409 containing the current state and what changed since their version.
- **No double ownership**: the `WHERE owner_id IS NULL` conditional update means the database atomically decides who wins a claim race — the application never sees an inconsistent state.
- **Transparent conflict resolution**: the 409 response includes `events_since_version` so the UI can show the user exactly what changed and let them decide how to proceed.

### Trade-off
- Users occasionally see conflict dialogs. This is annoying but honest — the alternative (last-write-wins) silently destroys work.
- Every mutation requires the client to track and send the version number.
- We accepted this because silent data loss in an operational system is far worse than an occasional conflict dialog.

### What we avoided
Pessimistic locking (SELECT FOR UPDATE held during user editing) would block other users and doesn't work well with HTTP request/response cycles.

---

## 3. Idempotency Keys for All Mutating Endpoints

### Decision
Every POST endpoint that creates or changes data accepts an `Idempotency-Key` header. On first use, the response is stored in `idempotency_keys`. The same key returns the stored response. A different payload with the same key returns 422.

### Why
- **Safe retries**: network failures, timeouts, and impatient double-clicks are normal. Without idempotency, a timeout leaves the user unsure if their action succeeded, and retrying might create duplicates or trigger double state changes.
- **Client simplicity**: the frontend generates one key per user intent and reuses it for automatic retries.
- **Concurrent duplicate safety**: the unique PK on `(user_id, key)` means concurrent duplicates are handled by the database.

### Trade-off
- Extra table, extra lookup on every mutation, and eventual need for a cleanup job.
- Slightly more complex service layer.
- We accepted this because the alternative — duplicate work items, double claims, or double state transitions — would undermine trust in the system.

### Implementation detail
The idempotency record is inserted in the **same transaction** as the actual mutation, so there's no window where the action succeeds but the idempotency record doesn't exist.

---

## 4. Transactional Outbox + PostgreSQL-Backed Worker

### Decision
When a mutation succeeds, an `outbox` row is inserted in the same transaction. A separate worker process polls the outbox, processes events (creates notifications), and marks them done. Failures are retried with exponential backoff; poison jobs go to `dead` status.

### Why
- **Reliability**: the outbox row and the state change are in the same transaction. If the transaction rolls back, no outbox event exists. If it commits, the event is guaranteed to be processed eventually.
- **Decoupling**: the primary action (state change) never waits for notification delivery. The user gets an immediate response.
- **No extra infrastructure**: no Redis, no RabbitMQ, no Kafka. Just PostgreSQL, which we already have.
- **Idempotent consumers**: notifications have a unique `dedupe_key`, so reprocessing an outbox event creates no duplicate notifications.

### Trade-off
- PostgreSQL is not a purpose-built message queue. Polling with `FOR UPDATE SKIP LOCKED` works well at moderate scale but has a ceiling.
- The worker adds a separate process to manage.
- We accepted this because the simplicity of a single-database architecture is valuable for a v1, and migrating to a real queue later is straightforward — the outbox pattern is the same, only the transport changes.

### Growth path
At higher scale: swap the worker's data source from outbox polling to SQS/Kafka consumption. The outbox table becomes the reliable publisher. The consumer pattern stays identical.

---

## 5. Per-Team Roles Checked at Resource Level, Enforced in Backend

### Decision
Authorization is **(user, team, role) checked against the specific resource**, not a global permission flag. Every endpoint loads the request, finds the user's membership in that request's team, and checks the role. No membership = 404 (not 403 — no information leak).

### Why
- **Matches reality**: in a multi-team organization, a user might be a lead in one team and a member in another. A global "admin" flag doesn't capture this.
- **Separation of duties**: an approver cannot approve their own work, enforced by comparing `request.owner_id` against the approver's user ID.
- **No existence leaks**: if a user is not in the request's team, they get 404 — they cannot even confirm the request exists.
- **Backend enforcement**: the UI hides unauthorized actions (server sends `allowed_actions`), but the backend independently rejects unauthorized calls. A `curl` bypass cannot circumvent the rules.

### Trade-off
- Every mutating endpoint requires a membership lookup, adding a query per request.
- More complex authorization logic than a simple role check.
- We accepted this because authorization that only exists in the UI is not authorization — it's decoration.

### Implementation
Authorization is a FastAPI dependency (`require_permission("approve")`), so it's declarative and impossible to forget on a route. List queries filter by team membership in SQL, never loading data the user shouldn't see.

---

## 6. Host-Level Nginx TLS Termination with Automated Certbot (Not Container-Baked SSL)

### Decision
For our live AWS EC2 deployment (`https://ops-pressure-demo.duckdns.org`), TLS termination is handled by **Host Nginx + Let's Encrypt Certbot**, rather than baking SSL certificates or reverse proxy certbot routines into the Docker images.

### Why
- **Environment-agnostic containers**: The Docker Compose stack runs identically on a reviewer's local laptop, in GitHub Actions CI runners, and in production EC2 without missing certificate errors.
- **Automated zero-downtime certificate renewals**: Let's Encrypt certificates renew automatically via `certbot.timer` without needing Docker container rebuilds or secrets mounting.
- **Clean separation of concerns**: The application services (`api`, `web`, `worker`, `postgres`) focus strictly on business logic and persistence, while the host edge layer handles external TLS handshakes, HTTP $\to$ HTTPS 301 redirects, and DDOS/traffic filtering.

### Trade-off
- Requires installing Nginx and Certbot on the EC2 host during initial machine provisioning.
- We accepted this because baking domain-specific certificates inside Docker containers breaks local developer ergonomics and GitHub Actions CI verification.

---

## What We Intentionally Did Not Build

| Feature | Reason |
|---|---|
| SSO / OAuth | Out of scope; simple JWT login is sufficient for demonstration |
| Email / Slack notifications | The outbox pattern makes this pluggable; in-app only for v1 |
| WebSocket / SSE | Polling is simpler and correctness doesn't depend on freshness |
| File attachments | Not core to the coordination problem |
| AI features | Would distract from demonstrating correctness and concurrency handling |
| Rate limiting | Internal tool; acceptable risk for v1 |
| Refresh tokens | JWT expiry is set long enough for a demo session |

Each omission is deliberate. The system is designed so these features can be added without restructuring the core.
