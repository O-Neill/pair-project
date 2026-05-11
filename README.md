# Reviewer Queue

A take-home fullstack implementation of an internal reviewer workspace tool. Vue 3 frontend + FastAPI backend + SQLite (seeded from JSON on first run).

## Structure

```
pair_project/
├── backend/        # FastAPI + SQLAlchemy + SQLite
│   ├── main.py         # routes & business rules
│   ├── database.py     # models, seeding
│   └── requirements.txt
└── frontend/       # Vue 3 + Vite (single-page app)
    ├── src/
    │   ├── App.vue     # all UI logic
    │   └── main.js
    ├── index.html
    └── package.json
```

## Setup & Running

### Backend

```bash
cd backend
python -m venv venv
# Windows:  venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

The API runs at **http://localhost:8000**.  
Interactive docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at **http://localhost:5173**.

## API Endpoints

| Method | Path                          | Description                                           |
|--------|-------------------------------|-------------------------------------------------------|
| GET    | /api/queue                    | Active (non-terminal) items, urgency-ordered          |
| GET    | /api/items                    | All items (active first, then terminal)               |
| GET    | /api/items/{id}               | Single item with notes                                |
| POST   | /api/items                    | Create a new ticket                                   |
| PATCH  | /api/items/{id}               | Edit title, risk level, tier, or summary              |
| POST   | /api/items/{id}/claim         | Claim an unassigned item                              |
| POST   | /api/items/{id}/approve       | Approve an in-review item                             |
| POST   | /api/items/{id}/reject        | Reject an in-review item                              |
| POST   | /api/items/{id}/escalate      | Escalate an in-review item                            |
| POST   | /api/items/{id}/unassign      | Return an in-review item to the unassigned queue      |
| POST   | /api/items/{id}/reopen        | Reopen a terminal item back to in-review              |
| POST   | /api/items/{id}/notes         | Add a note/comment to an in-review item               |

---

## Assumptions

These are decisions made during implementation that go slightly beyond the literal task spec, along with the reasoning.

### Unassign / revert state

The spec defines `approved`, `rejected`, and `escalated` as terminal states, but is silent on whether a reviewer can change their mind mid-review or correct a mistake. This implementation adds:

- **Unassign**: an `in_review` item can be returned to `unassigned`, releasing it back into the queue for anyone to claim. This is a common real-world need — a reviewer may pick up the wrong ticket, or capacity changes.
- **Reopen**: a terminal item can be moved back to `in_review`. Mistakes happen; a hard block on reopening would require manual database intervention.

Both actions are surfaced in the UI with intentional button labelling so reviewers understand what they're doing.

### Creating new tickets

The spec treats the seed file as the source of items, but an operations team typically needs to be able to create tickets. A "New Ticket" button (top right) allows creation of items with a title, risk level, customer tier, and summary. New items start as `unassigned`.

### Editing ticket fields

The spec's seed data includes `risk_level`, `customer_tier`, and `summary` as fields that inform review decisions. Triage often reveals that initial metadata is wrong (e.g., a ticket was logged as `low` risk but is actually `high`). Editing these fields while a ticket is `in_review` is therefore supported.

Edit controls are only shown when the item is `in_review` **and** assigned to the current user — so a reviewer cannot modify another reviewer's active ticket.

### `notes_count` as live comment count

The seed data has a static `notes_count` field. Rather than carry forward a meaningless static number, this implementation treats notes as a real comment thread. The `notes_count` returned by the API is derived from the live count of `Note` rows for that item. This makes the field meaningful and avoids a discrepancy between displayed count and visible comments.

Notes can only be added to items that are `in_review` and assigned to the current user, for the same reason as edit restrictions above.

### Reviewer identity is hardcoded

The current reviewer is hardcoded as a constant (`alex`) in the frontend and trusted on all API calls. The `claim` endpoint records whichever reviewer name is passed in the request body.

This is intentional — see "What's not implemented" below.

### Queue includes all non-terminal items

The UI shows three tabs: **Queue** (unassigned), **In Review**, and **Closed**. The "In Review" tab shows all in-review items across all reviewers (with an optional filter to show only the current user's items). This lets a reviewer see what colleagues are working on without being able to modify their tickets.

---

## What's not implemented

Due to time constraints, the following were deliberately left out:

- **Authentication**: there is no login, session, or token mechanism. The reviewer identity is hardcoded in the frontend. Anyone with access to the app can impersonate any reviewer by modifying the request.
- **API-enforced user permissions**: the backend has no concept of who is making a request. The "can only edit your own ticket" rule is enforced in the frontend only; a direct API call can bypass it.
- **Multi-user support**: state is shared across all browser sessions. In a real multi-user environment, concurrent actions on the same item would need locking or optimistic concurrency checks.
- **Persistence across restarts**: the SQLite database file is created at startup and seeded once. Restarting with a fresh DB resets all state. This is acceptable for a prototype.
- **Audit trail**: there is no record of who performed which action and when (beyond the note author). A production tool would log every state transition.

---

## Potential improvements

### Near-term (next iteration)

- **Auth & sessions**: add OAuth or a simple session token so the reviewer identity is server-verified, not client-supplied. Enforce edit/note permissions on the backend.
- **Optimistic UI**: currently the frontend refreshes data after each action (request-then-reload). Optimistic updates would make the UI feel faster.
- **Timestamps on state transitions**: record when an item moved to each status, to support SLA tracking (e.g., "in review for 3 days").
- **Undo grace period**: instead of a permanent "Reopen" button, offer a short undo window after a terminal action before the state is locked.
- **Pagination / virtual scroll**: the queue list renders all items. With hundreds of tickets this would be slow.

### Medium-term

- **Real-time updates**: use WebSockets or SSE so that when one reviewer claims or updates a ticket, other reviewers see the change without refreshing.
- **Assignment history / audit log**: a full log of state transitions with actor and timestamp, queryable per item.
- **Search and filtering**: filter by risk level, tier, assignee, or date range within each tab.
- **Bulk actions**: select multiple unassigned tickets and claim or escalate them at once.
- **Notifications**: alert a reviewer when someone comments on or reassigns a ticket they previously held.

### Longer-term

- **Role-based access control**: distinguish between regular reviewers, team leads (who can escalate), and admins (who can reopen terminal items or reassign between reviewers).
- **SLA dashboards**: surface queue age, throughput, and reviewer workload metrics.
- **Integration with upstream systems**: rather than seeding from a static JSON file, ingest items from the actual submission source via webhook or polling.
