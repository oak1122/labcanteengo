"""JSON API และ /health — เหมือนระบบกลางของรายวิชา แต่ไม่มี chaos engine"""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter()


class OrderLineIn(BaseModel):
    menu_id: int
    qty: int = Field(ge=1, le=10)


class OrderIn(BaseModel):
    customer_name: str = Field(min_length=1, max_length=60)
    items: list[OrderLineIn] = Field(min_length=1, max_length=20)


@router.get("/api/menu")
def menu(request: Request) -> dict:
    return {"items": request.app.state.repo.menu()}


@router.get("/api/menu/{item_id}")
def menu_item(item_id: int, request: Request) -> dict:
    item = request.app.state.repo.menu_item(item_id)
    if item is None:
        raise HTTPException(404, "ไม่พบเมนูนี้")
    return item


@router.post("/api/orders", status_code=201)
def create_order(body: OrderIn, request: Request) -> dict:
    try:
        return request.app.state.repo.create_order(body.customer_name.strip(), [(i.menu_id, i.qty) for i in body.items])
    except LookupError as exc:
        raise HTTPException(422, f"เมนูหมายเลข {exc.args[0]} ไม่มีอยู่หรือหมดแล้ว") from None


@router.get("/api/orders/{order_id}")
def get_order(order_id: int, request: Request) -> dict:
    order = request.app.state.repo.order(order_id)
    if order is None:
        raise HTTPException(404, "ไม่พบออเดอร์นี้")
    return order


@router.get("/api/orders")
def list_orders(request: Request, limit: int = Query(20, ge=1, le=100)) -> dict:
    return {"items": request.app.state.repo.orders(limit)}


@router.get("/health")
def health() -> dict:
    """Liveness: "โปรเซสยังมีชีวิตไหม" — ไม่แตะฐานข้อมูล"""
    return {"status": "ok"}
