# G0–G2 执行报告

设计收敛入口：[独立协作运行时 V3.1分类文档](../README.md)。该组文档统一 Router、共享上下文、直接 mention、月级恢复及首版边界，完整替代已归档的V1/V2；“采用”表示设计选择，不代表已实现。

后续静态研究：[Claude Code、DSH与Codex三方源码对照](../MULTI-AGENT-SOURCE-REVIEW.md)。已将控制接口、输入消费回执、唤醒政策、共享记录与通知分离、创建接受边界及用量身份合并到V3.1；未运行新实验或修改产品代码。

最新一轮：[长资料成本转折与无预警召回](superagent-long-pilot/README.md)。8个样本共186,885 tokens；32–96KiB之间出现总token成本排序反转，静默过期和未预告断链的预设检查通过。未执行192KiB扩样，未证明金额转折或月级记忆。

日期：2026-11-16。范围已按用户最新要求收敛：当前聚焦 Hermes 与 Codex；OpenClaw、DSH 的动态验证和实际适配延后，不作为当前阶段阻塞项。飞书 bot mention 的既有 patch 仅作为临时修复和现状证据；正式协议、身份与调度语义以独立协作运行时的架构讨论为准，不受该 patch 约束。Hermes 原生接口已有实机证据，Codex 已有协议与真实协作执行证据。质量试验没有显示出双 Agent 的明确优势。本轮未修改产品代码、未安装服务、未重启共享 Gateway、未发送飞书消息。

最新进展见[消息可审计性与预算边界验证](boundary-validation/README.md)：公开动态工具已跑通可读三消息链；原生共享预算已验证，但显式新回合、在途请求及冷恢复均存在硬上限反例。此前[场景与配置校准](NEXT-RESEARCH.md)已同步更新。两轮均不构成质量优势或月级验收。

最新动态结果见[Superagent小规模对照与抗遗忘结果](superagent-pilot/README.md)：四组机制对照及六次召回均已完成，共283,190 tokens，10个样本的预设召回检查均通过。短资料下订阅直通减少调用，外置读取反而增加总tokens；不构成月级抗遗忘或多Agent质量优势证明。[此前方案](SUPERAGENT-VALIDATION.md)保留作对照。

## 1. 执行状态与证据等级

| 阶段/对象 | 实际执行 | 结论与边界 |
| --- | --- | --- |
| G0 飞书 | 已核对运行服务、已连接 profile、渠道目录、会话来源元数据、指定 profile 的发送目标 | **已有临时补丁，本轮群内复验未执行**。已确认 e7b9eb6c7d 将纯文本 @名称转换为原生 mention；F1–F5 的本轮缺测不代表该能力未实现。 |
| G1 Hermes | 真实 Gateway + 真实模型，独立 tool 会话：create/input 去重、忙时排队、精确取消、断线重附着、事件回放、工具/usage | **本次原生接口烟测通过**。没有测 Gateway 进程冷恢复、steer 或飞书入口。 |
| G1 Codex | 已安装 App Server 二进制 + 本机确定性 SSE fixture：创建、忙时追加、steer、中断、自有进程重启后 resume | **协议烟测通过**。fixture 不是商业模型，不能据此保证真实模型的忙时语义；G2 另有真实模型与原生子 Agent 执行。 |
| G1 OpenClaw | 常规安装与部署位置、两个已知 IPv4 loopback 端口的有界检查 | **已延后，非当前阻塞项**。此前未发现可用 Gateway，没有发送 RPC；保留检查记录，不再继续动态验证。 |
| G1 DSH | 原型依赖、常规 CLI/Host、已知本机端口与可执行进程检查 | **已延后，非当前阻塞项**。此前未找到可用 Host，没有创建会话；保留静态证据，不再继续动态验证。 |
| G2 | 6 次单 Agent；6 次初始双 Agent 尝试；6 次修正后的双 Agent；另 1 次模型可达性探针 | **12 份主要比较产物齐备**。六组修正后均有双向原生投递回执；初始六组保留但剔除主要比较。质量优势未证实，硬预算公平性与协商语义验收未完成。 |

详细证据：[G0](g0/G0-evidence.md)、[Hermes](hermes/G1-evidence.md) / [原观察值](hermes/G1-observation.json)、[Codex 与 DSH](codex-dsh/README.md) / [协议观察值](codex-dsh/codex-smoke.json)、[OpenClaw](openclaw/G1-evidence.md)。

## 2. 实际发现的适配边界

**飞书相互 mention 并非待从零实现。** 已核对提交 `e7b9eb6c7d89f1df2b63ef4bbf68e986e88ac786`：`format_message()` 调用 `_convert_plain_mentions()`，借助 `mention_roster_path` 的 name→open_id 映射把 `@岗位名` 转为原生 `<at user_id="…">`。既有入站 `allow_bots=mentions` 与 mention 准入配合接收目标机器人的消息。[出站转换](/Users/season/workspace/github/hermes-agent/plugins/platforms/feishu/adapter.py:2080)、[入站准入](/Users/season/workspace/github/hermes-agent/plugins/platforms/feishu/adapter.py:3414)。仓库[修复记录](/Users/season/workspace/github/hermes-agent/docs/bug_fix/feishu-plain-text-mention-fix.md:1)记载九项转换验证和 Mac/Linux 部署。这是既有记录，本轮未重跑。运行提交号与源码不同，也不能据此断言补丁不在运行文件中，因为记录含安装副本同步。这项临时转换不等于正式 mention 协议。Agent 身份、目标解析、任务归属、调度权限、消息来源及飞书投影须按正式架构讨论，再决定保留、替换或迁移补丁。

**Hermes 的输入收据可用于精确控制。** 同 request/input ID、同载荷重试返回同一对象；改载荷得到冲突。首个输入执行中，第二个输入可单独取消而不取消首个输入。重连后回放 10 帧，随后恢复同一会话。运行中取消的即时回执仍是 started，后续才到 terminal/interrupted；调用方必须等终态。首轮两次模型调用，12,219 输入 / 238 输出 tokens。服务实际运行 0.23.1、提交 18e659df…，attach CLI 是 e7b9eb6…，不能把工作区 HEAD 当作服务版本。

**Codex 的客户端消息 ID 不是输入去重保证。** fixture 测试中，同一 clientUserMessageId 的两次提交形成两个不同 user item。忙时 turn/start 复用活跃 turn，显式 steer 的错误 expectedTurnId 返回 -32600。自有 App Server 重启后恢复 completed/interrupted 历史，没有新模型请求。恢复时 usage 是线程累计快照，其关联 turn ID 不可直接用作该轮新增费用。

**Codex 临时会话与某些 fork 路径不兼容。** 初始六个 B 运行均出现 `no rollout found` 的 spawn 错误；三份结果显式返回 INVALID_PEER_CONDITION，另三份虽输出了同伴相关陈述，也不足以独立验真。修正为新的持久测试会话、fork_turns=none、完整传递固定材料后，六组均建立恰好一个同伴。

**CLI 流不是完整协作审计流。** 本机 exec JSONL 省略 V2 spawn/activity 和部分直接消息；其 turn.completed usage 只含主线程。通过只读 App Server thread/read 与精确测试 rollout，六组均核验 root 和 peer completed，双方存在 interacted/send_message。分别提取两个线程最后一次累计 usage 后求和，避免漏掉同伴。每组 trace.json、trace-metadata.json 和 usage-summary.json 留存在各运行目录。

**原生send_message公开投影仍不能审核具体协商内容（G2旧路径）。** 原生接口展示双向活动，但没有可读消息参数；rollout 的 message 字段是密文。本轮没有解密，也没有把最终回答的“同伴指出”当成独立证据。已证实双向原生投递取得回执；这本身不能证明对方消费或认可消息。尚不能独立确认每一条质疑和回复满足语义要求。后续已通过另一条公开动态工具路径逐字核验三消息正文及同伴回应，见[补充验证](boundary-validation/messages/README.md)。这不追溯证明旧G2消息语义，也不代表飞书群聊投影已实现。

## 3. G2 材料、过程与结果

**计量复核更新：**[Token 增长分析](TOKEN-ANALYSIS.md)确认 6.50 倍累计量计算无误，但实验存在技能目录不一致、控制流驱动的多次模型续跑，以及非硬预算匹配等问题。该倍数只描述本次配置，不可作为正式多 Agent 架构的固有成本或费用倍数。

[事先固定的规则](g2/PRE-REGISTERED.md)、[三题与五项评分标准](g2/tasks-and-rubric.json)、[变更记录](g2/AMENDMENT-1.md)、[逐次指标](g2/metrics.json)、[评分](g2/scored-results.json)、[被剔除尝试](g2/excluded-attempts.json)。

模型统一请求 gpt-6.1-sol、medium；单 Agent 自审，双 Agent 使用同型号同伴并请求一次质疑/回应。三题为并发扣款故障、量化回测缺陷、市场来源口径冲突，各重复两次。每次先给初步意见，再读取同一份更正材料；12 次主线程事件顺序均验证初步意见先于更正读取。更正是按指令分阶段披露，**不是运行中异步注入的人类事件**。

每次上限 180 秒，请求可见总输出不超过 900 词、最终答案不超过 220 词。这是提示和墙钟约束，没有实现等额总 token 硬预算。没有调用外部网页，也没有实际交易、发布或业务写入。

| 指标，主要比较各 6 次 | 单 Agent A | 双 Agent B，主线程 + 同伴 |
| --- | ---: | ---: |
| 关键点覆盖评分 | 30/30 | 30/30 |
| 输入 tokens | 199,871 | 1,311,024 |
| 其中缓存输入 | 96,768 | 1,058,944 |
| 输出 tokens | 2,823 | 6,970 |
| 输入 + 输出 | 202,694 | 1,317,994 |
| 单次墙钟中位数 | 34.24 秒 | 49.74 秒 |
| 超时 / 非零退出 | 0 / 0 | 0 / 0 |
| 可核验双向投递回执 | 不适用 | 6/6 |

评分由协调助手按事先的五项二值覆盖标准评估，非独立盲评。两组都触及满分，说明这些合成题目区分度不足；不表示答案达到生产设计的完备性。软件题均识别副作用先于去重记录及 24h/7d 差异；量化题均修正时间点数据、样本与验证泄漏；市场题均接受 paid→active 的更正并拒绝错误 TAM/增长推论。

本轮双 Agent 的总 tokens 约为单 Agent 的 **6.50 倍**，墙钟中位数约 **1.45 倍**。这不是金额比：缓存比例不同，也没有实际账单数据。双 Agent 的非缓存输入为 252,080，单 Agent 为 103,103。不能拿这一非硬预算匹配、并行且缓存状态不同的小样本证明因果上的效率差异。

被剔除的六次原始 B 尝试另消耗至少 **694,002 主线程 tokens**，其同伴用量未完整追溯，不记作零。模型可达性探针另为 21,932 tokens。主要比较 + 已知剔除部分 + 探针的已知下限为 **2,236,622 tokens**。该数不含本次调研、调试与评分助手的消耗，也不含 Hermes 烟测，因此不是整个项目总费用。

**质量结论：本轮没有证据支持为了这些任务默认启用双 Agent。** 它证明现成 Codex 可以运行有双向消息的两人协作，也暴露了持久化、消息可见性与费用归集限制；并未证明对等协商优于单 Agent，更未证明月级持续任务。

## 4. 尚缺的最小输入与验收

1. **G0：**将现有 mention 补丁作为临时修复证据，正式机制服从架构设计。需要实际群链路验收时再定位群、机器人及部署配置；此前目标信息请求不作为当前架构讨论的前置条件。
2. **OpenClaw / DSH：**明确延后，不再要求当前提供实例、安装服务或完成四端适配。保留独立模块的可扩展方向，后续按实际接入需求再验证。
3. **G2 后续验收：**可观察正文已有有限实测路径；严格等额预算仍未具备。先压低并记录控制调用开销，再用固定真实任务及独立评审做质量/成本观测；不能把相同原生budget配置称为等额硬预算。尚不满足扩大运行时建设的收益门槛。
4. **恢复：**Hermes 已证实的是观察端断线，Codex fixture 已证实自有进程冷恢复；跨设备恢复、断网积压、目标漂移与一个月运行全部未验收。

## 5. 安全与留存

所有结果保存在当前仓库 docs/research 下，未提交 git。测试仅创建自己的会话/进程，Shared Gateway 保持运行；Hermes 三条测试 admission 均终结，六个持久 Codex root/peer 均完成。测试会话历史作为证据保留，未删除用户原有会话。

一次整段飞书平台配置读取被自动审批拒绝，原因是可能暴露 app secret/token。命令未执行；改用已有非敏感目标元数据继续核对。没有绕过该拒绝，也不需要为整个配置申请放行。
