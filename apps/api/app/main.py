from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.errors import AppError
from app.routers import (
    auth,
    chat,
    incense,
    meta,
    payment,
    profile,
    qian,
    scripture,
    wiki,
    wish,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(
    title="赛博天机寺 API",
    version="0.1.0",
    description="传统文化娱乐与心理疗愈 · 后端服务",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 统一错误响应 ──
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    msg = first.get("msg", "请求参数有误")
    # pydantic 的 "Value error, xxx" 去掉前缀更友好
    msg = msg.replace("Value error, ", "")
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "BAD_REQUEST", "message": msg, "details": exc.errors()}},
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("tianji").exception("未处理异常：%s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL", "message": "服务器开小差了，请稍后再试"}},
    )


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "llm": settings.llm_provider, "payment": settings.payment_provider}


for r in (auth, meta, qian, incense, wish, chat, scripture, wiki, profile, payment):
    app.include_router(r.router)
