"""SQLAlchemy engine/session factory with PostgreSQL as the production target."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .schema import Base


class Database:
    """Own database resources; schema creation is explicit and idempotent."""

    def __init__(self, url: str) -> None:
        if not url:
            raise ValueError("DATABASE_URL is required")
        options: dict[str, object] = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            options.update({"connect_args": {"check_same_thread": False}})
            if ":memory:" in url:
                options["poolclass"] = StaticPool
        self.engine: Engine = create_engine(url, **options)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def create_schema(self) -> None:
        """Create missing tables only; never deletes or rewrites audit rows."""
        Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        return self._session_factory()
