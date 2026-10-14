"""ชุดวัดโหลดของ Capstone (locust): เรียก /api/menu บ่อย ๆ และสั่งอาหารบ้าง ผ่าน gateway
รัน: docker compose -f compose.split.yml --profile loadtest run --rm locust   (ผลอยู่ที่ loadtest/results/)
วัด "ก่อน" และ "หลัง" ด้วยเงื่อนไขเดียวกัน (USERS / SPAWN_RATE / RUN_TIME) และจดไว้ในรายงาน"""
import random

from locust import HttpUser, between, task


class Customer(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self) -> None:
        res = self.client.get("/api/menu", name="/api/menu")
        items = res.json().get("items", []) if res.status_code == 200 else []
        self.menu_ids = [i["id"] for i in items if i.get("is_available", True)] or [1]

    @task(3)
    def browse_menu(self) -> None:
        self.client.get("/api/menu", name="/api/menu")

    @task(1)
    def place_order(self) -> None:
        item = {"menu_id": random.choice(self.menu_ids), "qty": random.randint(1, 2)}
        with self.client.post(
            "/api/orders", json={"customer_name": "loadtest", "items": [item]}, name="/api/orders", catch_response=True
        ) as res:
            if res.status_code == 201:
                res.success()
            else:
                res.failure(f"status {res.status_code}")
