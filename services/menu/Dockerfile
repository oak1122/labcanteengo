# menu-service — docker build ./services/menu
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt && useradd --create-home --uid 1000 app
COPY menu_service ./menu_service
ENV ROOT_PATH=""
EXPOSE 8000
USER app
CMD ["uvicorn", "menu_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
