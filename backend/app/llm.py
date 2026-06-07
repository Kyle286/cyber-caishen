"""DeepSeek LLM 客户端封装（OpenAI 兼容 /chat/completions）。

任何异常（无 key、超时、网络错误、非 200）都返回 None，由上层触发本地回退。
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from .config import settings

logger = logging.getLogger("caishen.llm")


def chat(system: str, user: str, temperature: float = 0.9) -> Optional[str]:
    """调用 DeepSeek 生成文案。失败返回 None。"""
    if not settings.llm_enabled:
        logger.info("未配置 DEEPSEEK_API_KEY，使用本地回退。")
        return None

    url = f"{settings.deepseek_base_url}/chat/completions"
    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        # 留足额度：若配置的是推理模型（如 deepseek-v4-pro），会先消耗 reasoning
        # tokens，额度过小会导致正文为空而触发回退。普通对话模型用不满，无副作用。
        "max_tokens": 2000,
    }
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=settings.llm_timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            return content or None
    except Exception as exc:  # noqa: BLE001 — 任何异常都回退
        logger.warning("DeepSeek 调用失败，回退本地模板：%s", exc)
        return None
