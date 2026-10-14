"""หน้าเว็บ (Jinja2 + HTMX) — ทุกลิงก์และ form ผ่านตัวแปร `root` (= ROOT_PATH) เพื่อให้ใช้ได้หลัง /salab/p/teamNN"""
import secrets
from itertools import groupby
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates


router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

CART_COOKIE = "cart_id"


def render(request: Request, name: str, **context) -> HTMLResponse:
    return templates.TemplateResponse(request, name, {"root": request.app.state.root_path, **context})


def cart_lines(request: Request, cart_id: str) -> tuple[list[dict], int]:
    """ตะกร้าเก็บในหน่วยความจำ (หายเมื่อรีสตาร์ต — จุดอ่อนที่นักศึกษาสังเกตได้)"""
    menu = {m["id"]: m for m in request.app.state.repo.menu()}
    lines = [{**menu[i], "qty": q, "subtotal": menu[i]["price"] * q} for i, q in request.app.state.carts.get(cart_id, {}).items() if i in menu]
    return lines, sum(line["subtotal"] for line in lines)


def cart_panel(request: Request, cart_id: str) -> HTMLResponse:
    lines, total = cart_lines(request, cart_id)
    response = render(request, "partials/cart.html", lines=lines, total=total)
    response.set_cookie(CART_COOKIE, cart_id, httponly=True, samesite="lax", path=request.app.state.root_path or "/")
    return response


def current_cart_id(request: Request) -> str:
    return request.cookies.get(CART_COOKIE) or secrets.token_urlsafe(12)


@router.get("/")
def index(request: Request) -> HTMLResponse:
    menu = sorted(request.app.state.repo.menu(), key=lambda m: (m["shop_th"], m["id"]))
    shops = [(shop, list(items)) for shop, items in groupby(menu, key=lambda m: m["shop_th"])]
    lines, total = cart_lines(request, request.cookies.get(CART_COOKIE, ""))
    return render(request, "index.html", shops=shops, lines=lines, total=total)


@router.post("/cart/add")
def cart_add(request: Request, menu_id: int = Form()) -> HTMLResponse:
    cart_id = current_cart_id(request)
    cart = request.app.state.carts.setdefault(cart_id, {})
    if len(cart) < 20:
        cart[menu_id] = min(cart.get(menu_id, 0) + 1, 10)
    return cart_panel(request, cart_id)


@router.post("/cart/clear")
def cart_clear(request: Request) -> HTMLResponse:
    cart_id = current_cart_id(request)
    request.app.state.carts.pop(cart_id, None)
    return cart_panel(request, cart_id)


@router.post("/cart/checkout")
def checkout(request: Request, customer_name: str = Form(min_length=1, max_length=60)) -> Response:
    cart_id = request.cookies.get(CART_COOKIE, "")
    cart = request.app.state.carts.get(cart_id)
    if not cart:
        raise HTTPException(400, "ตะกร้าว่างอยู่")
    try:
        order = request.app.state.repo.create_order(customer_name.strip(), list(cart.items()))
    except LookupError:
        raise HTTPException(422, "มีเมนูในตะกร้าที่หมดแล้ว") from None
    request.app.state.carts.pop(cart_id, None)
    url = f"{request.app.state.root_path}/orders/{order['id']}"
    if request.headers.get("HX-Request"):
        return Response(status_code=204, headers={"HX-Redirect": url})
    return RedirectResponse(url, status_code=303)


@router.get("/orders/{order_id}")
def order_page(order_id: int, request: Request) -> HTMLResponse:
    order = request.app.state.repo.order(order_id)
    if order is None:
        raise HTTPException(404, "ไม่พบออเดอร์นี้")
    return render(request, "order.html", order=order)


@router.get("/orders/{order_id}/status")
def order_status_partial(order_id: int, request: Request) -> HTMLResponse:
    order = request.app.state.repo.order(order_id)
    if order is None:
        raise HTTPException(404, "ไม่พบออเดอร์นี้")
    return render(request, "partials/order_status.html", order=order)
