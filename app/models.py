from datetime import datetime

from sqlalchemy import (
    Boolean,
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
    keywords: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    @property
    def keyword_list(self) -> list[str]:
        return [k for k in self.keywords.split(",") if k]

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
    rules: Mapped[list["Rule"]] = relationship(
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
    is_filtered: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")

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
    filter_logs: Mapped[list["EventFilterLog"]] = relationship(
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


class EventSummaryEmbedding(Base):
    __tablename__ = "event_summary_embeddings"

    model_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    event_summary_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("event_summary.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )


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


class Rule(TimestampMixin, Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source: Mapped["Source"] = relationship(back_populates="rules")
    filter_logs: Mapped[list["EventFilterLog"]] = relationship(
        back_populates="rule",
        passive_deletes=True,
    )


class EventFilterLog(TimestampMixin, Base):
    __tablename__ = "event_filter_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("rules.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)

    rule: Mapped["Rule | None"] = relationship(back_populates="filter_logs")
    event: Mapped["Event"] = relationship(back_populates="filter_logs")
