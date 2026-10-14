# CanteenGo Starter Kit — ชุดเริ่มต้นของ Capstone ทีม

ระบบสั่งอาหารโรงอาหาร (ชื่อสมมติ) ที่คุณศึกษามาตลอด Lab 1–6 ตอนนี้เป็นของทีมคุณ: **รันบนเครื่องของทีมเอง** แยกเป็นหลาย service ด้วย Docker Compose วัดผลด้วย locust แล้วนำผลไปเขียนรายงานและสาธิตในวิดีโอ (รายละเอียดงานและเกณฑ์อยู่ในหน้า Capstone ของ SA Lab)

## มีอะไรในโฟลเดอร์นี้
| ที่ไหน | คืออะไร |
|---|---|
| `monolith/` | ระบบก้อนเดียว (FastAPI + Jinja2 + HTMX + SQLite) |
| `services/menu/` | **menu-service** — เจ้าของข้อมูลเมนู (API ล้วน) |
| `services/order/` | **order-service** — เจ้าของข้อมูลออเดอร์ ถามราคาจาก menu-service ผ่าน HTTP |
| `gateway/nginx.conf` | API gateway (**มี TODO ให้ทำ**) |
| `compose.monolith.yml` | รันแบบก้อนเดียว |
| `compose.split.yml` | รันแบบแยก service (**ยังไม่ครบ มี TODO**) + ชุดวัดโหลด `locust` |
| `loadtest/locustfile.py` | สคริปต์วัดโหลด (เรียก `/api/menu` บ่อย ๆ และสั่งอาหารบ้าง) ผลเก็บใน `loadtest/results/` |
| `.devcontainer/` | ตั้งค่าสำหรับ GitHub Codespaces |

> ไฟล์ที่ต้องแก้หลัก ๆ มี 2 ไฟล์: `gateway/nginx.conf` และ `compose.split.yml` — ค้นหาคำว่า `TODO`

## 0. เตรียมเครื่อง
**ทางหลัก — Docker Desktop (Windows / macOS)**
1. ติดตั้ง Docker Desktop จาก https://www.docker.com/products/docker-desktop/ แล้วเปิดโปรแกรมทิ้งไว้จนสถานะเป็น Running
2. เปิดเทอร์มินัล (PowerShell / Terminal) แล้วตรวจ: `docker compose version` ต้องแสดงเวอร์ชัน
3. แตกไฟล์ starter แล้ว `cd` เข้าโฟลเดอร์นี้

**ทางสำรอง — GitHub Codespaces** (ถ้าไม่มีเครื่องที่ลง Docker ได้)
1. สร้าง repo บน GitHub ของทีม แล้ว push โฟลเดอร์นี้ขึ้นไป (ต้องมี `.devcontainer/` อยู่ใน repo)
2. หน้า repo → ปุ่ม **Code** → แท็บ **Codespaces** → **Create codespace on main**
3. รอจนเทอร์มินัลด้านล่างพร้อม แล้วตรวจ `docker compose version` · พอร์ต 8080 จะถูกเปิดให้ดูในเบราว์เซอร์อัตโนมัติ (แท็บ Ports)
4. บัญชีฟรีใช้ได้ประมาณ 60 ชั่วโมงต่อเดือนบนเครื่อง 2 core — **หยุด Codespace ทุกครั้งที่เลิกใช้** (Code → Codespaces → ⋯ → Stop codespace)

> ไม่ต้องสร้างหรือแก้ไฟล์ `.env` — ค่าเริ่มต้นใช้ได้เลย

## 1. รันแบบก้อนเดียวก่อน
```bash
docker compose -f compose.monolith.yml up -d --build
docker compose -f compose.monolith.yml ps
curl http://localhost:8080/health          # {"status":"ok"}
```
เปิด http://localhost:8080/ ในเบราว์เซอร์ ลองสั่งอาหาร เมื่อพอใจแล้วหยุดก่อนไปขั้นถัดไป (ใช้พอร์ต 8080 ร่วมกัน): `docker compose -f compose.monolith.yml down`

## 2. แยกเป็นหลาย service
1. `gateway/nginx.conf`: เติม `location /api/menu` → `menu:8000` และ `location /api/orders` → `order:8000`
2. `compose.split.yml`: เติมตาม TODO — `menu-db` / `order-db` (Postgres แยกกัน ไม่เปิดพอร์ต), `DATABASE_URL`, `healthcheck`, `depends_on` (ใช้ `condition: service_healthy`) และ `restart: unless-stopped` **ทุก service** (รวม gateway และฐานข้อมูล)
3. รัน:
   ```bash
   docker compose -f compose.split.yml up -d --build
   docker compose -f compose.split.yml ps       # ทุกตัวต้อง healthy
   curl http://localhost:8080/api/menu          # ต้องเห็น {"items": [...]}
   ```

## 3. วัดผลด้วย locust (QAS ก่อน/หลัง)
```bash
docker compose -f compose.split.yml --profile loadtest run --rm locust
```
- ค่าเริ่มต้น: 20 ผู้ใช้ · เพิ่มทีละ 5 คน/วินาที · 1 นาที — ปรับด้วยตัวแปร เช่น `USERS=50 RUN_TIME=2m docker compose -f compose.split.yml --profile loadtest run --rm locust` (ในเทอร์มินัล PowerShell ให้ตั้งตัวแปรก่อน: `$env:USERS=50; $env:RUN_TIME="2m"`)
- ผลสรุปแสดงในเทอร์มินัล และเก็บเป็น CSV ที่ `loadtest/results/` (`stats_stats.csv` = สรุปต่อ endpoint มีคอลัมน์ percentile เช่น 95%)
- **วัด "ก่อน" และ "หลัง" ด้วยเงื่อนไขเดียวกัน** (จำนวนผู้ใช้ เวลา เครื่องเดียวกัน) แล้วจดเงื่อนไขไว้ในรายงาน · เปลี่ยนชื่อไฟล์ผลก่อนวัดครั้งถัดไปไม่ให้ทับกัน
- ก่อนวัดให้ระบบ healthy ครบ และอย่าเปิดโปรแกรมหนัก ๆ อื่นพร้อมกัน (ตัวเลขจะแกว่ง)

## 4. คำสั่งสำหรับวิดีโอสาธิต (≤ 5 นาที)
ในวิดีโอต้องเห็นตามลำดับ:
```bash
# 1) ขึ้นระบบ และทุก service ต้อง healthy
docker compose -f compose.split.yml up -d --build
docker compose -f compose.split.yml ps

# 2) เรียก API ผ่าน gateway
curl http://localhost:8080/api/menu
curl -X POST http://localhost:8080/api/orders -H "Content-Type: application/json" -d "{\"customer_name\":\"demo\",\"items\":[{\"menu_id\":1,\"qty\":1}]}"

# 3) ทำให้ service หนึ่งดับเอง แล้วดูว่ากลับมาเองด้วย restart policy
docker compose -f compose.split.yml exec menu python -c "import os,signal; os.kill(1, signal.SIGTERM)"
docker compose -f compose.split.yml ps
docker inspect -f "RestartCount={{.RestartCount}}" $(docker compose -f compose.split.yml ps -q menu)
```
- ข้อ 3: คำสั่ง `exec … os.kill` ทำให้ process หลักของ menu ออกเอง (เหมือน service พังจริง) แล้ว Docker เริ่มใหม่ตาม `restart: unless-stopped` — `RestartCount` ต้องเพิ่มขึ้น และ `ps` กลับเป็น healthy ภายในไม่กี่วินาที
- **อย่าใช้ `docker compose stop` หรือ `docker compose kill` สาธิตข้อนี้** — Docker ถือว่าคุณสั่งหยุดเอง จึง *ไม่* เริ่มใหม่ให้ (ถ้ารันแล้วเห็น `exited` ให้ `docker compose -f compose.split.yml start menu`)
- (ทดสอบแล้วกับเฉลยของอาจารย์: `RestartCount` 0 → 1 และ menu กลับเป็น healthy; ถ้าระบบของทีมไม่ใส่ `restart` จะเห็น `exited` ค้างอยู่)
- สุดท้ายสรุปผลวัด QAS ก่อน/หลัง (ตัวเลขหรือกราฟจาก `loadtest/results/`)

## แก้ปัญหา
| อาการ | ลองอะไร |
|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop ยังไม่เปิด — เปิดแล้วรอจนเป็น Running |
| `port is already allocated` / พอร์ต 8080 ชน | หยุดชุดที่รันอยู่ (`docker compose -f <ไฟล์> down`) หรือเปลี่ยนพอร์ต: `TEAM_PORT=8081 docker compose -f <ไฟล์> up -d` (PowerShell: `$env:TEAM_PORT=8081`) แล้วใช้ `localhost:8081` แทน |
| service ขึ้นแล้วดับซ้ำ ๆ / ไม่ healthy | `docker compose -f <ไฟล์> logs <ชื่อ service>` อ่านบรรทัดสุดท้าย |
| `build` ช้าหรือโหลดไม่ได้ | เครือข่ายช้า รอแล้วลองใหม่ · รอบถัดไปจะเร็วขึ้น (มี cache) |
| ข้อมูลเก่าค้าง อยากเริ่มใหม่หมด | `docker compose -f <ไฟล์> down -v` (ลบข้อมูลในฐานข้อมูลด้วย) |
| Codespace ช้าหรือโควตาใกล้หมด | หยุด Codespace เมื่อไม่ใช้ · ทำงานหนักบนเครื่องสมาชิกที่ลง Docker ได้ แล้ว push ผ่าน git |

## กติกา
- **ห้ามใส่รหัสผ่านหรือคีย์จริง** ลงในไฟล์ที่ push ขึ้น git (ไฟล์ `.env` อยู่ใน `.gitignore` แล้ว)
- ใช้ AI ช่วยได้ แต่ต้องระบุในหัวข้อ "การใช้ AI" ของรายงาน และทุกคนในทีมต้องอธิบายระบบได้ในการสอบปากเปล่า
- แต่ละทีมทำงานของตัวเอง ห้ามคัดลอกงานทีมอื่น
