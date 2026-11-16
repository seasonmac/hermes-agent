# 独立多 Agent 协作运行时设计草案

> 修订提示：2026-11-16 的 V2 文档已替代本文执行归属、知识接受、依赖追踪、持久化、人工治理与阶段验收章节。请优先阅读 [V2 修订稿](/private/tmp/collaboration-runtime-design-2026-11-16-v2.md)。本文保留用于追溯，Temporal 与完整灾备不再属于首版方案。

日期：2026 年 11 月 15 日。状态：供设计评审，尚未批准实施。本文定义面向软件工程、量化研究、市场调研，最长持续一个月的跨 harness 协作基础设施。未编写产品代码。

**设计结论**

独立服务持有 Mission、协作消息、共享上下文与执行权威；设备上的 Node Daemon 经适配器连接 Hermes、OpenClaw、Codex、DeepSeek DSH。Agent 可以直接互相 mention；动态工作流用受约束的 JavaScript 表达六种模式；执行、传输和状态提交由持久运行时负责。

用户已要求：多种协作模式、直接 mention 与群聊、Router、Shared Context、Claude Dynamic Workflows、跨设备、独立模块和多 harness 适配。下列属于本设计的默认选择，尚非用户确认：单组织信任域、逻辑统一控制服务、分布式执行、断连时有界自治、TypeScript 控制接口、PostgreSQL 权威存储。首版不承诺多控制域联邦或任意 harness 私有会话状态互相迁移。

**架构路线和取舍**

| 路线 | 收益 | 代价 |
| --- | --- | --- |
| 独立控制服务与分布式节点，推荐 | 消息、预算、上下文和取消有明确权威，跨设备执行 | 控制服务不可达时暂停全局变更 |
| 多域联邦 | 数据和组织可以独立治理 | 跨域身份、授权、冲突和预算结算复杂 |
| 完全对等网络 | 强离线自治 | 全局计划、停止和资源约束难以一致 |

首版中心是逻辑权威，不是转述所有消息的 LLM。API、Router、投递 worker 可多副本；状态竞争由事务、版本和租约解决。此选择不妨碍 Agent 之间对等协作。

**组件和权威**

| 组件 | 负责 | 不承担 |
| --- | --- | --- |
| Mission Service | 目标合同、约束、状态、预算账户、最终验收 | 每步语义规划 |
| Directory | Agent 身份、节点注册、能力、在线状态、会话绑定 | 根据显示名猜身份 |
| Router | 地址解析、候选能力匹配、设备放置、上下文选择 | 改写或代言明确收件人的消息 |
| Messaging | inbox/outbox、回执、因果关系、话题事件 | 以发消息自动授予执行权限 |
| Context Service | 版本化事实、假设、决策、证据、快照和失效关系 | 保证各模型形成完全相同的认知 |
| Workflow Runtime | 脚本版本、控制流、步骤记录、等待、恢复 | 直接持有执行设备的全部权限 |
| Execution Service | assignment、lease、fencing、operation 和资源准入 | 假装外部副作用天然 exactly once |
| Node Daemon | 本地 journal、harness 管理、事件采集、资源与工作区 | 离线改写全局目标 |
| Harness Adapter | 将统一契约映射到 harness 的真实接口 | 伪造不具备的恢复或预算能力 |
| Room Gateway | Web 群聊与外部聊天渠道的事件投影 | 成为唯一持久历史 |

发布为独立仓库和版本化协议，包含 server、node daemon、SDK、pattern library、adapters 和 room UI。核心不导入具体 harness 包；适配器通过注册接口加入。

**身份与数据对象**

组织内使用稳定 UUID，别名仅用于展示与解析。Agent 身份包含名称、能力标签、信任主体和默认路由策略；AgentSession 是某个 harness 的一次会话；Node 是具体设备。迁移会话不改变 Agent ID；新会话身份和绑定 epoch 可观察。

| 对象 | 关键字段 |
| --- | --- |
| Mission | mission_id、contract_version、state、deadline、budget_account、control_epoch |
| Room/Thread | room_id、thread_id、membership、ACL、event_cursor |
| Collaboration | collaboration_id、pattern、participants、state、rubric_ref、termination_policy |
| Workflow | workflow_id、revision、script_hash、SDK_version、input_snapshot、policy_ref |
| Step | step_id、workflow_revision、input_hash、context_snapshot、dependencies、state |
| Attempt | attempt_id、step_id、agent_id、node_id、adapter_version、lease_epoch、state |
| Message | message_id、sender、recipients、kind、reply_to、correlation_id、context_refs |
| ContextItem | item_id、kind、version、status、source_refs、owner、valid_until、supersedes |
| Receipt | receipt_id、kind、subject、version/hash、evidence、issuer、decision |
| ExternalOperation | operation_key、provider、external_id、state、receipt、last_reconciled_at |

Mission 不依附某个协调者会话，也不依附 Kanban 卡片。协作过程跨多次 Workflow；一个 Room 可以观察多个 Workflow。

**六种模式的执行契约**

六种模式来自 Claude Dynamic Workflows 的分类；下面的可靠性与分布式语义是本设计的扩展。

| 模式 | 输入与执行 | 完成与失败 |
| --- | --- | --- |
| Classify-and-act | 分类结果包含类别、证据、置信信息；策略把类别映射到执行能力 | 低置信或无合适能力进入明确 fallback/needs_decision，不静默选人 |
| Fan-out-and-synthesize | 固定集合快照，稳定 item_id，有界并行；聚合器读取产物引用 | 默认等待全部终态；缺失分支显式列出。允许部分完成必须在合同中定义覆盖阈值 |
| Adversarial verification | 产物与 rubric 固定版本；审查上下文独立；记录作者/审查者关系 | pass/fail/unknown 三态；限流或取证失败是 unknown；限制修订次数与预算 |
| Generate-and-filter | 候选有独立 ID、来源、去重规则和评分证据 | 返回接受/拒绝/未评估全集索引；不能静默丢失候选 |
| Tournament | 记录候选、配对、评判标准、平局与不确定性 | 明确 winner/top-k/full-ranking；单淘汰只能选胜者，不提供完整排序或最优性证明 |
| Loop until done | 每轮独立 ID；判定进展与停止条件；事件等待释放计算槽 | satisfied/no_progress/budget_exhausted/needs_decision/cancelled，预算耗尽不是成功 |

Pattern library 是可组合模板，不是固定六类 Agent。Delegation、handoff、对等讨论、blackboard 是通信与责任机制，可用于任何模式。

**动态工作流语言与持久执行**

采用 JavaScript 作者界面，开放一个受约束的子集。允许纯 JSON、集合转换、条件、有限资源约束的循环；异步工作仅经宿主 SDK，禁止直接文件/网络、动态模块、未登记时间随机源和任意异步 Promise 竞态。脚本在独立受限进程/容器中执行；Node vm 不作为安全边界。生成脚本不持有数据库、节点或提供方主凭据。

逻辑 API 如下，这是拟定接口，不是 Claude API 的兼容承诺：

| 原语 | 语义 |
| --- | --- |
| agent(stepKey, request) | 调度一个 Agent 活动，指定能力/harness 偏好、上下文、输出和预算 |
| parallel(items, key, worker, policy) | 稳定项目身份、有界并发、明确部分失败政策 |
| pipeline(items, stages, policy) | 每个 item 顺序过阶段；item 间可并发；支持背压 |
| send(message) / awaitReply(requestId, deadline) | 持久发送与相关回复等待 |
| context.snapshot/query/propose | 读取快照与提交知识提案 |
| checkpoint / awaitEvent / timer | 持久进展、事件与计时等待 |
| verify / publishArtifact | 形成验收结果与不可变产物引用 |

每个调用的身份是 workflow_revision + 显式 stepKey + itemKey + iteration。prompt hash 是输入指纹，不是唯一身份。开始前保存派发 intent；执行后持久化结果。恢复时已完成步骤返回原结果，等待步骤恢复订阅，状态未知步骤先对账，不能当未执行。

重放限定于同一脚本版本与相同记录输入。来自共享上下文的新版本、消息、时钟和模型结果均由持久原语返回，重放必须返回第一次记录的值。依赖完成顺序的业务决策由运行时记录胜出事件，不依赖机器调度顺序。动态生成后续脚本作为子工作流版本提交，不 eval 未登记字符串。

脚本修改产生新 revision；在安全边界停止受影响旧步骤，并通过显式复用映射导入已验收产物。不能仅凭 prompt 相同跨版本复用。每个阶段设置检查点；历史达到配额时生成下一执行段，保留前段引用，避免一个月历史无限进入单个重放。

实现路径：推荐评估成熟 durable workflow 引擎承载计时、消息和恢复。Temporal 是候选，但动态 JS 作者界面不是把任意生成 JS 直接部署为 Temporal workflow；应由受限解释器生成稳定命令，通过固定、版本化的持久 runner 执行。具体引擎选型留给小范围验证；上述协议语义不依赖品牌。首版若自建同样必须满足本文故障契约，不以普通 Promise.all 加文件缓存替代。

若采用外部工作流引擎，它负责控制流历史与唤醒；PostgreSQL 负责执行授权、消息、上下文和预算。二者不共同裁决同一状态：引擎提交带稳定 command_id 的命令，控制服务通过事务去重并返回 receipt；响应丢失时查询原命令。引擎重放不能绕过控制服务重新授权。引擎里的步骤状态是控制服务 receipt 的投影，取消、预算和 epoch 的最终裁决始终在控制服务。

**Router 详细协议**

入口先执行确定性规则：明确 agent_id → 已登记 alias → 当前请求责任人 → 订阅关系。仅在未指定对象、未知归属或用户要求推荐时调用语义分类。显式 @B 不会被静默换为 @C；B 离线则排队并显示期限，也可返回替代建议。

选择候选先按 ACL、必需工具、数据位置、harness 能力、许可的模型/provider、预算硬过滤，再按负载、成本、延迟、上下文亲和性排序。模型建议的候选仍需策略验证。决策保存 router_version、候选快照、过滤原因、最终目标与决定依据。放置绑定具体 node 与 adapter 能力版本，执行前再次验证。

地址路由不需要 LLM；能力路由可以用分类器；上下文路由使用 Context Service 的策略。Router 只确定发送和执行位置，不获得编辑目标、扩大授权或替 Agent 发言的权力。

**mention、群聊与双向通信**

mention 编译为 recipients 中的稳定 Agent ID。消息最小字段：schema_version、message_id、mission_id、room/thread、sender(agent_id/session_id)、recipient_ids、kind、body、reply_to、correlation_id、context_refs、priority、expires_at、idempotency_key。sender 由认证绑定，不能由模型自行声明。原始消息保持不可变；更正、删除标记和失效以新事件表达。

消息类型：inform、request、reply、handoff_offer、handoff_accept、decision_proposal、decision_committed、execution_event。inform 默认不立刻调用模型；request 按接收者唤醒策略运行；@all 是显式策略控制的广播。订阅到上下文不意味着接手请求。

提交消息的事务同时保存 room event 和各收件人的 inbox 项；outbox 异步发送到节点与外部群聊。状态分别为 persisted、delivered、context_applied、acknowledged、resolved；harness 不支持 applied 事件时显示 unknown，不能把 API 调用成功当模型已读取。

每个话题有服务端序号；跨话题使用 causation/reply 引用，不承诺所有设备全局全序。投递至少一次，按 message_id 幂等消费；重启后用 cursor 补拉。外部聊天投影有单独回执，失败不影响内部 inbox；没有幂等发送 API 的渠道不能承诺显示绝不重复。

接收者忙时默认排队到安全轮次边界；适配器支持 mid-turn steering 才注入，并保留真实来源和权限等级。消息不伪装成人类授权。handoff 使用 offer/accept/commit：接收者接受后才能原子移交工作所有权；超时原 owner 保留责任。多人受邀回答不是多人获得独占任务所有权。

避免对话风暴：按 conversation/correlation 设回应预算、每轮最大唤醒、TTL；相同消息去重，多个 inform 合并成一次摘要，但保留原始事件。无新证据的往返计入 no_progress。群聊展示原作者消息、简要行动、交付物与状态，不展示私有思维链；盲审步骤不订阅作者所在话题，即使人类界面可看到两边。

awaitReply 不占用模型调用槽；持久等待建立 wait-for 依赖。出现循环等待时发出可诊断事件并按既定责任策略升级，不能无限等待。超时返回明确的 timeout/recipient_unavailable/cancelled；回复到达不等于请求已满足，request 的验收契约决定 resolved。

**共享上下文和一致性**

数据分四类：Contract（目标约束），Accepted State（已验证事实与决策），Working Knowledge（假设争议），Evidence/Artifact（原始证据产物）。不以大摘要覆盖这些对象。每条记录具有来源、版本、适用范围、作者、证据状态、有效期和可见范围。假设可以相互矛盾，不能最后写入者自动成为真相。

写入协议：propose(base_version) → validate → accept/reject/conflict。合约/决策采用授权角色与版本 CAS；确定性事实采用领域验证；无判据的分歧保留为 unresolved 并建立调查，不让 Memory Agent 任意裁决。独立审查是上下文与权限策略，使用不同模型只能降低部分相关性，不保证判断独立。

Context Snapshot 包含 contract/workflow revision、授权范围、accepted item versions、相关证据引用、未读消息、未决问题与token预算。策略支持 shared_baseline、isolated_exploration、blind_review、collaborative_subscription、synthesis。全文存储可检索，向量索引是派生投影，不是权威记录。

执行记录其 read_set：用了哪些数据/合同/证据版本。变更事件查反向依赖，将相关产物标为 stale，创建复核工作；不删除旧结论。高影响合同更新设置 barrier：旧版本执行可继续交还事实，但不允许晋级验收。使用时快照固定；增量在安全边界通过消息或工具结果进入，保持 harness system prompt/工具前缀稳定。

上下文可见不等于可理解。可观察的最强基础承诺是指定版本进入模型输入；对关键接口/约束还要求结构化确认或机器验收。私人上下文默认不跨 Agent 共享。

**分布式执行和恢复**

节点主动建立认证出站连接；支持短期节点凭据和按任务缩小的 capability grant。各节点自有本地 durable journal。代码/数据使用内容 hash 或仓库commit寻址，本地路径不是跨设备引用。秘密默认留在所属节点/凭据服务，Router 只见能力标签。

控制服务按 Mission 或执行实体串行化状态转移，不要求单个全局进程。原子事务包含 budget reservation、attempt 创建、lease、dispatch intent。节点收到 assignment 后先记本地 journal 再启动；重复 assignment 返回已有状态。启动成功但 ack 丢失时查同一 assignment，而非重开。

lease_epoch 是执行栅栏。旧 epoch 不可推进新状态或申请新受控动作，但迟到产物、费用和操作结果仍记为 late/stale。一个会话同一时间只有一个 active turn，避免消息与工作流同时启动两个轮次。心跳仅证明活性；应用进展与验证覆盖率独立衡量。

网络分区采用一致性优先：不可获得权威状态时不修改全局计划、不发放新预算。节点可在已授予时间/成本/操作范围内继续计算，lease 到期停止新受控动作。正在执行的工具不一定可立即中止，标为 draining/unknown；无法 enforce 该边界的 adapter 不接收要求强约束的步骤。中心不因心跳暂失就重派具有未知副作用的任务。

外部动作走 intent → submit → receipt → reconcile。operation_key 在重试间稳定，attempt_id 可变化。提供方支持幂等键则传入；否则查询外部ID/审计状态；不可查询且结果未知时进入 needs_reconciliation，不盲重放。runtime 的内部幂等不代表第三方 exactly once。

| 故障 | 恢复行为 |
| --- | --- |
| 控制服务提交后、派发前退出 | 重扫 outbox，同 assignment 派发 |
| 节点启动后 ack 丢失 | 查询本地 journal 与运行对象，恢复绑定 |
| harness 崩溃，节点仍在 | 适配器尝试原生恢复；否则新会话接力，核对副作用 |
| 节点永久丢失 | 撤销旧执行权，核对外部操作，按数据/工作区可迁移能力重建 |
| 旧节点恢复 | 过期写入被拒；实际产物与消费仍入账 |
| 取消时外部实验尚在运行 | 请求取消并保留 operation 跟踪，不立即标 cancelled-complete |
| 数据或合同改变 | 标记受影响结果 stale，显式重算/复验 |

pause 停止新准入，可选 drain 或有界 checkpoint；cancel 撤销新执行权并传播停止。终态区分 cancelled 与 cancelled_with_unresolved_operations。截止日期和预算耗尽都不是 succeeded。每次 Mission 成功需要最终验收 receipt 覆盖必需成果且无未决强制 gate。

**Harness Adapter 契约**

接口只传可序列化值和产物引用，协议支持版本协商。实际 SDK/CLI 路径在适配 spike 中验证；本文不宣称四种 harness 都已实现这些能力。

| 接口 | 必需语义 |
| --- | --- |
| describeCapabilities | harness/version、supported operations、恢复级别、输入注入、usage与权限执行能力 |
| ensureSession | 幂等创建/找到 session，绑定 Agent/Mission/权限与工作区 |
| startTurn | attempt_id 幂等启动一次轮次；返回真实执行身份 |
| deliverInput | message_id 幂等输入，声明 queued/applied/unsupported |
| streamEvents | cursor 重连，事件含来源、seq、执行身份与版本 |
| inspectExecution | 活动/终态/unknown，不能用进程存在直接推断完成 |
| interrupt | 明确 soft/hard 支持与实际停止确认，不能立即伪报停止 |
| checkpoint | 返回原生恢复引用或可移植 handoff manifest |
| resumeOrReconstruct | 返回 resumed/reconstructed/unavailable，保留差异 |
| collectUsage | 累计或增量标识、计量序号、估计/实际标记 |
| closeSession | 释放资源但按保留规则保留恢复材料 |

能力等级分开声明：输入(turn_boundary/mid_turn)、恢复(native/reconstruct/none)、预算(request_enforced/turn_enforced/observed)、副作用(guarded/unrestricted)、隔离(worktree/container/none)。不能用一个笼统“支持”掩盖差异。

最低可接入适配器：可幂等启动有界执行、获取终态或unknown、收集结果、提供可检查取消结果；不支持实时输入则仅轮次边界接收。严格预算或强副作用约束的任务必须选具备对应强执行能力的适配器，不能降级成prompt约定。

| Harness | 初步集成方向 | 必须实测的重点 |
| --- | --- | --- |
| Hermes | 独立插件/公开会话入口；复用其原生会话、工具和工作区 | native恢复范围、委派子树计量、工具前缀稳定、停止与重试所有权 |
| Codex | 受支持的SDK/服务协议或结构化CLI作为执行端 | 不同客户端能力差异、事件游标、恢复、子Agent计量与控制 |
| OpenClaw | 网关/插件/会话接口，由adapter封装 | 尚未代码审计，先验证身份、输入、事件、恢复和取消，不臆造API |
| DeepSeek DSH | Agent/Session、inbox、status/event接口封装 | input claimed与实际进入上下文的区别、后台工作、恢复和费用 |

普通调用统一经过协作SDK或MCP暴露给模型，节点控制走专门生命周期协议。MCP是工具入口而非全部分布式运行时。外部运行时与harness原生委派明确 recovery_owner；同一attempt不得被两者自动恢复。原生隐式子代理至少归入根attempt预算和停止范围；无法枚举/控制则拒绝需要精确跨Agent治理的模式或将整个子树视为不可拆的有界执行。

**预算、产物和一个月存活**

预算账户按 Mission → Workflow → Step/Attempt → 模型请求/外部计算分配。硬token控制要求所有真实请求包括子Agent、重试、压缩、审查都能准入或获得严格的有界turn配额。模型成本与外部API价格未知时美元仅估计；不可通过重启或换harness重置账户。未结算额度先保持占用，查明后结算。

长计算提交为operation，LLM session和执行槽可释放。应用自身保存实验checkpoint；进程元数据不等于训练状态。工作区、commit、数据快照、产物hash和环境recipe组成 handoff manifest；跨设备不迁移本地绝对路径。

活动Mission保留其恢复依赖闭包：脚本版本、输入快照、上下文read_set、消息/ack、原生会话或handoff、未决operation、验收和预算。普通harness的48小时或7天GC不能删除唯一恢复依据；需pin或可靠转存，能力不足时采用短会话+独立handoff而非承诺原生月级恢复。结束后的保留期可配置，默认建议90天；审计与隐私删除要求通过tombstone、授权和备份策略处理。

事件日志、状态投影和文件分别保留，恢复从最新一致检查点加后续事件推进。每个备份检查点有最后提交序号；恢复需要与外部operation对账，不能把回滚后的数据库当成外部世界也回滚。RPO/RTO首版不设未经测量的保证，部署验收必须测量并记录。

**灾备回滚的明确边界**

正常崩溃恢复与丢失已提交数据的灾备恢复分开处理。自动恢复要求从备份与权威日志重建全部已确认提交，覆盖 assignment、operation intent、预算和 receipt；不能证明连续性就进入 recovery_quarantine。首版允许部署未达到零数据损失的备份，但此类灾备不得自动恢复受影响 Mission；影响范围无法确认时冻结整个恢复库中的活动 Mission，并纳入节点/外部系统发现的孤立执行。

灾备恢复创建全新随机 control_incarnation_id，不复用备份内的旧值；新服务证书/授权密钥与 incarnation 一起发布。完整 fence 为 incarnation + mission_epoch + lease_epoch。服务与节点重新握手后只接受当前 incarnation；恢复前须隔离旧控制实例、撤销其在线凭据和出口授权，不能仅依赖新数据库拒绝旧写入。不能确认旧实例已被隔离时，不开放新的外部执行。

对离线授权，节点只在既有有界 lease 到期前继续允许的工作；恢复流程等待最长有效离线授权到期并重新注册节点。受控副作用网关校验当前 incarnation，旧授权立即拒绝；直接访问第三方、已提交的任务或未接入网关的工具不能承诺即时撤销，保持 unknown/draining 并对账。要求强防重的步骤必须采用受控出口；弱适配器不能获得这项保证。

对账合并节点 journal、外部提供方审计与可查询 operation_key、产物存储记录及可用权威日志；未知消费保留预算占用，不推定为零。节点丢失且外部不可枚举时，明确记录证据缺口，等待人工确认风险与恢复范围，不能凭内部不存在 operation 就重做。仅在执行权隔离、操作状态与预算处置均有 receipt 后解除冻结。这是灾备恢复所需操作条件，不是当前设计阶段向用户申请执行权限。

**端到端场景**

量化研究：Router把研究需求路由到DSH生成候选工作流；Hermes负责证据采集，Codex分析回测实现，远程计算节点运行实验。采用 generate-and-filter 产生假设、fan-out 执行、独立adversarial verification检查泄漏；不能把有噪声回测结果的两两胜出当统计显著。研究Agent直接 @数据Agent询问异常，消息带dataset版本和实验引用。数据修订使旧实验stale，新Workflow revision只重算受影响分支。断线节点恢复后递交旧结果，系统保留但不纳入新结论。最终报告由synthesis生成，Mission依证据覆盖与验收完成；证明假设无效可以是合格研究成果。

软件工程把验收换成commit、构建、行为测试与集成检查；市场调研换成来源、日期、独立性、冲突和覆盖率。三个领域复用协议，不共享同一套成功判据。

**实现阶段与验证**

1. 协议切片：两设备、两个harness、同一Room，直接mention、离线inbox、Context Snapshot、稳定执行身份。独立协议服务先行，不修改Hermes任务内核。
2. 持久工作流：受限JS、六种模式、有界预算、步骤恢复、明确失败、群聊执行投影。先用确定性fake adapter做契约测试，再实接adapter。
3. 分布式故障：崩溃窗口、双主/旧lease、断连、未知外部结果、消息重放、脚本修订、取消与恢复。
4. 月级运维：数据与代码版本、保留闭包、备份恢复、兼容升级、72小时/7天/30天真实运行。

验收项：明确mention不经LLM转述；失败投递可追踪；消息重放不重复启动turn；盲审看不到禁止的上下文；相同运行恢复不重做已确认步骤；未知副作用不盲重放；无双恢复所有者；暂停不自动复活；过期节点不提交新状态；不可用能力显式拒绝；费用不因重启归零；预算耗尽/未知验证不算成功；人类能从Room定位决策、输入版本和产物。灾备专项必须注入“备份后外部操作已提交、控制库回滚、执行节点永久丢失”，验证系统冻结并更换控制实例身份，而非重新执行未知操作。

建议指标：每模式验收成功率、单位有效成果成本、恢复成功率、重复副作用数、未知操作数量/滞留时间、上下文过期导致返工率、消息applied延迟、人类介入时间。除可靠性属性外，质量指标以强单Agent和相同预算基线比较。

**主要来源和界限**

- [Claude Dynamic Workflows 博客](https://claude.dev/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code/)：六种模式和任务专用JS编排的来源；本文跨设备协议是设计扩展。
- [Claude workflows 文档](https://code.claude.com/docs/en/workflows)：脚本/会话恢复边界；不假设具备任意harness分布式能力。
- [Temporal Workflow Execution](https://docs.temporal.io/workflow-execution)：成熟持久执行候选，最终引擎仍需spike验证动态脚本与恢复契约。
- [Node vm 文档](https://nodejs.org/api/vm.html)：vm不是执行不可信代码的安全机制。
- 本地 DSH prototype 的 src/core/ports.ts、docs/001-domain.md、docs/003-execution.md：借鉴窄接口、授权与上下文分离、持久副作用；不将其现有主会话协调误称为对等分布式实现。
- 前轮Hermes审计：复用其执行端能力，独立系统不依赖其私有Kanban数据库和进程内lifecycle handle。
