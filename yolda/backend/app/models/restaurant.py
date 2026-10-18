from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Float, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class Restaurant(Base):
    __tablename__ = "restaurants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    cuisine: Mapped[str] = mapped_column(String(200), default="")
    district: Mapped[str] = mapped_column(String(100), default="")
    address: Mapped[str] = mapped_column(String(300), default="")
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    color: Mapped[str] = mapped_column(String(10), default="#E4572E")
    integration_type: Mapped[str] = mapped_column(String(20), default="API")
    pos_system: Mapped[str] = mapped_column(String(50), default="")
    status: Mapped[str] = mapped_column(String(20), default="open")
    pause_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    rating: Mapped[float] = mapped_column(Numeric(2, 1), default=4.5)
    prep_minutes: Mapped[int] = mapped_column(Integer, default=15)
    phone: Mapped[str] = mapped_column(String(30), default="")
    hours: Mapped[str] = mapped_column(String(30), default="09:00–22:00")
    manager: Mapped[str] = mapped_column(String(100), default="")
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    api_key_prefix: Mapped[str | None] = mapped_column(String(30), nullable=True)
    api_key_hash: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
