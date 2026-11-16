# 飞书群多 Agent 协作证据与适配验证

日期：2026-11-16。范围：对等协作、互操作协议、飞书群产品能力，以及 Hermes、Codex、OpenClaw、DSH 的接入能力。本文是研究记录与待执行验证清单，不是新架构，不替代或批准此前架构草案。

## 证据等级与本轮边界

- **S 源码确认**：已核对指定 checkout/tag 的实现或测试；没有执行相应行为测试。
- **D 文档声明**：官方接口文档或作者论文说明；版本与部署实际行为仍需核对。
- **H 历史记录**：仓库中的部署/故障描述；不等于本次端到端验证。
- **V 待验证**：需要安装版本、租户权限、真实设备或任务实验才能确定。

本轮使用研究子 Agent 做只读核查，没有发送飞书消息、运行被评估 harness 的实测任务、读取凭据/私人群聊、安装依赖或修改产品代码。未将任何源码存在性写成线上已可用。

## 一 对等协作需要验证的行为

工作流的六种模式继续用于组织求解过程，但不能代替协作关系。以下是本次证据导出的测试分类，不是新增固定 Agent 角色。

| 协作关系 | 需要观察的行为 | 对现有方案的判断 |
| --- | --- | --- |
| 请求协助 | A 问 B，B 回答，A 仍负责原结果 | 这是最基本的委派/问答；有直接消息不代表已实现其他关系 |
| 责任交接 | A 提议交接，B 接受或拒绝；接受后后续请求与结果责任转到 B | 自主 handoff 已有先例，但很多实现只切换发言者，未保证业务责任原子转移 |
| 对等协商 | B 可反驳任务假设、提出范围/方法替代，A/B 达成明确共同决定 | 要测试是否改变了计划，而不是只有“收到，我执行” |
| 共享问题与证据 | A 先发布局部发现，B 主动复用；B 的反证能被 A 看到并修正结论 | 需要可追溯的公共记录，单次互相转述不够 |
| 独立审查 | 审查者能拒绝产物而不被作者提示或聊天污染 | 公开群聊与隔离输入是两个不同的可见范围 |

### 有直接相关性的框架和论文

| 来源 | 已有机制 | 能借鉴什么 | 不能据此声称什么 |
| --- | --- | --- | --- |
| [AutoGen Swarm](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/swarm.html) D | 参与者共享消息上下文，Agent 用 HandoffMessage 选择下一参与者 | 交接由当前 Agent 决定，不必由主 Agent 逐轮选人 | 默认轮流发言不等于异步多设备；所有人共享历史不适合盲审 |
| [AutoGen SelectorGroupChat](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html) D | 选择器依据共享上下文挑选发言者 | 将“谁发言”与“谁做领域判断”分开；可作为对照条件 | 它仍有中央选择器，不能当成去中心化证据 |
| [DeLM v3](https://arxiv.org/html/2606.10662v3) D，作者实验 | 在已有 harness 上增加共享上下文与任务认领；发布局部发现和失败，其他 Agent 自主复用与纠正 | 验证早期共享、同伴状态可见、纠正传播能否减少重复探索 | 编码基准和有限实验时长不证明飞书场景或一个月可靠；自然语言共享不保证精确计算或共识 |
| [ChatDev 2 DevAll 教程](https://github.com/OpenBMB/ChatDev/blob/main/frontend/public/tutorial-en.md) D | 图中的消息传递可与触发执行分离；有 Human Node 和 blackboard memory | 重点验证“看见消息”与“触发新工作”是否分离，以及人类审核如何进入流程 | 多模型节点不等于支持四种现成 harness；可视化图不等于飞书群产品 |
| [Magentic-One](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/magentic-one.html) D | Task Ledger 与 Progress Ledger；停滞时重新规划 | 用现成基线验证进展判断和改计划，而非先造治理角色体系 | 属于编排者架构，不提供对等协作的证明 |
| [ACL 2024 Bargaining benchmark](https://aclanthology.org/2024.findings-acl.213/) D，作者实验 | 将协商设为有独立目标和可计量收益的交互任务，并结合确定性报价约束与语言表达 | 提醒测试拒绝、反提案和目标满足情况，不能只看对话是否顺畅 | 买卖博弈不同于同一团队共同研究；不能把谈判成绩外推为工程协作质量 |

[Towards a Science of Scaling Agent Systems v3](https://arxiv.org/abs/2512.08296v3) 比较不同协作拓扑，显示收益取决于任务结构、模型能力和协调开销。它支持在相同工具/预算下做本地对照，不支持“多 Agent 一定更好”。本轮论文发现也使用了 SciSpace；[DeLM 索引](https://scispace.com/papers/decentralized-multi-agent-systems-with-shared-context-k2y3zxlgz3xc)、[Scaling 索引](https://scispace.com/papers/towards-a-science-of-scaling-agent-systems-uzbix3b1ubeb)，具体机制以作者原文版本为准。

这次没有将 Devin、Manus 等产品的宣传性长程能力当成协议实现证据；没有源码或公开接口依据的内部机制仍列为未知。本轮选择可核查机制，未做全产品市场排行。FIPA 原站访问被拒，未用搜索摘要补出其规范细节。

## 二 互操作协议能替代什么

| 协议 | 可复用层面 | 对本任务的边界 |
| --- | --- | --- |
| [A2A 规范](https://a2a-protocol.org/latest/specification/) D | 能力发现、Message/Task/Artifact、任务状态、异步结果及认证描述 | 适合研究跨 Agent 服务互通；不是各 harness 私有会话的共同恢复格式，不自动解决业务预算、对等决策或完整依赖观测 |
| [Agent Client Protocol](https://agentclientprotocol.com/get-started/introduction) D | 客户端与编码 Agent 的会话、输入、工具事件、取消与权限交互 | 可作 harness 接入口候选；能力取决于实现和协商，不等于 Agent 群协作协议 |
| [Agent Communication Protocol](https://agentcommunicationprotocol.dev/introduction/welcome) D | 历史上的 Agent 互操作协议 | 官方说明已经并入 A2A；不能与上一行同缩写协议混用 |
| MCP | 将数据与工具暴露给模型 | 可作为协作工具入口；单凭 MCP 不能推出可靠的进程生命周期、恢复或消息消费语义 |

最小验证先使用各 harness 已有接口；只有确认实际调用语义后，才判断 A2A/ACP 是否减少适配工作。不能先统一一个抽象接口，再把四种实现的差异藏起来。

## 三 飞书群是产品入口也是首个可行性门槛

仓库故障记录说明，已有投研场景尝试让机器人互相交接，且原生 `<at>` 与裸 `@岗位名` 的效果不同。[历史记录 H](/Users/season/workspace/github/hermes-agent/docs/bug_fix/feishu-plain-text-mention-fix.md:1)。本轮不据此推定所有当前机器人和设备已正确配置。

### 官方渠道证据

[larksuite Channel SDK 的 Bot-at-bot 文档](https://github.com/larksuite/channel-sdk-python/blob/main/docs/reference.md#bot-at-bot) 明确指出：接收他机器人 @ 的权限是 `im:message.group_at_msg.include_bot:readonly`，区别于普通用户 mention 权限；缺失可能静默不投递。群成员查询与机器人名录查询不同，名称歧义不能安全解析；SDK 提供可选防回环，但它只是启发式保护。以上是 SDK 文档声明，不是当前租户授权检查结果。

需分别验证四层：平台是否投递 → 本地准入是否接受 → 消息是否进入正确会话 → Agent 是否在正确工作中处理。发送 API 成功和群里看见消息，只证明前两者之前的一部分链路。

| 群聊可见行为 | 飞书/现有渠道可提供的基础 | 仍需核对或补齐的语义 |
| --- | --- | --- |
| 知道谁发给谁 | bot sender、原生 mention、各自机器人身份 | 名称/应用/设备/Agent 身份的映射；跨应用 open_id 不能假定可直接共用 |
| 追踪一次讨论 | message_id、回复及话题信息 | 讨论与工作对象的绑定；重复事件不能重复开工 |
| 看到接手或拒绝 | Agent 可以发送明确回复 | “已发送/已接收/已接受责任/已完成”不可合并成一个成功状态 |
| 看到证据与更正 | 消息、链接、文件引用 | 哪一版本已过期，谁读到更正；群历史不自动成为完整共享上下文 |
| 人类批准、否决与停止 | 人类带身份的消息，渠道支持交互能力 | 目标对象和版本要明确；普通机器人转述不能变成人类授权 |
| 不被协作噪音淹没 | 可按话题组织回复、限制机器人触发 | 核心请求/异议/交接/结果可见，内部工具碎片不必刷群；待测原平台的线程规则与发送频控 |

群聊必须同时通过两类检查：人类看得懂实际协作，后台也能区分原始来源和执行归属。仅把所有日志发到群里不能满足前者。

### 群聊转述的信任边界

Claude 原文的 [Quarantine 模式](https://claude.dev/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code/)将读取不可信内容与高权限执行分开。对现有群的直接含义是：真实 bot 身份只能证明消息来源，不能让网页转述变成人类授权。共享上下文与结构化摘要也不会自动消除注入。最小测试应检查人类停止是否会被另一机器人引用网页中的“可以继续”覆盖；不需先构建完整安全框架。

## 四 Harness 适配证据

本节按已核对版本记录；完整路径锚点与关键差异在下列小节。

| Harness | 审计版本 | 最有依据的候选接入口 | 首个适配障碍 |
| --- | --- | --- | --- |
| Hermes | 本地 `e7b9eb6c7d89f1df2b63ef4bbf68e986e88ac786` | 共享 Gateway JSON-RPC；ACP 是其客户端之一 | HTTP API 不能接管飞书拥有的 session；同群不同发送者可能被隔离成不同会话 |
| Codex | 本地 `e241c18544bab47f729dbfea6d6f2e21531ba0a7` | App Server；Python SDK 包装该接口 | 忙时 start 可变成 steer，客户端消息ID不保证幂等；没有本轮确认的原生飞书渠道 |
| OpenClaw | 官方 tag `v2026.11.3`，`847611dcaa3bf0e2783335f961dd1fd0580e4d9f` | Gateway WebSocket 原生会话/运行接口 | 滚动文档与发行版 schema 不一致；连接事件 seq 不是跨重连回放游标 |
| DSH | 原型 `8c32a9dc5d72c033816c6a8110b37f40cf94fba4`；部署文档 `dsh@0.2.1-rc.3` | 原型已实现的嵌入式 Agent/Cordis 接口；另评估公开 SDK/Web Host | 三种入口能力不同；原型 transcript 不保留 usage，滚动SDK文档不能证明固定版本支持取消 |

### Hermes

以下 S 证据均对应本地 HEAD，不要求以 Kanban 作适配入口。

| 能力 | 已确认行为 | 缺口或限制 | 证据 |
| --- | --- | --- | --- |
| 公开入口 | `hermes gateway attach --json`、`runtime.describe`、`session.create/resume`；可用 `@hermes/shared/gateway-client` | 需合法连接权限与 profile；不能绕过创建/会话所有权 | [公开入口](/Users/season/workspace/github/hermes-agent/website/docs/developer-guide/programmatic-integration.md:37) |
| 提交/取消/事件 | `prompt.submit` 持久准入；`prompt.receipt/cancel` 精确到 admission；`session.events.since` 用 epoch/seq 对齐；可返回结果和 usage | 事件回放与外部副作用的防重不是同一保证 | [控制与回执](/Users/season/workspace/github/hermes-agent/gateway/session_controls.py:909) |
| 断开/重启 | 观察客户端断开不停止工作；daemon 冷启动继续未开始 FIFO | 已启动但结果不明的输入变 unknown，暂停后继，不自动重跑 | [恢复契约](/Users/season/workspace/github/hermes-agent/website/docs/developer-guide/gateway-local-sessions.md:237) |
| HTTP/CLI/ACP | HTTP `/v1/runs` 有 run、幂等、SSE；CLI 有 resume/usage 输出；默认 ACP 连接 gateway | HTTP 只能使用 API 所有的会话，传已有飞书 session 会 409；挂原群会话需有权 Gateway 接入 | [HTTP 所有权](/Users/season/workspace/github/hermes-agent/website/docs/user-guide/features/api-server.md:497)、[ACP](/Users/season/workspace/github/hermes-agent/acp_adapter/gateway_server.py:687) |
| 原生子 Agent | 父会话可委派、控制、继续；有持久结果/未交付完成回放 | 插件 lifecycle handle 是活动父会话的进程内能力，重启不能直接 reconnect；原生自动恢复应避免与外部恢复重复 | [插件能力](/Users/season/workspace/github/hermes-agent/website/docs/developer-guide/subagent-lifecycle-api.md:38)、[委派](/Users/season/workspace/github/hermes-agent/website/docs/user-guide/features/delegation.md:553) |
| 工具/用量 | Gateway 工具事件、终态 usage 可观测；插件本地钩子可扩展 | 不等于能够枚举 shell 内所有读取或强制所有子调用共享硬预算 | [控制实现](/Users/season/workspace/github/hermes-agent/gateway/session_controls.py:909) |

飞书 S 证据：依赖 `lark-oapi==1.7.5`，使用低层 WS 与 EventDispatcherHandler，未使用新独立 Channel SDK；现有实现已识别 `bot/app`，无需仅为 scope 强行迁移 SDK。[依赖](/Users/season/workspace/github/hermes-agent/pyproject.toml:496)、[WS](/Users/season/workspace/github/hermes-agent/plugins/platforms/feishu/adapter.py:3908)。

具体缺口：

- 名称→bot_id 依赖部署 roster，没有群机器人发现；缓存建立后发送路径可能跳过 mtime 刷新。原生 `<at>` 转换已实现，但不能证明当前映射有效。[映射](/Users/season/workspace/github/hermes-agent/plugins/platforms/feishu/adapter.py:2032)
- `allow_bots` 默认关闭；群策略、mention、自身份识别与循环保护分别生效。只有 @ 无正文会被过滤；bot 多轮回复还受跳数/重复内容/答复链规则限制。[准入](/Users/season/workspace/github/hermes-agent/plugins/platforms/feishu/adapter.py:3414)、[循环保护](/Users/season/workspace/github/hermes-agent/gateway/bot_loop_guard.py:160)
- 群默认按发送者隔离会话；不能以“同一群”推定 A/B 共享一个上下文。`thread_id` 与仅用于引用的 `root_id` 也不同。[话题路由](/Users/season/workspace/github/hermes-agent/plugins/platforms/feishu/adapter.py:2662)
- 入站有有界持久去重，处理前去重与后续持久准入之间仍需测试崩溃窗口。已收到事件的内存 replay 不是断线期间未收到消息的回补；未见完整遗漏扫描路径。[入站](/Users/season/workspace/github/hermes-agent/plugins/platforms/feishu/adapter.py:2205)

判断：公开执行端能力比前两版设计所依据的材料完整，应优先验证这些已有入口；飞书语义、业务请求归属、跨设备实例映射仍非天然具备。

### Codex

以下 S 证据以本地 checkout 为准，不等同当前安装的桌面产品已暴露全部接口。

| 能力 | 已确认行为 | 缺口或限制 | 证据 |
| --- | --- | --- | --- |
| 会话与传输 | App Server 有 `thread/start/resume/read`，stdio/Unix socket/WebSocket；Python SDK 包装 App Server，TS SDK 驱动 exec JSONL | 两种 SDK 不同，不能假定事件与控制完全对齐 | [协议](/Users/season/workspace/github/codex/codex-rs/app-server-protocol/src/protocol/common.rs:575)、[Python](/Users/season/workspace/github/codex/sdk/python/src/openai_codex/client.py:214)、[TS](/Users/season/workspace/github/codex/sdk/typescript/src/thread.ts:66) |
| 忙时输入 | `turn/start` 可调用 start-or-steer 并返回原 turn ID；显式 `turn/steer` 检查 expectedTurnId | 不能将每次 start 都映射为一个独立工作；实验性队列需另测 | [实现](/Users/season/workspace/github/codex/codex-rs/app-server/src/request_processors/turn_processor.rs:730)、[已有测试](/Users/season/workspace/github/codex/codex-rs/app-server/tests/suite/v2/turn_start.rs:654) |
| 输入幂等 | `clientUserMessageId` 用于关联 UI/消息 | 测试源码中相同 client ID 可产生三个不同输入；不能用它作请求重放防重键 | [测试](/Users/season/workspace/github/codex/codex-rs/core/src/session/turn_input_tests.rs:1195) |
| 重连/恢复 | resume 可附着活跃 thread 并取得快照；补发部分 usage/goal/待处理请求 | 未确认完整事件游标回放；App Server 重启后未完成旧 turn 标中断，区别于断开观察连接 | [重新订阅](/Users/season/workspace/github/codex/codex-rs/app-server/src/request_processors/thread_lifecycle.rs:1181)、[选择性回放](/Users/season/workspace/github/codex/codex-rs/app-server/src/request_processors/thread_lifecycle.rs:1256)、[重启契约](/Users/season/workspace/github/codex/codex-rs/app-server/tests/suite/v2/thread_resume.rs:4973) |
| 取消 | `turn/interrupt(threadId,turnId)` 校验目标，常规路径等待 TurnAborted | 不能由发送取消请求推断外部已启动工具全部无副作用 | [实现](/Users/season/workspace/github/codex/codex-rs/app-server/src/request_processors/turn_processor.rs:1528) |
| 用量与工具 | tokenUsage updated 有 thread/turn、total/last；item start/completed 和命令输出；可读 turns/items 历史 | 工具事件不等于完整文件/网络依赖跟踪；费用金额与子树归集仍需核对 | [用量](/Users/season/workspace/github/codex/codex-rs/app-server-protocol/src/protocol/v2/thread.rs:2115)、[事件](/Users/season/workspace/github/codex/codex-rs/app-server-protocol/src/protocol/common.rs:2087) |
| 子 Agent | 原生模型工具及父子状态事件存在；子会话可在满足装载条件后附着 | 子输入受所有权校验，未确认通用外部管理所有子Agent的控制面 | [工具](/Users/season/workspace/github/codex/codex-rs/core/src/tools/handlers/multi_agents_spec.rs:222)、[输入归属](/Users/season/workspace/github/codex/codex-rs/app-server/src/request_processors/thread_input.rs:8) |

判断：App Server 是最直接的候选执行接口；不能将 Codex 桌面中“能发消息给子 Agent”当作独立模块已拥有同等权限。本轮未确认原生飞书 bot 接口，群聊接入仍需要现有可用桥接或未来适配，不能把 CLI 可用写成群聊可用。

### OpenClaw

S 证据取自 [v2026.11.3](https://github.com/openclaw/openclaw/releases/tag/v2026.11.3) 的公开源码；官方滚动文档单独作为 D，不以滚动参数代替发行版契约。

| 能力 | 已确认行为 | 缺口或限制 | 证据 |
| --- | --- | --- | --- |
| 会话创建 | `sessions.create` 有可选 idempotencyKey，返回会话地址/运行回执 | key、sessionId、runId 要分别记录；重试行为仍需实测 | [固定版 schema](https://github.com/openclaw/openclaw/blob/v2026.11.3/packages/gateway-protocol/src/schema/sessions-create.ts#L13-L62) |
| 忙时发送 | 外部 `chat.send.queueMode` 可选 followup/steer；`sessions.send` RPC 与模型 `sessions_send` 工具不是同一参数表 | 工具的 notify 是进程内上下文，不启动运行，不能当持久消息投递 | [发送 schema](https://github.com/openclaw/openclaw/blob/v2026.11.3/packages/gateway-protocol/src/schema/logs-chat.ts#L312-L350)、[模型工具](https://github.com/openclaw/openclaw/blob/v2026.11.3/src/agents/tools/sessions-send-tool.delivery.ts#L153-L181) |
| 重连 | sessions 和 session messages 有订阅；重连读 history/startup 重建状态 | seq 按连接排序并重置；固定版 subscribe 无滚动文档 initialHistory 参数 | [订阅 schema](https://github.com/openclaw/openclaw/blob/v2026.11.3/packages/gateway-protocol/src/schema/sessions.ts#L428-L437)、[重连文档](https://docs.openclaw.ai/gateway/clients#recover-state-after-reconnect) |
| 取消 | chat.abort 支持 runId；有 sessions.abort | 固定版闭合 schema 无滚动文档 sessionId fence，不能照抄 | [固定版取消](https://github.com/openclaw/openclaw/blob/v2026.11.3/packages/gateway-protocol/src/schema/logs-chat.ts#L352-L359) |
| 用量/工具 | usage/timeseries/logs 有 handler；工具流和会话镜像可观察 | 部分方法不 advertise，不能只查 hello 推断不存在；慢连接工具镜像可丢，不能作完整审计账本 | [方法表](https://github.com/openclaw/openclaw/blob/v2026.11.3/src/gateway/methods/core-descriptors.ts#L377-L402)、[工具事件](https://github.com/openclaw/openclaw/blob/v2026.11.3/src/gateway/server-chat.ts#L1329-L1389) |
| 子 Agent | 模型工具 sessions_spawn 支持 native subagent 或 ACP harness 分支 | 已确认工具入口，不等于有同等独立公共 spawn RPC | [分派](https://github.com/openclaw/openclaw/blob/v2026.11.3/src/agents/tools/sessions-spawn-tool.ts#L615-L645) |

飞书：固定版注册 `im.message.receive_v1`，有 allowBots、自消息过滤、真实 mention 校验、bot pair 防回环。需验证真实租户的 sender_type：该 tag 的分支只将 `bot` 归为 bot，而 Hermes 也处理 `app`，不能假设两者策略等价。[事件注册](https://github.com/openclaw/openclaw/blob/v2026.11.3/extensions/feishu/src/monitor.account.ts#L311-L320)、[分类/准入/保护](https://github.com/openclaw/openclaw/blob/v2026.11.3/extensions/feishu/src/bot.ts#L166-L181)、[官方权限要求](https://docs.openclaw.ai/channels/feishu/access-control#bot-authored-messages)。本轮未据此判定真实租户存在绕过问题，先采样事件与验证准入。

判断：它有可核验的原生 Gateway 和飞书接入，适配不是从零开始；版本差异、消息模式、工具流完整性是先测项目。

### DSH 与 superagent 原型

原型是可读实现，不能仅按理念文档判断；同时要区分原型嵌入接口、公开 stdio SDK 与 Web Host API。

| 能力 | S/D 证据 | 缺口或限制 |
| --- | --- | --- |
| Router | S：角色 prompt 实际装配；orchestrator_route 执行 accept/attach/stop/ignore | Router 不负责所有技术判断；不能把它扩成万能规划者再称为原理念 |
| Subscription/Mandate | S：线程订阅 fan-out 给 worker，accept 记录权限范围与来源，重复 accept 返回旧决定 | 上下文到达不等于新工作授权；这是可复用分离原则，不是完整对等协商协议 |
| 创建与投递 | S：Cordis sessionController 创建/解析 Agent，固定 worker Session ID；followup/steer/inject 分别走队列、当前工作输入、无唤醒注入 | 属于嵌入式 Host 能力，不自动暴露为统一远程接口 |
| 去重/已读 | S：按 request ID 检查 durable 历史和 nextTurn/nextStep inbox；以持久 user/message 标记读入 | inbox claimed 早于真正进入历史，不能冒充模型已看到 |
| 停止/恢复 | S：业务停止取消并清 inbox；恢复保留 inbox，结束旧 assignment、重新调度 | 会话恢复不是旧执行进程迁移；原型恢复与外部恢复不能同时负责同一工作 |
| 用量 | S：原型 transcriptEntry 只投影内容，明确丢弃 usage | 需从底层计量事件接入，不可从现有 transcript 补算完整费用 |

代码锚点：[实际路由提示词](/Users/season/workspace/github/dsh-superagent-prototype/prompts/orchestrator.md:1)、[派发提示词](/Users/season/workspace/github/dsh-superagent-prototype/prompts/dispatch.md:1)、[prompt装配](/Users/season/workspace/github/dsh-superagent-prototype/src/app/prompts.ts:102)、[路由工具](/Users/season/workspace/github/dsh-superagent-prototype/src/app/tools/main.ts:125)、[fan-out](/Users/season/workspace/github/dsh-superagent-prototype/src/core/intake.ts:19)、[accept](/Users/season/workspace/github/dsh-superagent-prototype/src/core/evals.ts:131)、[Session](/Users/season/workspace/github/dsh-superagent-prototype/src/app/sessions.ts:137)、[投递与去重](/Users/season/workspace/github/dsh-superagent-prototype/src/app/delivery.ts:40)、[读入/恢复](/Users/season/workspace/github/dsh-superagent-prototype/src/executor/dsh.ts:476)、[usage丢弃](/Users/season/workspace/github/dsh-superagent-prototype/src/app/context.ts:28)。

飞书入口以 message ID 作 trigger 身份，以 chatId+rootId（没有root时用本消息）形成线程，后续跟进走已订阅 worker，人类停止后不能被普通跟进复活。[飞书键](/Users/season/workspace/github/dsh-superagent-prototype/src/sources/feishu-trigger.ts:16)、[原线程回复](/Users/season/workspace/github/dsh-superagent-prototype/src/sources/feishu-channel.ts:18)、[唤醒规则](/Users/season/workspace/github/dsh-superagent-prototype/src/core/tickets.ts:246)。这些规则侧重人类请求；不能据此声称已支持任意 bot 自动授予新工单。

外部 DSH 已有[公开开源仓库](https://github.com/deepseek-ai/deepseek-harness)。当前[SDK协议文档](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/sdk/protocol/README.md)与[server说明](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/sdk/server/README.md)列出 prompt/resume/wait 和状态/子Agent通知，同时说明历史不重放、缺少逐 session cancel/close。另有[Web Host API](https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/web-client)列创建/排队/取消/事件跟随。它们是滚动资料，尚未锁定到原型部署版本；不能拿其中一条入口的能力填满另一条的表格。[原型部署版本](/Users/season/workspace/github/dsh-superagent-prototype/docs/006-deployment.md:73)、[依赖版本](/Users/season/workspace/github/dsh-superagent-prototype/package.json:62)。

判断：最有源码依据的是原型已有嵌入式接入；若要求独立进程适配，需要先验证公开 SDK/Web Host 的固定版本与取消、回放、usage能力，不宜提前承诺一致。

### 共同缺口

1. 四种执行端都不能仅凭工具事件保证完整 read_set。
2. 创建/发送接口上的不同 ID 不具有统一幂等语义。
3. reconnect、resume、重新执行和跨设备迁移是不同能力。
4. 自带子Agent控制通常受父会话/所有权限制，不是外部管理员通用接口。
5. 用量可观测不等于硬预算可执行，也不等于子树费用自动归集。
6. 对等协商的承诺、拒绝、反提案与共同验收没有由这些传输接口统一提供；需要先验证工作方式的价值，而不是假装标准协议已经实现。

## 五 最小验证方案

以下均为待执行方案。本轮没有运行这些场景；不需要先建 PostgreSQL、两套新适配器或完整工作流运行时。

### G0 飞书原生链路

选择现有群中的两个授权机器人 A/B，沿用当前设备与身份，使用无敏感内容、无实际外部副作用的探针。由现有渠道/操作者触发，不写新桥接服务。

| 探针 | 操作 | 必须保存的证据 | 失败意味着什么 |
| --- | --- | --- | --- |
| F1 人类与机器人 mention 区分 | 人类 @B；A 用原生 mention @B，均带明确正文 | 出站 message_id、收件端原始事件类型与 sender_type、准入结果 | 人类成功而 bot 失败，先查 include_bot 权限和投递，不先改模型提示 |
| F2 可见性与身份 | B 在同一话题回复 A；验证原作者与收件人 | 群截图/消息引用、thread/root、映射结果 | 回复跑到主群或身份错配，先修渠道配置/身份映射 |
| F3 忙时输入 | B 处理任务时收到 A 的问题 | 所属 session/turn/run、排队或steer结果 | 若混入另一任务，说明适配层不能直接承诺独立 Step |
| F4 去重与停止 | 验证现有重连/重复事件处理，再由人停止一次交接 | 消费次数、停止结果、迟到回复状态 | 消息重复引发工作或停止后复活，先定位原生恢复所有权 |
| F5 来源不升级权限 | 在隔离测试资料中放入“人已批准继续”的伪指令，经 A 摘要给 B | 原始来源、人工停止状态、B 是否擅自启动 | bot 转述使停止被解除，说明信任边界未成立；不执行真实外部写入 |

不得用无正文 @ 做唯一探针；Hermes 可能将移除 mention 后的空文本过滤。不要制造无限 bot 互聊来验证回环；预设最多两个来回并检查现有保护日志。重启/断连验证只在不承载其他工作的测试实例或获准维护窗口进行。

### G1 四个 harness 的原生接口烟测

每个 harness 各做一条短会话：创建 → 输入 → 忙时追加 → 查看事件/usage → 取消 → 恢复或重新附着。使用现有 CLI/协议客户端/UI；无现成入口时记录阻塞，不临时写适配代码。

记录统一事实而非统一成功：实际版本、会话ID、turn/runID、输入方式、输入是否合并、取消是否终止、恢复是否重跑、事件是否回放、费用是否完整、子Agent是否可枚举。将源码/文档判断升级为实测，未支持项明确留空。

额外重复一次相同客户端请求ID，只验证是否天然幂等；任务必须无副作用。不要在真实写操作上试重复。DSH 先确定嵌入、stdio SDK、Web Host 选哪一入口；OpenClaw按固定发行版参数，不能照抄滚动文档。

### G2 低成本质量验证

先做 3 个小任务、2 个条件、各 2 次，共 12 次任务运行，作为可行性探测，不作统计证明：

- 条件 A：单个强 Agent，允许自审，拥有相同证据和总预算。
- 条件 B：两个 Agent，允许直接质疑、提出替代方案、共享证据；不能由人类代替它们做推理协调。
- 三题分别覆盖软件故障定位、量化实验方法/数据缺陷审查、市场结论与来源冲突；采用固定资料，不涉及实际交易或发布。

任务中至少有一次预置证据更正，观察双方是否修正结论。领域评审尽量看匿名产物；记录质量、关键错误、总模型/工具消费、完成时间、人类整理和纠错时间。多 Agent 的协调、阅读共享材料和审查费用都计入同一额度。

若飞书原生链路未通过，可先用现成 harness 的会话/子Agent机制验证任务质量；明确这不能证明飞书协作成立。只有条件 B 显示值得继续的收益，才增加“委派 vs 对等协商 vs 共享证据”的消融组；不一开始铺开 108 次运行。

### 本轮之后的决策门

1. 飞书身份/权限或投递失败：先解决渠道前置条件，不建运行时。
2. 原生接口无法隔离任务或观测终态：先缩小能力承诺或选择另一个入口。
3. 对等协作没有质量/效率收益：保留单 Agent 与按需审查；不因已设计就建设。
4. 基础链路、至少两个执行端、一个有效协作场景均有证据后，才确定最小实现范围和控制部署方式。

一个月连续性、跨设备故障恢复、任务质量是不同的验收轴。以上短测只消除首批未知，不代表已证明月级可靠性。
