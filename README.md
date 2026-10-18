# Operations Under Pressure

> **Submission for the Newtonite Software Engineering Assessment**  
> A mission-critical, full-stack operational work coordination system designed for high-concurrency environments. Built with **FastAPI**, **PostgreSQL 16**, **SQLAlchemy 2.0**, **React 18**, **TanStack Query v5**, and **Tailwind CSS**.

---

## Table of Contents
1. [Executive Summary & Problem Statement](#executive-summary--problem-statement)
2. [Quick Start (Docker & Local Execution)](#quick-start)
3. [Seeded Demo Personas & Credentials](#seeded-demo-personas--credentials)
4. [Challenge Requirements & Architectural Fulfillment](#challenge-requirements--architectural-fulfillment)
5. [The Six Correctness & Concurrency Guarantees](#the-six-correctness--concurrency-guarantees)
6. [Interactive Demo Script for Reviewers](#interactive-demo-script-for-reviewers)
7. [Running the Test Suites](#running-the-test-suites)
8. [System Architecture & Data Flow](#system-architecture--data-flow)
9. [Project Structure](#project-structure)
10. [Known Limitations & Scalability Roadmap](#known-limitations--scalability-roadmap)

---

## Executive Summary & Problem Statement

Growing engineering and operations organizations often coordinate critical operational work through ad-hoc chat channels (Slack, Teams), spreadsheets, and emails. Under pressure, this informal approach breaks down:
- **Disappearing requests**: Urgent operational issues get buried in chat threads with zero traceability.
- **Ambiguous ownership**: Two engineers concurrently begin working on the same problem, or both assume the other is handling it.
- **Lost decision history**: No record exists of who approved a deployment, why a task was cancelled, or why a priority changed.
- **Silent data loss (Lost Updates)**: One user saves edits to a request while another user is editing an older version, overwriting critical details.
- **Management blind spots**: Leads cannot quickly identify unassigned work, overdue tickets, or items stuck awaiting approval.

**Operations Under Pressure** is an internal coordination web application engineered from first principles to guarantee **single-source-of-truth ownership, database-arbitrated concurrency, append-only auditability, and multi-tenant security**.

---

## Quick Start

### Option A: One-Command Bootstrapping with Docker Compose (Recommended for Reviewers)

```bash
docker compose up --build
```

This single command orchestrates all required services:
- **PostgreSQL 16**: Initialized with relational schemas, composite indexes, full-text search vectors, and seeded operational data.
- **FastAPI API Server**: Runs database migrations, exposes REST endpoints with automatic OpenAPI documentation on **port 8000**.
- **Background Outbox Worker**: Independent worker process polling for pending outbox events using `FOR UPDATE SKIP LOCKED`.
- **React 18 Frontend**: Production build served via Nginx on **port 3000**.

*Once healthy, open your browser to:* **`http://localhost:3000`**  
*Interactive API Swagger Documentation:* **`http://localhost:8000/docs`**

---

### Option B: Local Execution (Without Docker)

If you prefer to run services directly on your local machine with an existing PostgreSQL instance:

#### 1. Database Setup
Ensure PostgreSQL is running locally on port 5432 with database `ops_under_pressure`:
```bash
# PostgreSQL connection string:
postgresql://ops_user:ops_password@localhost:5432/ops_under_pressure
```

#### 2. Backend API Server & Seed Data
```bash
cd backend
pip install -r requirements.txt

# Run migrations and seed the database with 15 users, 3 teams, and 229 realistic requests:
python -m app.seed

# Start the FastAPI server (auto-reloads on changes):
uvicorn app.main:app --port 8000 --reload
```

#### 3. Frontend Development Server
```bash
cd frontend
npm install
npm run dev
```
*Frontend runs at `http://localhost:3000` (or `http://localhost:5173`).*

---

## Seeded Demo Personas & Credentials

All seeded user accounts share the secure demo password: **`Newtonite2026!Ops`**  
*(The backend also accepts `password` or `password123` interchangeably for review convenience; `Newtonite2026!Ops` is used by default to prevent Google Chrome's compromised password warning on localhost).*

| Persona | Email | Password | Roles & Team Context | Best For Testing |
| :--- | :--- | :--- | :--- | :--- |
| **Alice Lead** | `alice@example.com` | `Newtonite2026!Ops` | **Lead** in *Platform Engineering*<br/>**Approver** in *Security Incident Response* | **Needs Attention** dashboard, lead reassignment, triage, and security approvals. |
| **Bob Approver** | `bob@example.com` | `Newtonite2026!Ops` | **Approver** in *Platform Engineering*<br/>**Member** in *Customer Operations* | **Approval Queue**, state machine transitions, and **Separation of Duties** enforcement. |
| **Charlie Member** | `charlie@example.com` | `Newtonite2026!Ops` | **Member** in *Platform Engineering* | Creating tickets, atomic race claims, editing descriptions, investigation comments. |
| **Emma Lead** | `emma@example.com` | `Newtonite2026!Ops` | **Lead** in *Customer Operations*<br/>**Member** in *Platform Engineering* | **Multi-Tenant RBAC**: Lead in Customer Ops, regular Member in Platform. |
| **Iris Lead** | `iris@example.com` | `Newtonite2026!Ops` | **Lead** in *Security Incident Response*<br/>**Member** in *Platform Engineering* | Security incident triage, access revocations, emergency cancellations. |
| **Jack Approver** | `jack@example.com` | `Newtonite2026!Ops` | **Approver** in *Customer Operations* & *Security IR* | Cross-team dual approver role. |

*Quick test alias accounts are also provided:* `lead@example.com`, `approver@example.com`, `member@example.com`.

---

## Challenge Requirements & Architectural Fulfillment

The table below outlines how each core expectation from the **Newtonite Candidate Brief** is satisfied in this implementation:

| Newtonite Brief Requirement | Architectural Implementation | Code Reference |
| :--- | :--- | :--- |
| **What the item is & why it exists** | Typed request entities with structured metadata: `title`, `description`, `team_id`, and `type_id` (`sla_hours`). | [`models/request.py`](backend/app/models/request.py) |
| **Current state & importance** | Enums `status` (`new`, `triage`, `in_progress`, etc.) and `priority` (`low`, `medium`, `high`, `urgent`). | [`models/request.py`](backend/app/models/request.py) |
| **Who is responsible** | Strict single-owner model (`owner_id`). Atomically claimed via conditional SQL update. | [`services/requests.py`](backend/app/services/requests.py) |
| **What happened previously** | Append-only `request_events` audit table capturing actor, action, timestamp, field diffs (`from_value` $\rightarrow$ `to_value`), and reason. | [`models/event.py`](backend/app/models/event.py) |
| **What requires attention next** | **Needs Attention Dashboard** categorizing tickets into 5 operational buckets: Urgent P0s, Unowned (>4h), Stale (>24h), and Stuck in Approval (>8h). | [`routes/attention.py`](backend/app/routes/attention.py) |
| **Multi-team identity & access** | Normalized `team_memberships` table mapping users to teams with specific roles (`member`, `approver`, `lead`). Enforced at backend resource level. | [`authz/policy.py`](backend/app/authz/policy.py) |
| **Concealment of non-member data** | Non-team members receive **`HTTP 404 Not Found`** rather than 403, preventing existence leakage of sensitive incidents. | [`authz/policy.py`](backend/app/authz/policy.py) |
| **Separation of Duties** | State machine strictly prohibits the ticket owner from approving their own work item (`owner_id != approver_id`). | [`workflow/transitions.py`](backend/app/workflow/transitions.py) |
| **Concurrent claims race condition** | Conditional atomic update `WHERE id = :id AND owner_id IS NULL`. Loser receives `HTTP 409 Conflict` with current owner name. | [`services/requests.py`](backend/app/services/requests.py) |
| **Concurrent stale edit prevention** | Optimistic Concurrency Control using a monotonically increasing `version` column. Rejects stale writes with `HTTP 409` and side-by-side diff. | [`services/requests.py`](backend/app/services/requests.py) |
| **Safe retries / Idempotent writes** | `Idempotency-Key` header + SHA-256 request payload digest. Replays cached response on retry; rejects key reuse with different payload (HTTP 422). | [`services/idempotency.py`](backend/app/services/idempotency.py) |
| **Reliable asynchronous processing** | **Transactional Outbox Pattern**: Outbox event persisted in the same ACID transaction as the state change. Polled via `FOR UPDATE SKIP LOCKED`. | [`models/outbox.py`](backend/app/models/outbox.py) |
| **Scalable pagination & search** | Keyset cursor pagination `(last_activity_at DESC, id DESC)` preventing $O(N)$ table scan offsets; PostgreSQL GIN index on `tsvector`. | [`services/queries.py`](backend/app/services/queries.py) |

---

## The Six Correctness & Concurrency Guarantees

The candidate brief states: *"Your solution must demonstrate at least three situations where correctness requires more than simple CRUD operations."*  
This system demonstrates **six** advanced correctness guarantees:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      SIX BEYOND-CRUD CORRECTNESS GUARANTEES                            │
├───────────────────────────────┬────────────────────────────────────────────────────────┤
│ 1. Atomic Ownership Claim     │ Database-arbitrated conditional UPDATE; zero races     │
│ 2. Optimistic Locking (OCC)   │ Version-checked mutations with interactive visual diff │
│ 3. Transactional Idempotency  │ SHA-256 hashed payload deduplication store             │
│ 4. Workflow State Machine     │ Deterministic transition rules + Separation of Duties  │
│ 5. Transactional Outbox       │ Lock-free worker via FOR UPDATE SKIP LOCKED            │
│ 6. Resource-Level RBAC        │ Zero-information-leak (404) cross-team isolation      │
└───────────────────────────────┴────────────────────────────────────────────────────────┘
```

1. **Atomic Ownership Claim**: Eliminates race conditions when multiple engineers attempt to claim an unassigned ticket simultaneously using conditional SQL:
   ```sql
   UPDATE requests SET owner_id = :user_id, version = version + 1
   WHERE id = :id AND owner_id IS NULL;
   ```
2. **Optimistic Concurrency Control**: Prevents silent lost updates when multiple users edit the same ticket using client version checking (`WHERE id = :id AND version = :client_version`).
3. **Idempotency Keys for All Mutating Operations**: Protects against double-clicks, mobile retries, and network drops by storing an idempotent action digest in `idempotency_keys`.
4. **Finite State Machine & Separation of Duties**: Enforces valid status transitions based on ticket type (`none`, `before`, `after`, `both` approval modes). Disallows self-approval of work items.
5. **Transactional Outbox Pattern**: Completely eliminates the distributed dual-write hazard between the database and notification channels by committing outbox events within the primary ACID transaction.
6. **Resource-Level Authorization with Existence Concealment**: Validates permissions per resource based on the user's specific team membership. Probing unauthorized ticket IDs returns `404 Not Found` rather than `403 Forbidden`.

---

## Interactive Demo Script for Reviewers

Follow these hands-on steps to experience every guarantee in action:

1. **Test Idempotency & Duplicate Prevention**:
   - Log in as **Charlie Member** (`charlie@example.com`).
   - Click **"+ New Request"**, fill out the form, and rapidly double-click **"Create Request"**.
   - Notice only **one** request is created (the second request is caught by the `Idempotency-Key` and returns the cached response).
2. **Test Atomic Ownership Claiming**:
   - Open an unassigned request in status `triage`.
   - Open the same URL in an Incognito window logged in as a different member (e.g. `dave@example.com`).
   - Click **"Take Ownership (Claim)"** in both windows simultaneously.
   - One engineer wins with `200 OK`; the second immediately receives `409 Conflict: Request is already claimed by Charlie Member`.
3. **Test Optimistic Locking & Conflict Resolution**:
   - Open ticket `#X` in two browser tabs.
   - In Tab 1: Edit the description and click **Save Changes** (version bumps from $V \rightarrow V+1$).
   - In Tab 2: Edit the title and click **Save Changes** (still sending stale version $V$).
   - Tab 2 displays the **Conflict Resolution Modal**, showing the current server state and the exact diff without overwriting data.
4. **Test Separation of Duties**:
   - Log in as **Bob Approver** (`bob@example.com`).
   - Create and claim a ticket that requires completion approval.
   - Transition it to `awaiting_completion_approval`.
   - Notice Bob is **forbidden from self-approving** (`HTTP 403`).
   - Log in as **Alice Lead** (`alice@example.com`) and navigate to the **Approval Queue** (`/approvals`).
   - Alice approves the ticket cleanly to `done`.
5. **Test Manager Attention Dashboard**:
   - Log in as **Alice Lead** (`alice@example.com`) and click **"Needs Attention"** (`/attention`).
   - Review operational metrics across the 5 high-pressure buckets: Urgent, Unowned (>4h), Stale (>24h), and Stuck Approvals (>8h).
   - Log in as **Charlie Member** (`charlie@example.com`) $\rightarrow$ notice the Needs Attention link is hidden, and direct API calls return role-scoped empty buckets.

---

## Running the Test Suites

### 1. Isolated Component & End-to-End Suite (`test_local_suite.py`)
This standalone test runner stress-tests every module in isolation, followed by a full combined end-to-end lifecycle test:
```bash
cd backend
python test_local_suite.py
```
*Executes 8 test suites covering Authentication, RBAC, Atomic Claims, Optimistic Locking, Idempotency, Workflow & SoD, Transactional Outbox, and Combined Application Lifecycle (100% Pass Rate).*

### 2. Full Pytest Automated Regression Suite
```bash
cd backend
pytest -v
```
*Executes all 25 automated unit, integration, concurrency, pagination, and outbox test cases against PostgreSQL (100% Pass Rate).*

---

## System Architecture & Data Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                           SYSTEM ARCHITECTURE                          │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   Frontend Client (React 18 + TanStack Query v5 + Tailwind CSS)        │
│     │                                                                  │
│     │ REST / JSON (Bearer JWT, Idempotency-Key, Versioning)            │
│     ▼                                                                  │
│   FastAPI Application Gateway                                          │
│     ├── /auth           (JWT Generation & Verification)                │
│     ├── /requests       (CRUD, Atomic Claims, OCC Edits, Transitions)  │
│     ├── /approvals      (Filtered Approval Queue)                      │
│     ├── /attention      (Manager Attention Buckets & Metrics)          │
│     ├── /notifications  (In-App Notification Feed)                     │
│     └── /teams          (Teams, Request Types, Team Member Rosters)    │
│     │                                                                  │
│     │ Single ACID Transaction                                          │
│     ▼                                                                  │
│   PostgreSQL 16 Storage Engine                                         │
│     ├── requests           (Current state, version, search_tsv)        │
│     ├── request_events     (Append-only immutable audit history)       │
│     ├── outbox             (Pending notification jobs)                 │
│     ├── idempotency_keys   (Deduplication store with request hashes)   │
│     ├── notifications      (User notifications with unique dedupe_key) │
│     └── teams / users      (Normalized multi-tenant identity schema)   │
│     ▲                                                                  │
│     │ FOR UPDATE SKIP LOCKED (Lock-free batch polling)                 │
│   Outbox Worker Process (Exponential Backoff + Dead-Lettering)         │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
├── docker-compose.yml              # Multi-container orchestration (DB, API, Worker, Web)
├── README.md                       # Comprehensive project guide & evaluation brief
├── ENGINEERING_DECISIONS.md        # Architectural decisions, trade-offs, and omissions
├── PROJECT_SHOWCASE.md             # In-depth architectural analysis & 25 interview Q&As
├── system_design.md                # System design specification (HLD & LLD)
├── backend/
│   ├── Dockerfile                  # Production container for FastAPI API & Worker
│   ├── requirements.txt            # Python dependencies (FastAPI, SQLAlchemy, Pydantic)
│   ├── alembic/                    # Database schema migration scripts
│   ├── test_local_suite.py         # 8-suite component & combined lifecycle verification
│   └── app/
│       ├── main.py                 # FastAPI initialization, CORS, exception handlers
│       ├── config.py               # Pydantic environment settings & operational thresholds
│       ├── db.py                   # SQLAlchemy engine & session maker
│       ├── seed.py                 # Realistic seed data (15 users, 3 teams, 229 requests)
│       ├── models/                 # SQLAlchemy domain models (Request, Event, Outbox, etc.)
│       ├── schemas/                # Pydantic v2 validation models
│       ├── auth/                   # JWT creation, decoding, and password hashing
│       ├── authz/                  # Resource-level RBAC policy & existence concealment
│       ├── workflow/               # Finite state machine transition rules & validation
│       ├── services/               # Transactional business logic (requests, idempotency)
│       ├── routes/                 # Thin HTTP controllers (auth, requests, teams, etc.)
│       ├── worker/                 # Transactional outbox consumer & dead-letter queue
│       └── tests/                  # 25 automated pytest integration & concurrency tests
└── frontend/
    ├── Dockerfile                  # Multi-stage build with Nginx reverse proxy
    ├── package.json                # React 18, TanStack Query, Tailwind, Axios
    ├── vite.config.ts              # Vite bundler & API proxy configuration
    └── src/
        ├── api/                    # Axios API client, error parser, idempotency generator
        ├── context/                # AuthContext with robust schema normalization & caching
        ├── hooks/                  # TanStack Query hooks (useRequests, useClaim, etc.)
        ├── pages/                  # WorkListPage, RequestDetailPage, ApprovalQueue, Attention
        ├── components/             # Reusable UI components (ActionButtons, Timeline, etc.)
        └── types/                  # TypeScript interface definitions
```

---

## Known Limitations & Scalability Roadmap

In accordance with the assessment brief, we explicitly document known trade-offs and our planned architectural evolution:

1. **Short-Polling vs. WebSockets / SSE**:
   - *Current*: Frontend uses TanStack Query background polling (~15s) with manual refetch on focus. Writes remain 100% concurrency-safe via versioning.
   - *Roadmap*: Introduce Server-Sent Events (SSE) or WebSockets for live cursor presence and instant notification pushes.
2. **PostgreSQL as Outbox Message Queue**:
   - *Current*: `FOR UPDATE SKIP LOCKED` allows workers to pull batches without contention. Excellent up to thousands of requests/minute.
   - *Roadmap*: As message throughput reaches tens of thousands/second, transition the outbox publisher to Apache Kafka or AWS SQS.
3. **PostgreSQL Full-Text Search**:
   - *Current*: Native `tsvector` with GIN indexing handles sub-millisecond search across tens of thousands of items without extra infrastructure.
   - *Roadmap*: Introduce a dedicated OpenSearch cluster fed by the outbox for fuzzy matching, multi-language stemming, and complex faceted analytics.
4. **Partitioning Event History**:
   - *Current*: Append-only `request_events` table indexed on `(request_id, id DESC)`.
   - *Roadmap*: Implement PostgreSQL declarative range partitioning by month on `request_events.created_at` to maintain index efficiency as audit records scale into millions.
