from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .models import current_millis
from .prompts_world import WorldPrompts
from .store import WorldStore


class FactEnricher:
    def __init__(
        self,
        store: WorldStore,
        *,
        output_dir: str,
        llm: Callable[[str], str] | None = None,
        image_generator: Callable[[str, str, str], str | None] | None = None,
        language: str = "zh-CN",
    ):
        self.store = store
        self.output_dir = Path(output_dir)
        self.llm = llm or (lambda prompt: "")
        self.image_generator = image_generator or self._default_image_generator
        self.language = language

    def build_description_prompt(self, fact: dict[str, Any]) -> str:
        return WorldPrompts.fact_description_prompt(fact, language=self.language)

    def build_image_prompt(self, fact: dict[str, Any], metadata: dict[str, Any]) -> dict[str, str]:
        return WorldPrompts.fact_image_prompt(fact, metadata, language=self.language)

    def enrich_fact(self, fact_id: int, *, now: int | None = None) -> dict[str, Any]:
        now = now if now is not None else current_millis()
        try:
            fact = self.store.get_fact(fact_id)
        except KeyError:
            return {"error": "事实不存在"}

        metadata = dict(fact.get("metadata") or {})
        metadata["enriching"] = True
        self._update_fact_metadata(fact_id, metadata, now)

        ai_description = metadata.get("aiDescription")
        if not ai_description:
            ai_description = self.llm(self.build_description_prompt(fact)).strip().strip("\"'")

        image_url = None
        image_input = self.build_image_prompt(fact, metadata)
        try:
            image_url = self.image_generator(
                image_input["category"], image_input["prompt"], str(self.output_dir)
            )
        except Exception:
            image_url = None

        if ai_description:
            metadata["aiDescription"] = ai_description
            i18n = metadata.get("i18n") if isinstance(metadata.get("i18n"), dict) else {}
            description = (
                i18n.get("description") if isinstance(i18n.get("description"), dict) else {}
            )
            description.setdefault(self.language, ai_description)
            i18n["description"] = description
            metadata["i18n"] = i18n

        if image_url and _is_image_path(image_url):
            images = metadata.get("images") if isinstance(metadata.get("images"), list) else []
            old_image = metadata.get("imageUrl")
            if _is_image_path(old_image) and old_image not in images:
                images.append(old_image)
            if image_url not in images:
                images.append(image_url)
            metadata["images"] = images
            metadata["imageUrl"] = image_url

        metadata["enrichedAt"] = now
        metadata.pop("enriching", None)
        self._update_fact_metadata(fact_id, metadata, now)
        self.store.add_fact_event(
            fact_id,
            "note",
            f"资产丰富化完成{'（含图片）' if image_url else '（仅文字）'}",
            created_at=now,
            metadata={"source": "fact-enrich"},
        )
        return {"imageUrl": image_url, "aiDescription": ai_description}

    def _update_fact_metadata(self, fact_id: int, metadata: dict[str, Any], now: int) -> None:
        if hasattr(self.store, "update_fact_metadata"):
            self.store.update_fact_metadata(fact_id, metadata, now)
            return
        import json

        self.store.conn.execute(
            "UPDATE world_facts SET metadata_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(metadata, ensure_ascii=False), now, fact_id),
        )
        self.store.conn.commit()

    def _default_image_generator(self, category: str, prompt: str, output_dir: str) -> str:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        path = output / f"{category}-fact.txt"
        path.write_text(prompt, "utf-8")
        return str(path)


def _is_image_path(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return value.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
