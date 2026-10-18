from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class Courier(Base):
    __tablename__ = "couriers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20))
    pinfl: Mapped[str] = mapped_column(String(14), unique=True)
    vehicle: Mapped[str] = mapped_column(String(20), default="Skuter")
    plate: Mapped[str] = mapped_column(String(20), default="—")
    shift: Mapped[str] = mapped_column(String(20), default="09:00–21:00")
    rating: Mapped[float] = mapped_column(Numeric(2, 1), default=5.0)
    account_status: Mapped[str] = mapped_column(String(20), default="active")
    work_status: Mapped[str] = mapped_column(String(20), default="offline")
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    online_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idle_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    break_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    balance: Mapped[int] = mapped_column(BigInteger, default=0)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_order_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_female: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_seed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    api_token_hash: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
