# G1 Hermes 原生接口实机验证

**2026-11-16 · 通过。** 实测对象为既有 Hermes Gateway 0.23.1，服务端提交 `18e659dfc93ef319771d51441573e3fa31b8f5b7`，本地 attach CLI 提交 `e7b9eb6c7d89f1df2b63ef4bbf68e986e88ac786`。以下观察适用于运行中的服务端版本。没有重启共享 Gateway、改配置或发飞书消息。

使用 `hermes gateway attach --json` 的发现模式连接 loopback，协商 `hermes-gateway-v1`，在 `runtime.describe` 协商后创建一个 `source: "tool"` 会话。测试 cwd 为独立临时目录，工具集仅 `terminal`，每轮上限 3 次。工作负载要求执行一次短等待与输出测试标记，无交易、文件写入或外部发信。attach 的票据只在进程内传给 WebSocket。初次握手因客户端沿用系统代理以 `InvalidMessage` 失败，未发送 RPC。改用 Hermes 客户端同样的 `proxy=None` 后，验证运行耗时 28.47 秒。 [公共 attach 契约](/Users/season/workspace/github/hermes-agent/website/docs/developer-guide/gateway-internals.md:582) · [客户端直连](/Users/season/workspace/github/hermes-agent/hermes_cli/gateway_client.py:381)

| 检查 | 实际观察 |
| --- | --- |
| 创建与重试 | `session.create` 返回相同的逻辑 ID 和存储 ID。完全相同的 `request_id` 及参数重试返回同一会话。复用 ID 且改 `max_turns` 返回 `invalid_params`。 |
| 输入幂等 | `prompt.submit` 先返回 `queued` 收据。完全相同的 `input_id` 与正文重试返回同一 admission。复用输入 ID 且改正文返回 `admission_conflict`。 |
| 忙时追加及取消 | 首个输入已 `started`，执行代次 1。第二个输入为 `queued`，对其 admission 调 `prompt.cancel` 得到 `terminal/cancelled`，首个输入继续并最终完成。 |
| 断开、回放、恢复 | 关闭观察端前最近一次首个输入收据仍为 `started`。新连接使用原 epoch 和游标调用 `session.events.since`，得到 10 帧，`snapshot_required=false`。随后 `session.resume` 返回同一逻辑会话。 |
| 实际执行、工具与用量 | 首个输入最终 `terminal/completed`，结果含测试标记，`api_calls=2`。汇合去重后的流中有 `tool.start`、`tool.complete` 各 1，`session.usage` 和 `message.delta` 各 2。精确终态收据的 input/output/total tokens 为 12,219 / 238 / 12,457。 |
| 运行中取消 | 第三个输入进入 `started`，执行代次 2。对它调用 `prompt.cancel` 时回执仍为 `started`，轮询终态为 `terminal/interrupted`。客户端应观察终态，避免把取消请求的回执提前显示成已结束。 |

本轮验证覆盖运行中的 Gateway 重附着、同进程回放和精确 admission 控制。进程冷恢复、第二条排队输入自然执行、`steer`、ACP/HTTP 的等价性和飞书原生事件交付均超出本轮实测。测试会话保留在 Gateway 历史，末次观测时三个 admission 都已终结。

脱敏后的 [结构化观察](../hermes/G1-observation.json) 来自本次探针的标准输出。
