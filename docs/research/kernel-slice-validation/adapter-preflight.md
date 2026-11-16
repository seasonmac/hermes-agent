# T0：Hermes / Codex 静态适配基线

2026-11-16 · 对应[已提交的实施计划](../2026-11-16-kernel-slice-implementation-plan.md) T0 · 结构化结果见 [capability-baseline.json](capability-baseline.json)。

**结论：两条公开接入路线均有依据，可以进入 T0-P 的受限兼容性验证；尚不能认定适配器或自动恢复已可用。** T0 静态清单已完成，T0-P、产品实现和新模型实验均未开展。当前真正需要优先验证的是 Hermes 正常工具身份/费用归属，以及 Codex 冷恢复后的动态工具回调和在途对账。

## 核对范围与证据等级

本轮读取源码、公开协议类型、本地安装入口和历史报告；运行了 Git 查询、Codex `--version`、Python `--version`，以及绕过 Hermes CLI 启动器的只读版本解析。没有运行 Gateway attach、创建会话、启动 AppServer、加载插件、发送群消息、运行 Responses fixture 或付费模型。没有读取 `.env`、认证文件或真实会话正文。

能力清单将三个维度分开：

- `contract_status`：核对到的入口能否提供该语义，值为 supported / unsupported / unknown，受具体条件约束。
- `evidence`：本轮源码依据、只读元数据，或历史 native/fixture 记录；历史 tested 不自动成为本轮实测。
- `current_integration_status`：独立运行时尚未实现，统一为 unknown；不把接口存在当作完整接入通过。

JSON 中每条能力有入口、证据 ID、边界、阻塞项和下一验证任务。源码证据记录仓库、提交、路径、行号和文件 SHA-256；行号用于定位，提交和 hash 用于判断后续漂移。

## 实际版本：区分源码、安装入口与存活服务

| 对象 | 本轮观测 | 可以据此确认的范围 |
|---|---|---|
| Hermes 工作区 | `multiAgent`，`72b056be3b9d1548f3a59731189943b64e1ec694`；核对开始时干净 | 当前可读源码；之后文档提交可能改变 HEAD，不表示服务升级 |
| Hermes 安装入口 | `/Users/season/.local/bin/hermes` → 当前仓库 `.hermes/bin/hermes` → PM 管理的 Python 3.14.9；启动器将当前仓库加入导入路径 | 这是源码安装，不是另一份固定 wheel；新启动进程会解析该安装树 |
| Hermes 版本解析 | `base_version=0.23.1`，`derived_version=0.23.1+71957.g72b056b`，`source=git`，`dirty=false` | 直接调用已核对的只读 `get_version_info()`，未运行带修复逻辑的 CLI launcher。`pyproject.toml` 的 `0.0.0` 不是有效运行版本 |
| Hermes 现有 Gateway | **本轮未连接，当前进程版本 unknown** | 历史 G1 记录为 0.23.1 / `18e659dfc93ef319771d51441573e3fa31b8f5b7`，不能将它当成新鲜服务查询 |
| Codex 安装二进制 | `/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex`；`codex-cli 0.169.0-alpha.11.1` | 本轮实际执行版本命令；没有启动服务。二进制 hash 见 JSON |
| Codex 源码 | `e241c18544bab47f729dbfea6d6f2e21531ba0a7`，核对时干净 | 本地可审计实现。尚无证据证明此提交就是安装二进制的准确构建提交 |

Codex `--version` 附带“无法创建 PATH aliases”的沙箱警告，但成功返回版本；没有为此提权、改 PATH 或重新安装。Hermes 的 launcher 包含启动修复路径，因此本轮只解析版本模块，不通过 launcher 触发初始化。

版本来源：[Hermes 解析器](../../../hermes_cli/version_info.py:293)、[源码安装 Git 版本计算](../../../hermes_cli/version_info.py:242)、[历史 Hermes G1](../g0-g2-2026-11-16/hermes/G1-evidence.md)、[历史 Codex G1](../g0-g2-2026-11-16/codex-dsh/README.md)。本轮比较的五个 Hermes 关键文件（handler、插件注册、canonical session schema、工具集策略、辅助 usage hooks）与历史服务端提交相同；这降低部分接口漂移疑虑，但不证明服务当前仍运行或插件/配置已加载。

## Hermes：可用公开路径与边界

### 1. 必须使用 canonical Gateway 合同

`hermes gateway attach --json` 不带 `--start/--recover` 是发现入口。后续 T0-P 应在内存中捕获返回值，分离客户端 `client_code_sha` 与服务端 `endpoint.code_sha`，不得保存 ticket。WebSocket 使用返回的 subprotocols、无 Origin、loopback、禁用代理；ticket 单次使用、绑定 profile/instance、30 秒有效，重连须重新获取。[attach 契约](../../../website/docs/developer-guide/gateway-internals.md:582)

这里有一个容易接错的同名接口：`tui_gateway/contracts/sessions.py` 是独立 TUI/sidecar 的 `idempotency_key` 版本；计划使用的 **`hermes-gateway-v1` 应看 `canonical_sessions.py` 的 `request_id`、`toolsets`、`max_turns` 等字段**。适配器不能将两份同名 schema 拼接。实际创建前读 `runtime.describe.session_create.parameters`，不盲送工作区 HEAD 才支持的字段。[canonical 创建合同](../../../tui_gateway/contracts/canonical_sessions.py:30)、[发现响应](../../../tui_gateway/contracts/canonical.py:402)

| 能力 | 核对到的入口/字段 | 证据与限制 |
|---|---|---|
| 创建/恢复 | `session.create(request_id, source="tool", toolsets, …)`；`session.resume(session_id)` | 源码＋历史 G1。create 同 ID 参数冲突拒绝；session 逻辑 ID、存储段 ID 和 handler ID 不应假定永远相等 |
| 提交/接受边界 | `prompt.submit` 的 `submission_id` 或 `input_id`；receipt 有 admission_id/status/authority_epoch/execution_generation | `queued` 不是执行完成；首切片忙时留在运行时，不利用原生 FIFO 提前排多个 turn |
| 结果/取消 | `prompt.receipt(..., include_result=true)`；`prompt.cancel(session_id, admission_id)` | 终态才可能有 result/usage；取消请求响应可能仍为 started，需继续查询终态 |
| 事件回放 | `session.events.since(last_sequence, replay_epoch)` | 返回 snapshot_required/truncated 时重取快照；游标有 epoch，不能当成永久逐消息消费证明 |
| 冷恢复 | 源码存在 local-session 恢复；unknown admission 会阻断队列 | 尚无本项目 Gateway 冷重启实测；`prompt.resolve_unknown` 是显式处置，不是安全重发证明，不自动调用它清障 |
| 插件工具 | `plugin.yaml`＋`__init__.py:register(ctx)`，`ctx.register_tool(...)` | 外部薄插件可承载 send/read；注册/安装成功不等于真实回合已选择该工具集 |
| 用量 | receipt.usage、session.usage/session.stats；公开 API/auxiliary hooks | session 流含累计值；同消费的汇总与 hooks 不叠加。辅助流式/失败返回可能没有 usage，不能记零或声称全覆盖 |

上述字段定位：[提交/事件类型](../../../tui_gateway/contracts/canonical_sessions.py:249)、[receipt/cancel/resolve_unknown](../../../tui_gateway/contracts/canonical.py:42)、[原生事件回放](../../../gateway/session_controls.py:785)、[恢复队列](../../../gateway/session_local_recovery.py:476)、[用量累计口径](../../../gateway/session_usage.py:1)。

### 2. 身份、压缩与工具回执

普通 handler 收到 `task_id/session_id/conversation_id`，以及适用时的 `user_task`；普通路径**没有直接透传 `tool_call_id/turn_id`**。插件 fork 的额外 `turn_origin` 可识别一类来源，但缺少该字段不证明一定是受控主 Agent。[实际派发](../../../model_tools.py:851)、[公开说明](../../../website/docs/developer-guide/plugins/index.md:887)

逻辑作者必须由 profile、预存 binding、当前受控 Attempt 与实际 handler 上下文联合确定。正文的 sender/owner 字段只是数据。压缩可能换 session；delegated child 有自己的 session，却可共享 conversation；`execute_code` 内调用可能无会话上下文。因此缺绑定、只有 conversation、摘要 fork、未纳管 child 和不一致 revision 都须拒绝，不能回退默认成员。

send 的业务幂等采用稳定 request_id＋收件人＋内容指纹。公开工具 hooks 可补原生相关性，但不能把 hooks 的 tool_call_id 当作 handler 必有字段。跨崩溃/压缩准确回放原工具回执尚未验证，首切片不能为得到成功响应而重新发送业务请求。

### 3. 一个具体配置冲突：safe_mode 排除插件

源码 `_resolve_toolsets` 在 `safe_mode` 下移除插件工具集；safe_mode 还隐含 ignore_user_config。**不能要求 safe_mode=true，同时要求外部协作插件正常工作。** 显式 toolsets 会校验名称并剔除未点名的扩展工具集，这为最小表提供了路径。[策略](../../../gateway/session_policy.py:669)

T0-P 建议配置：专用隔离 profile，正常插件加载路径，显式选择协作插件工具集，yolo 关闭，无生产写凭据，无自动原生再委派；按实际权限与模型收到的工具表核对。profile 隔离不是 OS 沙箱，不能当作抵御同用户恶意代码的边界。没有验证安全而可用的配置前，不运行真实资料任务；本轮没有创建或修改 profile。

usage 方面，主调用 hooks 有 api_request_id/turn_id/task_id/session_id；辅助调用的 parent 字段可能为空，streaming 或 error 时 usage 明确可能为 null。这些都是观察钩子，并非 provider 硬预算闸门，也不保证崩溃后可重放。[API hook](../../../agent/api_request_hooks.py:164)、[辅助身份](../../../agent/auxiliary_hooks.py:26)、[辅助 usage 缺失分支](../../../agent/auxiliary_hooks.py:159)

## Codex：公开实验性接口与恢复路径

| 能力 | 核对到的入口/字段 | 证据与限制 |
|---|---|---|
| 初始化/建线程 | `initialize.capabilities.experimentalApi=true`，完成握手，再 `thread/start.dynamicTools` | dynamicTools 是实验性字段；稳定 TypeScript schema 可能不含它，必须固定二进制/实验性 schema |
| 原生工具身份 | `item/tool/call` 带 threadId/turnId/callId/namespace/tool/arguments | 字段由服务端生成；运行时仍核对它们属于哪个成员/Attempt，不信工具正文自报身份 |
| 提交/繁忙 | `turn/start`，底层 `start_or_steer_turn` | busy 提交可能进入旧 turn；同 clientUserMessageId 不保证去重。运行时必须本地排队 |
| 终态/查询/取消 | `turn/completed`、`thread/read`、`turn/interrupt` | interrupt 接受不是终态；无原 turn ID 的超时无法只凭 thread 存在判定未执行 |
| 会话历史恢复 | 同 CODEX_HOME 新服务调用 `thread/resume(threadId)` | 历史 fixture 验证过终态历史恢复且无新增 provider 请求；不证明所有在途情形 |
| 动态工具恢复 | resumed initial_history 取 persisted_dynamic_tools，并在未显式配置时恢复到 session_configuration | 本轮找到明确源码路径；仍待安装二进制＋新连接下实际 callback 验证 |
| 用量 | `thread/tokenUsage/updated` 的 tokenUsage.total/last、threadId/turnId | 累计差额须持久基线；历史 fixture 中恢复的旧累计量可挂在后一个 interrupted turn ID，不能再计一次 |
| 工具表/权限 | thread config、sandbox、approvalPolicy；源码有 shell_tool 关闭路径 | 注入两项 dynamicTools 不意味着内置工具被移除；实际完整表与有效权限仍需 T0-P 核验 |

来源：[实验性字段](/Users/season/workspace/github/codex/codex-rs/app-server-protocol/src/protocol/v2/thread.rs:147)、[初始化门控](/Users/season/workspace/github/codex/codex-rs/app-server/src/message_processor.rs:1043)、[服务端工具请求](/Users/season/workspace/github/codex/codex-rs/app-server/src/bespoke_event_handling.rs:1122)、[start_or_steer_turn](/Users/season/workspace/github/codex/codex-rs/app-server/src/request_processors/turn_processor.rs:722)、[恢复动态工具定义](/Users/season/workspace/github/codex/codex-rs/core/src/session/session.rs:1602)、[usage 类型](/Users/season/workspace/github/codex/codex-rs/app-server-protocol/schema/typescript/v2/ThreadTokenUsageUpdatedNotification.ts:6)、[shell 工具开关](/Users/season/workspace/github/codex/codex-rs/core/src/tools/spec_plan.rs:1289)。

### 专用 stdio 服务恢复的执行边界

采用计划指定的专用子进程＋持久独立 CODEX_HOME。stdio 关闭在 single_client_mode 下可导致服务退出并关闭 threads；不能将其理解为一个始终存活的守护服务。源码链接见下段。

恢复顺序必须是：确认旧进程实例归属和退出 → 同状态目录启动新服务 → 重新 initialize → 恢复原 thread → 查询原 turn、工具配置和累计用量 → 按原 Attempt 对账。旧进程状态不明时不并启第二写者；进程已退出也不证明 provider 未收费。没有接受证据则保留 unknown，不把 `thread/start` 或 `turn/start` 当恢复查询。

连接断开时，尚未获得客户端回执的 dynamic tool request 在当前源码可能变为失败工具结果；恢复**工具定义**不等于恢复**待决 RPC**。runtime 的业务请求可能已经落盘而原生工具回执未达，故 request_id 的业务幂等与工具 callId 的回执处置仍需分别核对。[stdio 退出](/Users/season/workspace/github/codex/codex-rs/app-server/src/lib.rs:1241)、[线程关闭](/Users/season/workspace/github/codex/codex-rs/app-server/src/lib.rs:1402)、[动态工具回执失败路径](/Users/season/workspace/github/codex/codex-rs/app-server/src/dynamic_tools.rs:18)。

## 最小工具表与接受合同

两个新业务工具保持计划不变：`collab_send`（稳定 request_id、目标、原文/引用、reply_to、工作归属）和 `evidence_read`（授权范围内 artifact/version，返回正文位置/hash 或 unavailable）。身份由受信回调绑定，参数不授予权限。send 只返回持久回执，不阻塞等同伴；接收由下一获准回合注入。T0-P 真实探针只需调用 send，不将两个工具都强塞进短探针。

Worker/Lead 的结构化结果和 Owner 接受提案沿用 V3.2；不新增任意代码执行、修改 Mission、解除暂停或通用批准工具。注册时固定实际模型、工具、skills 与权限，后续仅追加消息/证据。完整实际表、裁剪效果和隔离强度本轮均为 unknown，不能承诺“模型只有两个工具”。

## 阻塞项与解除证据

| ID | 范围/级别 | 当前缺口 | 下一步与通过标准 |
|---|---|---|---|
| B01 | 版本适配门槛 | 当前 Gateway 进程版本/能力未新鲜确认；Codex 二进制与源码构建提交不能一一对应 | T0-P 记录实际 endpoint/runtime.describe 与固定 Codex schema；不自动重启用户服务 |
| B02 | Hermes 配置门槛 | safe_mode 排除插件；尚无实际加载、最小工具表与有效权限证据 | T0-P 隔离 profile＋显式工具集；真实受控 send 被选择且无越权表项，不能仅插件 doctor 成功 |
| B03 | Hermes 身份/回执门槛 | 当前 Attempt 的可信映射、缺上下文拒绝、压缩/child 分流和回执重传未集成 | T0-P 先证正常作者；T6 fixture 证拒绝/幂等；未知原调用禁止自动重放 |
| B04 | Hermes 用量门槛 | 辅助 streaming/error/无父身份、hook 丢失时费用完整性不明 | T0-P 对账正常总量/coverage；T6/T8 验证缺失保留预约。总量不能核对就停止新调用 |
| B05 | Codex 冷恢复能力门槛 | 源码恢复工具定义，但安装版重启后 callback/待决 RPC 未验证 | T0-P 用确定性 fixture 恢复原工具并观察新回调；不能把继承 native child 的旧实验当作独立线程证据 |
| B06 | 两路径在途恢复门槛 | 对端接受后断线、原生终态与迟到费用的真实边界未验证 | T8 各一次已接受/未对账窗口，原业务 submit=1；分列 reconciled/safely_blocked/unsafe |
| B07 | 工具/来源边界 | 两边完整工具表、原生子树禁用、黑盒关键读取依赖覆盖尚未实证 | T0-P/T5/T6 固定实效表；关键源受控读，其他依赖标 opaque；无凭据/工具越权 |

这些是**进入相应实现/能力声明的门槛**，不是要求 T0 执行动态实验。B05 未解除可关闭自动恢复路径，但 B02–B04 连正常工作都无法满足时不能宣布 Hermes 接入成立。完整 read_set、严格金额硬限、exactly-once 外部副作用、任意私有推理/KV 迁移均不作能力承诺。

## T0 完成记录与交接

- [x] 工作区/安装入口/历史服务端版本分离，并记录实际观测方式。
- [x] 核对 Hermes manifest、register_tool、handler 身份及压缩/子树边界。
- [x] 核对 canonical Gateway 创建、提交、回执、取消、回放、恢复和 usage。
- [x] 核对 Codex 实验性初始化、动态工具、提交、终态、历史恢复与累计量。
- [x] 明确 stdio 进程所有权、原线程恢复、未决调用/费用处置。
- [x] 固定两个拟新增业务工具及接受合同；实效表未知项单独保留。
- [x] 为能力记录状态、来源、局限、阻塞 ID 与后续关卡；验证文档/JSON 引用一致。

执行记录：复用用户指定的 `multiAgent` checkout；本轮范围是 T0 文档核对，不创建产品 worktree、不执行 TDD/产品测试、不继续 T0-P。技能的连续执行要求受用户“只开始 T0”范围限制；这不是因动态验证缺失而放弃 T0。按计划仅提交这份报告与 JSON 清单，其他设计和历史实验不改。

后续 T0-P 优先处理 Hermes 正常身份/计费和 Codex 工具冷恢复 fixture；任何付费探针仍须在用户下一步执行指令内按已定软预算开展。本次新增付费模型实验 tokens 为 **0**，研究助手消耗不包含在此数中。
