from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal

import httpx

InteractionIntent = Literal["chitchat", "task"]
RequestedInteractionIntent = Literal["auto", "chitchat", "task"]

TASK_PATTERNS: tuple[str, ...] = (
    r"\b(pytest|ruff|mypy|git|pr|pull request|commit|branch|diff|stack trace|traceback)\b",
    r"\b(bug|fix|debug|implement|refactor|test|lint|build|deploy|api|sdk|cli)\b",
    r"[\w./-]+\.(py|ts|tsx|js|jsx|md|json|toml|yaml|yml|sql|sh|html|css)\b",
    r"(帮我|请你|麻烦).{0,12}(做|运行|安装|创建|修改|生成|写|查|搜索|分析|总结|翻译|导出|实现|修|提交)",
    r"(运行|安装|创建|修改|生成|写一个|写一份|查一下|搜索|分析|总结|翻译|导出|实现|重构|修复|提交)",
    r"(代码|报错|测试|接口|文件|文档|脚本|报告|图片|表格|邮件|计划|方案|PRD|网页|浏览器|命令)",
)

CHITCHAT_PATTERNS: tuple[str, ...] = (
    r"^(hi|hello|hey|你好|嗨|早|早安|晚安|在吗|在不在|哈喽)[呀啊～~！!。\s]*$",
    r"(陪我|陪陪我|聊聊|说会儿话|随便聊|想聊)",
    r"(有点累|好累|难过|睡不着|焦虑|烦|崩溃|开心|想你|孤独|委屈|emo)",
    r"(chenyuan|你).{0,8}(在吗|心情|今天怎么样|想我|记得我|梦见|昨晚梦)",
    r"(昨晚梦见什么|做梦了吗|还记得我吗|你还记得)",
    r"(我们聊了|之前聊过|上次聊过|之前说过|上次说过)",
    r"(刚下班|今天发生|突然想|跟你说句话|近况)",
)


@dataclass(frozen=True)
class IntentClassification:
    resolved_intent: InteractionIntent
    classifier: str
    confidence: float
    reason: str


def classify_intent_rules(user_message: str) -> IntentClassification:
    text = _normalize(user_message)
    if not text:
        return IntentClassification("task", "rules", 0.6, "空输入按任务处理，避免误注入 LifeOS。")

    if _matches_any(TASK_PATTERNS, text):
        return IntentClassification("task", "rules", 0.9, "命中明确任务信号。")

    if _matches_any(CHITCHAT_PATTERNS, text):
        return IntentClassification("chitchat", "rules", 0.85, "命中闲聊/陪伴信号。")

    return IntentClassification("task", "rules", 0.55, "未命中明确闲聊信号，默认按任务处理。")


def classify_intent(
    user_message: str,
    *,
    requested_intent: RequestedInteractionIntent = "auto",
    llm_classifier: DeepSeekIntentClassifier | None = None,
) -> IntentClassification:
    if requested_intent in ("chitchat", "task"):
        return IntentClassification(
            requested_intent,
            "explicit",
            1.0,
            f"请求显式指定 interaction_intent={requested_intent}。",
        )

    if llm_classifier:
        llm_result = llm_classifier.classify(user_message)
        if llm_result:
            return llm_result

    return classify_intent_rules(user_message)


class DeepSeekIntentClassifier:
    """Classifies whether LifeOS companionship context should be injected."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        timeout_seconds: float = 3.0,
        min_confidence: float = 0.6,
        client: httpx.Client | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.min_confidence = min_confidence
        self._client = client

    def classify(self, user_message: str) -> IntentClassification | None:
        if not self.api_key.strip():
            return None
        request_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": self._user_prompt(user_message)},
            ],
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
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
            return None
        finally:
            if should_close:
                client.close()

    def _system_prompt(self) -> str:
        return (
            "你是 LifeOS 的意图分类器，只判断是否应该注入 LifeOS 陪伴/人格上下文。"
            "不要回答用户问题，不要执行任务。任务、工具调用、代码、文件、搜索、总结、"
            "翻译、分析、生成产物都分类为 task。只有明确日常闲聊、情绪陪伴、关系互动、"
            "陈远/LifeOS 人格互动、梦境或记忆闲谈才分类为 chitchat。"
            "冲突时输出 task。只输出严格 JSON。"
        )

    def _user_prompt(self, user_message: str) -> str:
        return (
            "请分类下面这条用户消息是否应该注入 LifeOS 陪伴上下文。\n\n"
            f"用户消息：{user_message}\n\n"
            '输出 JSON：{"intent":"chitchat|task","confidence":0到1,"reason":"短原因"}'
        )

    def _parse_result(self, content: str) -> IntentClassification | None:
        text = _strip_json_fence(content)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        intent = str(data.get("intent") or "").strip()
        if intent not in ("chitchat", "task"):
            return None
        try:
            confidence = float(data.get("confidence"))
        except (TypeError, ValueError):
            return None
        if confidence < self.min_confidence:
            return None
        reason = str(data.get("reason") or "").strip()[:120]
        return IntentClassification(intent, "llm", min(confidence, 1.0), reason or "LLM 分类结果。")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _matches_any(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _strip_json_fence(content: str) -> str:
    text = (content or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
        text = text.rsplit("\n", 1)[0].strip()
    return text
