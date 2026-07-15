# ── 后端镜像 ──
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先装依赖（利用层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir "uvicorn[standard]"

COPY . .

EXPOSE 3001

# 启动前先跑迁移，再拉起服务
CMD alembic upgrade head && \
    python -m app.seed && \
    uvicorn app.main:app --host 0.0.0.0 --port 3001
