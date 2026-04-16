from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )


account_sources = Table(
    "account_sources",
    Base.metadata,
    Column("account_id", ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True),
    Column("source_id", ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True),
)


class Account(TimestampMixin, Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    users: Mapped[list["User"]] = relationship(
        back_populates="account",
        passive_deletes=True,
    )
    sources: Mapped[list["Source"]] = relationship(
        secondary=account_sources,
        back_populates="accounts",
    )
    events: Mapped[list["Event"]] = relationship(
        back_populates="account",
        passive_deletes=True,
    )
    event_summaries: Mapped[list["EventSummary"]] = relationship(
        back_populates="account",
        passive_deletes=True,
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)

    account: Mapped["Account"] = relationship(back_populates="users")


class Source(TimestampMixin, Base):
    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint("key", name="uq_sources_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    accounts: Mapped[list["Account"]] = relationship(
        secondary=account_sources,
        back_populates="sources",
    )
    events: Mapped[list["Event"]] = relationship(
        back_populates="source",
        passive_deletes=True,
    )
    event_logs: Mapped[list["EventLog"]] = relationship(
        back_populates="source",
        passive_deletes=True,
    )


class Event(TimestampMixin, Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payload: Mapped[str] = mapped_column(Text, nullable=False)

    account: Mapped["Account"] = relationship(back_populates="events")
    source: Mapped["Source"] = relationship(back_populates="events")
    summary_record: Mapped["EventSummary | None"] = relationship(
        back_populates="event",
        passive_deletes=True
    )
    logs: Mapped[list["EventLog"]] = relationship(
        back_populates="event",
        passive_deletes=True,
    )


class EventSummary(TimestampMixin, Base):
    __tablename__ = "event_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    summary: Mapped[str] = mapped_column(String(255), nullable=False)

    account: Mapped["Account"] = relationship(back_populates="event_summaries")
    event: Mapped["Event"] = relationship(back_populates="summary_record")


class QueuedEventRequest(TimestampMixin, Base):
    __tablename__ = "queued_event_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)


class EventLog(TimestampMixin, Base):
    __tablename__ = "event_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)

    event: Mapped["Event"] = relationship(back_populates="logs")
    source: Mapped["Source"] = relationship(back_populates="event_logs")
