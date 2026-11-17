# T0-P 零付费验证协议

2026-11-17。依据 [实施计划](../../2026-11-16-kernel-slice-implementation-plan.md) 和 [T0 基线](../adapter-preflight.md)。本轮仅执行零付费子集，不作为整个 T0-P 完成或成本校准通过。

## 执行前冻结

- Mission `preflight-20261117`，Step `tool-roundtrip`，Attempt 分别为 `codex-before` / `codex-after` / `hermes-dispatch`。
- 工具 `collab_send`；目标 `peer-fixture`；原文 `SYNTHETIC_ONLY: preserve this message exactly.`；每次业务请求的 request_id 固定为对应 Attempt。不自动重试业务提交。
- Codex 使用安装二进制、临时持久 CODEX_HOME 和空工作目录。provider 唯一指向本机 fixture，无账户凭据、禁用重试；两次完整 turn，每次恰好一次工具调用、两次 Responses 请求。fixture 的 usage 是人为计数，不能用于真实费用预测。
- Hermes 使用已安装 Python 与现有依赖，只把测试插件复制进临时 HERMES_HOME。不执行安装/修复、不读真实 profile、不连接 Gateway、不创建 AIAgent。公开加载器和实际工具派发接收合成受信身份；不将其称为真实 Agent 身份证明。
- 只保留合成正文、受信 ID、schema、配置 hash、回执及终态。临时目录退出删除，正式源码和历史记录不改。

## 预设判据

1. Codex 未声明 experimentalApi 的连接拒绝 dynamicTools，provider 请求数为 0。
2. 开启能力后，同一线程工具请求的 threadId/turnId/callId 与控制端记录一致；正文逐字一致；回执进入后续请求；观察到 completed 和预设合成累计值。
3. 关闭 stdio，确认旧服务退出，再启动新服务。只传原 threadId 恢复，不重传 dynamicTools；resume/read 不触发 provider 请求；第二个 turn 仍出现相同 schema 的工具及正确回调。
4. 记录完整 provider tools 表，不能因只注入两个工具就宣称其他工具均已裁掉。
5. Hermes 真正经过公开插件发现/加载注册。正常配置显式选测试工具集，safe_mode 对照不暴露插件工具；yolo 关闭。记录策略和实际生成的工具表。
6. Hermes 经过真实 handle_function_call：传递 task/session/conversation；记录 turn/tool_call 字段是否进入 handler。测试缺绑定、共享 conversation 的 child、伪造正文身份、未授权目标、旧 session 和未选中工具。拒绝逻辑属于探针，不能算内核已实现。
7. 缺身份/权限/回执或配置漂移时保留失败，不改产品以迁就测试。任何网络模型请求、未知 provider 或非预期工具请求使探针失败。

## 本轮不会解除的门槛

真实模型是否选择工具、真实 tokens/缓存/辅助费用、压缩后重绑定、在途 RPC 恢复、月级恢复和飞书群交互均不在本轮内。正常终态后的冷恢复通过，也不等于接受后断线的 T8 通过。
