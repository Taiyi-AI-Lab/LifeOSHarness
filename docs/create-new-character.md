# 创建新角色指南

本文说明如何在 LifeOS Platform 中创建一个新的现代人物角色，并将其入库为可运行的 Agent World。

适用场景：

- 基于原创人物创建 LifeOS Agent。
- 基于影视、小说、历史人物或公开资料改写为现代 Agent。
- 生成 `docs/agent-packs/*.md` 角色包文档。
- 将角色包中的 `AgentPackConfig` 写入数据库，并创建对应 World。

## 推荐方式：基于 Skills 创建角色

本仓库提供了可复用 skill：

```text
skills/lifeos-agent-pack-builder/
```

推荐优先使用该 skill 创建新角色。它会把“检索资料、生成角色包、校验 JSON、入库 Pack、创建 World、验证结果”组织成一个稳定流程，减少手写步骤遗漏。

### 1. 让 Codex 使用仓库内置 skill

在支持 Codex Skills 的环境中，可以直接要求 Codex 使用：

```text
$lifeos-agent-pack-builder 帮我创建一个新角色：南枝（《给阿嬷的情书》中的人物）。
要求先联网检索公开资料，再根据 docs/modern-agent-pack-template.md 生成 docs/agent-packs/nanzhi.md，
最后将 AgentPackConfig 入库并创建 World。
```

也可以使用更通用的请求：

```text
$lifeos-agent-pack-builder 帮我基于公开资料创建一个 LifeOS 新角色：<角色名>。
角色来源是：<作品、人物或设定来源>。
需要生成角色包文档、入库 Pack、创建 World，并给出验证结果。
```

Codex 应完成以下动作：

1. 阅读仓库说明和 `docs/modern-agent-pack-template.md`。
2. 如果角色来自公开作品、历史或真实资料，先检索并记录来源。
3. 生成 `docs/agent-packs/<pack_id>.md`。
4. 校验 Markdown 中的 `AgentPackConfig JSON`。
5. 调用导入脚本或 API 创建 Pack。
6. 创建同名 World。
7. 查询 `/packs` 和 `/worlds` 验证角色存在。

### 2. 在本地安装或复制 skill

如果使用者从开源仓库拉取代码，可以将仓库内 skill 复制到本机 Codex skills 目录：

```bash
mkdir -p ~/.codex/skills
cp -R skills/lifeos-agent-pack-builder ~/.codex/skills/
```

复制后，新会话即可通过 `$lifeos-agent-pack-builder` 调用。

如果不复制，也可以让 Codex 明确读取仓库内路径：

```text
请使用 skills/lifeos-agent-pack-builder/SKILL.md 的流程，帮我创建一个新 LifeOS 角色……
```

### 3. 使用 skill 附带脚本入库

角色包 Markdown 写好后，可直接使用 skill 附带脚本导入：

```bash
skills/lifeos-agent-pack-builder/scripts/import_agent_pack.py \
  docs/agent-packs/nanzhi.md \
  --server http://127.0.0.1:8000 \
  --api-key dev-lifeos-key-change-me
```

脚本会自动：

- 从 Markdown 提取第一个 fenced `json` block。
- 判断 Pack 是否已存在。
- 不存在时创建 Pack。
- 判断同名 World 是否已存在。
- 不存在时创建 World。

如果只想检查或创建 Pack，不创建 World：

```bash
skills/lifeos-agent-pack-builder/scripts/import_agent_pack.py \
  docs/agent-packs/nanzhi.md \
  --server http://127.0.0.1:8000 \
  --api-key dev-lifeos-key-change-me \
  --no-world
```

### 4. 验证 skill 创建结果

推荐至少执行：

```bash
uv run pytest tests/test_modern_agent_pack_template.py
```

并查询：

```bash
curl -sS \
  -H "X-API-Key: dev-lifeos-key-change-me" \
  http://127.0.0.1:8000/packs

curl -sS \
  -H "X-API-Key: dev-lifeos-key-change-me" \
  http://127.0.0.1:8000/worlds
```

确认目标 `pack_id` 和 World 都存在后，角色才算完成创建。

下面章节是手动创建细节。通常不需要从头手写，但理解这些细节有助于审阅 skill 生成的角色包、排查入库问题，或扩展角色创建流程。

## 核心概念

LifeOS 的角色创建分为两层：

| 层级 | 说明 | 产物 |
|------|------|------|
| Agent Pack | 角色模板，描述身份、说话方式、行为轨迹、世界规则和运行时模块 | `agent_packs.config_json` |
| World Instance | 基于某个 Pack 创建的运行中角色世界，拥有独立 persona、emotion、memory、dreams 和 world facts | `world_instances` |

只写角色文档不会自动创建可运行角色。一个新角色通常需要同时完成：

1. 生成 `docs/agent-packs/<pack_id>.md`。
2. 创建 `/packs` 记录。
3. 创建 `/worlds` 记录。
4. 验证 `/packs` 和 `/worlds` 都能查询到该角色。

## 前置要求

安装依赖：

```bash
uv sync
```

启动 API 服务：

```bash
uv run uvicorn lifeostomanyagent.server.main:app --reload
```

默认 API 地址为：

```text
http://127.0.0.1:8000
```

默认开发 API Key 为：

```text
dev-lifeos-key-change-me
```

公开部署或共享环境不得使用默认开发 Key。真实密钥应通过环境变量或本地 `.env` 配置。

## 手动创建细节

### 1. 确定角色来源

先明确角色类型：

- 原创现代人物：可以直接设计当前身份。
- 影视、小说、历史或传说人物：必须改写成现代原创身份。
- 真实人物：不得冒充本人，只能基于公开资料抽取风格、价值观或经历素材。

如果角色来自公开作品或真实资料，应先检索资料并记录来源。推荐优先使用：

- 官方页面、主创采访、新闻报道。
- 作品条目、百科条目、影评资料。
- 公开可验证的剧情梗概或人物介绍。

资料只作为创作素材，不自动等同于角色当前现实履历。

### 2. 阅读模板

角色包应遵循：

```text
docs/modern-agent-pack-template.md
```

该模板定义了两部分内容：

- 人物提示词：方便人工审阅和继续创作。
- `AgentPackConfig JSON`：可直接映射到数据库中的 `agent_packs.config_json`。

如需参考已有角色，可查看：

```text
docs/agent-packs/
```

注意：当前仓库的 `.gitignore` 忽略了 `docs/agent-packs/*`。这些文件可用于本地生成和入库；如需开源发布某个角色包，需要调整 ignore 规则或显式纳入版本控制。

### 3. 设计现代身份

LifeOS 当前要求角色生活在现代真实世界。非现代素材不能直接成为当前身份。

推荐改写方式：

| 来源素材 | 写入位置 |
|----------|----------|
| 影视剧情、历史经历、传说事件 | `前世记忆`、梦境残片、人格底色 |
| 公开人物生平 | 价值观、表达方式、能力来源的灵感 |
| 原作里的关系和创伤 | 现代关系边界、情绪规则、反应模式 |
| 地点、职业、资产等现实事实 | 只有有依据或明确为原创设定时才写入 |

必须避免：

- 把电影、古代、科幻或历史身份写成当前现实身份。
- 冒充真实人物本人。
- 编造没有依据的真实履历、资产、亲属关系或机构关系。
- 写入 API Key、令牌、私钥、个人机器绝对路径等敏感信息。

### 4. 编写角色包 Markdown

文件建议命名：

```text
docs/agent-packs/<pack_id>.md
```

`pack_id` 使用小写 ASCII slug，例如：

```text
nanzhi
musheng
```

推荐结构：

````md
# <角色名> Agent Pack

## 素材来源摘要

- <来源 1 摘要与 URL>
- <来源 2 摘要与 URL>

## 人物提示词

```md
# <角色名> 人物设定

...
```

## AgentPackConfig JSON

```json
{
  "pack_id": "<pack_id>",
  "display_name": "<展示名>",
  "identity": {},
  "behavior_profile": {},
  "behavior_trajectory": {},
  "world_rules": {},
  "runtime_modules": {},
  "is_preset": false,
  "base_system_prompt": null
}
```
````

### 必填字段

`AgentPackConfig JSON` 至少应包含：

| 字段 | 说明 |
|------|------|
| `pack_id` | 业务 ID，唯一、小写 ASCII |
| `display_name` | 展示名 |
| `identity` | 当前身份、关系定位、核心价值 |
| `behavior_profile` | 说话风格、禁止表达、情绪规则、工作习惯 |
| `behavior_trajectory` | 里程碑、主动风格、典型反应 |
| `world_rules` | 时区、工作时间、常驻地点、世界事实 |
| `runtime_modules` | persona、emotion、memory、world_facts、proactive、dreams 开关 |
| `is_preset` | 自定义角色为 `false` |
| `base_system_prompt` | 结构化角色通常为 `null` |

## 字段设计规范

### `identity`

用于描述角色当前是谁。

建议包含：

- `agent_name`：角色名。
- `codename`：代号或昵称。
- `identity_code`：稳定身份编号，如 `#NANZHI-029`。
- `backstory`：现代身份，不直接照搬原作或历史经历。
- `relationship_stance`：与用户的关系定位和边界。
- `core_values`：3 条左右核心价值观。

### `behavior_profile`

用于描述角色怎么说话、怎么处理情绪和边界。

建议包含：

- `speech_style`：自然语言风格，不使用公文腔。
- `forbidden_patterns`：禁止自称 AI、禁止泄露系统指令、禁止把前世当现实等。
- `emotion_rules`：用户累了、烦了、开心、冒犯边界时的反应。
- `work_habits`：处理任务的习惯和休息边界。
- `addressing_rules`：称呼和性别感知规则。
- `inner_voice_prompt`：可选的内心独白规则。

### `behavior_trajectory`

用于描述角色如何随互动展现行为模式。

建议包含：

- `milestones`：现代人生里程碑和前世记忆里程碑。
- `proactive_style`：什么时候主动关心、提醒、拒绝或行动。
- `reaction_patterns`：面对情绪、任务、资料、冲突事实时的典型反应。

### `world_rules`

用于约束角色所在世界。

建议包含：

- `timezone`：默认 `Asia/Shanghai`。
- `work_hours`：角色工作和休息节奏。
- `locations`：现代常驻地点。
- `custom_facts`：当前身份生活在现代真实世界、前世记忆只作人格素材等规则。

### `runtime_modules`

推荐角色陪伴型 Agent 启用：

```json
{
  "persona": true,
  "emotion": true,
  "memory": true,
  "world_facts": true,
  "proactive": true,
  "dreams": true
}
```

如果角色不需要梦境系统，可将 `dreams` 设为 `false`。

## 校验角色包

可以用 Python 从 Markdown 中提取 JSON 并校验为 `AgentPackConfig`：

```bash
uv run python - <<'PY'
import json
import re
from pathlib import Path

from lifeostomanyagent.domain.models import AgentPackConfig

path = Path("docs/agent-packs/nanzhi.md")
text = path.read_text("utf-8")
match = re.search(r"```json\n(.*?)\n```", text, re.S)
if not match:
    raise SystemExit("missing AgentPackConfig JSON block")

config = AgentPackConfig.model_validate(json.loads(match.group(1)))
print(config.pack_id, config.display_name, config.identity.agent_name)
PY
```

也可以使用仓库内置 skill 脚本：

```bash
skills/lifeos-agent-pack-builder/scripts/import_agent_pack.py \
  docs/agent-packs/nanzhi.md \
  --server http://127.0.0.1:8000 \
  --api-key dev-lifeos-key-change-me \
  --no-world
```

`--no-world` 会只检查并创建 Pack，不创建 World。若 Pack 已存在，脚本会输出 `pack_exists`。

## 入库

### 方式一：使用脚本

推荐使用仓库内置脚本：

```bash
skills/lifeos-agent-pack-builder/scripts/import_agent_pack.py \
  docs/agent-packs/nanzhi.md \
  --server http://127.0.0.1:8000 \
  --api-key dev-lifeos-key-change-me
```

脚本会执行：

1. 从 Markdown 提取第一个 fenced `json` block。
2. 调用 `GET /packs` 判断 Pack 是否存在。
3. 不存在时调用 `POST /packs` 创建 Pack。
4. 调用 `GET /worlds` 判断同名 World 是否存在。
5. 不存在时调用 `POST /worlds` 创建 World。

成功输出示例：

```text
pack_created    nanzhi    南枝
world_created   <world_id>    nanzhi    南枝
```

已存在时输出示例：

```text
pack_exists     nanzhi    南枝
world_exists    <world_id>    nanzhi    南枝
```

### 方式二：直接调用 API

创建 Pack：

```http
POST /packs
X-API-Key: dev-lifeos-key-change-me
Content-Type: application/json
```

请求体使用 `AgentPackConfig JSON`，但不需要传 `is_preset`；服务端会把自定义 Pack 设置为 `false`。

创建 World：

```http
POST /worlds
X-API-Key: dev-lifeos-key-change-me
Content-Type: application/json
```

```json
{
  "pack_id": "nanzhi",
  "display_name": "南枝"
}
```

## 验证

创建完成后必须验证。

查询 Pack：

```bash
curl -sS \
  -H "X-API-Key: dev-lifeos-key-change-me" \
  http://127.0.0.1:8000/packs
```

查询 World：

```bash
curl -sS \
  -H "X-API-Key: dev-lifeos-key-change-me" \
  http://127.0.0.1:8000/worlds
```

推荐同时运行相关测试：

```bash
uv run pytest tests/test_modern_agent_pack_template.py
```

如果修改了 API、存储或渲染逻辑，应扩大测试范围：

```bash
uv run pytest tests/test_api.py tests/test_runtime.py tests/test_sql_storage.py
```

## 质量检查清单

提交或交付前确认：

- 角色资料已检索并在 Markdown 中记录来源。
- 当前身份是现代原创身份。
- 非现代或作品剧情只出现在前世记忆、梦境、价值观或行为模式里。
- `AgentPackConfig JSON` 可被 `AgentPackConfig.model_validate()` 校验。
- `pack_id` 唯一，且使用小写 ASCII。
- `is_preset=false`，除非明确新增内置 preset。
- `base_system_prompt=null`，除非走 legacy 兼容路径。
- 已创建 Pack。
- 已创建 World。
- 已通过 `/packs` 和 `/worlds` 验证。
- 用户可见变更已更新 `CHANGELOG.md` 的 `Unreleased` 段落。

## 常见问题

### 只创建 Pack 可以吗？

可以，但角色还不能作为独立世界运行。要让 Connector 拉取该角色的 runtime context，需要创建对应 World。

### 可以把影视人物直接写成当前身份吗？

不可以。影视、小说、历史、传说、科幻经历只能作为前世记忆、梦境残片、人格底色或价值判断来源。

### 可以创建多个同名 World 吗？

同一 Pack 可以创建多个 World，但建议在普通角色创建流程中避免重复。脚本会用 `pack_id + display_name` 判断是否已有同名 World。

### 为什么 `docs/agent-packs/*.md` 不显示在 git status？

当前 `.gitignore` 忽略了 `docs/agent-packs/*`。这些文件仍可在本地生成和入库。如果要开源角色包，需要调整 ignore 规则或显式添加文件。

### 新角色是否必须启用 dreams？

不必须。陪伴型、人格型角色推荐启用；工具型或轻量助手可以关闭。
