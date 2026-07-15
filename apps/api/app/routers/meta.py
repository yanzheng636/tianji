"""静态配置 + 首页数据：殿、香、灯档位、免责声明、今日运势。"""

from __future__ import annotations

from fastapi import APIRouter

from app.constants import DISCLAIMER, HALLS, INCENSES, LAMP_PLAN_META
from app.services.bazi import today_fortune_seed

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/config")
async def config() -> dict:
    return {
        "halls": list(HALLS.values()),
        "incenses": list(INCENSES.values()),
        "lampPlans": list(LAMP_PLAN_META.values()),
        "disclaimer": DISCLAIMER,
    }


@router.get("/today")
async def today() -> dict:
    ganzhi, date_str = today_fortune_seed()
    # 今日运势百分比：按干支日 + 日期做稳定伪随机（同一天同一值），非纯 random
    seed = sum(ord(c) for c in ganzhi + date_str)
    luck = 60 + (seed * 7) % 40  # 60~99，当天稳定
    return {
        "ganzhi": ganzhi,
        "date": date_str,
        "luck": luck,
        "yi": ["摸鱼充电", "大胆开麦"],
        "ji": ["精神内耗"],
    }
