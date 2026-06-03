# pi agent 适配层协议

## 目标

首版通过独立子进程接入 `pi` agent，让 Alice 现有 Electron 主进程可以在保留既有 preload IPC、persona、memory、world、planner、swarm 体系的前提下，跑通基础聊天、文件操作和 skills 能力。

## 首版范围

- Electron main process 启动并管理 `pi` agent 子进程。
- Alice UI 继续通过现有 `agent:chat`、`agent:stream`、`agent:abort` 等 IPC 入口与主进程交互。
- 主进程中的适配层负责把 Alice IPC 请求转成子进程输入事件，并把子进程输出事件转成 Alice 现有流式事件。
- 文件操作只允许发生在用户选定的工作目录内。
- skills 能力优先复用 `pi` 的 skills 体系。
- 首版必须支持流式输出。

## 子进程协议

首版先使用简单的 stdin/stdout 事件协议。每一行是一条 JSON 事件。

### 输入事件

```json
{"type":"chat","sessionId":"session-id","message":"用户输入","cwd":"/selected/workdir"}
```

```json
{"type":"abort","sessionId":"session-id"}
```

### 输出事件

```json
{"type":"start","sessionId":"session-id"}
```

```json
{"type":"text_delta","sessionId":"session-id","content":"流式文本片段"}
```

```json
{"type":"tool_call","sessionId":"session-id","toolName":"read","summary":"读取文件"}
```

```json
{"type":"error","sessionId":"session-id","message":"错误信息"}
```

```json
{"type":"done","sessionId":"session-id"}
```

## 安全约定

- 子进程只能接收经过主进程校验后的工作目录。
- 子进程不得把 API Key、访问令牌等敏感信息输出到 stdout/stderr。
- 模型 API Key 通过 `DEEPSEEK_API_KEY` 或安全 keystore 注入，不写入前端代码或仓库。

## 运行时约定

- 适配层优先启动已构建的 `pi/packages/coding-agent/dist/cli.js`。
- 如果 `pi` 尚未构建，但本地工作区存在 `pi/node_modules/.bin/tsx`，适配层可用源码入口 `pi/packages/coding-agent/src/cli.ts` 启动 `pi` agent，并显式传入 `pi/tsconfig.json`。
- 可通过 `ALICE_PI_AGENT_CLI` 或 `PI_AGENT_CLI` 指定 `pi` CLI 入口。
- 可通过 `ALICE_PI_AGENT_NODE` 指定运行 agent 子进程的 Node 可执行文件。
- 可通过 `ALICE_PI_AGENT_PROVIDER` 或 `PI_AGENT_PROVIDER` 覆盖 `pi` provider；未设置时默认使用 `deepseek`。
- 可通过 `ALICE_PI_AGENT_MODEL` 或 `PI_AGENT_MODEL` 覆盖默认模型；未设置时默认使用 `deepseek-v4-pro`。
- Alice UI 当前选中的模型不会覆盖 `pi` agent 默认模型，避免既有 Alice 模型选择影响首版 `pi` 底层验证。
- 首版传给 `pi` 的内置工具限制为 `read,grep,find,ls`，用于满足工作目录内只读文件操作验证。
- 适配层不传 `--no-skills`，保留 `pi` CLI 默认的 skills 发现与加载能力；后续如需指定额外 skill 路径，再扩展显式配置。

## 待实现时验证

- 能从 Alice UI 发起一次聊天。
- 能看到流式文本输出。
- 能在用户选定工作目录内完成一次只读文件操作。
- 能加载并使用 `pi` skills 体系中的基础 skill。
