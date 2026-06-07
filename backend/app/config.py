"""应用配置：从环境变量 / .env 读取。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "").strip()
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
    db_path: str = os.getenv("DB_PATH", "caishen.db")
    llm_timeout: float = float(os.getenv("LLM_TIMEOUT", "20"))

    @property
    def llm_enabled(self) -> bool:
        """是否配置了可用的 LLM key。"""
        return bool(self.deepseek_api_key)


settings = Settings()
