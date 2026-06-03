# LifeOS 数据库与存储

LifeOS 元数据存 **Postgres**，context 短缓存用 **Redis**（可选），各 World 的运行时状态（persona / emotion / memory / world）存 **本地文件系统**。

ORM 定义：[`lifeostomanyagent/server/db/models.py`](../lifeostomanyagent/server/db/models.py)  
应用启动时执行 `init_db()` → `Base.metadata.create_all()`，当前无独立 Alembic 迁移。

---

## Postgres 连接

| 项 | 默认值 |
|----|--------|
| 连接串环境变量 | `DATABASE_URL` |
| 默认 URL | `postgresql+psycopg://lifeos:lifeos@127.0.0.1:5432/lifeos` |
| Docker Compose | 见 [`docker-compose.yml`](../docker-compose.yml) 中 `postgres` 服务 |

---

## 表一览

| 表名 | 说明 | 对应 ORM |
|------|------|----------|
| `agent_packs` | Agent Pack 模板（人设、行为、世界规则等） | `AgentPackRow` |
| `world_instances` | 用户创建的世界实例 | `WorldInstanceRow` |
| `session_records` | Connector 会话起止记录 | `SessionRecordRow` |

关系简述：

```
agent_packs (pack_id)
    └── world_instances (pack_id) ──► 文件系统 runtime_dir/
            └── session_records (world_id)
```

---

## `agent_packs`

Agent 世界「模板」。Alice 官方预设 `pack_id = 'alice'`，`is_preset = true`。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `VARCHAR(36)` | PK | 内部 UUID |
| `pack_id` | `VARCHAR(128)` | UNIQUE, INDEX | 业务 ID，如 `alice`、`nova` |
| `display_name` | `VARCHAR(256)` | NOT NULL | 展示名 |
| `config_json` | `JSON` | NOT NULL | 完整 Pack 配置，结构见下 |
| `is_preset` | `BOOLEAN` | DEFAULT false | 是否为官方预设 |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | 创建时间 |

### `config_json` 结构（`AgentPackConfig`）

对应 [`lifeostomanyagent/domain/models.py`](../lifeostomanyagent/domain/models.py)：

```json
{
  "pack_id": "alice",
  "display_name": "Alice",
  "identity": {
    "agent_name": "Alice",
    "codename": "白艾莉",
    "identity_code": "#76ACAD",
    "backstory": "……",
    "relationship_stance": "……",
    "core_values": ["……"]
  },
  "behavior_profile": {
    "speech_style": ["……"],
    "forbidden_patterns": ["……"],
    "emotion_rules": {},
    "work_habits": ["……"],
    "addressing_rules": ["……"]
  },
  "behavior_trajectory": {
    "milestones": ["……"],
    "proactive_style": "……",
    "reaction_patterns": ["……"]
  },
  "world_rules": {
    "timezone": "Asia/Shanghai",
    "work_hours": "08:00-24:00",
    "locations": ["珠海横琴"],
    "custom_facts": ["……"]
  },
  "runtime_modules": {
    "persona": true,
    "emotion": true,
    "memory": true,
    "world_facts": true,
    "proactive": true
  },
  "is_preset": true,
  "base_system_prompt": null
}
```

说明：

- 推荐使用结构化字段 `identity` / `behavior_*` / `world_rules`。
- `base_system_prompt` 为 legacy 兼容字段；与 `identity` 二选一即可。

---

## `world_instances`

用户基于 Pack 创建的「世界实例」。同一 Pack 可创建多个 World。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `VARCHAR(36)` | PK | 内部 UUID |
| `world_id` | `VARCHAR(36)` | UNIQUE, INDEX | 对外 world ID（API / CLI 使用） |
| `pack_id` | `VARCHAR(128)` | INDEX | 关联 `agent_packs.pack_id` |
| `display_name` | `VARCHAR(256)` | NOT NULL | 世界展示名 |
| `overrides_json` | `JSON` | DEFAULT `{}` | 世界级覆盖，结构见下 |
| `runtime_dir` | `TEXT` | NOT NULL | 运行时状态目录绝对路径 |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | 创建时间 |

### `overrides_json` 结构（`WorldOverrides`）

```json
{
  "display_name": null,
  "base_system_prompt_append": null
}
```

| 字段 | 说明 |
|------|------|
| `display_name` | 可选，覆盖展示名（当前 API 以创建时 `display_name` 为准） |
| `base_system_prompt_append` | 追加到 Pack 身份块末尾的自定义 markdown |

### `runtime_dir` 文件布局

默认根目录：`{LIFEOS_DATA_ROOT}/worlds/{world_id}/`（环境变量 `LIFEOS_DATA_ROOT`，默认 `lifeostomanyagent/data`）。

| 路径（相对 `runtime_dir`） | 说明 | 模块 |
|----------------------------|------|------|
| `persona.json` | Alice persona 状态 | `runtime_modules.persona` |
| `emotion.json` | 情绪状态 | `runtime_modules.emotion` |
| `memory/` | 用户记忆目录 | `runtime_modules.memory` |
| `world.sqlite3` | 世界物品 / 事实 | `runtime_modules.world_facts` |

这些文件 **不在 Postgres**，由 `WorldRuntimeEngine` 读写（复用 `003-life-os/bws_fuxian` 子系统）。

---

## `session_records`

记录 Connector 会话生命周期（`/runtime/session/start` / `end`）。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `VARCHAR(36)` | PK | 记录 UUID |
| `world_id` | `VARCHAR(36)` | INDEX | 关联 `world_instances.world_id` |
| `connector_id` | `VARCHAR(64)` | NOT NULL | 如 `hermes`、`pi`、`claude-code` |
| `session_id` | `VARCHAR(128)` | INDEX | Connector 侧会话 ID |
| `started_at` | `TIMESTAMPTZ` | NOT NULL | 会话开始时间 |
| `ended_at` | `TIMESTAMPTZ` | NULL | 会话结束时间；未结束为 NULL |

说明：

- 同一 `world_id` + `session_id` 可有多条历史记录（按 `started_at` 降序取最近一条更新 `ended_at`）。
- `/runtime/turn/begin` / `turn/finish` 不单独落库，仅触发情绪引擎与 cache 失效。

---

## Redis（可选）

| 项 | 说明 |
|----|------|
| 环境变量 | `REDIS_URL`（未配置或连不上则跳过缓存） |
| 用途 | `/runtime/context` 响应短缓存 |
| Key 格式 | `lifeos:context:{world_id}:{sha256}` |
| TTL | `CONTEXT_CACHE_TTL_SECONDS`（默认 30 秒） |
| 失效 | `session/start|end`、`turn/begin|finish` 时按 `world_id` 前缀批量删除 |

Redis **不存业务表数据**，仅作 context 组装结果缓存。

---

## 常用 SQL 示例

```sql
-- 所有 Pack
SELECT pack_id, display_name, is_preset, created_at FROM agent_packs;

-- 某 Pack 下的世界
SELECT world_id, display_name, runtime_dir, created_at
FROM world_instances
WHERE pack_id = 'alice';

-- 某世界最近会话
SELECT connector_id, session_id, started_at, ended_at
FROM session_records
WHERE world_id = 'your-world-uuid'
ORDER BY started_at DESC
LIMIT 10;
```

---

## 相关 API

| 操作 | 接口 |
|------|------|
| 安装/刷新 Alice 预设 | `POST /packs/presets/alice` |
| 创建 Pack | `POST /packs` |
| 列出 Pack | `GET /packs` |
| 创建 World | `POST /worlds` |
| 列出 World | `GET /worlds` |
| 拉 context | `POST /runtime/context` |
| 会话事件 | `POST /runtime/session/start` · `end` |

详见 [`docs/api/lifeos-platform.md`](../../docs/api/lifeos-platform.md)。
