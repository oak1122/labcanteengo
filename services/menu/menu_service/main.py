"""menu-service — เจ้าของข้อมูลเมนู (ฐานข้อมูลของตัวเอง: menu-db)"""
import os
import time

from fastapi import FastAPI, HTTPException
from sqlalchemy import Integer, String, create_engine, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_th: Mapped[str] = mapped_column(String(100))
    shop_th: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(20))
    is_available: Mapped[bool] = mapped_column(default=True)


SEED = [
    ("ร้านป้าแดง ข้าวแกง", "rice", [("ข้าวแกงเขียวหวานไก่", 45), ("ข้าวผัดหมู", 40), ("ข้าวหมูกระเทียม", 45), ("ข้าวไข่เจียวหมูสับ", 35), ("ข้าวมันไก่", 40)]),
    ("ร้านลุงชัย ก๋วยเตี๋ยว", "noodle", [("ก๋วยเตี๋ยวเรือ", 40), ("เย็นตาโฟ", 45), ("ผัดไทยกุ้งสด", 50), ("บะหมี่หมูแดง", 45), ("ก๋วยเตี๋ยวต้มยำ", 45)]),
    ("ร้านน้ำหวาน", "drink", [("ชาเย็น", 25), ("โกโก้เย็น", 30), ("น้ำมะนาวโซดา", 25), ("กาแฟเย็น", 30), ("น้ำเปล่า", 10)]),
    ("ร้านของทอด", "snack", [("ไก่ทอด", 35), ("ไส้กรอกทอด", 25), ("เฟรนช์ฟรายส์", 30), ("ลูกชิ้นทอด", 20), ("กล้วยทอด", 20)]),
]


def item_dict(m: MenuItem) -> dict:
    return {"id": m.id, "name_th": m.name_th, "shop_th": m.shop_th, "price": m.price, "category": m.category,
            "is_available": m.is_available}


def connect(url: str, attempts: int = 30):
    """ฐานข้อมูลอาจยังไม่พร้อมตอนเริ่ม (docker compose) — ลองใหม่ทุกวินาที"""
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
    app = FastAPI(title="menu-service", root_path=os.environ.get("ROOT_PATH", "").rstrip("/"))
    engine = connect(os.environ.get("DATABASE_URL", "sqlite:///menu.db"))
    session = sessionmaker(engine, expire_on_commit=False)
    with session() as s:
        if s.scalar(select(MenuItem.id).limit(1)) is None:
            s.add_all(MenuItem(name_th=n, shop_th=shop, price=p, category=c) for shop, c, dishes in SEED for n, p in dishes)
            s.commit()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/ready")
    def ready() -> dict:
        with session() as s:
            s.execute(text("SELECT 1"))
        return {"status": "ready"}

    @app.get("/api/menu")
    def menu() -> dict:
        with session() as s:
            return {"items": [item_dict(m) for m in s.scalars(select(MenuItem).order_by(MenuItem.id))]}

    @app.get("/api/menu/{item_id}")
    def menu_item(item_id: int) -> dict:
        with session() as s:
            m = s.get(MenuItem, item_id)
        if m is None:
            raise HTTPException(404, "ไม่พบเมนูนี้")
        return item_dict(m)

    return app


app = create_app()
