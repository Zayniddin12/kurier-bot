from datetime import datetime
from sqlalchemy import (ARRAY, BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, Numeric, Sequence,
                        String, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("restaurant_id", "external_id", name="uq_order_ext"),)
    id: Mapped[int] = mapped_column(BigInteger, Sequence("orders_id_seq", start=118401), primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    subtotal: Mapped[int] = mapped_column(BigInteger, default=0)
    delivery_fee: Mapped[int] = mapped_column(BigInteger, default=0)
    total: Mapped[int] = mapped_column(BigInteger, default=0)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    pay_method: Mapped[str] = mapped_column(String(20), default="Naqd")
    pay_status: Mapped[str] = mapped_column(String(20), default="cod")
    customer_name: Mapped[str] = mapped_column(String(200), default="")
    customer_phone: Mapped[str] = mapped_column(String(30), default="")
    district: Mapped[str] = mapped_column(String(100), default="")
    address: Mapped[str] = mapped_column(String(400), default="")
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    courier_id: Mapped[int | None] = mapped_column(ForeignKey("couriers.id"), nullable=True, index=True)
    queued: Mapped[bool] = mapped_column(Boolean, default=False)
    queue_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    search_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    declined_courier_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    picked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    prep_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delay_added_minutes: Mapped[int] = mapped_column(Integer, default=0)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    customer_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reassigned_count: Mapped[int] = mapped_column(Integer, default=0)
    handoff_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    handoff_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    handoff_name: Mapped[str | None] = mapped_column(String(200), nullable=True)


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    qty: Mapped[int] = mapped_column(Integer, default=1)
    price: Mapped[int] = mapped_column(BigInteger, default=0)
