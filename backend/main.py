from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import Base, Note, ReviewItem, SessionLocal, engine, seed_database

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TERMINAL_STATES = {"approved", "rejected", "escalated"}
RISK_ORDER = {"high": 3, "medium": 2, "low": 1}
TIER_ORDER = {"priority": 2, "standard": 1}
VALID_RISKS = {"high", "medium", "low"}
VALID_TIERS = {"priority", "standard"}


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

def _run_migrations() -> None:
    """Apply any schema migrations that create_all won't handle automatically."""
    with engine.connect() as conn:
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(review_items)"))]
        if "closed_reason" not in cols:
            conn.execute(text("ALTER TABLE review_items ADD COLUMN closed_reason TEXT"))
            conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def note_to_dict(note: Note) -> dict:
    return {
        "id": note.id,
        "author": note.author,
        "content": note.content,
        "created_at": note.created_at.isoformat() + "Z",
    }


def item_to_dict(item: ReviewItem) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "submitted_at": item.submitted_at.isoformat() + "Z",
        "risk_level": item.risk_level,
        "customer_tier": item.customer_tier,
        "status": item.status,
        "assigned_reviewer": item.assigned_reviewer,
        "notes_count": len(item.notes),
        "summary": item.summary,
        "closed_reason": item.closed_reason,
    }


def item_to_detail_dict(item: ReviewItem) -> dict:
    d = item_to_dict(item)
    d["notes"] = [note_to_dict(n) for n in item.notes]
    return d


def urgency_key(item: ReviewItem):
    """Lower sort value = higher urgency (sort ascending)."""
    return (
        -RISK_ORDER.get(item.risk_level, 0),
        -TIER_ORDER.get(item.customer_tier, 0),
        item.submitted_at,   # older = smaller datetime = earlier = higher priority
    )


def get_or_404(db: Session, item_id: str) -> ReviewItem:
    item = db.query(ReviewItem).filter(ReviewItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found")
    return item


def generate_item_id(db: Session) -> str:
    rows = db.query(ReviewItem.id).all()
    max_num = 1000
    for (item_id,) in rows:
        try:
            num = int(item_id.split("-")[1])
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            pass
    return f"RV-{max_num + 1}"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/queue")
def get_queue(db: Session = Depends(get_db)):
    """Active (non-terminal) items ordered by urgency."""
    items = db.query(ReviewItem).filter(
        ReviewItem.status.notin_(TERMINAL_STATES)
    ).all()
    items.sort(key=urgency_key)
    return [item_to_dict(i) for i in items]


@app.get("/api/items")
def get_all_items(db: Session = Depends(get_db)):
    """All items: active first (by urgency), then terminal (newest first)."""
    all_items = db.query(ReviewItem).all()
    active = [i for i in all_items if i.status not in TERMINAL_STATES]
    terminal = [i for i in all_items if i.status in TERMINAL_STATES]
    active.sort(key=urgency_key)
    terminal.sort(key=lambda i: i.submitted_at, reverse=True)
    return [item_to_dict(i) for i in active + terminal]


@app.get("/api/items/{item_id}")
def get_item(item_id: str, db: Session = Depends(get_db)):
    return item_to_detail_dict(get_or_404(db, item_id))


class ClaimBody(BaseModel):
    reviewer: str


@app.post("/api/items/{item_id}/claim")
def claim_item(item_id: str, body: ClaimBody, db: Session = Depends(get_db)):
    item = get_or_404(db, item_id)
    if item.status != "unassigned":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot claim: item is '{item.status}'. Only unassigned items can be claimed.",
        )
    item.status = "in_review"
    item.assigned_reviewer = body.reviewer
    db.commit()
    db.refresh(item)
    return item_to_detail_dict(item)


@app.post("/api/items/{item_id}/approve")
def approve_item(item_id: str, db: Session = Depends(get_db)):
    item = get_or_404(db, item_id)
    if item.status != "in_review":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve: item is '{item.status}'. Only in-review items can be approved.",
        )
    item.status = "approved"
    db.commit()
    db.refresh(item)
    return item_to_detail_dict(item)


class CloseReasonBody(BaseModel):
    closed_reason: Optional[str] = None


@app.post("/api/items/{item_id}/reject")
def reject_item(item_id: str, body: CloseReasonBody = CloseReasonBody(), db: Session = Depends(get_db)):
    item = get_or_404(db, item_id)
    if item.status != "in_review":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject: item is '{item.status}'. Only in-review items can be rejected.",
        )
    item.status = "rejected"
    item.closed_reason = body.closed_reason
    db.commit()
    db.refresh(item)
    return item_to_detail_dict(item)


@app.post("/api/items/{item_id}/escalate")
def escalate_item(item_id: str, body: CloseReasonBody = CloseReasonBody(), db: Session = Depends(get_db)):
    item = get_or_404(db, item_id)
    if item.status != "in_review":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot escalate: item is '{item.status}'. Only in-review items can be escalated.",
        )
    item.status = "escalated"
    item.closed_reason = body.closed_reason
    db.commit()
    db.refresh(item)
    return item_to_detail_dict(item)


class CreateItemBody(BaseModel):
    title: str
    risk_level: str
    customer_tier: str
    summary: str


@app.post("/api/items", status_code=201)
def create_item(body: CreateItemBody, db: Session = Depends(get_db)):
    if body.risk_level not in VALID_RISKS:
        raise HTTPException(status_code=422, detail=f"risk_level must be one of {sorted(VALID_RISKS)}")
    if body.customer_tier not in VALID_TIERS:
        raise HTTPException(status_code=422, detail=f"customer_tier must be one of {sorted(VALID_TIERS)}")
    item_id = generate_item_id(db)
    item = ReviewItem(
        id=item_id,
        title=body.title.strip(),
        submitted_at=datetime.now(),
        risk_level=body.risk_level,
        customer_tier=body.customer_tier,
        status="unassigned",
        assigned_reviewer=None,
        summary=body.summary.strip(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item_to_detail_dict(item)


class UpdateItemBody(BaseModel):
    title: Optional[str] = None
    risk_level: Optional[str] = None
    customer_tier: Optional[str] = None
    summary: Optional[str] = None


@app.patch("/api/items/{item_id}")
def update_item(item_id: str, body: UpdateItemBody, db: Session = Depends(get_db)):
    item = get_or_404(db, item_id)
    if item.status != "in_review":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot update: item is '{item.status}'. Only in-review items can be updated.",
        )
    if body.title is not None:
        if not body.title.strip():
            raise HTTPException(status_code=422, detail="title must not be empty")
        item.title = body.title.strip()
    if body.risk_level is not None:
        if body.risk_level not in VALID_RISKS:
            raise HTTPException(status_code=422, detail=f"risk_level must be one of {sorted(VALID_RISKS)}")
        item.risk_level = body.risk_level
    if body.customer_tier is not None:
        if body.customer_tier not in VALID_TIERS:
            raise HTTPException(status_code=422, detail=f"customer_tier must be one of {sorted(VALID_TIERS)}")
        item.customer_tier = body.customer_tier
    if body.summary is not None:
        item.summary = body.summary.strip()
    db.commit()
    db.refresh(item)
    return item_to_detail_dict(item)


class AddNoteBody(BaseModel):
    author: str
    content: str


@app.post("/api/items/{item_id}/notes", status_code=201)
def add_note(item_id: str, body: AddNoteBody, db: Session = Depends(get_db)):
    item = get_or_404(db, item_id)
    if item.status != "in_review":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot add note: item is '{item.status}'. Notes can only be added to in-review items.",
        )
    note = Note(
        item_id=item_id,
        author=body.author,
        content=body.content.strip(),
        created_at=datetime.now(),
    )
    db.add(note)
    db.commit()
    db.refresh(item)
    return item_to_detail_dict(item)


@app.post("/api/items/{item_id}/unassign")
def unassign_item(item_id: str, db: Session = Depends(get_db)):
    item = get_or_404(db, item_id)
    if item.status != "in_review":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot unassign: item is '{item.status}'. Only in-review items can be unassigned.",
        )
    item.status = "unassigned"
    item.assigned_reviewer = None
    db.commit()
    db.refresh(item)
    return item_to_detail_dict(item)


@app.post("/api/items/{item_id}/reopen")
def reopen_item(item_id: str, db: Session = Depends(get_db)):
    item = get_or_404(db, item_id)
    if item.status not in TERMINAL_STATES:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reopen: item is '{item.status}'. Only closed items can be reopened.",
        )
    item.status = "in_review"
    db.commit()
    db.refresh(item)
    return item_to_detail_dict(item)