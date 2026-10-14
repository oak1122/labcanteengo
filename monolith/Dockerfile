# CanteenGo monolith — docker build ./monolith
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt \
    && useradd --create-home --uid 1000 app \
    && mkdir /data && chown app:app /data
COPY canteen ./canteen
ENV ROOT_PATH=""
VOLUME /data
EXPOSE 8000
USER app
# --proxy-headers: อยู่หลัง nginx ต้องเชื่อ header ที่ส่งต่อมา
CMD ["uvicorn", "canteen.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
