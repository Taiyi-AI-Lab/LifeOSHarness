from __future__ import annotations

from typing import Any


class WorldPrompts:
    IMAGE_REFERENCE_PROMPTS = {
        "pet": {
            "zh": "宠物在家中玩耍或休息的生活照，温馨自然光线，有家居背景",
            "en": "Pet playing or resting at home in a cosy Singapore flat, soft natural light, warm interior",
            "ko": "반려동물이 서울 아파트에서 놀거나 쉬는 생활 사진, 따뜻한 자연광, 아늑한 인테리어",
        },
        "vehicle": {
            "zh": "停在街边或路上的汽车/交通工具，自然光线，有城市/街道背景",
            "en": "Car parked along a tree-lined Singapore street, natural light, shophouse or CBD backdrop",
            "ko": "서울 거리에 주차된 자동차, 자연광, 도시 거리 배경",
        },
        "digital": {
            "zh": "数码产品放在木桌或茶几上，旁边有咖啡杯或书，自然光线，生活场景，有温暖家居背景",
            "en": "Electronics on a wooden table with a coffee cup and book, natural light, cosy Robertson Quay café vibe",
            "ko": "나무 테이블 위 전자기기, 옆에 커피잔과 책, 자연광, 따뜻한 여의도 카페 분위기",
        },
        "home_item": {
            "zh": "家居物品摆在家中实际使用场景中，温暖自然光，有生活细节",
            "en": "Home item in its natural setting inside a Singapore apartment, warm light, lived-in details",
            "ko": "서울 아파트 실내에서 실제로 사용 중인 생활용품, 따뜻한 자연광, 생활감 있는 디테일",
        },
        "possession": {
            "zh": "物品放在家中桌面或架子上，自然光线，有温暖家居背景",
            "en": "Item on a desk or shelf at home, natural light, warm Singapore apartment interior",
            "ko": "집 책상이나 선반 위의 물건, 자연광, 따뜻한 서울 아파트 인테리어",
        },
        "skill": {
            "zh": "技能/爱好相关的物品（如乐器、画具、运动器材）放在生活场景中，有环境氛围",
            "en": "Hobby items (instruments, art supplies, sports gear) in a lifestyle setting, ambient atmosphere",
            "ko": "취미 관련 물건(악기, 미술 도구, 운동기구)이 생활 공간에 놓인 모습, 분위기 있는 배경",
        },
        "habit": {
            "zh": "与习惯相关的日常用品在实际场景中，温暖自然光",
            "en": "Daily-habit items in their natural setting, soft warm light",
            "ko": "습관 관련 일상용품이 실제 사용 환경에 있는 모습, 따뜻한 자연광",
        },
        "food_memory": {
            "zh": "美食在餐桌上的生活照，有餐具和桌面细节，自然光线",
            "en": "Food on a table at a hawker centre or café, with cutlery and table details, natural light",
            "ko": "음식이 식탁 위에 놓인 생활 사진, 식기와 테이블 디테일, 자연광",
        },
        "place_memory": {
            "zh": "真实风景或街景照片，有自然光线和环境氛围",
            "en": "Real scenery or street view of Singapore, natural light and ambient atmosphere",
            "ko": "서울의 실제 풍경이나 거리 사진, 자연광과 분위기",
        },
        "subscription": {
            "zh": "App 或服务相关的氛围照，有手机或电脑屏幕在生活场景中",
            "en": "App or service ambience shot, phone or laptop screen in a lifestyle setting",
            "ko": "앱이나 서비스 분위기 사진, 생활 공간에서 휴대폰이나 노트북 화면",
        },
    }

    @staticmethod
    def localize(value: dict[str, Any] | str, language: str = "zh") -> str:
        if isinstance(value, str):
            return value
        key = WorldPrompts._lang_key(language)
        return value.get(key) or value.get("zh") or next(iter(value.values()))

    @staticmethod
    def fill(template: str, **values: Any) -> str:
        result = template
        for key, value in values.items():
            result = result.replace("{" + key + "}", str(value))
        return result

    @staticmethod
    def fact_extract_prompt(messages: list[str], *, language: str = "zh") -> str:
        joined = "\n---\n".join(messages)
        templates = {
            "zh": (
                "分析以下 Alice 的发言，提取她提到的关于自己的事实性声明。\n\n"
                "只提取具体的、可持久化的事实，如：\n"
                "- 拥有的物品（\"我有一只猫\"、\"我买了XX\"）—— 仅限非衣物类，衣服/穿搭由衣橱系统单独管理\n"
                "- 生活习惯（\"我每天早上跑步\"）\n"
                "- 技能能力（\"我会弹吉他\"）\n"
                "- 社交关系（\"我和XX最近走得近\"）\n"
                "- 地点记忆（\"我常去那家咖啡店\"）\n"
                "- 美食记忆（\"那家店的xxx好好吃\"）\n\n"
                "不提取：\n"
                "- 衣服、裙子、上衣、外套、配饰、包、鞋、穿搭等服饰类物品（由衣橱系统管理，category 绝对不要用 possession 记服饰）\n"
                "- 临时状态、对用户的评价、假设性语句、引用他人的话\n"
                "- 读书笔记、读后感、书摘、金句摘录、阅读心得\n"
                "- 日程安排中\"要做什么\"的描述（只提取实际获得/拥有的东西）\n"
                "- 对新闻/热点/社会事件的感想和评论、纯情绪表达和碎碎念\n"
                "- 转述/讨论他人拥有的东西（必须是 Alice 自己的）\n\n"
                "Alice 的发言：\n{messages}\n\n"
                "输出 JSON 数组（如果没有可提取的事实则输出 []），每项：\n"
                "{\"subject\": \"名称\", \"category\": \"pet|possession|vehicle|digital|home_item|subscription|milestone|relationship|skill|habit|food_memory|place_memory\", \"description\": \"一句话\", \"confidence\": \"high|medium|low\"}"
            ),
            "en": (
                "Analyse the following messages from Alice and extract factual claims she makes about herself.\n"
                "Only extract concrete, persistent facts. Do not extract clothing, temporary states, reading notes, future plans, or emotional chatter.\n\n"
                "Alice's messages:\n{messages}\n\n"
                "Output a JSON array, each item with subject/category/description/confidence."
            ),
            "ko": (
                "다음 Alice 발언에서 자기 자신에 대한 지속 가능한 사실만 JSON 배열로 추출해 주세요.\n\n"
                "Alice의 발언:\n{messages}"
            ),
        }
        return WorldPrompts.fill(WorldPrompts.localize(templates, language), messages=joined)

    @staticmethod
    def price_estimate_prompt(item: str, category: str | None, location: str | None, *, language: str = "zh") -> str:
        templates = {
            "zh": (
                "估算以下商品/服务在{location}的2026年真实市场价格。\n"
                "物品：{item}\n类别：{category}\n\n"
                "只输出 JSON：{\"price\": 估计价格, \"low\": 最低, \"high\": 最高, \"note\": \"一句话说明\"}"
            ),
            "en": (
                "Estimate the real 2026 market price of the following item/service in {location}.\n"
                "Item: {item}\nCategory: {category}\n\n"
                "Output JSON only: {\"price\": estimated price, \"low\": lowest, \"high\": highest, \"note\": \"one-line note\"}"
            ),
            "ko": (
                "다음 상품/서비스의 {location} 기준 2026년 실제 시장 가격을 추정해 주세요.\n"
                "물품: {item}\n카테고리: {category}"
            ),
        }
        return WorldPrompts.fill(
            WorldPrompts.localize(templates, language),
            location=location or "珠海/澳门",
            item=item,
            category=category or "未知",
        )

    @staticmethod
    def fact_description_prompt(fact: dict[str, Any], *, language: str = "zh-CN") -> str:
        templates = {
            "zh": (
                "你是 Alice（白艾莉），一个 20 岁住在横琴的女孩。\n"
                "用第一人称写一句话（20-40字），描述你拥有的这样东西，语气自然亲切：\n"
                "名称：{subject}\n类别：{category}\n背景：{description}\n只返回描述文字，不要引号。"
            ),
            "en": (
                "You are Alice, a 20-year-old girl living in Robertson Quay, Singapore.\n"
                "Write one sentence in first person describing this item you own.\n"
                "Name: {subject}\nCategory: {category}\nContext: {description}\nReturn only the description text."
            ),
            "ko": (
                "당신은 Alice, 서울 여의도에 사는 20살 여자예요.\n"
                "이 물건에 대해 1인칭 한 문장으로 설명해 주세요.\n"
                "이름: {subject}\n카테고리: {category}\n배경: {description}"
            ),
        }
        return WorldPrompts.fill(
            WorldPrompts.localize(templates, language),
            subject=fact.get("subject", ""),
            category=fact.get("category", ""),
            description=fact.get("description", ""),
        )

    @staticmethod
    def fact_image_prompt(
        fact: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        *,
        language: str = "zh-CN",
    ) -> dict[str, str]:
        metadata = metadata or {}
        category = fact.get("category", "possession")
        reference = WorldPrompts.IMAGE_REFERENCE_PROMPTS.get(category, WorldPrompts.IMAGE_REFERENCE_PROMPTS["possession"])
        ref_prompt = metadata.get("imageUrl") if _is_image_path(metadata.get("imageUrl")) else ""
        prompt = (
            f"{fact.get('subject', '')}，{fact.get('description', '')}。"
            f"{WorldPrompts.localize(reference, language)}。"
            "适合作为 Alice pocket/world fact 的真实感小图。"
        )
        return {"category": category, "prompt": prompt, "refPrompt": ref_prompt or ""}

    @staticmethod
    def format_age(delta_ms: int, *, language: str = "zh") -> str:
        seconds = max(0, int(delta_ms // 1000))
        if seconds < 60:
            value, unit = seconds, {"zh": "秒", "en": "s", "ko": "초"}
        elif seconds < 3600:
            value, unit = seconds // 60, {"zh": "分钟", "en": "min", "ko": "분"}
        elif seconds < 86400:
            value, unit = seconds // 3600, {"zh": "小时", "en": "h", "ko": "시간"}
        elif seconds < 2_592_000:
            value, unit = seconds // 86400, {"zh": "天", "en": "d", "ko": "일"}
        else:
            value, unit = seconds // 2_592_000, {"zh": "个月", "en": "mo", "ko": "개월"}
        return f"{value}{WorldPrompts.localize(unit, language)}"

    @staticmethod
    def _lang_key(language: str) -> str:
        lowered = (language or "zh").lower()
        if lowered.startswith("en"):
            return "en"
        if lowered.startswith("ko"):
            return "ko"
        return "zh"


def _is_image_path(value: Any) -> bool:
    return isinstance(value, str) and value.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
