"""DeepSeek LLM 客户端封装（OpenAI 兼容 /chat/completions）。

任何异常（无 key、超时、网络错误、非 200）都返回 None / 静默，由上层触发本地回退。
支持：非流式 chat、流式 chat_stream、以及规则不确定时的 LLM 槽位抽取 extract_slots。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Iterator, Optional

import httpx

from .config import settings
from .models import ChatTurn

logger = logging.getLogger("caishen.llm")

# 多轮历史最多带入的条数，避免上下文膨胀
_MAX_HISTORY = 6


def _build_messages(system: str, user: str, history: Optional[list[ChatTurn]]) -> list[dict]:
    messages = [{"role": "system", "content": system}]
    for turn in (history or [])[-_MAX_HISTORY:]:
        messages.append({"role": "assistant" if turn.sender == "agent" else "user", "content": turn.text})
    messages.append({"role": "user", "content": user})
    return messages


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }


def chat(
    system: str,
    user: str,
    history: Optional[list[ChatTurn]] = None,
    temperature: float = 0.9,
    model: Optional[str] = None,
) -> Optional[str]:
    """调用 DeepSeek 生成文案（非流式）。失败返回 None。"""
    if not settings.llm_enabled:
        return None
    payload = {
        "model": settings.resolve_model(model),
        "messages": _build_messages(system, user, history),
        "temperature": temperature,
        # 留足额度：推理模型会先消耗 reasoning tokens，额度过小会导致正文为空
        "max_tokens": 2000,
    }
    try:
        with httpx.Client(timeout=settings.llm_timeout) as client:
            resp = client.post(f"{settings.deepseek_base_url}/chat/completions", json=payload, headers=_headers())
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            return content or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("DeepSeek 调用失败，回退本地模板：%s", exc)
        return None


def chat_stream(
    system: str,
    user: str,
    history: Optional[list[ChatTurn]] = None,
    temperature: float = 0.9,
    model: Optional[str] = None,
) -> Iterator[str]:
    """流式生成，逐段 yield 文本增量。无 key / 出错时不产出任何内容（上层回退）。"""
    if not settings.llm_enabled:
        return
    payload = {
        "model": settings.resolve_model(model),
        "messages": _build_messages(system, user, history),
        "temperature": temperature,
        "max_tokens": 2000,
        "stream": True,
    }
    try:
        with httpx.Client(timeout=settings.llm_timeout) as client:
            with client.stream("POST", f"{settings.deepseek_base_url}/chat/completions", json=payload, headers=_headers()) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        delta = json.loads(data)["choices"][0]["delta"]
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
                    # 只取正文增量，忽略推理过程 reasoning_content
                    piece = delta.get("content")
                    if piece:
                        yield piece
    except Exception as exc:  # noqa: BLE001
        logger.warning("DeepSeek 流式调用失败，回退本地模板：%s", exc)
        return


_SLOT_SYSTEM = """你是消费意图槽位抽取器。从用户中文消息中抽取结构化信息，严格只输出 JSON：
{"intent": "purchase|set_goal|query_progress|resist|chitchat", "item": "商品名或null", "price": 数字或null}
说明：purchase=想买东西/询价；set_goal=想攒钱设目标；query_progress=问攒钱进度；resist=表示不买/想克制；chitchat=其他闲聊。
item 为简短商品名（如"手表""绿植"），price 为人民币数字。只输出 JSON，不要解释。"""


def extract_slots(message: str, model: Optional[str] = None) -> Optional[dict]:
    """规则不确定时，用 LLM 抽取意图槽位。返回 dict 或 None。"""
    if not settings.llm_enabled:
        return None
    raw = chat(_SLOT_SYSTEM, f"用户消息：{message}", temperature=0.0, model=model)
    if not raw:
        return None
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "intent" not in data:
        return None
    return data
