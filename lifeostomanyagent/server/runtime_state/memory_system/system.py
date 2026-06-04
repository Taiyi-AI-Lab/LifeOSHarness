from __future__ import annotations

import json
import math
import re
import shutil
import time
from pathlib import Path
from typing import Any

USER_MEMORY_TYPES = ["identity", "workflow", "voice", "instruction"]


def _now() -> int:
    return int(time.time() * 1000)


def _tokens(text: str) -> set[str]:
    chunks = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text.lower())
    return set(chunks)


def _similarity(a: str, b: str) -> float:
    left = _tokens(a)
    right = _tokens(b)
    if not left or not right:
        return 0.0
    return len(left & right) / math.sqrt(len(left) * len(right))


def _hashed_vector(text: str, dims: int = 64) -> list[float]:
    vector = [0.0] * dims
    for token in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text.lower()):
        vector[abs(hash(token)) % dims] += 1.0
    return vector


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


class UserMemorySystem:
    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.entries_path = self.storage_dir / "entries.json"
        self.backup_path = self.storage_dir / "entries.json.bak"
        self.snapshots_dir = self.storage_dir / "snapshots"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.entries: list[dict[str, Any]] = self._load_entries()

    def _load_entries(self) -> list[dict[str, Any]]:
        if not self.entries_path.exists():
            return []
        try:
            data = json.loads(self.entries_path.read_text("utf-8"))
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            shutil.copyfile(self.entries_path, self.backup_path)
            return []

    def _persist(self) -> None:
        tmp = self.entries_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.entries, ensure_ascii=False, indent=2), "utf-8")
        tmp.replace(self.entries_path)

    def list_entries(self, include_archived: bool = False) -> list[dict[str, Any]]:
        entries = self.entries if include_archived else [
            entry for entry in self.entries if entry.get("status") == "active"
        ]
        return [dict(entry) for entry in entries]

    def get_entry(self, entry_id: str, *, include_archived: bool = False) -> dict[str, Any] | None:
        for entry in self.entries:
            if entry.get("id") != entry_id:
                continue
            if not include_archived and entry.get("status") != "active":
                return None
            return dict(entry)
        return None

    def smart_add(
        self,
        memory_type: str,
        content: str,
        *,
        now: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = now if now is not None else _now()
        memory_type = memory_type if memory_type in USER_MEMORY_TYPES else "identity"
        clean = " ".join(content.split())
        for entry in self.entries:
            if entry.get("status") != "active" or entry.get("type") != memory_type:
                continue
            if entry.get("content") == clean or _similarity(entry.get("content", ""), clean) >= 0.92:
                entry["activationCount"] = int(entry.get("activationCount", 1)) + 1
                entry["updatedAt"] = now
                entry["lastActivatedAt"] = now
                entry.setdefault("metadata", {}).update(metadata or {})
                self._persist()
                return dict(entry)

        entry = {
            "id": f"mem_{now}_{len(self.entries) + 1}",
            "type": memory_type,
            "content": clean,
            "status": "active",
            "createdAt": now,
            "updatedAt": now,
            "lastActivatedAt": now,
            "activationCount": 1,
            "metadata": metadata or {},
        }
        self.entries.append(entry)
        self._persist()
        return dict(entry)

    def search(self, query: str, top_k: int = 5, memory_type: str | None = None) -> list[dict[str, Any]]:
        scored = []
        for entry in self.list_entries():
            if memory_type and entry["type"] != memory_type:
                continue
            score = _similarity(query, entry["content"])
            if score > 0:
                scored.append({**entry, "score": score})
        scored.sort(key=lambda item: (item["score"], item["activationCount"]), reverse=True)
        return scored[:top_k]

    def vector_search(
        self, query: str, top_k: int = 5, memory_type: str | None = None
    ) -> list[dict[str, Any]]:
        query_vector = _hashed_vector(query)
        scored = []
        for entry in self.list_entries():
            if memory_type and entry["type"] != memory_type:
                continue
            score = _cosine(query_vector, _hashed_vector(entry["content"]))
            if score > 0:
                scored.append({**entry, "score": score, "vectorScore": score})
        scored.sort(key=lambda item: (item["score"], item["activationCount"]), reverse=True)
        return scored[:top_k]

    def archive(self, entry_id: str) -> bool:
        for entry in self.entries:
            if entry["id"] == entry_id:
                entry["status"] = "archived"
                entry["updatedAt"] = _now()
                self._persist()
                return True
        return False

    def delete_by_id(self, entry_id: str) -> bool:
        before = len(self.entries)
        self.entries = [entry for entry in self.entries if entry["id"] != entry_id]
        changed = len(self.entries) != before
        if changed:
            self._persist()
        return changed

    def edit_entry(
        self,
        entry_id: str,
        *,
        content: str | None = None,
        memory_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        now: int | None = None,
    ) -> dict[str, Any] | None:
        now = now if now is not None else _now()
        for entry in self.entries:
            if entry.get("id") != entry_id:
                continue
            if content is not None:
                entry["content"] = " ".join(content.split())
            if memory_type is not None:
                entry["type"] = memory_type if memory_type in USER_MEMORY_TYPES else "identity"
            if metadata:
                entry.setdefault("metadata", {}).update(metadata)
            entry["updatedAt"] = now
            self._persist()
            return dict(entry)
        return None

    def rebuild(self, *, now: int | None = None) -> dict[str, Any]:
        now = now if now is not None else _now()
        seen: set[tuple[str, str]] = set()
        rebuilt: list[dict[str, Any]] = []
        archived = 0
        merged = 0
        for entry in sorted(self.entries, key=lambda item: item.get("updatedAt", 0), reverse=True):
            clean = " ".join(str(entry.get("content", "")).split())
            memory_type = entry.get("type") if entry.get("type") in USER_MEMORY_TYPES else "identity"
            if not clean:
                archived += 1
                continue
            key = (memory_type, clean.lower())
            if key in seen:
                merged += 1
                continue
            seen.add(key)
            rebuilt.append(
                {
                    **entry,
                    "type": memory_type,
                    "content": clean,
                    "status": entry.get("status") or "active",
                    "updatedAt": entry.get("updatedAt") or now,
                    "activationCount": int(entry.get("activationCount", 1) or 1),
                    "metadata": entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {},
                }
            )
        rebuilt.sort(key=lambda item: item.get("createdAt", 0))
        before = len(self.entries)
        self.entries = rebuilt
        self._persist()
        return {"before": before, "after": len(rebuilt), "archived": archived, "merged": merged}

    def dedup(self, *, now: int | None = None) -> int:
        now = now if now is not None else _now()
        seen: set[str] = set()
        archived = 0
        for entry in self.entries:
            if entry.get("status") != "active":
                continue
            key = str(entry.get("content", "")).strip()
            if key in seen:
                entry["status"] = "archived"
                entry["updatedAt"] = now
                archived += 1
            else:
                seen.add(key)
        if archived:
            self._persist()
        return archived

    def clear_all(self) -> int:
        count = len(self.entries)
        if count and self.entries_path.exists():
            shutil.copyfile(self.entries_path, self.backup_path)
        self.entries = []
        self._persist()
        return count

    def save_snapshot(self, label: str = "snapshot", *, now: int | None = None) -> dict[str, Any]:
        now = now if now is not None else _now()
        safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "-", label).strip("-") or "snapshot"
        path = self.snapshots_dir / f"{now}-{safe_label}.json"
        path.write_text(json.dumps(self.entries, ensure_ascii=False, indent=2), "utf-8")
        return {"label": label, "path": str(path), "createdAt": now, "count": len(self.entries)}

    def restore_snapshot(self, path: str) -> int:
        data = json.loads(Path(path).read_text("utf-8"))
        if not isinstance(data, list):
            raise ValueError("snapshot must contain a list")
        self.entries = data
        self._persist()
        return len(self.entries)

    def extract_from_messages(self, messages: list[dict[str, str]], *, now: int | None = None) -> list[dict[str, Any]]:
        created = []
        for message in messages:
            if message.get("role") != "user":
                continue
            content = message.get("content", "")
            if "必须" in content or "不要" in content:
                created.append(self.smart_add("instruction", content, now=now))
            elif "喜欢" in content or "我是" in content:
                created.append(self.smart_add("identity", content, now=now))
        return created

    def extract_with_gatekeeper(
        self,
        messages: list[dict[str, str]],
        *,
        now: int | None = None,
    ) -> dict[str, Any]:
        user_text = "\n".join(
            message.get("content", "")
            for message in messages
            if message.get("role") == "user"
        )
        durable_markers = ["必须", "不要", "以后", "我是", "喜欢", "偏好", "习惯"]
        if not any(marker in user_text for marker in durable_markers):
            return {"decision": "skip", "created": [], "reason": "no durable user memory"}
        return {
            "decision": "extract",
            "created": self.extract_from_messages(messages, now=now),
            "reason": "durable markers found",
        }

    def get_system_prompt_block(self, limit_per_type: int = 8) -> str:
        active = self.list_entries()
        if not active:
            return ""
        lines = ["<user_memory_update>", f'<user_memory mode="full" total="{len(active)}">']
        for memory_type in USER_MEMORY_TYPES:
            items = [entry for entry in active if entry["type"] == memory_type]
            if not items:
                continue
            lines.append(f'<section type="{memory_type}">')
            for entry in sorted(items, key=lambda item: item["updatedAt"], reverse=True)[:limit_per_type]:
                lines.append(
                    f'<item id="{entry["id"]}" activation="{entry["activationCount"]}">'
                    f'{entry["content"]}</item>'
                )
            lines.append("</section>")
        lines.extend(["</user_memory>", "</user_memory_update>"])
        return "\n".join(lines)
