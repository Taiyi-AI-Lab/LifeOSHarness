from __future__ import annotations

import json

import httpx

from lifeostomanyagent.server.engine.intent_classifier import (
    DeepSeekIntentClassifier,
    classify_intent,
    classify_intent_rules,
)


def test_rules_classify_clear_chitchat():
    result = classify_intent_rules("Alice，今天有点累，陪我聊聊")

    assert result.resolved_intent == "chitchat"
    assert result.classifier == "rules"
    assert result.confidence > 0
    assert "闲聊" in result.reason or "陪伴" in result.reason


def test_rules_classify_clear_task():
    result = classify_intent_rules("帮我修一下 pytest 报错，然后提交 PR")

    assert result.resolved_intent == "task"
    assert result.classifier == "rules"
    assert result.confidence > 0
    assert "任务" in result.reason


def test_rules_prefer_task_for_mixed_message():
    result = classify_intent_rules("我今天有点累，顺便帮我改一下测试")

    assert result.resolved_intent == "task"


def test_rules_classify_memory_chitchat():
    result = classify_intent_rules("昨天我们聊了阿嬷的信，还有木生怎么在现代生活。")

    assert result.resolved_intent == "chitchat"


def test_rules_default_unknown_to_task():
    result = classify_intent_rules("蓝色玻璃")

    assert result.resolved_intent == "task"
    assert "默认" in result.reason


def test_explicit_intent_overrides_classifier():
    result = classify_intent("帮我修 bug", requested_intent="chitchat")

    assert result.resolved_intent == "chitchat"
    assert result.classifier == "explicit"


def test_deepseek_intent_classifier_sends_requested_shape():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "intent": "chitchat",
                                    "confidence": 0.93,
                                    "reason": "用户在表达疲惫并请求陪伴。",
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)
    classifier = DeepSeekIntentClassifier(api_key="test-key", client=client)

    result = classifier.classify("今天好累，陪我说会儿话")

    assert result is not None
    assert result.resolved_intent == "chitchat"
    assert result.classifier == "llm"
    assert result.confidence == 0.93
    assert len(requests) == 1
    request = requests[0]
    assert request.url == "https://api.deepseek.com/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-key"
    body = json.loads(request.content)
    assert body["model"] == "deepseek-chat"
    assert body["stream"] is False
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["role"] == "user"


def test_deepseek_intent_classifier_returns_none_for_invalid_json():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"choices": [{"message": {"content": "not json"}}]}
            )
        ),
        trust_env=False,
    )
    classifier = DeepSeekIntentClassifier(api_key="test-key", client=client)

    assert classifier.classify("今天有点累") is None


def test_deepseek_intent_classifier_returns_none_for_low_confidence():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "intent": "chitchat",
                                        "confidence": 0.4,
                                        "reason": "不确定",
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
            )
        ),
        trust_env=False,
    )
    classifier = DeepSeekIntentClassifier(api_key="test-key", client=client)

    assert classifier.classify("今天有点累") is None
