# LifeOS 人物角色总览

本文汇总当前仓库中已定义或可安装的 LifeOS 人物角色。每个角色都对应一个 `Agent Pack`；除 Alice 内置 preset 外，其他角色均以 `docs/agent-packs/*.md` 的形式保存完整人物提示词和 `AgentPackConfig JSON`。

| 人物 | Pack ID | 类型 | 来源 / 原型 | 现代身份定位 | Runtime 模块 | 文档 |
|------|---------|------|-------------|--------------|---------------|------|
| Alice | `alice` | 内置 preset | LifeOS 示例角色 | 26 岁，澳门氹仔成长、现居珠海横琴的远程协作助理，强调共情、边界和可靠执行 | persona、emotion、memory、world_facts、proactive | [alice.py](../../lifeostomanyagent/server/presets/alice.py) |
| 木生 | `musheng` | 自定义 Agent Pack | 《给阿嬷的情书》中的郑木生 | 32 岁，现居深圳南山的社区档案与华侨文化项目顾问，擅长侨批、家书、口述史和项目推进 | persona、emotion、memory、world_facts、proactive、dreams | [musheng.md](musheng.md) |
| 南枝 | `nanzhi` | 自定义 Agent Pack | 《给阿嬷的情书》中的谢南枝 | 29 岁，现居广州越秀的华文教育与侨批记忆项目策划人，擅长跨文化沟通、华文教育和长期承诺整理 | persona、emotion、memory、world_facts、proactive、dreams | [nanzhi.md](nanzhi.md) |
| 淑柔 | `shurou` | 自定义 Agent Pack | 《给阿嬷的情书》中的叶淑柔 | 34 岁，现居汕头小公园片区的社区家庭支持与侨批记忆项目协调人，擅长家庭关系梳理、长辈陪伴和家书档案整理 | persona、emotion、memory、world_facts、proactive、dreams | [shurou.md](shurou.md) |

## 入库状态

在本地开发环境中，角色应先创建 Pack，再创建对应 World。可使用仓库内置脚本导入自定义角色：

```bash
skills/lifeos-agent-pack-builder/scripts/import_agent_pack.py \
  docs/agent-packs/shurou.md \
  --server http://127.0.0.1:8000 \
  --api-key dev-lifeos-key-change-me
```

安装或刷新 Alice preset：

```bash
curl -X POST \
  -H "X-API-Key: dev-lifeos-key-change-me" \
  http://127.0.0.1:8000/packs/presets/alice
```

查询当前数据库中的 Pack：

```bash
curl -sS \
  -H "X-API-Key: dev-lifeos-key-change-me" \
  http://127.0.0.1:8000/packs
```

查询当前数据库中的 World：

```bash
curl -sS \
  -H "X-API-Key: dev-lifeos-key-change-me" \
  http://127.0.0.1:8000/worlds
```

## 创建新人物

新增角色请优先使用仓库内置 skill：

```text
$lifeos-agent-pack-builder
```

完整流程见 [创建新角色指南](../create-new-character.md)。
