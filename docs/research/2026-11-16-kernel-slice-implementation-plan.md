# 第一个协作运行时内核切片 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 本次只交付计划；这些步骤尚未执行。后续建议单执行者顺序推进，避免每项任务重新装载全部研究上下文。

**Goal:** 在独立模块中完成单机、一个 Mission/Collaboration、两个固定成员槽位的 Hermes ↔ Codex 协作，证明有界规划、直接质疑/回复、证据接受、人工控制和重启对账可共同工作。

**Architecture:** 一个本地控制进程，SQLite 是 journal、输入、消息、预算与当前状态的唯一权威；产物按 hash 保存。规则 Router、阶段校验、上下文、准入和恢复共用执行记录，模型仅负责获授权的规划和工作。两个本地适配器分别连接 Codex AppServer 和 Hermes Gateway/外部薄插件，不引入远程节点代理。

**Tech Stack:** 建议实现默认：独立 Python `>=3.11,<3.15` 包，`asyncio`、`sqlite3`、JSON/JSON-RPC、本地产物目录和 Unix domain socket；Hermes Gateway 使用 `websockets>=15.0.1,<16`（以已有探针的客户端行为为基线，T0 再核对安装版兼容性）。单元/契约验证用标准库 `unittest`，不先引入 Web 框架、ORM 或工作流引擎。实现语言、SQLite 和单控制实例仍是提案默认，不冒充已确认部署事实；更换语言不改变本计划的协议与验收。

**Spec:** 已提交的 V3.2：`24371f8dbb`；证据迁移：`cec05f7746`。规范入口为 [000–008 九篇文档](README.md)，主要执行依据是 [003 Execution](003-execution.md)、[007 Architecture](007-architecture.md) 和 [006 Deployment](006-deployment.md)。本文件是任务分解，不建立第二套规范；冲突时先修订所属规范，不静默改变契约。

**Revision:** 2026-11-16 审查后修订。适配探针前移；Codex 采用显式 stdio 冷恢复路径；G-D 与协议内核分别决策；36 万预算按校准后的路径准入，三组使用相同评分额度；加入真实已接受、未对账窗口的恢复验证。以下全部仍是待执行计划。

## Global Constraints

以下引号内容直接沿用 V3.2；任务中的数字限制另标为本轮验证建议。

- “当前文档在Hermes的`docs/research`维护，运行时仍通过外部适配层接入，不加入Hermes核心。”
- “每个模型调用有Step/Attempt归属，包括路由、规划、评审、摘要和恢复。”
- “Step先属于Mission，Workflow只编排和引用Step。”
- “内核切片不启用模型Router，归属不明由人澄清”。
- “内核切片不使用busy steer，也不提前把下一输入排进harness；先在运行时排队。”
- “摘要与评审读取固定快照，不能推进业务收件箱消费游标。”
- “暂停跨会话、进程和设备恢复持续有效；bot消息、数据更新、超时和无人回复均不能解除。”
- “首版承诺软停止：到限后关闭新增准入并请求取消，继续收集迟到费用。”
- Hermes 会话内保持实际 system prompt、工具和 skills 前缀稳定；新增事实追加到输入，工具能力变化走新绑定，不修改 Hermes stock prompt/tools。
- 首次执行前按实际 checkout/安装版本再读适用的 `AGENTS.md`。Hermes 如需另行获授权的产品改动，测试必须用 `scripts/run_tests.sh`；本计划不安排这类改动。
- 所有历史实验、哈希清单、诊断脚本保持冻结。后续新样本另建目录；不运行会覆盖历史结果的旧汇总脚本。
- 本次不创建产品仓库、不安装插件、不启动付费模型、不重启现有 Gateway，不提交或推送新计划。

## Review Focus

这五种输入容易在正常路径以外破坏切片；已分别加入对应任务的行为验收。

1. 同伴先回复、原 turn 后结束：保存回复但不同时启动第二 turn；T3、T7 检验。
2. Hermes 压缩换 session、子 Agent 共享 conversation：不能认错作者，也不能回退到默认成员；T0/T0-P、T6 检验。
3. 对端接受输入而本地没有 turn ID，或控制器退出带走 stdio 服务：保持 unknown，不能把改计划/换会话当作重发许可；T0-P、T3、T5、T8 检验。
4. 已 verified 的依据静默变化或断链：保留历史验收，但阻止依赖旧依据的新派发和验收；T4、T8 检验。
5. usage 重复、重置、辅助调用未覆盖：不能少算、重复算或重启清零；T2、T5、T6、T8 检验。

---

## 1. 交付边界与先后顺序

**先验证最短接入路径，再建设内核；质量筛查提前开展，但不作为协议内核的硬门控。** 保留 T0–T8 编号以便追溯，新增前置任务 T0-P。先验证风险较高的 Hermes 插件身份/用量，再验证 Codex 工具/恢复入口；正式适配器仍先 Codex、后 Hermes。

| 顺序 | 交付 | 继续的条件 |
|---|---|---|
| T0 | 两个适配器的静态能力清单，尤其 Hermes 身份/回执/usage 缺口 | 公共路径存在；无法满足的能力明确阻塞或降级，不用私有核心补洞 |
| T0-P | 不依赖完整内核的两个最短兼容性探针；先无付费协议 fixture，再各一个短真实任务 | 正常工具回调身份、原始回执和费用总量可核对；失败先限制对应接入，不先实现阶段引擎 |
| T1 / G-D | 校准后冻结一题三组、相同评分额度 | 报告有改善、无改善、题目饱和、预算内未完成或不可比；后三类均不自动阻断 T2–T8 |
| T2–T3 | 最小持久账本、直接消息、准入/暂停及 fake harness 闭环 | 先让一条请求/回复有唯一执行和费用归属，不先建完整阶段功能 |
| T5 → T6 | 将已验证路径接入真实内核，先 Codex 后 Hermes | 适配器复用 T0-P 协议证据；集成用 fixture，真实集成验收合并到 T7，不各重跑付费探针 |
| T4 | 在上述小闭环上补证据接受、检查点和有限阶段 | 从一个具体阶段开始；不新增通用解释器或独立治理角色 |
| T7 / G-A | Hermes＋Codex 的一个真实协作阶段 | 直接正文、平级工作、规划和证据接受在同一账本闭环 |
| T8 / G-B | 控制进程重启及故障恢复 | 不盲重发、不丢暂停/预算/未知项；与 G-A 合成首个切片验收 |

执行依赖是 `T0 → T0-P → T2 → T3 → T5 → T6 → T4 → T7 → T8`；T1 的题目准备可提前，付费筛查在 T0-P 校准后、完整内核建设前优先安排。T1 没有结论时停止该实验扩样，记录收益未知；协议链仍按既有需求、接入证据和剩余额度推进，不重新索取此前已给出的方向授权。若协作无额外收益，减少默认协作频率，不能删除双成员直接通信/暂停/计费/恢复验收。只有实际身份、权限、费用或接受边界不可安全处理，才阻断对应协议路径。三次小样本不是统计显著性证明。

首个可运行中间里程碑是 T2/T3/T5/T6 的“请求→原文回复→账本→暂停”，仍不叫完整内核切片。T4/T8 补齐后才能验收 G-A/B。自动“两个检查点无进展后调用诊断 Agent”的建议策略后移；本切片保留进展事实、下一验证、人工暂停和无事件零模型调用。

**此切片不交付**：真实飞书群桥、第二设备、交接、小范围订阅、模型 Router、OpenClaw/DSH 动态接入、任意脚本/通用工作流模板、常驻治理 Agent、HA、严格金额硬限。它们仍在完整首版/G-C 或后续范围内，不因本计划而删除。月级声明另需 G-E 的真实 72 小时 → 7 天 → 30 天证据。

## 2. 文件与模块划分

拟在后续实施时新建独立目录 `/Users/season/workspace/github/collaboration-runtime`，本文记作 `R/`；目前没有创建。仓库名只是工作默认，确定位置后统一替换 `R/`，不能把这些文件写进 Hermes 核心。Hermes 薄插件与适配器同仓维护，按公开插件机制安装到专用测试 profile。

| 计划文件，相对 R/ | 责任与边界 |
|---|---|
| `pyproject.toml`、`README.md` | 包入口、受支持版本、测试/启动说明；随 T2 创建，不单独做脚手架阶段 |
| `src/collab_runtime/contracts.py` | 明确 ID 类型、版本、状态、消息/输入/回执/结果和端口 DTO；字段遵循 007，不放数据库或模型调用 |
| `src/collab_runtime/store.py`、`schema.sql` | 显式事务、唯一约束、版本比较、journal/current state/outbox 同库更新；迁移版本记入库 |
| `src/collab_runtime/budget.py` | 预约、逐响应或累计差额结算、coverage、不确定费用和软停止 |
| `src/collab_runtime/runtime.py` | 程序启动 Mission/默认 Collaboration/planning Step，串接模块；不承载另一套状态机 |
| `src/collab_runtime/execution.py` | 准入、领取、结果、等待、控制变更及替代链检查；唯一受控派发路径 |
| `src/collab_runtime/messaging.py` | 已知对象直达、请求幂等、平级 Step、原文与回复关联、消息消费；不调用模型 Router |
| `src/collab_runtime/context.py` | 证据/Decision、按 hash 产物、依赖失效、执行包和检查点；不裁决研究真假 |
| `src/collab_runtime/phase.py`、`prompts/lead.md`、`prompts/worker.md` | 有限阶段/结构化结果校验与角色指令；不运行模型生成的代码 |
| `src/collab_runtime/adapters/base.py`、`codex.py`、`hermes.py` | 同一语义端口的能力报告、绑定、提交、观察、查询、取消；保留原生差异 |
| `integrations/hermes/runtime_bridge/{plugin.yaml,__init__.py,tools.py,usage.py}` | 外部插件 manifest、`register(ctx)` 公开入口、工具处理器和 usage 观察桥；T0 复核安装版支持情况 |
| `src/collab_runtime/local_api.py`、`__main__.py` | 最小本地操作入口与插件回调入口，状态/消息事件查询；没有 Web/飞书 UI |
| `src/collab_runtime/recovery.py` | 重启读取检查点、查询未决绑定/Attempt/费用、保守恢复准入；不重放模型调用 |
| `tests/support.py`、`tests/fixtures/`、`tests/test_*.py` | 可控制接受边界、终态、计数器和故障的 fake harness；生产端口契约测试 |
| `evals/kernel/` | 后续新建小规模实验配置、原始观察、盲评分与汇总；不是产品运行路径 |

T0-P 的一次性诊断文件先放本文旁的 `kernel-slice-validation/preflight/`，不需要 R/、完整数据库或阶段引擎。记录最小测试 Mission/Step/Attempt、调用意图、原始回执和 usage；重启不自动重发。它是研究探针，不宣称具备运行时恢复保证；T5/T6 复用经核对的协议事实和用例，不将探针账本变为第二套生产权威。

一个进程、一套库、少量模块即可；这些文件不是独立服务。`Store` 拥有事务，领域模块通过同一个工作单元操作；适配器不直接写表，不能私有地调度续跑。产物先写临时文件、校验 hash 后原子落位，再提交引用；中途留下的未引用文件可以回收，已引用文件不能缺失。

### 共用类型和接口约定

以下是计划中的接口签名，不是当前已存在的 API。所有类型在 `contracts.py` 定义；ID 使用不同的字符串别名，时间使用带时区时间。错误返回统一 `Rejected(code, details)`，不靠异常文本驱动状态机。

| 类型族 | 必须携带的信息 |
|---|---|
| `MissionContract / MemberSpec / ControlCommand / Principal` | 001/002 的合同、两成员能力、操作者认证来源及预期版本；Principal 来自受信入口，不接受正文自报 |
| `WorkSpec / StepRef / PhaseProposal / ValidatedPhase / WorkerResult` | 稳定工作引用与 revision、有限动作/条件/依赖、Owner/门槛/限额、结构化结果和等待引用 |
| `MessageDraft / MessageReceipt / ToolOrigin` | 007 消息字段；回执含原 request/message ID；ToolOrigin 含受信 binding/native IDs 和观测来源 |
| `InputSet / Admission / DispatchClaim / SubmissionReceipt` | 不可变 payload/hash/消费引用、Attempt/预约/intent、领取版本、接受状态与原生 ID |
| `BindingSpec / BindingReceipt / BindingRef / NativeEvent / NativeState / CancelReceipt` | 逻辑成员及实际配置、原生身份、事件键/epoch/游标、接受与终态证据；未知是显式状态 |
| `UsageObservation / BudgetState` | 逐响应或累计模式、scope/epoch/sequence/baseline/coverage、实际/预约/未知额度；两种来源不重复相加 |
| `EvidenceRef / DecisionDraft / DecisionRef / ContextPacket / Checkpoint / RecoveryReport` | 对象版本/hash/可用性、接受者及依据/条件、三层上下文、恢复事实与阻塞原因 |
| `CapabilityReport / RuntimeConfig` | 实际版本、模型/权限/skills/tools 指纹、supported/unsupported/unknown、来源证据级别；状态目录与测试配额 |

`HarnessAdapter` 统一异步端口：`describe() -> CapabilityReport`、`ensure_binding(spec: BindingSpec) -> BindingReceipt`、`submit(claim: DispatchClaim, input_set: InputSet) -> SubmissionReceipt`、`observe(binding: BindingRef, cursor: str | None) -> AsyncIterator[NativeEvent]`、`query(binding: BindingRef) -> NativeState`、`cancel(binding: BindingRef, attempt_id: AttemptId) -> CancelReceipt`、`close(binding: BindingRef) -> NativeState`。缺原生身份的 binding 也可传入查询，结果允许 unknown，不能为了符合端口而重新创建。

### Codex 传输、进程所有权与恢复合同

首切片选 **运行时管理专用 AppServer 子进程，经 stdio JSON-RPC 连接，使用独立且持久的 `CODEX_HOME`**。不连接用户当前桌面服务，不新增独立常驻代理。绑定中记录二进制版本、进程实例身份（不能只凭 PID/argv）、状态目录、thread/turn ID、配置/工具指纹、usage 基线和接受证据。

1. 每次启动服务均先 `initialize` 并声明 `capabilities.experimentalApi=true`，完成初始化握手，再使用 `thread/start.dynamicTools`；不支持则报告 unsupported，不静默省略工具。字段及门控依据：[thread.rs](/Users/season/workspace/github/codex/codex-rs/app-server-protocol/src/protocol/v2/thread.rs:147)、[message_processor.rs](/Users/season/workspace/github/codex/codex-rs/app-server/src/message_processor.rs:1043)。冻结实际二进制与实验性 schema，不能只使用删去该字段的稳定 schema。
2. stdio 断开可能触发单客户端服务退出，见 [lib.rs](/Users/season/workspace/github/codex/codex-rs/app-server/src/lib.rs:1241)。控制器重启先确认旧子进程已退出；若仍存活且无法重新接管 stdio，仅可停止可证明属于本运行时的隔离子进程并等候退出。无法证明进程归属/结束则阻塞，不同时启动第二个同状态目录的写者。
3. 然后以原状态目录启动新服务、重新初始化，用已保存 `threadId` 调用 `thread/resume`，查询原 turn/历史和 usage。恢复历史不是 `turn/start`，不能自动重送旧 payload。已有 [Codex 冷恢复 fixture](g0-g2-2026-11-16/codex-dsh/README.md)仅证明局部历史恢复，不证明工具回调和在途计费全部可恢复。
4. 核验恢复线程的工具可用性、配置/权限与回调归属，再允许新 turn。T0-P 用确定性 Responses fixture 验证原动态工具在新服务中仍能产生可识别回调；不能仅凭同 thread ID 宣称恢复成功。不支持保留工具时禁用该自动续跑路径，不靠新建 thread 绕过原 Attempt。
5. 旧 turn 的终态、消息处置和费用分别对账。服务已退出不等于 provider 没执行或已算清费用；`interrupted` 也不证明原输入未提交。无法定位原 turn/接受情况时保持 unknown；累计计数重置时核对 scope/epoch/coverage，原预约保留，不能将差额填零。

Hermes 路径则恢复到隔离 profile 的既有 Gateway；只重启独立控制器，不重启用户现有 Gateway。两条路径分别记录进程恢复、会话恢复、工具恢复和业务恢复结果，不能用一个“resume 成功”覆盖全部。

## 3. 本轮实验额度和停止规则

**新增实验建议总预算：360,000 total tokens，分阶段软停止。** 本计划不启动调用；历史已花费不挤占该新增额度，也不隐藏在新结果里。总量定义 `input + output`，cached 是 input 的子集，reasoning 是 output 的子集，不重复相加。实际金额只有在可核对模型/价格和账单时另列。

| 阶段 | 建议子预算 | 最大样本/用途 |
|---|---:|---|
| T0、各任务的离线/协议 fixture | 0 付费模型 tokens | 包括真实 AppServer 接确定性本地 Responses fixture；不把写测试所耗助手 tokens 算作零 |
| T0-P 最短适配探针与校准 | 60,000 | Hermes 30,000、Codex 30,000；各一个最短 send→回执→结束，不同时堆叠 read/多轮协商 |
| T1 / G-D | 150,000 | 一题三组各一次，共同额度 B＝50,000；组内全部成员、协调、审查、修订和失败累计 |
| T7 / G-A | 90,000 | 一个真实混合阶段，兼作 T5/T6 集成实测；校准后预检完整最短路径，不另跑两次单适配器实验 |
| T8 / G-B 真实补充 | 40,000 | 每条路径最多一个短新 Attempt，覆盖已接受/未对账窗口；重启/查询应不额外调用模型，尾账仍计入 |
| 失败与诊断预留 | 20,000 | 最多一次有明确修复且费用估算可容纳的补跑；不是必须补跑一次，不能把调试费用另藏 |
| **合计** | **360,000** | 未使用额度保持未使用，不自动扩大样本/角色/步骤 |

预算依据而非成本预测：[旧三消息实验](g0-g2-2026-11-16/boundary-validation/messages/README.md)用了 100,110 tokens、8 次模型用量增量；[短资料直通组](g0-g2-2026-11-16/superagent-pilot/README.md)为 33,697；[长资料实验](g0-g2-2026-11-16/superagent-long-pilot/README.md)单样本约 16,689–27,301。因此 90,000 的新 G-A 不是照搬旧路径即可达成的保证：只有校准后的最短路径预计可容纳才开跑，否则先离线缩短无效控制往返或记录预算内不可执行，不追加样本追求通过。

这是新增实验总池，不是完工估算。T0-P 后、T1 第一组开始前，允许依据已记录校准结果在未支出/未承诺额度间修订一次预算矩阵；须同时记录各项旧值/新值、原因和合计，不能超过 360,000 或占用已发生/未知费用。调整 G-D 时三组 B 同步变化。冻结后不根据已看到的组间结果调额度，不私自从别组借款；未分配到可行路径的任务标待验证，G-D 未完成仍不阻断协议内核。

具体操作约束：

- 真实探针默认全局最多 **1 个在途模型 Attempt**，两个成员按需交替。这个成本控制不减少两个逻辑成员，也不把对等协商改成委派；多 Attempt 竞争用 fixture 验证。
- **取消统一每 Attempt 20,000 的下限。** T0-P 首次探针先按该 harness 的整个 30,000 子额度预约，仅做一个最短任务，结算后释放剩余。后续按同配置/角色/上下文规模的校准记录估算完整 Attempt，包括预期 provider 请求数、每次输入（缓存也计）、输出、工具续跑和辅助调用。建议预约 `ceil(1.25 × max(同类已测总量, 当前路径估算量))`；1.25 是可修订的保守系数，不是统计上界。配置/路径不可比则不套用旧数，先 fixture 分析或保留未验证，不能为准入而调低估值。
- 每阶段开跑前列出最短成功路径的 turn、预期内部请求、逐 Attempt 预约与预计结算；总池和阶段都能容纳才开始。每次实际准入重新检查“已用＋未决预约＋本次预约”，并保留后续必需步骤的估算空间，避免必需修订无法开始。分支超出估算或预算不足记 `budget_incomplete`，不计为答错，也不默默给少跑的条件更高质量评价。
- 预约是会计预留，**不是** provider 硬限；模型仍可能多次续跑。只能使用适配器实证支持的限制，记录在途 overshoot。费用不确定时保留预约，不能拿校准估计冒充已知实际用量。
- G-D 的交互限制：单 Agent 最多 2 个受控 turn；一次审查最多“初稿→审查→修订”3 个；协商最多 4 个。所有工具后模型续跑另记录 provider 请求数，不能只数 turn。
- G-A 最短路径为 planning→A 发请求并 waiting→B 原文回应→A 处理并交付，预计 4 个受控 turn；确需补证时最多 6 个（含规划和格式修正）、3 个业务 Step、2 次同伴请求、20 分钟。上限不是承诺都能跑满，开跑前须预算预检；无效提案最多修正一次且仍计费。该配置不是 V3.2 的永久系统上限。
- 发现总量无法对账、未知费用范围无法收敛或身份不唯一，立即停止该路径新调用。断线期间保留预约，迟到用量继续入账；累计达到阶段停止线就停止新增、请求取消并收集尾账。
- 同一故障不反复付费试错；先定位并用 fixture 复现，通过后才用预留补跑一次。若在途调用突破 360,000，报告实际总量及 overshoot，停止剩余实验，不称“预算内完成”。
- 本轮研究/实现助手和外部评审的 tokens **另表**记录，不包含在 360,000 模型实验预算里；不可观测时明确 unknown，不承诺整个工程总消耗上限。默认不为每个任务派一轮模型评审。

每次样本保存：样本/条件、版本与实际配置 hash、输入/产物 hash、Step/Attempt/native IDs、input/output/cached、计数基线/coverage、turn 数与可观测 provider 请求数、规划/工具续跑/恢复/失败归属、墙钟时间、质量评分、召回错误、unknown、人工介入次数/耗时。没有明细则标 coverage，不把聚合差额拆成虚构请求；无实际账单时金额标 unknown。

### G-D 公平对照与超线产物

三组共同主要停止线为冻结后的 B（初始 50,000），相同模型/推理设置、原始资料、有效权限/工具/skills 和评分标准；调用拓扑允许不同，全部成员成本按组累计。所有组的新会话条件一致，不把前组解题历史带入后组；模型缓存冷热仍需记录，不能宣称完全控制。

- 运行前固定允许交付的产物形式和编号；每份可评分产物必须完成、持久化，并能关联到费用已结算的 Attempt/模型响应。不评分流中的半份答案或一个尚未结束的工具往返。
- 只将“该产物完成时、组内截至此时的累计实际成本 ≤ B”的最后一份合格产物纳入预算内评分。usage 延迟时等尾账再判，不凭到达顺序假定更便宜；若只有 turn 聚合量，则整 turn 结算后判断，不倒推虚构分项。
- 一次响应将累计量从 B 以下跳到 B 以上，其产物只列为超线探索结果，主要比较采用之前合格产物；没有此前产物则 `budget_incomplete`，质量分为 N/A，并单列完成率/可用性，不与“0 分错误答案”混为一谈。费用归属无法确定则 `cost_unknown`，不纳入公平质量结论。
- 全部组按同一规则停止新增准入和收集在途尾账；主要结论同时报告质量、预算内完成情况、关键错误和实际总量，不只比较成功样本。已超线的答案可保留分析，不能把额外预算所得改善归为同预算收益。
- 一题一轮只形成筛查结论。单组满分可停止其余组以省成本，但记录 `saturated/inconclusive`；不能将未运行组当作被击败，也不能据此停止 G-A/B。若三组最短路径不能在同一 B 内预检通过，先报告预算设计不可行而不是启动一个注定少跑步骤的比较。

离线评分验收例（B＝50,000）：

| 已结算的产物/用量 | 主要评分选择 |
|---|---|
| 完整产物 A 在 42,000；修订产物 B 在 54,000 | 评 A；B 只列超线结果，总消耗仍记 54,000 |
| 只有一份完整产物，在 54,000 | budget_incomplete，质量 N/A，预算内完成为否 |
| 产物先到，usage 暂报 48,000；尾账确认其完成已花 52,000 | 不按 48,000 评分；回溯选择此前合格产物或 N/A |
| 产物完成，累计量存在无法核对的缺口 | cost_unknown；不填零，不进入公平质量结论 |

## 4. 分任务实施步骤

下面命令均是**未来实施命令**。`python -m unittest` 在独立 R/ 的已激活隔离环境中执行，测试目录使用标准库 discovery；不要假设宿主机已有 `python` 别名。它不是 Hermes 的测试命令，不在 Hermes 中绕过 `scripts/run_tests.sh`。所有提交仅限该任务文件，本计划不授权推送。

### T0：冻结适配合同，先排 Hermes 风险

**Files:** 未来在本文所在目录新增 `kernel-slice-validation/adapter-preflight.md` 和 `capability-baseline.json`；只读 Hermes/Codex 源码及已有实验，不创建 R/。

**Interfaces:** 消费 [007 两条实际适配路径](007-architecture.md)；产出 `CapabilityReport` 对应字段的静态基线，包括 installed/source 版本差异和每项停止原因，作为 T5/T6 的输入。

- [ ] 记录实际 checkout 与安装版、公开入口、工具注册方式和专用测试 profile 的隔离方案；不读取或输出真实凭据值。
- [ ] 核对 Hermes `ctx.register_tool` 的真实 manifest/handler 形式，逐项记录 `session_id/task_id/conversation_id` 来源，确认普通 handler 不假定 `tool_call_id`；把缺绑定、压缩换 session、共享 conversation 的子调用列为必拒绝或待核验案例。
- [ ] 核对 Gateway 的 create/submit/receipt/cancel/events/resume 以及公开 usage hooks；说明哪些仅源码可见、哪些安装版已有证据、哪些仍缺实际覆盖。
- [ ] 核对 Codex `thread/start`、dynamicTools、`item/tool/call`、`turn/start/completed`、read/resume/interrupt 和累计 usage 字段；保留“clientUserMessageId 不提供原生去重”的限制。
- [ ] 记录 Codex 实验性 schema/初始化开关、独立状态目录、专用 AppServer 的进程所有权与 stdio 生命周期；明确“控制器重启→确认旧服务退出→新服务恢复原线程”的步骤，不假设旧服务存活或工具自动恢复。
- [ ] 为后续插件选择最小固定工具表：`collab_send`、`evidence_read`，以及角色结果的固定结构化文本格式。Owner 的决定由其结果提案进入运行时校验，不增加通用高权限控制工具。记录无法实际裁剪的工具，不用提示词假装裁剪成功。
- [ ] 人工核对每项都有来源路径/版本、supported/unsupported/unknown 和验收任务；若身份或费用的公开路径确实缺失，记录 blocker，停止对应适配承诺。完成后仅提交新能力清单。

**验收：** 静态可行不冒充 tested。不动态测试 OpenClaw/DSH，不动正在使用的 Gateway。Hermes 的历史同进程 resume 不等于冷恢复。

### T0-P：先跑最短适配探针，不等待完整内核

**Files:** 未来新增本文旁 `kernel-slice-validation/preflight/{protocol.md,calibration.json,probe_codex.py,probe_hermes.py,fixture_responses.py,observations/}`，以及 `hermes_probe_plugin/{plugin.yaml,__init__.py,tools.py,usage.py}`。只做诊断所需最小入口，不创建产品 R/；这些文件本次也不创建。

**Interfaces:** 消费 T0 的能力/版本基线；输出各 harness 的正常工具回调、身份与原始回执样本、usage coverage、实际输入规模/工具续跑费用、Codex 冷恢复的 0 付费 fixture 记录。`calibration.json` 为每种已测配置保存配置 hash、任务路径、受控 turn 数、内部请求数、input/output/cached、总量和局限，供 T1/T5–T8 复用。

- [ ] 先冻结测试 Mission/Step/Attempt、原文及稳定 request_id；用最小文件记录保存调用前意图、输入 hash、native ID、回执和 usage。任何回执未知停止探针并留档，不自动重放，不把一次性探针当产品恢复实现。
- [ ] Codex 先用真实隔离 AppServer＋本地确定性 Responses fixture 验证初始化能力门控、dynamicTools 回调和累计计数，再关服务、用相同状态目录恢复原 thread，确认工具还可调用、回调归属正确、history 查询不调用 provider。fixture 中调用 provider 是本地合成响应，真实模型 tokens 为 0；这一条在途/工具恢复的协议检查不替代 T8。
- [ ] Hermes 先以公开插件装载/受信上下文样本验证 schema、注册和权限边界，只有这些检查通过才安排真实短任务。后续获授权执行时使用隔离测试 profile，插件仅向本地探针收件端写入消息，不接真实群聊。
- [ ] 依次跑 Hermes、Codex 各一个短真实任务：关键证据内联，只调用一次 `collab_send` 并结束，收件端是探针，不启动第二个模型。各有 30,000 软预算；调用前预约该探针全部子额度，未知尾账保留。不把 evidence_read、重复发送、压缩、协商同时塞进这一个探针；这些先由 fixture 验证，必要真实读取合并 T7。
- [ ] 原始记录须证明回调作者唯一映射到受控执行、正文/ID 未改写、工具回执和 terminal 可观察、实际总量可核对；否则暂停该适配路径。仅记录“注册成功”或模型说“已发送”不能通过。
- [ ] 依据校准列出 T1/T7/T8 每条最短路径的 turn/内部请求/预计总量和预约表。新增读取工具或更长资料的路径需单列增量/不确定性，不直接照搬最短 send 探针成本。冻结预算修订（如有）和 G-D 规则；探针失败先离线定位，只有明确修复且预留可容纳才补跑一次。
- [ ] 保存和提交脱敏观察/脚本/校准。T5/T6 不再重复这些付费探针；它们验证接入真实内核的行为，最终真实集成覆盖归 T7/T8。

**停止边界：** 安全身份/正常路径费用不可核对会阻断相应适配承诺；某恢复能力不支持只关闭该能力并标注。G-D 题目难度和得分不参与这项接入判断。

### T1：先跑一题三组质量筛查（G-D）

**Files:** 未来新增 `kernel-slice-validation/quality/{protocol.md,fixture/,rubric.json,verify_scoring.py,results/}`，置于本文旁；此阶段不依赖 R/ 或数据库。

**Interfaces:** 消费 T0/T0-P 的实际模型/工具配置及成本校准；产出一次筛查的冻结资料、共同 B、逐组原始 usage、质量/错误/完成状态表、默认协作策略建议。T1 不输出协议内核的通过/禁止建设决定。

- [ ] 先制作一个虚构市场数据口径研究任务，资料不超过约 24 KiB：包含统计截止、单位、分母、分组重复、版本更正和一项确实缺失的关键证据。输出可复算结果、有条件结论、来源引用和未知项。不得把答案或“哪里有陷阱”放入执行输入。
- [ ] 在模型运行前冻结评分：单位、截止、分母、排重、复算、版本冲突、未知项、结论适用条件各 1 分，共 8 分；猜填关键未知、引用不存在证据、使用失效核心口径任一发生则安全项不通过。关键错误分别报告，不用总分遮蔽。
- [ ] 用第 3 节四个合成用量/产物例验证离线评分选择，运行 `python3 kernel-slice-validation/quality/verify_scoring.py`（在本文所在目录），预期四例通过、0 模型调用；此校验器只读新实验目录，不覆盖历史报告。
- [ ] 三组用相同模型/推理设置/证据/权限/实际 skills 与 tools；用现成 Codex harness 做强单 Agent、一次独立审查、有界对等协商，每组一次，条件标签在评分前隐藏。后两组第二成员全新最小上下文；基线不得偷看其他组产物。原生协作路径比 T0-P 独立线程多出的工具/创建/协调开销须纳入预检；无法匹配工具表时标不可比，不解释为因果效率结论。
- [ ] 冻结三组共同额度 B＝50,000（如有事前矩阵修订则三组同步）、最长 2/3/4 turn 的最短可行路径和第 3 节评分规则；预检任何一组不能完成最小路径时不启动该对照，报告预算设计不可行。不能只降低某组证据/质量要求或预约来获得准入。
- [ ] 先跑单 Agent；若已经 8/8 且无错误，记录 saturated/inconclusive 并停止其余组，后续换题另立实验；这只停止 G-D，不暂停 T2–T8。否则在共同 B 下运行另外两组，不加模型 Router/评分 Agent。
- [ ] 用固定答案/复算程序检查事实，人工在隐藏组名后检查结论与引用。按“最后一份预算内、已完成且费用可归属的合格产物”评分；预算内未完成、cost_unknown、答错分别列出，超线产物不能进入主要比较。
- [ ] 汇总改善、额外错误、完成率、总/缓存 tokens 和人工时间；全部同质或明显无益时停止扩样、建议降低协作频率，收益不确定时不声称质量优势。协议路径仍依自身验收推进，保存失败/未知和超额记录，不只保留成功组。

**验收：** 一个可解释的小样本决策；不据此宣称“多 Agent 普遍更优”。T7 不与该不同模型构成的混合链直接计算优化倍数。

### T2：单一事务存储与可恢复费用账本

**Files:** 创建 R/ 的 `pyproject.toml`、`README.md`、`src/collab_runtime/{__init__.py,contracts.py,store.py,schema.sql,budget.py}`，`tests/{__init__.py,support.py,test_store.py,test_budget.py}`。

**Interfaces:** 产出 `Store.open(path: Path) -> Store`、`Store.transaction() -> ContextManager[Transaction]`；`Budget.reserve(tx: Transaction, attempt_id: AttemptId, amount: int) -> ReservationId | Rejected`、`Budget.observe(tx: Transaction, usage: UsageObservation) -> BudgetState | Rejected`。所有事实写入和预算操作同事务，可供 T3 使用。

- [ ] 写 `test_atomic_intent_and_reservation`、`test_duplicate_and_conflicting_event`：提交后 journal/state/intent/reservation 同时存在；故障点回滚后四者都不存在；同 ID 同指纹复用，同 ID 不同指纹拒绝。核心断言为 `assert persisted_counts == (1, 1, 1, 1)` 和回滚场景的 `assert persisted_counts == (0, 0, 0, 0)`。加 `test_reopen_preserves_facts`，关闭/重开临时库仍可读暂停、旧 revision 和 unknown。
- [ ] 写 `test_usage_modes_do_not_double_count`、`test_counter_reset_is_unknown`：从已确认零基线累计 100→160、重复 160，`assert actual_total == 160`，不是 420；计数器无明确新 epoch 变成 20 时不得减账或记零。逐响应重复 ID 只入一次，覆盖同一消费的两种流不叠加；未知费用保留预约，跨重开不丢失。
- [ ] 写 `test_calibrated_reservation_and_path_preflight`：比较已测 8,000/路径估算 10,000，预约为 12,500；不得再强制加到 20,000。共同 B＝50,000 下三步预约各 12,500 可通过起跑预检；三步各 20,000 不通过；新增未知费用使可用额不足时拒绝，不能调低估算。此处数字为会计规则 fixture，不表示真实模型已经测得该成本。
- [ ] 运行 `python -m unittest discover -s tests -p 'test_store.py' -v` 和 `test_budget.py` 对应命令，确认上述行为因未实现而失败；不得用永远失败的占位断言充当红灯。
- [ ] 实现表/唯一约束、事务与预算接口；字段依据 007 的记录结构，条件唯一性在同一写事务检查。第一版数据库初始化和 schema 版本检查即可，未知新版本拒绝打开，不建立通用迁移平台。
- [ ] 重跑两个文件，所有行为通过；检查输入 payload 与 artifact 内容不混进可公开的诊断日志。仅提交 T2 文件，提交信息建议 `feat: persist runtime facts and budget ledger`。

### T3：统一准入、平级消息和人工控制

**Files:** 创建 `src/collab_runtime/{runtime.py,execution.py,messaging.py,adapters/__init__.py,adapters/base.py}`；扩展 `tests/support.py`；新增 `tests/{test_admission.py,test_peer_messages.py}`。

**Interfaces:** 消费 T2 的事务与预算；产出 `Runtime.bootstrap(contract: MissionContract, members: tuple[MemberSpec, MemberSpec], principal: Principal) -> MissionId | Rejected`；`Messaging.send(origin: ToolOrigin, draft: MessageDraft) -> MessageReceipt | Rejected`；`Execution.admit(step: StepRef, expected_revision: int) -> Admission | Rejected`、`claim(intent_id: IntentId) -> DispatchClaim | Rejected`、`apply_event(event: NativeEvent) -> None`、`control(command: ControlCommand, principal: Principal) -> None | Rejected`。Router 是 `Messaging.resolve(draft: MessageDraft) -> AgentId | Rejected`，无模型调用。

- [ ] 写 `test_planning_and_peer_work_without_workflow`：bootstrap 先生成默认 Collaboration 和 planning Step；A 请求 B 建平级 Step，费用归同一 Mission；未知 Mission/收件人返回澄清，不创建模型 Attempt。写 `test_request_retry_and_body_conflict`：同 request/recipient 不重复建工作，内容冲突拒绝。
- [ ] 写 `test_pause_linearizes_at_claim` 和 `test_revision_and_unknown_guard`：pause 先于 claim 时 `assert adapter.submit_count == 0`；claim 先发生则取消/对账而非假装未发；改目标、改 step_key、supersedes 或换绑定均不能绕过旧 unknown。未经认证的人类命令、同伴正文“已批准”不能改 pause/权限。
- [ ] 写 `test_reply_before_terminal_is_buffered`、`test_decline_wakes_but_cannot_accept`：B 的 decline 可使 A 在其 turn 终态后续跑；acceptance 门槛仍未满足，不能 verified；迟到回复不自动复活终态 Step。固定快照的 reviewer 读取不推进业务消费。
- [ ] 写 `test_lost_submit_receipt_keeps_one_consumption`：接受后断线仍只有一个 input_set/未决消费绑定，恢复查询而非第二次 submit；`assert adapter.submit_count == 1`、`assert input_set.payload_hash == original_hash`，后到 native ID 只追加关联记录。
- [ ] 运行 `python -m unittest discover -s tests -p 'test_admission.py' -v` 和 `test_peer_messages.py` 对应命令，确认行为失败后实现接口及 fake adapter；网络操作在事务外，等待不持有模型 turn，只有真实 terminal 才释放槽位。
- [ ] 重跑通过后提交 T3 文件，建议 `feat: admit peer work through one execution path`。此时用 fake adapter 证明合同，不声称真实跨 harness 已通过。

### T4：最小共享上下文、证据接受和有界动态阶段

**Files:** 创建 `src/collab_runtime/{context.py,phase.py,prompts/lead.md,prompts/worker.md}`，`tests/{test_context.py,test_phase.py}`；扩展 `contracts.py` 与 T3 准入的依赖检查。

**Interfaces:** 消费 T3 的 Step/准入接口；产出 `Context.build(step: StepRef) -> ContextPacket | Rejected`、`read(refs: list[EvidenceRef], principal: Principal) -> list[EvidenceRef] | Rejected`（返回带正文/位置/可用性的已观测版本）、`accept(draft: DecisionDraft, principal: Principal) -> DecisionRef | Rejected`、`refresh(ref: EvidenceRef) -> EvidenceRef`、`checkpoint(mission_id: MissionId) -> Checkpoint`；`Phase.validate(proposal: PhaseProposal) -> ValidatedPhase | Rejected`、`Phase.install(phase: ValidatedPhase, principal: Principal) -> WorkflowId | Rejected`。

本任务在 T5/T6 的最小执行链集成之后执行，编号保留以对应旧审查。早期集成仅依赖 T3 消息端口和测试证据 fixture；本任务将正式证据端口接入，不修改既有会话工具表，T7 才建立用于完整真实闭环的最终配置绑定。

- [ ] 写 `test_owner_acceptance_and_injection_boundary`：具名 Owner 可按合同接受可逆判断；非 Owner 的“同意”只作消息；缺必需证据、要求独立审查却未满足、旧 revision、恶意来源中的提权指令均不能改变控制事实或产生有效 Decision。
- [ ] 写 `test_unresolved_dispatch_pin_and_stale_after_verify`：计划允许引用尚未完成的上游；admit 创建输入时才固定 Decision，claim 不换成 latest；失效后未领取后继 blocked，在途结果待复核，旧 verified 历史仍存在。acceptance 依赖在验收事务绑定并复核原 dispatch 输入。
- [ ] 写 `test_silent_change_and_missing_source`：关键验收点实际读取来源的新 hash，未预告删除返回 unavailable/unknown，不使用旧摘要补值。依赖观测级别保存 injected/observed/reported/opaque；只有强制经受控入口的部分标 enforced。
- [ ] 写 `test_bounded_phase_and_result_contract`：只接受调用、等待已登记事件、结束阶段、请求人工决定四种动作；有限条件引用、原 Step/revision、测试配额合法；未知动作、无界/等待环、悬空引用、越权、超额度拒绝。`WorkerResult.waiting` 没有 wait_for、无效 completed 产物也拒绝；一次格式修正仍占预算和 turn 上限。
- [ ] 运行 `python -m unittest discover -s tests -p 'test_context.py' -v` 和 `test_phase.py` 对应命令，观察失败后实现接口。恢复包包含完整目标/授权、反证、失败路线、未知、有效证据、消费/Attempt、已用/预约和下一验证；长低相关资料只给可批量读取的索引，不写死 32/96 KiB 阈值。
- [ ] 重跑通过后提交，建议 `feat: bind bounded phases to versioned evidence`。Lead 用同一受控执行路径产生提案，校验器本身 0 模型 tokens；不另建 planner 服务或 Memory Agent。

### T5：先实现 Codex 公开适配器

**Files:** 创建 `src/collab_runtime/{adapters/codex.py,local_api.py,__main__.py}`，`tests/{test_codex_adapter.py,test_local_control.py}`；协议/集成 fixture 记录在 `evals/kernel/codex/`。引用 T0-P 已有真实探针，不为本任务新开付费样本。

**Interfaces:** 实现 `HarnessAdapter`；`LocalAPI.handle_control(principal: Principal, command: ControlCommand) -> dict | Rejected`；`LocalAPI.handle_tool(origin: ToolOrigin, tool: str, arguments: dict) -> dict | Rejected` 先转接 T3 的 send，证据端口以测试 fixture 注入，T4 再接正式 Context；`Runtime.run(config: RuntimeConfig) -> None` 负责装配/事件泵。最小 CLI 为 `serve --mission <合同文件>`、`status`、`events`、`control <结构化命令文件>`；命令包含 pause/resume/revise/decide、mission/proposal/expected_revision，不分别建设七套交互。启动读取合同经 bootstrap 幂等登记，重复 serve 不重建 Mission 或绕过暂停。

在 T4 完成前，正式证据读取/接受返回能力未启用，只有契约测试可注入证据 fixture；控制事实的 pause/resume/revise 仍按 T3 生效。不能将测试用接受器暴露给模型或操作者并假装是真实验收。

- [ ] 写 `test_dynamic_tool_origin_and_resume`：来自 `threadId/turnId/callId` 的回调唯一映射到受控 Attempt；伪造正文作者、未知线程、summary/native child 调用拒绝。重复 call 回放持久工具回执，不产生第二条请求；线程兼容则续用，不每次回复 thread/start。
- [ ] 写 `test_stdio_restart_recovers_original_thread`：fixture 覆盖初始化未声明 experimentalApi 被拒、旧服务状态不明不启动第二实例、同状态目录恢复原 thread、恢复动态工具可用和回调归属。`assert recovery_model_calls == 0` 针对纯查询阶段；为检验工具能力而安排的本地 fixture turn 单独计数。丢原 thread ID 时不得以 thread/start 当恢复。
- [ ] 写 `test_busy_and_lost_turn_receipt`：busy 时没有第二次 turn/start；原 turn 终结才提交下一输入；未拿到 turn ID 不靠 clientUserMessageId 自动重试。query 无证据就 unknown。累计 usage 事件重连不双算，计数器重置检查持久基线和 coverage。
- [ ] 写 `test_local_operator_is_not_agent_tool`：控制与工具入口使用不同本地凭据/允许操作；Agent 的工具凭据无权 pause/resume/改合同。Unix socket/凭据文件仅授权本机用户可读，运行时验证 capability 与 binding；操作员凭据不放入模型输入。真实低权限配置另验，不把同用户文件权限称为恶意本机进程隔离。
- [ ] 运行 `python -m unittest discover -s tests -p 'test_codex_adapter.py' -v` 和 `test_local_control.py` 对应命令，确认失败后实现 JSON-RPC 传输和公开端口，不调用私有 Rust Host/AgentControl。最小工具 send 只返回持久回执，不持有工具请求等同伴。
- [ ] 用 T0-P 原始回执形态和真实 AppServer＋本地 Responses fixture 验证与 T2/T3 的连接，不复跑真实短任务。核对每次 submit/工具回调/usage 都进入内核既有 Attempt；已登记工具能力不能从 model arguments 自报授权。
- [ ] 保存实际生效工具/skills/权限指纹、原始回执和 coverage；fixture 通过后提交，建议 `feat: connect controlled turns through Codex AppServer`。此时标签为“原生入口有实测＋内核集成 fixture 通过”，真实内核集成待 T7，不能提前宣称完成；未知请求恢复的保守阻塞是合格行为，盲重发不是。

### T6：Hermes Gateway 与外部薄插件

**Files:** 创建 `src/collab_runtime/adapters/hermes.py`、`integrations/hermes/runtime_bridge/{plugin.yaml,__init__.py,tools.py,usage.py}`，`tests/test_hermes_adapter.py`、`evals/kernel/hermes/`；借鉴 T0-P 已核实的插件回调形态，不复制其诊断账本；不修改 Hermes 仓库产品文件。

**Interfaces:** 实现同一 `HarnessAdapter` 和 T5 的受限工具回调入口；插件将 `session_id/task_id/conversation_id`、已保存绑定和实际观察上下文转换成 `ToolOrigin`，不让模型 arguments 提供身份授权。usage 观察进入 `Budget.observe`，不能另有余额权威。

- [ ] 写 `test_handler_origin_and_rotation`：唯一绑定有效时 send 成功；无上下文、只有共享 conversation、摘要 fork/未纳管子树一律拒绝；压缩 session 改变时阻塞新消息直至受信映射重建，不猜成员。
- [ ] 写 `test_request_receipt_and_gateway_reconcile`：request_id/input_id 原样持久化，同 ID 不同正文冲突；工具正常重传复用业务 ID；prompt 接受后失联通过 receipt/events 查询原 Attempt，未知则阻塞。普通 handler 没有 tool_call_id 时不伪造它；关联证据不足的自动工具回放禁用。
- [ ] 写 `test_gateway_usage_coverage`：Gateway 汇总与 hook 报告交叠只结算一次；主调用、辅助调用、失败、压缩的覆盖分别标注。只有主调用却声称全部覆盖必须拒绝能力报告；总量也不可核对则停止新工作。
- [ ] 运行 `python -m unittest discover -s tests -p 'test_hermes_adapter.py' -v`，确认失败后实现公开 attach/discovery、Gateway 协议、插件注册和 profile 绑定。loopback WebSocket 明确禁用系统代理，attach 票据只在进程内使用，不写入实验记录；这一点沿用 [Hermes G1 实测](g0-g2-2026-11-16/hermes/G1-evidence.md)。不导入 Hermes 私有核心、不改全局环境切换其他 profile、不热换会话工具表。
- [ ] 在隔离 profile 装载正式薄插件，进行无模型的注册/契约/本地回执 fixture 检查；对照 T0-P 真实调用样本，检查工具 schema/身份路径是否变化。真实证据读取、消息与实际加载后的执行合并 T7，不再支付一次独立短任务的成本。
- [ ] 将压缩轮换、Gateway 冷重启、辅助 usage 无法证明的部分保留 unknown：切片允许遇到该状态阻塞/请人，不宣称自动恢复通过；总量/作者连正常任务都不可核对则 G-A 阻塞。保存证据后提交，建议 `feat: bridge Hermes through public gateway and plugin APIs`，标签为“入口已实测、内核集成待 T7”。

### T7：一个真实跨 harness 场景（G-A）

**Files:** `evals/kernel/peer-review/{mission.json,evidence/,protocol.md}`、运行结果目录；`tests/test_kernel_flow.py`。实现接缝若需修正，仅修改 T2–T6 已列模块，不另建编排层。

**Interfaces:** 消费 Runtime、两个 Adapter、Phase、Context 的既有接口；产出同一个 Mission 的可审计事件、检查点、条件结论和完整用量。Hermes 为 A（Lead/交付 Owner），Codex 为 B（按需同伴）；不再增加专职 Router/Reviewer/Memory 进程。

- [ ] 先写 fake 全链 `test_cross_harness_phase`，用 `python -m unittest discover -s tests -p 'test_kernel_flow.py' -v` 验证：人工授权后 planning Step 生成一段图；A 因证据口径冲突直接 @B；B 可以 needs_evidence/反提案而不先 verified；A 收到原文后处理并提交有依据的条件结论。确认至少一条 A→B 与 B→A 原始正文、平级 Step、独立 wait_for/acceptance gate 和每次调用归属；若声明必需 B 的有效结果，则必须补齐对应 Decision 才能最终验收，不能用 B 的拒绝本身满足门槛。
- [ ] 将同一协议换成真实适配器，使用另一份短资料：新旧统计口径相冲突且一项数据不可得。模型需自己提出一段合法计划和具体质疑；不让执行脚本预填模型答案。没有实际直接交流或没有生成合法阶段即记录未通过，不用 fixture 替它补成成功。
- [ ] 使用 T0-P 校准完成逐步预算预检，按 90,000 软预算运行一次；最短 4 turn，必要补证/修正上限 6 turn、2 请求、20 分钟，不能把上限当作已预付。消息工具立即回执；回复在空闲时由下一获准输入接收，不 busy steer、不模型轮询、不额外 READY/ACK。后续轮次以结构化结果驱动，不由人代传正文。
- [ ] 用本地 `events/status` 导出作者、目标、reply_to、Step/Attempt、回执层级、原文/产物引用和费用。人可通过明确 proposal/version 接受或否决结果；被授权 Agent Owner 的接受也必须校验合同和证据。此视图只是群聊协议输入的验证，不等于飞书已经接通。
- [ ] 检查总量/coverage、关键错误和 unknown；确认两成员权限限制实际生效，不能通过读入资料的指令获得控制凭据或生产写权限。没有有效低权限配置则停止，不把提示词约束当隔离。
- [ ] 保存失败也完整的样本，修复如有则先补对应行为测试；仅提交明确变更与脱敏证据，建议 `test: verify one bounded Hermes Codex collaboration`。G-A 不要求模型永远选择 B，但本验收样本必须实际覆盖协作，未发生则不通过。

### T8：恢复与停止验收（G-B），并生成后续缺口清单

**Files:** `src/collab_runtime/recovery.py`、`tests/test_recovery.py`、`evals/kernel/recovery/` 和 `README.md` 的能力边界；注册到现有 Runtime 启动路径。

**Interfaces:** 消费 Context.checkpoint、Store、HarnessAdapter.query/observe/cancel；产出 `Recovery.reconcile(mission_id: MissionId) -> RecoveryReport`，报告 recovered/blocked/requires_revalidation 及逐 Attempt 依据。实验分类 reconciled 对应充分对账的 recovered（仍可另有证据 requires_revalidation），safely_blocked 对应保留未知的 blocked；unsafe 是不变量违背，不能映射为成功。恢复只推进已有合法事实，不以重新调用模型生成旧结果。

- [ ] 写 `test_crash_matrix_no_duplicate_effect`，故障点覆盖事务前、intent 后/claim 前、claim 后/网络前、对端接受后回执前、结果保存后确认前；关闭并重开真实临时 SQLite 与控制进程。只有证明未提交的意图可重发；接受未知时始终只 query，不新增业务 submit。
- [ ] 写 `test_pause_goal_and_budget_survive_restart`：人工暂停、revision、已用和未知预约保留；新“retry”或修改 Workflow 不绕过旧 Attempt；过时结果保存但不能推进新目标；显式恢复后仍须旧执行终态/隔离证据才准入。
- [ ] 写 `test_checkpoint_rebuild_and_stale_source`：删去可重建摘要仍能恢复原目标/禁止项/反证/未决项/消费引用；来源静默改变或断链，在恢复/关键验收点真实重读并阻止旧依据使用。恢复已完成工作不触发模型重做；处于 waiting 的 Mission 无事件则模型调用数为 0。
- [ ] 写 `test_waiting_checkpoint_never_polls_model`：检查点保留证据增量、反证、未决项和下一验证；纯状态查询/计时器观察不调用模型。自动两检查点诊断策略延期，用户仍可按原合同暂停/改目标；不另增进度审查 Agent。
- [ ] 运行 `python -m unittest discover -s tests -p 'test_recovery.py' -v` 确认失败，最小实现 reconcile 和检查点恢复，再运行全套 `python -m unittest discover -s tests -v`。补真实 AppServer＋本地 Responses fixture 的已接受输入/丢回执/stdio 冷恢复路径；纯 fake 状态机测试不能代替它。
- [ ] 在 40,000 总额度内，为 Hermes、Codex 各安排最多一个短真实 Attempt。逐条按校准预检，不要求各硬分 20,000。先在上一检查点做一次无模型的空闲重启查询，再提交这个短 Attempt；由探针观察到原生接受证据（admission started/turn started/工具回调等）后，在**运行时尚未完成回执或结果/费用对账**的屏障点停止控制器。观察屏障在外部测试夹具中，不让模型配合“故障演戏”，不增加 READY 回合。
- [ ] Hermes 保留测试 Gateway 运行，重启控制器后查询原 admission/events；Codex 按明确的 stdio 进程退出、原状态目录、原 thread 恢复路径对账，不假装旧 AppServer 留存。若预算内无法完成第二条路径，报告缺口而不是以第一条代替两条。
- [ ] 每条路径断言：同一 input hash/Step/Attempt/消息消费绑定保留；原业务输入 `submit_count == 1`；暂停和未知预约未丢；只 query/resume/cancel 收集原结果、终态和迟到 usage，恢复本身没有第二个业务 turn。fixture 再覆盖“暂停已落盘但取消尚未发出”的竞争；真实测试选定的屏障及暂停时序随样本记录，不把不同窗口混为一项通过。
- [ ] 将结果分别记 `reconciled`（原执行结果/费用足够可核对）、`safely_blocked`（未知未消除，但确实无重发/无清账）或 `unsafe`。safely_blocked 只证明安全边界，不证明自动恢复成功；unsafe 阻断 G-B。真实在途样本未运行时，G-B 只能标部分验证，不能拿空闲恢复＋fake 故障矩阵宣称全部通过。恢复后的业务续跑只有在原执行处置清楚、当前授权及剩余额度满足时才进行，本轮不为了展示续跑新增模型样本。
- [ ] 汇总 G-D/G-A/G-B、已用/失败/未知/超额、所有保守阻塞及未验证事项；全套通过且真实单机闭环证据齐备才标“首个内核切片完成”。提交建议 `feat: reconcile kernel state without replaying model work`。未达到则提交具体缺口，不用“支持一个月”作结。

## 5. 最小验证清单与发布判断

| 场景 | 最低证据 | 关卡与预算归属 |
|---|---|---|
| 有区分度的单执行/一次审查/对等协商 | 一题最多三样本、共同 B、预算内合格产物、全量 usage/错误；无结论不阻断协议 | T1 / G-D，150k（每组 50k） |
| 真实直接 mention 与受信作者 | 前置最短适配探针＋一次内核混合链；原文、目标、回执、唯一工作可追溯 | T0-P/T7，60k＋90k |
| 工作流与自由请求并存 | 首次规划先有 Step；B 的拒绝可唤醒 A；结果依赖不等于回复门槛 | T3/T4 fixture，T7 实例 |
| 人工控制与注入边界 | 认证操作员可 pause/revise/decide；同伴、网页和工具参数不能冒充控制命令 | T3/T5/T7 |
| 暂停竞争、丢回执、重复消息、晚回复 | 数据库/传输故障注入，证明没有第二个消费或越界准入 | T2/T3/T8，0 模型 tokens |
| 目标/证据/预算的跨进程连续性 | 空闲查询＋每条路径一个真实已接受/未对账窗口，核对无重发/尾账；成功恢复与保守阻塞分列 | T8 / G-B，40k |
| 稳定角色与最小上下文 | 实际配置 hash、同工作复用会话、关键事实内联/长资料按需 | T0、T4–T8 |

**G-A/B 完成要求**：真实 Hermes↔Codex 链通过；两条路径的真实在途验证均实际执行并记录结果；所有未决/重复/暂停/过期情况按契约处理；正常执行的费用总量可核对（逐请求明细允许显式不完整），未知故障费用仍保留预约。G-B 可接受契约允许的 safely_blocked，但完成声明必须附带逐路径自动恢复能力表，不能将安全阻塞称为自动续跑。某路径未测或存在 unsafe 则 G-B 未完成；不能连普通任务都无法认证/计费。Hermes 自动压缩绑定与 Gateway 冷恢复未验证时，必须在能力报告标出并禁用对应自动继续路径。G-D 单独报告，不以题目饱和、无收益或预算内未完成否决协议验收。

**月级连续性在本切片中的交付**是目标/证据/控制/费用独立于会话、检查点和保守恢复机制；不是一个月实测。完整首版仍要补 G-C：飞书真实平台身份/回显/人工操作、两设备断线重连、交接、小范围订阅和有界 Router。G-E 再补真实会话压缩/轮换、72 小时/7 天/30 天连续任务、目标漂移与进展、人介入负担及长期累计成本。

## 6. 需求与证据覆盖、自审结论

| V3.2 要求或历史结论 | 本计划的处理 |
|---|---|
| 独立模块，不能绑死 Hermes | 独立 R/，公开协议＋外部插件；T0/T0-P 提前排风险，T5/T6 集成 |
| 不只有 delegation | 平级 Step、共同预算、拒绝/反提案、wait_for 与 required_for 分开；T3/T7 |
| Router 与共享上下文 | 规则寻址端口、三层版本上下文、Owner 接受、依赖可观测边界；T3/T4 |
| dynamic workflow | planning Step 先存在、Lead 生成有限阶段、程序校验、结果触发后续；T3/T4/T7 |
| 直接 mention 和群聊可见 | 内核验证原作者/正文/收件人事件投影；飞书正式 G-C 保留，临时 patch 不是架构依据 |
| 分布式和多 harness | Hermes/Codex 两适配器先验证；两设备、OpenClaw/DSH 按原边界延期，不宣称完成 |
| 人的批准/否决/改目标/暂停 | 本地认证控制与具体版本提案；T3/T5/T8。通知节奏与飞书交互留到 G-C |
| 6.5 倍耗用且早期质量饱和 | T0-P 校准、T1 共同 B 与完成状态分列；饱和停扩样，不硬门控协议内核；全调用计量 |
| 短资料内联较省、32–96 KiB 特定排序交叉 | T4 混合策略，实际配置冻结；不追加完整四条件矩阵，不设普遍大小阈值 |
| 静默过期/未预告断链已有合成通过 | T4/T8 将机制变为可检验读取行为；保留真实压缩、深层依赖、月级效果未验证 |
| 回执不等于理解、旧 unknown 不能绕过 | T3/T5/T6/T8 保留可观察层级、稳定工作身份和保守阻塞 |

自审采用 superpowers:writing-plans 的规范覆盖、步骤可执行性、类型/接口一致性、Review Focus 和篇幅检查。本轮逐项处理审查意见，保留 V3.2 的授权、直接通信、证据、暂停、计费与未知边界。没有增加付费样本矩阵或评审 Agent，也没有将历史 fixture、静态源码或合成召回改称真实产品验收。

实施交接内容是独立目录/技术默认、T0/T0-P 的接入与成本证据、冻结预算，以及独立报告的 T1 结果。协议内核按用户既有方向推进，不把 G-D 不确定当作重新批准的理由。本次仅修订计划；后续执行须以用户新的实施指令为起点，不由此文档自动启动代码或实验。
