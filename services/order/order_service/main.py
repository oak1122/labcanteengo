"""order-service — เจ้าของข้อมูลออเดอร์ (order-db) ราคาเมนูถามจาก menu-service ผ่าน HTTP (ไม่แตะฐานข้อมูลของเมนู)"""
import os
import time
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, Integer, String, create_engine, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

STATUS_STEPS = ((10, "received"), (40, "cooking"), (90, "ready"))


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(60))
    items: Mapped[list] = mapped_column(JSON)
    total: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class OrderLineIn(BaseModel):
    menu_id: int
    qty: int = Field(ge=1, le=10)


class OrderIn(BaseModel):
    customer_name: str = Field(min_length=1, max_length=60)
    items: list[OrderLineIn] = Field(min_length=1, max_length=20)


def as_utc(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def order_dict(o: Order) -> dict:
    age = (datetime.now(UTC) - as_utc(o.created_at)).total_seconds()
    status = next((name for limit, name in STATUS_STEPS if age < limit), "picked_up")
    return {"id": o.id, "customer_name": o.customer_name, "items": o.items, "total": o.total, "status": status,
            "created_at": as_utc(o.created_at).isoformat()}


def connect(url: str, attempts: int = 30):
    engine = create_engine(url, pool_pre_ping=True)
    for n in range(attempts):
        try:
            Base.metadata.create_all(engine)
            return engine
        except OperationalError:
            if n == attempts - 1:
                raise
            time.sleep(1)


def create_app() -> FastAPI:
    app = FastAPI(title="order-service", root_path=os.environ.get("ROOT_PATH", "").rstrip("/"))
    engine = connect(os.environ.get("DATABASE_URL", "sqlite:///order.db"))
    session = sessionmaker(engine, expire_on_commit=False)
    menu_url = os.environ.get("MENU_URL", "http://menu:8000").rstrip("/")

    def price_of(menu_id: int) -> dict:
        """เรียก menu-service — ถ้า menu ล่ม ออเดอร์ก็สร้างไม่ได้ (การพึ่งพากันระหว่าง service)"""
        try:
            res = httpx.get(f"{menu_url}/api/menu/{menu_id}", timeout=2.0)
        except httpx.HTTPError:
            raise HTTPException(503, "menu-service ไม่ตอบสนอง") from None
        if res.status_code == 404 or (res.status_code == 200 and not res.json()["is_available"]):
            raise HTTPException(422, f"เมนูหมายเลข {menu_id} ไม่มีอยู่หรือหมดแล้ว")
        if res.status_code != 200:
            raise HTTPException(503, "menu-service ตอบผิดปกติ")
        return res.json()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/ready")
    def ready() -> dict:
        with session() as s:
            s.execute(text("SELECT 1"))
        return {"status": "ready"}

    @app.post("/api/orders", status_code=201)
    def create_order(body: OrderIn) -> dict:
        items, total = [], 0
        for line in body.items:
            m = price_of(line.menu_id)
            items.append({"menu_id": m["id"], "name_th": m["name_th"], "qty": line.qty, "price": m["price"]})
            total += m["price"] * line.qty
        with session() as s:
            order = Order(customer_name=body.customer_name.strip(), items=items, total=total)
            s.add(order)
            s.commit()
            return order_dict(order)

    @app.get("/api/orders/{order_id}")
    def get_order(order_id: int) -> dict:
        with session() as s:
            o = s.get(Order, order_id)
        if o is None:
            raise HTTPException(404, "ไม่พบออเดอร์นี้")
        return order_dict(o)

    @app.get("/api/orders")
    def list_orders(limit: int = Query(20, ge=1, le=100)) -> dict:
        with session() as s:
            return {"items": [order_dict(o) for o in s.scalars(select(Order).order_by(Order.id.desc()).limit(limit))]}

    return app


app = create_app()
