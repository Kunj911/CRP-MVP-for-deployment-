"""
app/models/login_session.py

Tracks active JWT login sessions per user.

Allows the platform to:
- Audit login history (IP, user-agent, time)
- Implement token revocation by checking if a session is still valid
- Show active sessions in a future "Security" settings page

SQL reference: login_sessions table
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.user import User


class LoginSession(Base):
    __tablename__ = "login_sessions"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(
        "session_id", primary_key=True, autoincrement=True
    )

    # ── Foreign key ───────────────────────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Session data ──────────────────────────────────────────────────────────
    jwt_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    login_time: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="login_sessions")

    def __repr__(self) -> str:
        return (
            f"<LoginSession id={self.id} user_id={self.user_id} "
            f"ip='{self.ip_address}'>"
        )
