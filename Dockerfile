FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    DEBUG=false \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 10001 insightai \
    && mkdir -p /app/models /app/logs /app/exports /app/data \
    && chown -R insightai:insightai /app

USER insightai

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=8s --start-period=90s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

CMD ["python", "backend/run.py"]
