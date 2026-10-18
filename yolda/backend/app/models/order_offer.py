from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class OrderOffer(Base):
    __tablename__ = "order_offers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    courier_id: Mapped[int] = mapped_column(ForeignKey("couriers.id"), index=True)
    offered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    result: Mapped[str] = mapped_column(String(20), default="pending", index=True)
