import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./data.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class ReviewItem(Base):
    __tablename__ = "review_items"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    submitted_at = Column(DateTime, nullable=False)
    risk_level = Column(String, nullable=False)      # high | medium | low
    customer_tier = Column(String, nullable=False)   # priority | standard
    status = Column(String, nullable=False)          # unassigned | in_review | approved | rejected | escalated
    assigned_reviewer = Column(String, nullable=True)
    summary = Column(String, nullable=False)

    notes = relationship("Note", back_populates="item", order_by="Note.created_at")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String, ForeignKey("review_items.id"), nullable=False)
    author = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)

    item = relationship("ReviewItem", back_populates="notes")


def seed_database(db) -> None:
    """Populate the database from review_items.json if the table is empty."""
    if db.query(ReviewItem).count() > 0:
        return

    seed_path = Path(__file__).with_name("review_items.json")
    with seed_path.open("r", encoding="utf-8-sig") as f:
        items = json.load(f)

    for raw in items:
        # Parse ISO-8601 and strip timezone to store as naive UTC
        dt_str = raw["submitted_at"].replace("Z", "+00:00")
        dt = datetime.fromisoformat(dt_str).replace(tzinfo=None)
        db.add(ReviewItem(
            id=raw["id"],
            title=raw["title"],
            submitted_at=dt,
            risk_level=raw["risk_level"],
            customer_tier=raw["customer_tier"],
            status=raw["status"],
            assigned_reviewer=raw.get("assigned_reviewer"),
            summary=raw["summary"],
        ))
    db.commit()
