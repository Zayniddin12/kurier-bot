from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class Payment(Base):
    """Onlayn to'lov urinishi (bitta buyurtmada bir nechta bo'lishi mumkin: havola muddati tugasa — yangisi)."""
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    provider: Mapped[str] = mapped_column(String(20), default="multicard")
    method: Mapped[str] = mapped_column(String(20), default="card")   # card | payme | click | uzum ...
    invoice_id: Mapped[str] = mapped_column(String(100), unique=True)   # bizning identifikator (Multicard ga yuboriladi)
    provider_uuid: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # Multicard tranzaksiya ID
    amount: Mapped[int] = mapped_column(BigInteger)                     # so'mda
    # pending | paid | cancelled | expired | refund_required | refunded
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    checkout_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    short_link: Mapped[str | None] = mapped_column(String(300), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    billing_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    card_pan: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ps: Mapped[str | None] = mapped_column(String(20), nullable=True)
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_callback: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
