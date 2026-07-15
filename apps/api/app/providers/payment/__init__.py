"""支付 Provider。

- mock：不接真支付。下单后由 order service 起一个后台任务几秒后自动「支付成功」，
        用于本地跑通「下单 → 支付 → 履约（发放供灯权益/记功德）」完整闭环。
- wechat / alipay：真支付。需营业执照申请到的商户号，个人拿不到。
        这里给出接口与验签骨架，接线时补密钥即可。

金额单位统一「分」。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger("tianji.payment")


@dataclass
class PaymentNotify:
    out_trade_no: str
    transaction_id: str
    paid: bool


class PaymentProvider(Protocol):
    name: str
    # mock 为 True：下单即安排自动成功，前端轮询订单状态即可
    auto_confirm: bool

    async def create_payment(
        self, out_trade_no: str, amount_fen: int, subject: str
    ) -> dict | None:
        """返回前端拉起支付所需参数；mock 返回 None。"""
        ...

    async def parse_notify(self, headers: dict, raw_body: bytes) -> PaymentNotify:
        """解析并验签支付平台回调。验签失败必须抛异常。"""
        ...


class MockPayment:
    name = "mock"
    auto_confirm = True

    async def create_payment(
        self, out_trade_no: str, amount_fen: int, subject: str
    ) -> dict | None:
        logger.info("[mock-pay] 下单 %s ¥%.2f（%s），3 秒后自动成功", out_trade_no, amount_fen / 100, subject)
        return None

    async def parse_notify(self, headers: dict, raw_body: bytes) -> PaymentNotify:
        # mock 不走真实回调；保留以满足接口
        raise NotImplementedError("mock 支付无外部回调")


class WechatPayment:
    name = "wechat"
    auto_confirm = False

    def __init__(self) -> None:
        if not (settings.wechat_app_id and settings.wechat_mch_id and settings.wechat_api_v3_key):
            raise RuntimeError("PAYMENT_PROVIDER=wechat 但微信支付配置不完整")

    async def create_payment(  # pragma: no cover - 需真商户号
        self, out_trade_no: str, amount_fen: int, subject: str
    ) -> dict | None:
        # TODO: 微信支付 V3 下单（JSAPI/H5）。返回 { prepay_id / h5_url / jsapi 签名参数 }
        raise NotImplementedError("微信支付需接入商户号后启用")

    async def parse_notify(self, headers: dict, raw_body: bytes) -> PaymentNotify:  # pragma: no cover
        # TODO: 用 API v3 证书验签，AES-GCM 解密 resource，取 out_trade_no / transaction_id / trade_state
        raise NotImplementedError("微信支付回调验签需接入后启用")


class AlipayPayment:
    name = "alipay"
    auto_confirm = False

    def __init__(self) -> None:
        if not (settings.alipay_app_id and settings.alipay_private_key and settings.alipay_public_key):
            raise RuntimeError("PAYMENT_PROVIDER=alipay 但支付宝配置不完整")

    async def create_payment(  # pragma: no cover
        self, out_trade_no: str, amount_fen: int, subject: str
    ) -> dict | None:
        # TODO: alipay.trade.wap.pay / page.pay，返回可跳转的下单表单 URL
        raise NotImplementedError("支付宝需接入后启用")

    async def parse_notify(self, headers: dict, raw_body: bytes) -> PaymentNotify:  # pragma: no cover
        # TODO: RSA2 验签 form 表单，取 out_trade_no / trade_no / trade_status
        raise NotImplementedError("支付宝回调验签需接入后启用")


_instance: PaymentProvider | None = None


def get_payment() -> PaymentProvider:
    global _instance
    if _instance is None:
        if settings.payment_provider == "wechat":
            _instance = WechatPayment()
        elif settings.payment_provider == "alipay":
            _instance = AlipayPayment()
        else:
            _instance = MockPayment()
    return _instance
