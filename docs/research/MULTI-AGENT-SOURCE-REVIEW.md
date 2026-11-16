# Claude Code、DSH 与 Codex 多 Agent 基础设施对照

2026-11-16。只读静态研究；未运行研究对象、测试或新的模型对照实验，未修改产品代码。三方采用项已收敛进[V3.1分类设计](README.md)，首版组件范围不变。源码存在、测试代码存在、安装版通过实测分别记录。

## 1 证据边界

- Codex：本地HEAD `e241c18544bab47f729dbfea6d6f2e21531ba0a7`，核对时工作树干净。重点是MultiAgent V2、AgentControl/host扩展和message-board，不与V1或legacy扩展混同，也不等同于此前实测的安装版`0.169.0-alpha.11.1`。
- Claude 本地仓库：`collection-claude-code-source-code`，HEAD `b934603b2800374b315b25061bbeffb40ab6ab26`。主要核对 `original-source-code/src`。仓库另含 `claude-code-source-code` 解包/改写树、`claw-code` 和 `clawspring` 等重写项目，不混为同一实现。目录名和仓库说明不构成官方来源、完整性或线上启用状态认证；根README声称的v2.1.88不能用于证明所有子目录均为相同版本。
- DSH：`dsh-superagent-prototype`，HEAD `8c32a9dc5d72c033816c6a8110b37f40cf94fba4`。README明确它是研究原型，不是官方DeepSeek产品，公开版本与内部版本及文章描述不完全相同。以下区分文档理念、实际调用路径和我们的推论。
- 用户给出的[微信资料一](https://mp.weixin.qq.com/s/U_wc8PH4uiuw5kLqghKvDA)、[微信资料二](https://mp.weixin.qq.com/s/TTu1h2pDcTeLCOMXc7SokQ)：网页工具无法读取，浏览器随后明确因站点安全策略拒绝访问。没有取得正文，也未用其他路径绕过；不将任何观点归于这两篇文章。
- 官方公开对照：Claude当前文档说明teammate可以直接按名称通信，每个成员有独立上下文，团队通常增加token消耗；同时明确in-process teammates不能由`/resume`或`/rewind`恢复。这用于核对产品边界，不能反推本地历史快照的全部功能。[Agent teams官方说明](https://code.claude.com/docs/en/agent-teams)

## 2 最值得借鉴的机制

| 机制 | 本地可见证据 | 对独立运行时的建议 | 与V3的关系 |
|---|---|---|---|
| 定向对等消息与持续成员身份 | Claude直接写收件人邮箱，teammate回合结束进入idle等待后续输入 | 逻辑Agent身份跨Attempt保留；消息寻址与进程是否活跃分开；忙时按适配器安全边界注入 | 补强现有mention与节点绑定 |
| 路由与技术规划分离 | DSH路由提示禁止重写需求或技术计划；路由工具支持一批候选 | Router只决定归属，Lead另做规划；已知归属程序直通 | 保留V3，增加批量与退回规则 |
| 上下文订阅与工作所有权分离 | DSH的context-only订阅不拥有后续请求；相关性不产生路由或授权 | 区分看见、负责回答、允许执行；明确退出订阅与退回请求 | 补齐V3工作接缝 |
| 可寻址证据与小入口 | DSH卡片含ID、短预览、原文入口及关系；读取按Ticket权限裁剪 | 按角色生成小视图，保留原文可达性；短资料仍内联 | 保留V3混合上下文 |
| 进入收件箱与进入模型上下文分开 | DSH request ID去重、待处理收件箱核对、历史持久化、readAt | 把投递receipt和context消费receipt分开，恢复按确切消息ID对账 | 本次最重要的协议补充 |
| 副作用先存后做 | DSH SQLite effect队列与业务命令事务配合，执行后按generation结算 | 采用事务outbox与版本化回执，不引入第二个调度权威 | 为V3单库方案补实现依据 |
| 摘要过程没有业务消费权 | Claude特意禁止session-memory fork消费leader邮箱 | 摘要/评审只读快照，不得ACK业务消息或改owner | 补充共享上下文权限边界 |
| 保持缓存前缀，按需采用fork | Claude fork保留父提示、工具与公共消息前缀，差异放尾部 | 同harness有条件复用前缀；跨harness用证据引用，单独计量缓存 | 新增可选优化，非首版保证 |
| 控制接口与宿主策略分离 | Codex AgentControl与Host准入/记账扩展 | 核心执行与协作政策分开，明确每项控制责任 | 纳入V3.1，扩展可达性待核 |
| 持久正文与通知分离 | Codex board先提交记录，再尽力通知 | 正文作为事实源，短通知＋消费游标补读 | 纳入原有journal，不增服务 |
| 创建接受边界 | Codex PendingSpawn持有临时资源直到接受 | 接受前取消清理，回执未知先查询 | 纳入Attempt恢复 |
| 费用事件与turn归属分离 | Codex Host usage报告单次响应及压缩 | 防止同turn多笔费用漏计；报告重试不重跑推理 | 纳入单一账本契约 |

## 3 Router：从“中央大脑”收敛为归属判断

DSH的[orchestrator提示](/Users/season/workspace/github/dsh-superagent-prototype/prompts/orchestrator.md:1)与[shared提示](/Users/season/workspace/github/dsh-superagent-prototype/prompts/shared.md:1)明确主Session不做技术实现决定，不改写原始请求，不靠sleep或模型轮询等Worker。实际[路由工具](/Users/season/workspace/github/dsh-superagent-prototype/src/app/tools/main.ts:125)一次接受最多20个候选；每个候选独立返回结果，不因其中一个失败而使所有候选失败。[路由附注校验](/Users/season/workspace/github/dsh-superagent-prototype/src/app/tools/main.ts:17)限制长度并要求保留原意。

值得采用的是“所有权稳定后退出路由路径”。在[receive](/Users/season/workspace/github/dsh-superagent-prototype/src/core/intake.ts:19)中先去重、记录关联、扇出订阅，再决定是否送Eval；[followupOwners](/Users/season/workspace/github/dsh-superagent-prototype/src/core/model.ts:75)限定只有符合条件的人类后续消息才由现有Worker拥有。不能把它概括成“所有订阅事件都免Router”：没有owner的事件仍进入Eval路径，bot事件也如此；进入Eval不等于每次都会调用模型。

对我们的补充：明确给B的新请求由B接手；若B判定超出范围，以原request ID记录handback和原因。程序先检查已有负责者，全部退回后才重新判断归属，不让Router与多个Worker同时重复解决同一请求。Agent消息仍须通过V3协作范围、预算和授权准入，不能复制DSH“仅人类后续请求有owner”的来源限制。

Router与Lead可以由同一个逻辑Agent按不同执行角色承担，但路由步骤不能顺便写技术计划；这无需增加常驻管理Agent。批量数量与附注长度是实现参数，不能照搬20或30词作为经过实验优化的值。

## 4 共享上下文：共享可核对状态，不共享整段脑内历史

DSH实际实现的是Trigger、Thread、Ticket、Assignment、Report等持久对象及读取关系。[cards.ts](/Users/season/workspace/github/dsh-superagent-prototype/src/app/cards.ts:8)生成160字符预览，较长输入保留原文入口；[resources.ts](/Users/season/workspace/github/dsh-superagent-prototype/src/app/resources.ts:210)允许沿回复和邻近消息展开，并按Worker所属Ticket裁剪其他工作的不可达信息。图关系既用于找资料，也受访问范围约束。

这支持V3的小上下文包，但不是“所有Agent拥有同一份已接受知识”或自动真值维护系统。DSH没有在这些路径中实现我们要求的领域结论接受、完整read_set或全局过期传播；那些机制仍需我们自己验证。它的[Worker工具](/Users/season/workspace/github/dsh-superagent-prototype/src/app/tools/executor.ts:23)主要面向本Ticket的读取、报告、跟随话题和回复；跨Ticket传事实的[工具](/Users/season/workspace/github/dsh-superagent-prototype/src/app/tools/main.ts:177)属于主Session。因此不能拿DSH作为已实现任意对等mention的证据。

另一个重要边界来自Claude：[attachments.ts](../../../collection-claude-code-source-code/original-source-code/src/utils/attachments.ts:898)明确排除session-memory fork读取并标记leader邮箱，因为它可能把本应进入业务会话的消息先消费掉。对我们而言，摘要、恢复卡生成和评审都应读取指定版本快照；只有绑定业务Attempt的消费者才可提交消息消费回执。读取上下文和ACK收件箱必须是不同权限。

DSH在[模型请求时组装带revision的提示](/Users/season/workspace/github/dsh-superagent-prototype/src/app/sessions.ts:244)。未变内容不意味着每轮必定缓存失效，但revision或提示内容变动会改变相应前缀；不能照搬到Hermes并假定仍满足其会话前缀不变约束。V3继续采用稳定基础提示/工具表，加版本化任务输入。

## 5 mention：值得复制接口，不值得复制文件邮箱

Claude快照的[handleMessage](../../../collection-claude-code-source-code/original-source-code/src/tools/SendMessageTool/SendMessageTool.ts:149)用发送者身份直接写目标成员邮箱，无需leader模型转述。[inProcessRunner](../../../collection-claude-code-source-code/original-source-code/src/utils/swarm/inProcessRunner.ts:1317)回合结束只转idle而非成员完成，再等待消息；[useInboxPoller](../../../collection-claude-code-source-code/original-source-code/src/hooks/useInboxPoller.ts:843)区分闲时新回合和忙时排队。这里的等待由宿主实现，不需要持续调用模型。

值得借鉴的是Agent身份、一次任务关系和当前会话生命周期分开。一次审查结束可以释放执行槽，逻辑成员仍可被@；后续输入可恢复或重建会话。普通subagent在该快照也有收信/恢复路径，因此不能把“能否通信”硬编码为subagent与teammate的区别。[相关路径](../../../collection-claude-code-source-code/original-source-code/src/tools/SendMessageTool/SendMessageTool.ts:800)

不能复制其邮箱持久化保证：[消息结构](../../../collection-claude-code-source-code/original-source-code/src/utils/teammateMailbox.ts:43)没有普通消息ID；[写入](../../../collection-claude-code-source-code/original-source-code/src/utils/teammateMailbox.ts:134)加文件锁后整文件覆写，部分失败仅记录错误而返回，调用者仍可能返回success。文件锁解决并发修改的部分问题，不等于跨设备持久投递、按ID确认或副作用幂等。此处是静态边界判断，没有运行故障注入来验证发生频率。

我们的mention仍需稳定message/request ID、事务inbox/outbox、明确输入注入点和可查询回执。补充三类优先级：人工暂停/撤销等控制信号优先；业务请求按依赖与截止时间处理；inform和重复idle通知可合并。Claude的[等待循环](../../../collection-claude-code-source-code/original-source-code/src/utils/swarm/inProcessRunner.ts:760)优先处理shutdown，给这一方向提供了具体依据；它并不意味着我们的所有leader消息都应压过同伴。

## 6 月级恢复：需要“输入消费账本”，不能只有会话文件

DSH提供了比笼统的checkpoint更具体的接缝：

1. [AgentDelivery](/Users/season/workspace/github/dsh-superagent-prototype/src/app/delivery.ts:15)从request ID产生稳定消息ID，并核对已保存历史及nextTurn/nextStep收件箱；[send](/Users/season/workspace/github/dsh-superagent-prototype/src/app/delivery.ts:65)支持queue、steer和不唤醒的inject，方法完成前flush会话持久化。它依赖DSH内部接口，不可当作任意harness通用能力。
2. [Assignments.delivered/read](/Users/season/workspace/github/dsh-superagent-prototype/src/core/assignments.ts:48)分开登记送达和readAt；[事件调用方](/Users/season/workspace/github/dsh-superagent-prototype/src/executor/dsh.ts:489)区分claimed与真正进入Session history，防止刚取出消息就取消导致被误记为已处理。
3. [requeueUntaken](/Users/season/workspace/github/dsh-superagent-prototype/src/core/tickets.ts:333)重新排入已交付但未进入上下文的消息；[launch](/Users/season/workspace/github/dsh-superagent-prototype/src/executor/dsh.ts:446)移除旧收件箱中等待的重复副本，避免恢复消息和重投消息同时进入下一轮。
4. [恢复入口](/Users/season/workspace/github/dsh-superagent-prototype/src/executor/dsh.ts:524)对运行中Assignment、等待和失败状态分别处理；[interrupted](/Users/season/workspace/github/dsh-superagent-prototype/src/core/assignments.ts:83)根据报告及后续输入判断是否需要启动新的Assignment。它不是无条件把所有工作重新跑一遍。

建议在V3既有记录内细分事实：runtime已持久接收、harness已接收、某次模型上下文已包含、已有回复/报告、结果已验收。后两项不能从“消息进了history”推出。适配器必须说明它实际能观察到哪一层；不能观察消费时保持unknown，并先查原会话，不能虚构ACK。

DSH的readAt以进入Session history为可观察信号，也不能证明provider已经成功接收请求、模型正确理解或完成处理。跨harness协议应分别标注history_committed与实际可观测的request/turn receipt，避免把字段名read误解为认知保证。

DSH的[Effects](/Users/season/workspace/github/dsh-superagent-prototype/src/app/effects.ts:43)和[Engine](/Users/season/workspace/github/dsh-superagent-prototype/src/core/engine.ts:20)还给出单SQLite事务内先保存业务变化和待执行动作、提交后执行的实际模式。结算时匹配seq/generation，避免旧回执删除后来排入的工作。这值得采用，但外部发送完成、receipt尚未写入就崩溃的窗口仍需渠道幂等/对账，不能宣称exactly-once。

不照搬两处：DSH的[Pause processing](/Users/season/workspace/github/dsh-superagent-prototype/docs/003-execution.md:192)不打断运行中的Executor；我们的人工暂停仍采用V3的禁止派发、请求取消、迟到结果待复核。Claude的历史/身份恢复也不是整队复活，当前官方明确不恢复in-process teammates。两者都没有为我们的跨harness、跨设备、30天完整恢复提供实测证据。

## 7 token：两条不同的优化路径

DSH主要减少进入模型的事件与材料：所有权稳定后绕开路由判断，小卡片和按需读取降低重复大输入，批量路由减少续跑，主Session不等待或轮询。我们的既有小测支持直达和混合读取方向，但不能给这些机制分别归因一个稳定节省率。

Claude另有缓存优化：[forkSubagent](../../../collection-claude-code-source-code/original-source-code/src/tools/AgentTool/forkSubagent.ts:96)让fork子分支保留相同公共前缀、把各自指令放尾部；[AgentTool](../../../collection-claude-code-source-code/original-source-code/src/tools/AgentTool/AgentTool.tsx:483)尽量复用父会话已渲染的系统提示。[forkedAgent](../../../collection-claude-code-source-code/original-source-code/src/utils/forkedAgent.ts:83)还明确缓存相关参数和累计usage。

两条路径不能混为“fork天然更省token”：复制长历史可能提高总输入tokens，却提高缓存命中并降低金额；独立小上下文可能降低总输入但需补读。跨模型、provider或harness不能假设共用缓存。首版继续默认最小任务上下文；同harness的受控fork列为可选优化，只有在相同任务、固定工具/提示、可区分缓存写入/读取的对照后才启用。

不采用常驻记忆维护Agent。Claude的[SessionMemory](../../../collection-claude-code-source-code/original-source-code/src/services/SessionMemory/sessionMemory.ts:1)可后台运行fork提取笔记，但有功能门控且仍会调用模型；后台不等于免费，写了笔记也不等于知识被验证。我们的恢复卡在必要检查点更新并计费。

## 8 对V3的最小修改建议与验证顺序

上一轮提出以下五项，本轮与第10节Codex证据一起纳入V3.1；无需扩充首版组件：

1. **消息消费回执：**补harness接收与进入模型上下文的区别、证据等级及未知状态；按消息ID恢复，不按整箱read标志。
2. **请求所有权与退回：**区分context订阅和负责响应；保留request ID与退回原因，防止Router和Worker重复执行。
3. **身份与生命周期：**逻辑Agent不随回合完成消失；节点/session是可替换绑定，换会话后核对合同，不宣称恢复私有推理。
4. **控制消息优先及只读摘要：**暂停/撤销不被聊天淹没；摘要和评审不得消费业务消息或修改所有权。
5. **上下文启动策略可计量：**默认小包，前缀复用作为同harness能力选项；记录是否fork及实际输入/缓存/输出，不直接把它宣传为省钱功能。

可选借鉴Claude的[任务认领](../../../collection-claude-code-source-code/original-source-code/src/utils/tasks.ts:541)：宿主可以把无owner且依赖满足的已授权Step分给空闲成员，减少逐次模型派工。认领必须与准入/派发intent同事务；不因此重建Kanban产品或开放成员无限自行创建工作，首版仍可用固定两个成员。

验证不在本轮执行。以后先用已有harness做窄测试：一条输入送达前后、进历史前后分别中断；重复请求和handback只产生一次工作；压缩读取不得改变业务收件游标；大量inform到达时人工暂停仍及时生效。随后比较默认小包与缓存fork的实际金额/总tokens及召回错误。它们优先于新增角色、第三适配器或灾备系统。

仍缺完整跨harness闭环、两设备恢复、任务质量收益和真实30天连续性。源码里有一种机制，只说明存在可参考实现，不替代我们的验收。

## 9 Dynamic Workflows 的额外资料缺口

本地快照有`WORKFLOW_SCRIPTS`功能开关及LocalWorkflowTask引用，但在此次核对的两个TypeScript源码树中未找到对应实现文件。[引用处](../../../collection-claude-code-source-code/original-source-code/src/components/tasks/BackgroundTasksDialog.tsx:105)明确写了内部功能门控。因此本轮不能宣称已从泄漏代码核实工作流脚本生成、前缀缓存或确定性重放的完整实现。V3对Dynamic Workflows的借鉴仍应标为公开文章支持的设计方向，不能升级为源码验证结论。

## 10 Codex：协作工具后面的运行时分层

### 控制接口与宿主政策分开

实际调用链是V2工具handler → [thread_spawn准备](../../../codex/codex-rs/core/src/thread_spawn.rs:99) → [AgentControl](../../../codex/codex-rs/core/src/agent/api.rs:35) → 控制后端。接口统一resolve、spawn、send、interrupt、成员查询、邮箱观察和用量归属，但文件明确它不是wire protocol。

[AgentRuntimeOwnership](../../../codex/codex-rs/core/src/agent/host/ownership.rs:13)在启动时选择Controller或Host。Host必须提供[AgentTurnAdmission](../../../codex/codex-rs/core/src/agent/host/admission.rs:14)，可提供[AgentUsageAccounting](../../../codex/codex-rs/core/src/agent/host/usage.rs:30)等扩展；缺少准入provider会失败，不静默回退。[实际准入调用方](../../../codex/codex-rs/core/src/tasks/admission.rs:31)支持取消，并保证permit附到原任务，不能因turn ID重用而错挂新任务。

采用它的控制责任划分：独立运行时拥有Mission/Step准入、预算与消息事实，harness拥有推理循环、工具和内部历史。每项能力由谁控制必须在适配器中声明，避免两套调度各自唤醒、记账和恢复。

边界：这些是Rust嵌入扩展，本轮未找到可通过App Server协议直接安装这些provider的对应入口；首版仍走已验证的公开会话/动态工具路径，扩展接入另行验证。`Host`命名不证明已有跨设备协议。也不为复用它而把独立运行时写进Codex核心。

### 消息投递、唤醒和等待分别定义

V2 send_message走QueueOnly、followup_task走TriggerTurn，共用[消息工具](../../../codex/codex-rs/core/src/tools/handlers/multi_agents_v2/message_tool.rs:61)与AgentControl.send。值得采用显式wake_policy：inform只进入上下文入口，新工作才申请启动回合。

但不能概括为send_message永不唤醒：[根会话判断](../../../codex/codex-rs/core/src/session/turn_input.rs:837)允许WakeOnAgentMessages开启、模式允许且未被中断等条件下自动唤醒，durable sleep另有处理。适配器须验证有效行为；无法保证不唤醒时，inform保留在运行时，等授权回合再注入。

[wait_agent](../../../codex/codex-rs/core/src/tools/handlers/multi_agents_v2/wait.rs:68)先订阅输入活动，再等待消息、用户输入或超时，期间无需模型轮询。但它仍可能处于活跃turn的工具调用中，不能等同于V3持久waiting_event，也不证明执行槽已释放。我们仍需checkpoint和确认可恢复边界。

### 身份、驻留与运行容量分离

[AgentRegistry](../../../codex/codex-rs/core/src/agent/registry.rs:25)管理路径和线程身份；[目标解析](../../../codex/codex-rs/core/src/agent/control/target.rs:45)按调用者路径解析名字，不靠模型猜测。[Residency](../../../codex/codex-rs/core/src/agent/control/residency.rs:37)卸载合适的非活跃V2子线程时先停执行、搬邮件、保存有效配置及环境绑定，再释放驻留槽；[ExecutionLimiter](../../../codex/codex-rs/core/src/agent/control/execution.rs:17)另管运行回合。

采用“可被@的成员不必一直驻留或运行”；首版固定两个成员即可，自动淘汰优化延后。本地capacity检查和运行计数不是一个原子预留，root/V1也不受该本地限制，不能照搬为分布式硬限流。远端进程失联时没有Rust析构器替我们释放容量，要有持久预约和对账。

AgentPath树用于成员来源和生命周期归属；我们的对等协商、交接和共享证据仍由Collaboration表达，不把树变成唯一协作关系。

### 接受、消费、持久化与创建回执

[PendingAgentMessage](../../../codex/codex-rs/core/src/agent_communication.rs:109)共享投递ownership；[consumed](../../../codex/codex-rs/core/src/agent_communication.rs:215)一次性取出publication并执行消费回调。receive日志可在入队时出现，on_consumed对应进入内存历史，终态结果另有持久化后的ResultWrite确认。这些状态均不代表模型正确理解或业务验收。

它与DSH输入账本相互印证，但未加载成员的[邮箱本体](../../../codex/codex-rs/core/src/agent/control/mailbox.rs:15)仍为进程内Mutex/HashMap，序列化也跳过delivery ownership。驻留卸载后的reload与进程崩溃后的未消费邮件恢复不是同一保证；我们仍需要durable inbox/outbox。

创建边界也值得采用：[PendingSpawn](../../../codex/codex-rs/core/src/agent/control/spawn_guard.rs:21)在接受前持有临时资源清理责任，取消时处理子线程及关系写入；[最终接受](../../../codex/codex-rs/core/src/agent/control/spawn.rs:1019)后解除临时责任。之后工具结果或网络回执丢失，不等于子任务未创建。我们的spawn request ID、接受状态和harness绑定须落盘；未知先查询，不盲重建。

### 持久共享黑板与短通知

Codex另有message-board，不能与私信邮箱混同。[写入](../../../codex/codex-rs/message-board/src/local.rs:223)以caller-scoped request ID和请求指纹处理重试；[事务提交](../../../codex/codex-rs/message-board/src/local.rs:337)保存正文/相关订阅后才尽力通知，通知失败不撤销帖子。未加载收件人返回[SkippedInactive](../../../codex/codex-rs/agent-message-board-host/src/lib.rs:225)，不为通知自动恢复所有Agent。

采用“正文是持久事实，通知是引用线索”，漏通知后按持久游标补读。这支持共享黑板式协作，且不要求Lead转发。首版沿用Message、Context item与journal，不新增board服务或第二权威库。帖子只证明“有人说过”，不等于知识已accepted。

[连接权限](../../../codex/codex-rs/ext/agent-message-board/README.md:28)由宿主提供，冷恢复/fork要重新提供，不是数据库ACL，也不是跨harness身份认证。另一个[ext/agent入口](../../../codex/codex-rs/ext/agent/src/lib.rs:63)实际仍调用legacy subagent runner，不是可直接接Hermes的外部Agent总线。

### 用量归属与有效上下文快照

[AgentUsageReport](../../../codex/codex-rs/core/src/agent/host/usage.rs:8)报告单次模型响应及压缩用量，thread/turn只是归属，同一turn可产生多笔费用。hook计费和序列化会省略的provider budget units也需显式保留。[会话调用方](../../../codex/codex-rs/core/src/session/rollout_budget.rs:134)按选定责任方记账；Host报告失败不自动回退或重跑推理。Host缺accounting时也不会自动补计，故我们的接入须要求有效记账能力，未知消耗不能记零。

采用单一账本权威、独立费用事件ID及报告重试去重；它仍不是硬预算，turn准入与响应后记账不能撤销其他在途请求。此前安装版预算反例继续保留。

[child_config](../../../codex/codex-rs/core/src/agent/child_config.rs:123)使用调用时捕获的有效配置，[权限覆盖](../../../codex/codex-rs/core/src/agent/child_config.rs:193)补当前approval/cwd/permission snapshot，避免读取过时磁盘配置。[history](../../../codex/codex-rs/core/src/agent/history.rs:46)还表明fresh子会话可继承always-retained内容，full fork也有过滤规则。fork=none不等于零上下文，fork=all不等于复制全部原始事件。

因此我们要记录实际model、effort、提示/工具指纹、插件状态、保留输入、权限和启动方式，并在恢复时重新核对当前授权。默认最小上下文，同harness缓存fork仍待成本验证。

### 证据等级

[消息来源判断](../../../codex/codex-rs/core/src/tools/handlers/multi_agents_v2.rs:54)区分加密与明文。公开SubAgentActivity等活动记录不保证正文可读；原生消息不可读与dynamicTools三消息可核验仍是两条路径，首版继续使用运行时持有正文的协议。

已阅读[Host准入测试入口](../../../codex/codex-rs/core/tests/suite/host_turn_admission.rs:164)、[邮件与淘汰](../../../codex/codex-rs/core/tests/suite/agent_eviction_tests.rs:59)、[唤醒与控制变化](../../../codex/codex-rs/core/tests/suite/agent_message_wake.rs:107)。本轮未运行这些测试，测试存在不等于本环境通过。

## 11 三方合并后的采用清单

| 决定 | 综合来源 | 首版落点 | 尚缺验证 |
|---|---|---|---|
| 采用程序寻址、归属直通、请求退回 | DSH归属＋Codex路径解析 | Router/Collaboration | 跨harness不重复处理同一请求 |
| 采用长期身份、短执行绑定、显式wake_policy | Claude idle＋Codex投递/驻留分离 | Agent注册/适配器 | 自动唤醒不绕过准入 |
| 采用小上下文包、持久记录＋短通知 | DSH资源引用＋Codex board | Context/Message/journal | 漏通知补读、过期与权限 |
| 采用消费证据分层和只读摘要 | DSH readAt＋Codex ownership＋Claude摘要隔离 | inbox/恢复 | 交付及历史边界中断重试 |
| 采用创建接受边界和有效配置快照 | Codex PendingSpawn/child_config | Attempt/适配器 | 丢回执不重复创建，旧权限不复活 |
| 采用单一账本权威，费用身份独立于turn | Codex Host accounting＋预算实测 | usage/reservation | 辅助调用覆盖、重复/未知费用 |
| 保留阶段验收、证据恢复和人工暂停 | 三方边界＋V3任务合同 | Mission/checkpoint | 72小时、7天、30天连续性 |
| 条件采用缓存fork、自动驻留淘汰、工作认领 | Claude/Codex局部机制 | 首版不必启用 | 真正收益与并发行为 |
| 不采用文件/内存邮箱充当月级权威；不假设私有Rust扩展可由公开RPC调用 | 三方限制 | 保持运行时独立 | 公开接入可达性 |

这些机制合并的是设计要求，不是拼出一个已经验证的分布式月级系统。V3.1仍为一个控制服务、一个账本、Hermes/Codex两个适配器及飞书桥，不新增治理Agent、独立board服务或第三harness。
