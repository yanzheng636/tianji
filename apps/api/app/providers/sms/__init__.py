"""短信验证码 Provider。

``console`` 只允许本地开发；生产使用阿里云 SendSms RPC 接口。
阿里云的签名遵循官方 POP/RPC 签名协议，凭证只从环境变量读取。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import quote

import httpx

from app.core.config import settings

logger = logging.getLogger("tianji.sms")


class SmsProvider(Protocol):
    async def send_code(self, phone: str, code: str) -> None: ...


class SmsDeliveryError(RuntimeError):
    """短信服务拒绝、超时或返回非成功码。"""


class ConsoleSms:
    async def send_code(self, phone: str, code: str) -> None:
        logger.info("📱 [console-sms] 向 %s 发送验证码：%s", phone, code)


class AliyunSms:
    """阿里云短信 SendSms RPC 调用。

    请求采用 POST + application/x-www-form-urlencoded，按阿里云官方
    ``SignatureMethod=HMAC-SHA1`` POP 规则签名；这样生产镜像不需要额外
    SDK，也不会把 AccessKey 放到请求 URL 或日志中。
    """

    def __init__(self) -> None:
        self._key_id = settings.aliyun_sms_access_key_id
        self._secret = settings.aliyun_sms_access_key_secret
        self._sign = settings.aliyun_sms_sign_name
        self._template = settings.aliyun_sms_template_code
        self._region = settings.aliyun_sms_region_id
        self._endpoint = settings.aliyun_sms_endpoint
        if not all([self._key_id, self._secret, self._sign, self._template]):
            raise RuntimeError("SMS_PROVIDER=aliyun 但阿里云短信配置不完整")

    @staticmethod
    def _encode(value: str) -> str:
        return quote(str(value), safe="-_.~")

    def _signed_params(self, phone: str, code: str) -> tuple[str, str]:
        params = {
            "AccessKeyId": self._key_id or "",
            "Action": "SendSms",
            "Format": "JSON",
            "PhoneNumbers": phone,
            "RegionId": self._region,
            "SignName": self._sign or "",
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": str(uuid.uuid4()),
            "SignatureVersion": "1.0",
            "TemplateCode": self._template or "",
            "TemplateParam": json.dumps({"code": code}, ensure_ascii=False, separators=(",", ":")),
            "Timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Version": "2017-05-25",
        }
        canonical = "&".join(
            f"{self._encode(key)}={self._encode(params[key])}"
            for key in sorted(params)
        )
        string_to_sign = f"POST&%2F&{self._encode(canonical)}"
        digest = hmac.new(
            f"{self._secret}&".encode(), string_to_sign.encode(), hashlib.sha1
        ).digest()
        params["Signature"] = base64.b64encode(digest).decode()
        body = "&".join(
            f"{self._encode(key)}={self._encode(params[key])}"
            for key in sorted(params)
        )
        return body, params["Signature"]

    async def send_code(self, phone: str, code: str) -> None:
        body, _ = self._signed_params(phone, code)
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0)) as client:
                response = await client.post(
                    self._endpoint,
                    content=body,
                    headers={"content-type": "application/x-www-form-urlencoded; charset=utf-8"},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("阿里云短信请求失败：%s", type(exc).__name__)
            raise SmsDeliveryError("短信服务暂时不可用，请稍后重试") from exc

        result_code = str(payload.get("Code") or "")
        if result_code != "OK":
            message = str(payload.get("Message") or "短信服务拒绝发送")
            request_id = str(payload.get("RequestId") or "")
            logger.warning(
                "阿里云短信返回失败 code=%s request_id=%s message=%s",
                result_code,
                request_id,
                message,
            )
            raise SmsDeliveryError("短信发送失败，请检查短信签名和模板配置")
        logger.info("阿里云短信已受理 phone=%s request_id=%s", _mask_phone(phone), payload.get("RequestId", ""))


def _mask_phone(phone: str) -> str:
    return f"{phone[:3]}****{phone[-4:]}" if len(phone) >= 7 else "***"


_instance: SmsProvider | None = None


def get_sms() -> SmsProvider:
    global _instance
    if _instance is None:
        _instance = AliyunSms() if settings.sms_provider == "aliyun" else ConsoleSms()
    return _instance
