# 可读协商正文验证

2026-11-16；实装 codex-cli 0.169.0-alpha.11.1，真实 gpt-6.1-sol / medium。结论：**公开动态工具可以成为可审计的消息接入点**。一次原生主/子 Agent 的三消息往返已完成，发送参数、主机日志、接收工具结果逐字匹配，同伴最终明确回应并复述收到的消息 hash。它不改变原生 `send_message` 的正文不可读限制，也不证明多 Agent 的质量优势。

## 接入点与实际结果

通过 App Server `thread/start.dynamicTools` 注入 `collaboration_exchange`，开启 `features.multi_agent_v2_dynamic_tools=true`，由原生 `spawn_agent(fork_turns=none)` 创建一个同伴。调用方身份取自服务端工具请求的 threadId；同伴绑定来自实际 spawn 活动，而不是模型自报。两端均实际调用继承的工具。

一个固定三消息的临时诊断程序记录发送参数，然后把原文作为收件方工具结果返回。程序不生成、总结或替任何 Agent 写消息；没有中间模型转述。三条正文由真实模型生成。该程序只处理当前探针的待决回调，不是生产消息队列或调度器。

| 消息 | 发→收 | 回复对象 | 验证 |
|---|---|---|---|
| m1 | root→peer | 无 | root工具参数 = journal = peer接收工具结果 |
| m2 | peer→root | m1 | peer工具参数 = journal = root等待工具结果 |
| m3 | root→peer | m2 | root工具参数 = journal = peer等待工具结果 |

双方 turn 均 completed，探针42.05秒，进程退出0。peer 的最终输出独立表示 m3 回应了其质疑，并带回正确SHA-256。三个 hash、回复链、亲子归属与上述等式已由 [verify-evidence.py](verify-evidence.py) 对 [history.json](history.json)、[message-journal.jsonl](message-journal.jsonl) 和 [observation.json](observation.json) 逐项断言；结果见 [verification.json](verification.json)。[完整可读对话](transcript.md) 保留模型原文。

**证明范围：**公开接口确实保存了发送与接收正文，并观察到同伴明确认可。它不证明任意任务中的理解正确性。`source_kind=agent_message_not_human_authorization` 是来源标记，不是已经验证的注入防御。普通文件flush及hash核对不等于崩溃耐久或防篡改日志。

## 用量与失败尝试

| 成功运行 | root | peer | 全组 |
|---|---:|---:|---:|
| 已记录模型用量增量 | 5 | 3 | 8 |
| 输入 | 63,170 | 36,172 | 99,342 |
| 缓存输入（输入子集） | 36,992 | 23,552 | 60,544 |
| 输出（已含推理） | 471 | 297 | 768 |
| 总tokens | 63,641 | 36,469 | **100,110** |

非缓存输入38,798；非缓存输入+输出39,566。实际金额不可得，不能把100,110称为费用。每次输入11,670–13,041 tokens：root五次生成分别用于spawn、发送m1、发送m3、wait、最终回答；peer三次用于receive、发送m2、最终回答。因此三条业务消息仍对应八次模型增量，初始化与控制流程也有成本。不能从这一探针与旧任务的不同总量计算优化倍数，也没有新的单 Agent 对照。

- attempt-0：App Server 不接受全局 `--ignore-user-config`，启动阶段EOF，无模型运行。保存原错误，随后删除不支持的启动参数，保留显式进程级覆盖；因此本探针不是完全隔离用户配置的环境。
- attempt-1：root先发送，peer后开始receive，诊断程序错误地拒绝此顺序。修正为允许先发送后接收，再跑上述成功样本。此为探针缺陷，不是Codex不支持收件。已知root消耗24,787 tokens；peer已经发出工具请求，但停服前没有持久化usage事件，**其用量未知，不能计零**。失败费用不从记录中剔除。
- 两次真实模型尝试合计已知下限 **124,897 tokens**，不含研究助手及其他历史实验。成功与失败各目录保存 `usage-evidence.json` / `usage-summary.json`；线程累计量取各线程最后一条一次，缓存及推理子集不再相加。

## 留存与限制

[probe-source-snapshot.py](probe-source-snapshot.py) 为实际成功诊断脚本快照；含本机路径且会向固定目录追加日志，**不要在原证据目录原样重跑**。重跑需新输出目录并计入真实模型消耗。验证脚本只读证据、重写verification结果，不会调用模型。请求配置见[settings.json](settings.json)，输入见[prompt.txt](prompt.txt)。未修改全局配置、产品代码或共享服务；没有外发飞书消息。

仍未验证：任意拓扑对等 Agent、休眠/掉线后的唤醒、跨设备、重复消息去重、崩溃回放、授权隔离、消息编辑/撤回、群聊投影。原生亲子结构是本次低成本测试载体，不要求正式协作关系必须是一棵委派树。

源码对照（本地HEAD与实装不同，仅辅助解释）：`codex-rs/core/src/agent/control/spawn.rs` 的 `inherited_dynamic_tools` 以V2及feature开关控制继承；`app-server-protocol/src/protocol/thread_history.rs` 保存 DynamicToolCall 的参数和内容，但忽略 InterAgentCommunication 的正文投影。能力结论以本次实际接口结果为准。
