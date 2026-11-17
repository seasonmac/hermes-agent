# T0-P：零付费适配验证结果

2026-11-17。范围来自[冻结协议](protocol.md)；接续 [T0 静态基线](../adapter-preflight.md)。

**Codex 在安装版上通过了终态后的动态工具冷恢复；Hermes 通过了公开加载器、合成身份派发和候选权限配置核对。整个 T0-P 尚未完成：真实模型工具选择、真实用量与辅助费用仍未验证。** 本轮不修改产品实现，不启动现有 Gateway，不接飞书，不测试 OpenClaw/DSH。

## 版本与证据范围

| 对象 | 本轮实际执行 | 边界 |
|---|---|---|
| Codex | `0.169.0-alpha.11.1`；二进制 SHA-256 与 T0 一致；真实独立 AppServer＋本机 Responses SSE fixture | provider 只有 loopback，不继承认证变量，独立 CODEX_HOME；服务协议是真的，模型回答和 usage 是合成的 |
| Hermes | 源码 `cf02ef9e5196649b0884b0fd4e9ca341b42cc9bb`；安装 Python 3.14.9；只读选择已有 PM 依赖 | 直接使用真实插件加载器、策略构建器和工具派发器；未运行 CLI bootstrap、Gateway 或 AIAgent；原生身份参数由测试端构造 |

Hermes 每个配置使用独立临时 HERMES_HOME、空工作目录、空 bundled-plugin 目录和显式用户插件允许列表。Python audit guard 禁止连接、子进程、读取真实用户配置/凭据与临时目录外写入；最终三组均没有触发这些禁止项。这是诊断隔离，不是产品沙箱承诺。

## Codex：冷恢复实际通过了什么

最终一次运行有 **4 次本机合成 Responses 请求、2 个 turn、2 次动态工具回调**，三个 AppServer 实例均关闭 stdin 后正常退出，无 terminate/kill。

| 检查 | 实际结果 |
|---|---|
| 实验能力门控 | 未声明 experimentalApi 的连接提交 dynamicTools，返回 `-32600`；未触发 provider |
| 正常工具路径 | fixture 经实际暴露的 `functions.exec` 调用 `tools.collab_send`；控制端收到 `item/tool/call`，threadId/turnId/callId 齐全，参数逐字一致 |
| 旧服务结束 | 第一轮 completed 后关闭 stdio，进程退出码 0，随后才启动新服务 |
| 恢复查询 | 新连接重新 initialize；`thread/resume` **只传 threadId，不重传 dynamicTools**；`thread/read` 返回原 turn，provider 增量 0 |
| 恢复后工具 | 第二轮仍包含同一工具声明，并产生正确回调、回执和 completed；恢复前后有效工具定义相同 |
| 合成累计值 | 每次响应给定 input=11、cached input=3、output=2、reasoning output=1、total=13；第一轮累计 26，第二轮累计 52。cached/reasoning 是相应部分，不能再加到 total |

原始记录：[codex.json](observations/codex.json)。预先落盘的[调用意图](observations/codex.intent.json)保留 Mission/Step、请求 ID、正文与 hash。该探针没有独立协作运行时，也没有证明业务消息 exactly-once。

### 两项必须进入适配路径的修正

1. **不能只查顶层 `tools`。** 本版本将工具表放在 `input` 的 `additional_tools` 项，并把 `collab_send` 的 TypeScript 声明放入 `functions.exec` 描述。最初探针误把两个空 `tools` 数组相等当作 schema 稳定；发现后保留诊断记录，改为校验真实声明并走 exec，重新验证通过。
2. **原生子 Agent 需要显式 `agents.enabled=false`。** 最初只设 multi_agent/multi_agent_v2=false，实际仍出现 collaboration 工具；最终配置加入 agents.enabled=false 后不再出现。必须检查实效表，不能只检查配置文本。

即使关闭 shell、apps、plugins、web 和原生子 Agent，最终仍有 `functions.exec/wait/request_user_input/request_user_input_async`、`clock.sleep`，以及 exec 内的 apply_patch、goal、resource、view_image 等工具声明。因此，**Codex 当前不能声称“只有协作工具”**。本轮 read-only/never 配置由 AppServer 接受，但没有尝试文件写入或人类审批流程来证明这些内置能力的执行限制。

本轮没有在待决 `item/tool/call`、provider 已接受未终态、回执丢失或收费未知窗口重启；这些仍属于 T8。没有测试删除/损坏 CODEX_HOME 或迁移设备。

## Hermes：safe_mode 替代配置与身份边界

最终运行三个独立进程：unguarded、guarded、safe。插件通过公开 `plugin.yaml → discover_plugins → register(ctx) → ctx.register_tool` 路径加载；测试插件只返回 JSON，没有收件网络、真实群聊或模型调用。

| 配置 | 观测 |
|---|---|
| 环境 safe mode | `HERMES_SAFE_MODE=1` 时插件不加载 |
| session safe mode 对照 | 已加载插件的进程里，构建 safe_mode=true 策略，所选插件工具集被移除 |
| 候选正常配置 | 独立 profile；safe_mode=false、ignore_user_config=false、yolo=false；显式 `toolsets=[t0p_collaboration]`；`tools.tool_search.enabled=off`；最终生成的工具表只有 collab_send |
| 派发负对照 | 即使把 enabled_tools/toolsets 传给底层 handle_function_call，未选中的无副作用测试工具仍能执行 |
| 增加公开拒绝钩子 | 测试插件的 pre_tool_call 对不在允许列表的工具返回 block；相同未选中工具被拒绝，handler 未执行 |

**工具展示过滤与派发授权是两个边界。** 这不是已证实的完整 Agent 回合越权：本轮直接调用底层派发器，未经过完整 Agent 执行层。它说明适配器若直接使用该入口，不能把 enabled_toolsets 当作它已经实施的通用授权闸门。测试钩子只证明公开扩展点能拒绝该调用；钩子异常/超时、skip hook 路径、并发 profile、其他直接注册表入口尚未验证，不能把这个示例当作生产安全方案。

默认 Tool Search 会将插件工具转换为 tool_search/tool_describe/tool_call。短探针显式关闭它以固定工具表；未来要开启时须另验 bridge 的身份和权限，不在会话中途改表。

### 身份与回执观察

- 正常 handle_function_call 向 handler 传入 task_id、session_id、conversation_id；即使测试端传了 native turn_id/tool_call_id，它们也没有进入普通 handler。
- 缺上下文、与主调用共享 conversation 的 child session、旧 session、正文声称自己是 worker、未授权收件目标，均被测试插件的固定绑定规则拒绝；没有生成成功回执。
- 额外 `sender` 参数在进入 handler 前，被 Hermes 原生 schema 校验以“不存在此参数”拒绝。
- 正常合成身份返回原文和 `receipt:hermes-dispatch`。该回执仅是探针 JSON，**不是运行时持久消息回执**。

这些检查证明“真实加载器/派发器能承载所需的身份和拒绝逻辑”；它们不证明正常模型回合中的 task/session 就能直接唯一映射 Mission/Attempt，也没有验证压缩重绑定、插件 fork 或原生 delegation 的实际身份生成。

原始记录：[hermes.json](observations/hermes.json)；[调用意图](observations/hermes.intent.json)。源码锚点：[普通派发](../../../../model_tools.py:851)、[工具表组装](../../../../model_tools.py:524)、[safe_mode 策略](../../../../gateway/session_policy.py:669)、[公开 hook 合同](../../../../website/docs/developer-guide/plugins/index.md:1608)。

## 成本、诊断过程与能力变化

**本轮真实模型调用与真实模型实验 tokens 均为 0**，不包括执行研究的助手会话本身。最终 Codex 一次验证报告的 52 是 fixture 人工给定计数，不是 tokenizer 计算值，更不是账单。

包括排查及最终复核，共进行了 4 次 Codex fixture 运行、16 次本机响应；另一次初始启动在 loopback bind 阶段被沙箱拦截，未启动 AppServer。Hermes 的早期诊断分别发现：隔离 profile 后不能直接用它查询已有 PM 依赖选择；build_policy 需要 private_secrets 收集容器（只记录字段路径，不记录值）；默认工具桥接；原生参数拒绝早于插件拒绝。均修正探针，无产品改动。见[诊断记录](observations/diagnostics.json)和[前一次成功记录摘要](observations/prior-success.json)。

| T0 项 | 本轮推进 | 仍阻塞什么 |
|---|---|---|
| B01 版本 | Codex 当前安装版能力门控、回调、恢复实际验证 | Hermes 存活 Gateway 版本未查询；Codex 二进制与源码构建提交仍不等同 |
| B02 配置 | Hermes 候选隔离 profile、公开加载、直接工具表、拒绝钩子通过零模型检查 | 真正 Gateway/Agent 回合和完整权限边界未验证 |
| B03 身份 | 普通 handler 字段、缺失/冲突拒绝的合成案例通过 | 原生回合到 Attempt 的可信绑定、压缩/子调用、持久业务回执仍待验证 |
| B04 费用 | 未推进真实费用覆盖 | 主调用、辅助调用、流式/失败尾账与预约均未知 |
| B05 工具冷恢复 | **终态后、同目录、新进程、不重传定义的回调已通过** | 未决 RPC 及在途业务消息/费用的恢复不在此结论内 |
| B06 在途恢复 | 未测试 | 保留 T8 门槛 |
| B07 工具/来源 | 记录了 Codex 实效工具表、关闭原生子 Agent；Hermes 展示与派发分层得到验证 | Codex 内置权限、完整 Agent 执行层、opaque read_set 尚未证明 |

[calibration.json](calibration.json)明确标记 `real_model_cost_calibration=not_run`、T0_P_complete=false。36 万软预算本轮未消费；30,000/探针的未来额度没有被合成计数替代，也未据此推算 T1/T7/T8 费用。

## 复核与下一步

无网络的记录审计：

Python 语法、JSON、引用、观察记录和 artifact hash 均已核对。第一次提交钩子要求两处 subprocess.run 显式写出 check=False，已补齐（返回码仍由探针检查，语义不变）。正常仓库钩子还执行了默认 PM setup 校验/同步入口，输出工具和依赖已安装；这与探针本身不运行 bootstrap/安装是两件事。产品文件没有变化。

```sh
python3 -B docs/research/kernel-slice-validation/preflight/verify_evidence.py
```

复跑入口（Codex 需要允许 loopback bind；Hermes 不需要网络）：

```sh
python3 -B docs/research/kernel-slice-validation/preflight/probe_codex.py --binary /Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex --output docs/research/kernel-slice-validation/preflight/observations/codex.json
python3 -B docs/research/kernel-slice-validation/preflight/probe_hermes.py --repo /Users/season/workspace/github/hermes-agent --python /Users/season/.hermes/tools/python-3.14.9+20261021-darwin-arm64/bin/python3 --output docs/research/kernel-slice-validation/preflight/observations/hermes.json
```

下一步先确定两条适配器的有效工具/权限合同，再做获授权的正常模型最短 send 与费用覆盖探针；T8 仍须单独验证在途窗口。本轮在零付费子集结束，不启动这些后续任务。
