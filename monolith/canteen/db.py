"""ฐานข้อมูล: เมนูอาหารและออเดอร์ (SQLite ในไฟล์เดียว) — อ่านจากบนลงล่างแล้วเข้าใจได้ในห้านาที"""
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Integer, String, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

STATUS_STEPS = ((10, "received"), (40, "cooking"), (90, "ready"))  # วินาทีนับจากสั่ง


class Base(DeclarativeBase):
    pass


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_th: Mapped[str] = mapped_column(String(100))
    shop_th: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(20))  # rice | noodle | drink | snack
    is_available: Mapped[bool] = mapped_column(default=True)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(60))
    items: Mapped[list] = mapped_column(JSON)  # [{menu_id, name_th, qty, price}]
    total: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


def item_dict(m: MenuItem) -> dict:
    return {"id": m.id, "name_th": m.name_th, "shop_th": m.shop_th, "price": m.price, "category": m.category,
            "is_available": m.is_available}


def as_utc(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)  # SQLite เก็บเวลาโดยไม่มี time zone


def order_status(order: Order) -> str:
    """received → cooking → ready → picked_up ตามอายุของออเดอร์"""
    age = (datetime.now(UTC) - as_utc(order.created_at)).total_seconds()
    return next((name for limit, name in STATUS_STEPS if age < limit), "picked_up")


def order_dict(order: Order) -> dict:
    return {"id": order.id, "customer_name": order.customer_name, "items": order.items, "total": order.total,
            "status": order_status(order), "created_at": as_utc(order.created_at).isoformat()}


class Repo:
    def __init__(self, url: str) -> None:
        self.engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
        self.session = sessionmaker(self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

    def ping(self) -> None:
        with self.session() as s:
            s.execute(text("SELECT 1"))

    def menu(self) -> list[dict]:
        with self.session() as s:
            return [item_dict(m) for m in s.scalars(select(MenuItem).order_by(MenuItem.id))]

    def menu_item(self, item_id: int) -> dict | None:
        with self.session() as s:
            m = s.get(MenuItem, item_id)
            return item_dict(m) if m else None

    def create_order(self, customer_name: str, lines: list[tuple[int, int]]) -> dict:
        """`lines` = [(menu_id, qty)] — LookupError เมื่อไม่มีเมนูนั้นหรือหมดแล้ว"""
        with self.session() as s:
            items, total = [], 0
            for menu_id, qty in lines:
                m = s.get(MenuItem, menu_id)
                if m is None or not m.is_available:
                    raise LookupError(menu_id)
                items.append({"menu_id": m.id, "name_th": m.name_th, "qty": qty, "price": m.price})
                total += m.price * qty
            order = Order(customer_name=customer_name, items=items, total=total)
            s.add(order)
            s.commit()
            return order_dict(order)

    def order(self, order_id: int) -> dict | None:
        with self.session() as s:
            o = s.get(Order, order_id)
            return order_dict(o) if o else None

    def orders(self, limit: int) -> list[dict]:
        with self.session() as s:
            return [order_dict(o) for o in s.scalars(select(Order).order_by(Order.id.desc()).limit(limit))]

    def seed(self) -> None:
        with self.session() as s:
            if s.scalar(select(MenuItem.id).limit(1)) is not None:
                return
            s.add_all(MenuItem(name_th=n, shop_th=shop, price=p, category=c) for shop, c, dishes in SEED for n, p in dishes)
            s.commit()


SEED = [
    ("ร้านป้าแดง ข้าวแกง", "rice", [("ข้าวแกงเขียวหวานไก่", 45), ("ข้าวผัดหมู", 40), ("ข้าวหมูกระเทียม", 45), ("ข้าวไข่เจียวหมูสับ", 35), ("ข้าวมันไก่", 40)]),
    ("ร้านลุงชัย ก๋วยเตี๋ยว", "noodle", [("ก๋วยเตี๋ยวเรือ", 40), ("เย็นตาโฟ", 45), ("ผัดไทยกุ้งสด", 50), ("บะหมี่หมูแดง", 45), ("ก๋วยเตี๋ยวต้มยำ", 45)]),
    ("ร้านน้ำหวาน", "drink", [("ชาเย็น", 25), ("โกโก้เย็น", 30), ("น้ำมะนาวโซดา", 25), ("กาแฟเย็น", 30), ("น้ำเปล่า", 10)]),
    ("ร้านของทอด", "snack", [("ไก่ทอด", 35), ("ไส้กรอกทอด", 25), ("เฟรนช์ฟรายส์", 30), ("ลูกชิ้นทอด", 20), ("กล้วยทอด", 20)]),
]
