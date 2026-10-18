from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class OrderIssue(Base):
    __tablename__ = "order_issues"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    courier_id: Mapped[int] = mapped_column(ForeignKey("couriers.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    auto_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
