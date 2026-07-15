from __future__ import annotations

import pytest

from app.core.errors import AppError
from app.core.redis_client import MemoryStore
from app.providers import sms
from app.providers.sms import SmsDeliveryError
from app.services import auth


class FailingSms:
    async def send_code(self, phone: str, code: str) -> None:
        raise SmsDeliveryError("短信服务暂时不可用，请稍后重试")


@pytest.mark.asyncio
async def test_send_code_failure_releases_cooldown_and_daily_counter(monkeypatch):
    store = MemoryStore()

    async def fake_get_kv():
        return store

    monkeypatch.setattr(auth, "get_kv", fake_get_kv)
    monkeypatch.setattr(auth, "get_sms", lambda: FailingSms())

    with pytest.raises(AppError) as error:
        await auth.send_code("13800138000")

    assert error.value.status_code == 503
    assert await store.get(auth._cooldown_key("13800138000")) is None
    assert await store.get(auth._daily_key("13800138000")) == "0"


@pytest.mark.asyncio
async def test_memory_store_set_if_absent_prevents_duplicate_cooldown():
    store = MemoryStore()
    key = "sms:cd:13800138000"
    assert await store.set_if_absent(key, "1", 60) is True
    assert await store.set_if_absent(key, "1", 60) is False


def _aliyun_provider() -> sms.AliyunSms:
    provider = object.__new__(sms.AliyunSms)
    provider._key_id = "test-key"
    provider._secret = "test-secret"
    provider._sign = "测试签名"
    provider._template = "SMS_TEST"
    provider._region = "cn-hangzhou"
    provider._endpoint = "https://dysmsapi.aliyuncs.com/"
    return provider


@pytest.mark.asyncio
async def test_aliyun_non_ok_response_is_delivery_error(monkeypatch):
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"Code": "isv.MOBILE_NUMBER_ILLEGAL", "Message": "bad phone"}

    class Client:
        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, *_args: object, **_kwargs: object) -> Response:
            return Response()

    monkeypatch.setattr(sms.httpx, "AsyncClient", lambda **_kwargs: Client())
    with pytest.raises(SmsDeliveryError):
        await _aliyun_provider().send_code("13800138000", "123456")


@pytest.mark.asyncio
async def test_aliyun_ok_response_is_accepted(monkeypatch):
    captured: dict[str, object] = {}

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"Code": "OK", "RequestId": "req-1"}

    class Client:
        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, *_args: object, **kwargs: object) -> Response:
            captured.update(kwargs)
            return Response()

    monkeypatch.setattr(sms.httpx, "AsyncClient", lambda **_kwargs: Client())
    await _aliyun_provider().send_code("13800138000", "123456")
    assert "TemplateParam" in str(captured["content"])
    assert "123456" in str(captured["content"])
