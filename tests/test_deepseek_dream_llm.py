from __future__ import annotations

import json

import httpx

from lifeostomanyagent.server.engine.dream_llm import DeepSeekDreamLLM


def test_deepseek_dream_llm_sends_requested_chat_completion_shape():
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
                                    "title": "雨里的旧信",
                                    "emotional_tone": "怀旧",
                                    "fragments": ["梦里有旧信和雨声。"],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)
    generator = DeepSeekDreamLLM(api_key="test-key", client=client)

    result = generator(
        {
            "dream_date": "2026-06-02",
            "timezone": "Asia/Shanghai",
            "triggers": ["昨天聊到阿嬷的信。"],
            "fallback_title": "没寄出的信",
            "fallback_emotional_tone": "怀旧",
        }
    )

    assert result == {
        "title": "雨里的旧信",
        "emotional_tone": "怀旧",
        "fragments": ["梦里有旧信和雨声。"],
    }
    assert len(requests) == 1
    request = requests[0]
    assert request.url == "https://api.deepseek.com/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-key"
    body = json.loads(request.content)
    assert body["model"] == "deepseek-v4-pro"
    assert body["thinking"] == {"type": "enabled"}
    assert body["reasoning_effort"] == "high"
    assert body["stream"] is False
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["role"] == "user"


def test_deepseek_dream_llm_returns_none_for_invalid_json():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})
        ),
        trust_env=False,
    )
    generator = DeepSeekDreamLLM(api_key="test-key", client=client)

    assert generator({"dream_date": "2026-06-02", "triggers": ["x"]}) is None
