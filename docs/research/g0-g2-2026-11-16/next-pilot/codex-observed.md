# G1 · Codex 和 DSH 原生接口烟测

## Codex

实测二进制为桌面安装自带的 `codex-cli 0.169.0-alpha.11.1`。测试通过 stdio JSON-RPC 驱动两个先后启动的独立 `codex app-server` 进程，使用临时 `CODEX_HOME` 和临时工作目录、只读沙箱，以及本机确定性的 Responses HTTP SSE fixture。两个进程均正常退出。SSE fixture 共收到四次模型请求，真实模型调用次数为零。测试输入只有合成文本，未提供账户凭据。

| 检查 | 观察 |
| --- | --- |
| 创建和事件 | `thread/start` 与 `thread/started` 返回相同会话。首轮观察到活跃状态、`turn/started`、五个 item 的开始和完成，以及 `turn/completed`。 |
| 忙时追加 | fixture 暂停首轮响应期间，两次 `turn/start` 和一次显式 `turn/steer` 都返回原活跃 turn ID。使用错误的 `expectedTurnId` 返回 `-32600`。 |
| 消息 ID | 使用同一个 `clientUserMessageId` 两次提交同样的文本，`thread/read` 读到两条不同 item。该字段可用于关联和对账。 |
| 中断 | 空闲后启动新 turn，fixture 收到请求后保持流打开。按目标 turn ID 调用 `turn/interrupt` 返回 `{}`，终态是 `interrupted`。 |
| 冷恢复 | 新进程用同一临时持久化目录执行 `thread/resume`，得到原 thread ID、相同 turn 顺序及 `completed`、`interrupted` 状态。fixture 请求数在恢复前后均为四。 |
| Usage | 在线事件把 11 输入、3 缓存输入、2 输出、1 推理输出的合成计数归到成功 turn。冷恢复时，同一组 thread usage 快照出现在后一个中断 turn ID 上。该中断请求在 fixture 端未发 `response.completed`，说明恢复时的 usage 通知可用于恢复 thread 快照，接收方应避免按其 turn ID 将累计值再次记为消耗。 |

初次尝试时 fixture 的健康检查返回 204，但本机 Codex 的模型请求未抵达。本次确认结果使用测试进程的 `features.respect_system_proxy = true` 接通同一个 loopback fixture。生产模型兼容性、WebSocket 重新附着及工具调用观测沿用源码证据，本次运行覆盖 stdio 和冷恢复。实测记录见 [codex-smoke.json](../codex-dsh/codex-smoke.json)。

## DSH

**范围更新：用户已要求延后 DSH 的动态验证和实际适配。以下仅保留既有环境检查，不构成当前阶段阻塞项。**

原型源码处于 `8c32a9dc5d72c033816c6a8110b37f40cf94fba4`。当前 PATH 未发现 `dsh`、`node` 或 `tmux`，常规安装位置和原型依赖目录没有候选。审批后在本机按可执行文件名检查没有找到 DSH 进程，默认的 TCP 3080 和 3082 端口也没有监听证据。没有可直接用于建会话的已确认实例，本次未运行 DSH，未安装依赖。公开 DSH 的部署资料仍可作为后续固定版本验证依据。实测记录见 [dsh-availability.json](../codex-dsh/dsh-availability.json)。

## G2 计量和事件的源码边界

在本地 Codex 源码 `e241c18544bab47f729dbfea6d6f2e21531ba0a7`，V2 的成功 spawn 发出 `SubAgentActivity::Started`，App Server 将其投影成 `item/completed`。exec JSONL 的 item 映射丢弃这类 `SubAgentActivity`，另有保留旧式 `CollabAgentToolCall::SpawnAgent` 的映射，且明确过滤 `SendMessage`、`FollowupTask`、`InterruptAgent` 和 `ListAgents`。G2 的 peer 证据需要查每个 Session 的历史、rollout 或 App Server 事件。对应文件为 `codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs:162`、`codex-rs/app-server-protocol/src/protocol/event_mapping.rs:187` 和 `codex-rs/exec/src/event_processor_with_jsonl_output.rs:237`、`:324`。

exec JSONL 的 `turn.completed.usage` 复制主 thread 最近一次 `thread/tokenUsage/updated` 的累计 `total`。exec 入口按主 thread ID 和当前 turn ID 过滤通知。续跑同一 thread 时，直接使用此数会包含已累计的历史值。汇总全树成本需要读取各子 thread 的计数。对应文件为 `codex-rs/exec/src/lib.rs:1441`、`:1797` 和 `codex-rs/exec/src/event_processor_with_jsonl_output.rs:119`、`:512`、`:536`。
