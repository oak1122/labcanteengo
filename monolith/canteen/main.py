"""CanteenGo (monolith) — ระบบสั่งอาหารโรงอาหารแบบก้อนเดียว จุดเริ่มต้นของโปรเจ็กต์ทีม"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response

from canteen import api, pages
from canteen.db import Repo


def create_app() -> FastAPI:
    root_path = os.environ.get("ROOT_PATH", "").rstrip("/")  # ปกติว่าง: แอปอยู่ที่ราก / ของโฮสต์ทีมเอง (ใส่ได้ถ้าต้องวางไว้ใต้ path)
    url = os.environ.get("DATABASE_URL", "sqlite:////data/canteen.db")
    app = FastAPI(title="CanteenGo", root_path=root_path)
    app.state.root_path = root_path
    app.state.repo = Repo(url)
    app.state.repo.seed()
    app.state.carts = {}  # cart id → {menu_id: qty}
    app.include_router(api.router)
    app.include_router(pages.router)

    static_dir = (Path(__file__).parent / "static").resolve()

    @app.get("/static/{filename}", include_in_schema=False)
    def static_file(filename: str) -> Response:
        path = (static_dir / filename).resolve()
        if path.parent != static_dir or not path.is_file():
            return Response(status_code=404)
        return FileResponse(path)

    return app


app = create_app()
