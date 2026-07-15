"""业务错误。抛出后由全局 handler 统一转成 {error: {code, message}}。"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def unauthorized(msg: str = "请先登录") -> AppError:
    return AppError(401, "UNAUTHORIZED", msg)


def forbidden(msg: str = "无权访问") -> AppError:
    return AppError(403, "FORBIDDEN", msg)


def not_found(msg: str = "资源不存在") -> AppError:
    return AppError(404, "NOT_FOUND", msg)


def bad_request(msg: str, details: Any = None) -> AppError:
    return AppError(400, "BAD_REQUEST", msg, details)


def rate_limited(msg: str = "操作太频繁，请稍后再试") -> AppError:
    return AppError(429, "RATE_LIMITED", msg)


def quota_exceeded(msg: str = "今日额度已用完") -> AppError:
    return AppError(429, "QUOTA_EXCEEDED", msg)


def moderation_rejected(msg: str = "内容未通过审核") -> AppError:
    return AppError(422, "MODERATION_REJECTED", msg)


def payment_error(msg: str) -> AppError:
    return AppError(402, "PAYMENT_ERROR", msg)


def service_unavailable(msg: str) -> AppError:
    return AppError(503, "SERVICE_UNAVAILABLE", msg)
