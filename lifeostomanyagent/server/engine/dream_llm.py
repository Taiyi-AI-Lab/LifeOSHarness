from __future__ import annotations

import json
from typing import Any

import httpx


class DeepSeekDreamLLM:
    """Generates a symbolic dream from collected LifeOS dream seeds."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "deepseek-v4-pro",
        base_url: str = "https://api.deepseek.com",
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._client = client

    def __call__(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not self.api_key.strip():
            return None
        request_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": self._user_prompt(payload)},
            ],
            "thinking": {"type": "enabled"},
            "reasoning_effort": "high",
            "stream": False,
        }
        client = self._client or httpx.Client(timeout=self.timeout_seconds, trust_env=False)
        should_close = self._client is None
        try:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json=request_body,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return self._parse_result(content)
        finally:
            if should_close:
                client.close()

    def _system_prompt(self) -> str:
        return (
            "你是 LifeOS 的梦境生成器。你的任务是根据一个现代人物昨天的事件种子，"
            "写出一段自然、克制、有象征感的昨夜梦境。梦境只能是情绪整理、记忆残片"
            "和隐喻，不能把梦写成现实事实，不能新增真实履历、真实关系、资产、地点或"
            "未提供的事件。不要自称 AI，不要解释生成过程。只输出 JSON。"
        )

    def _user_prompt(self, payload: dict[str, Any]) -> str:
        triggers = payload.get("triggers") or []
        trigger_lines = "\n".join(f"- {item}" for item in triggers[:8]) or "- 没有明确事件"
        return (
            "请根据以下信息生成昨夜梦境。\n\n"
            f"日期：{payload.get('dream_date')}\n"
            f"时区：{payload.get('timezone', 'Asia/Shanghai')}\n"
            f"规则版标题参考：{payload.get('fallback_title', '')}\n"
            f"规则版情绪参考：{payload.get('fallback_emotional_tone', '')}\n"
            "昨日触发线索：\n"
            f"{trigger_lines}\n\n"
            "输出必须是严格 JSON，字段如下：\n"
            "{\n"
            '  "title": "6 到 18 个中文字符的梦境标题",\n'
            '  "emotional_tone": "一个短词，例如 怀旧、疲惫、明亮、平静、温柔",\n'
            '  "fragments": ["2 到 4 句梦境片段，每句不超过 80 个中文字符"]\n'
            "}\n"
            "梦境要像真实醒来后能记住的片段，不要写成故事梗概。"
        )

    def _parse_result(self, content: str) -> dict[str, Any] | None:
        text = (content or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if "\n" in text:
                text = text.split("\n", 1)[1]
            text = text.rsplit("\n", 1)[0].strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        title = str(data.get("title") or "").strip()
        emotional_tone = str(data.get("emotional_tone") or "").strip()
        fragments = [str(item).strip() for item in data.get("fragments") or [] if str(item).strip()]
        if not title or not emotional_tone or not fragments:
            return None
        return {
            "title": title[:40],
            "emotional_tone": emotional_tone[:20],
            "fragments": fragments[:4],
        }
