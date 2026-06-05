# LifeOS 数据库与存储

LifeOS 核心状态统一存入 SQLAlchemy 管理的单一数据库。默认是 **SQLite**，文件位于 `{LIFEOS_DATA_ROOT}/lifeos.sqlite3`；设置 `DATABASE_URL=postgresql+psycopg://...` 后，Pack / World / Session / persona / emotion / memory / dreams / world facts 等核心状态都会进入 **PostgreSQL**。

Redis 仍然是可选的 context 短缓存，不是核心数据层。旧版 `runtime_dir` 下的 JSON / `world.sqlite3` 文件只作为自动迁移来源和备份保留。

ORM 定义：[`lifeostomanyagent/server/db/models.py`](../lifeostomanyagent/server/db/models.py)  
应用启动时执行 `init_db()` → `Base.metadata.create_all()`，当前无独立 Alembic 迁移。

---

## 数据库连接

| 项 | 默认值 |
|----|--------|
| 连接串环境变量 | `DATABASE_URL` |
| 默认 URL | `sqlite+pysqlite:///{LIFEOS_DATA_ROOT}/lifeos.sqlite3` |
| SQLite 文件 | 默认 `{LIFEOS_DATA_ROOT}/lifeos.sqlite3` |
| PostgreSQL | 设置 `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db` |
| Docker Compose | 默认 API + SQLite；Postgres / Redis 通过 profile 可选启用 |

---

## 表一览

| 表名 | 说明 | 对应 ORM |
|------|------|----------|
| `agent_packs` | Agent Pack 模板（人设、行为、世界规则等） | `AgentPackRow` |
| `world_instances` | 用户创建的世界实例；`runtime_dir` 仅保留为旧文件迁移来源 / 非核心产物目录 | `WorldInstanceRow` |
| `session_records` | Connector 会话起止记录 | `SessionRecordRow` |
| `runtime_state_documents` | persona / emotion 等小型运行时 JSON 状态 | `RuntimeStateDocumentRow` |
| `user_memories` | 用户记忆条目 | `UserMemoryRow` |
| `memory_snapshots` | 记忆快照 | `MemorySnapshotRow` |
| `dream_seeds` | 梦境生成种子 | `DreamSeedRow` |
| `dream_records` | 已生成梦境与 prompt block | `DreamRecordRow` |
| `world_facts` | 世界事实 / 物品 / 状态 | `WorldFactRow` |
| `fact_events` | 世界事实事件记录 | `FactEventRow` |
| `world_clock_events` | 计划/待触发世界事件 | `WorldClockEventRow` |
| `venue_visits` | 地点访问历史 | `VenueVisitRow` |
| `runtime_migrations` | 旧 runtime 文件导入标记，保证幂等 | `RuntimeMigrationRow` |

关系简述：

```
agent_packs (pack_id)
    └── world_instances (pack_id)
            ├── session_records (world_id)
            ├── runtime_state_documents (world_id)
            ├── user_memories / memory_snapshots (world_id)
            ├── dream_seeds / dream_records (world_id)
            └── world_facts / fact_events / world_clock_events / venue_visits (world_id)
```

---

## `agent_packs`

Agent 世界「模板」。陈远示例预设 `pack_id = 'chenyuan'`，`is_preset = true`。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `VARCHAR(36)` | PK | 内部 UUID |
| `pack_id` | `VARCHAR(128)` | UNIQUE, INDEX | 业务 ID，如 `chenyuan`、`nova` |
| `display_name` | `VARCHAR(256)` | NOT NULL | 展示名 |
| `config_json` | `JSON` | NOT NULL | 完整 Pack 配置，结构见下 |
| `is_preset` | `BOOLEAN` | DEFAULT false | 是否为内置示例预设 |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | 创建时间 |

### `config_json` 结构（`AgentPackConfig`）

对应 [`lifeostomanyagent/domain/models.py`](../lifeostomanyagent/domain/models.py)：

```json
{
  "pack_id": "chenyuan",
  "display_name": "陈远",
  "identity": {
    "agent_name": "陈远",
    "codename": "UBI-公民",
    "identity_code": "#CHENYUAN-2035",
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
    "work_hours": "10:00-23:30",
    "locations": ["2035 年中国一座二三线城市", "陈远的出租屋", "虚拟世界"],
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
| `runtime_dir` | `TEXT` | NOT NULL | 旧版运行时文件迁移来源；也可作为非核心产物目录 |
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

### 旧版 `runtime_dir` 自动迁移

旧版本默认根目录：`{LIFEOS_DATA_ROOT}/worlds/{world_id}/`。新版本首次访问 World 时会检测以下旧文件并导入当前 `DATABASE_URL` 指向的数据库：

| 旧路径（相对 `runtime_dir`） | 新 SQL 表 |
|-----------------------------|-----------|
| `persona.json` | `runtime_state_documents(module='persona')` |
| `emotion.json` | `runtime_state_documents(module='emotion')` |
| `memory/entries.json` | `user_memories` |
| `memory/snapshots/*.json` | `memory_snapshots` |
| `dreams.json` | `dream_seeds` / `dream_records` |
| `world.sqlite3` | `world_facts` / `fact_events` / `world_clock_events` / `venue_visits` |

导入以 `runtime_migrations` 标记幂等；旧文件不会被删除，可作为备份保留。损坏的旧 JSON / SQLite 模块会跳过并记录 warning，不阻塞其他模块导入。

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

Redis **不存业务表数据**，仅作 context 组装结果缓存。未配置或不可连接时，服务会自动跳过缓存。

---

## 常用 SQL 示例

```sql
-- 所有 Pack
SELECT pack_id, display_name, is_preset, created_at FROM agent_packs;

-- 某 Pack 下的世界
SELECT world_id, display_name, runtime_dir, created_at
FROM world_instances
WHERE pack_id = 'chenyuan';

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
| 安装/刷新 陈远示例预设 | `POST /packs/presets/chenyuan` |
| 创建 Pack | `POST /packs` |
| 列出 Pack | `GET /packs` |
| 创建 World | `POST /worlds` |
| 列出 World | `GET /worlds` |
| 拉 context | `POST /runtime/context` |
| 会话事件 | `POST /runtime/session/start` · `end` |

详见 [`docs/api/lifeos-platform.md`](api/lifeos-platform.md)。
