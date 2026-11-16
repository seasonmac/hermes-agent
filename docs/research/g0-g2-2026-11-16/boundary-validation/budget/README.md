# rollout_budget 实装边界验证

日期：2026-11-16。实装 **codex-cli 0.169.0-alpha.11.1**。只用独立 App Server + 127.0.0.1 确定性 Responses SSE；**真实模型调用 0，真实模型花费 0**。本地服务只返回合成文本、工具和 usage。没有读取用户凭据、修改产品代码/全局配置、安装依赖或外发消息。HOME 保持原值；CODEX_HOME 为每例临时独立目录；子进程环境不继承凭据变量；fixture 收到的所有请求均无 Authorization。

结论：预算确实累计扣费、跨 native parent/child 共享，也能终止自动续跑，但**不是拒绝一切新模型请求/工具、永不超额、跨进程持久化的硬上限**。

## 实测结果

| 情形 | provider 请求数/usage | 观察 |
|---|---|---|
| 同一 turn 自动续跑 | 首响应 input=120，上限100；1次请求 | 动态 `budget_probe` 已调用并成功返回 `PROBE_TOOL_RAN`；随后 turn failed/sessionBudgetExceeded；没有自动发出第二次请求。不能说此响应内工具被阻断。 |
| 显式新 turn | 累计请求1→2；第二响应再120 | 请求携带 remaining=0 提示仍送达 provider；工具仍实际执行成功；随后同样 failed。 |
| 同进程 thread/resume | 累计2→3；响应input=1 | remaining仍0，回合failed/sessionBudgetExceeded；没有重置耗尽状态。 |
| 停服后 cold thread/resume | 累计3→4；响应input=1 | 新增remaining=100提示，回合completed；**冷恢复重置预算的功能证据**，不仅是提示文字变化。 |
| 缓存输入口径 | 3请求；首 input=1000、cached=990、output=5 | 首回合completed；第二请求新增remaining=85，证明扣15而非1005。第二响应86令累计101并failed；第三显式新turn仍有请求，随后failed。 |
| provider units 优先 | 3请求；每次input=1000、output=10；units=5/96/96 | 首回合completed，即未按fallback1010扣费；第二后累计units101失败。无需把总token数误称预算单位。 |
| native parent/child 共享 | 5请求；首阶段root10+root10+child70=90 | fresh child由原生 `collaboration.spawn_agent` 创建，fork_turns=none。父下一请求提示remaining10；再返回20后父failed，此刻父自身仅40、子仅70，单独均未达100。子先completed/CHILD_OK。 |
| 两条响应已在途 | 首阶段3请求；spawn10+child100+root100=210 | fixture屏障确认root续请求和child请求均已进入后才释放；max_simultaneous_requests=2。child先返回，root约0.61秒后仍成功发送完整响应；两者rollout均记录usage并以session_budget_exceeded结束。**上限100实用210，超额110**。后两条显式新turn另发100+100，整例最终410；这200不是在途超额。 |

所有案例每个阶段的 before/after 请求数、usage、预算提示、RPC终态、事件和工具结果均在对应JSON。最终固定证据集共20个本地provider请求；先前传输/路由诊断及被替换的复核运行不计入这20，但同样真实模型调用为0。

## 方法与可复核材料

- `schema-check.json`：首先用实际binary `app-server generate-json-schema --experimental`生成协议schema，核对thread/start、turn/start、thread/read、thread/resume字段，记录schema SHA-256。没有把源码HEAD当binary协议保证。
- 每例`strict_config`记录实际`--strict-config --print-startup-config` exit0。接受的预算字段为 `enabled=true, limit_tokens=100, reminder_at_remaining_tokens=[90,50,10], enforce_limit=true`。
- `breach.json`：显式新turn、工具调用、同进程与冷resume对照。`events`保留同进程3个回合；`resumed_turn`为冷恢复终态。`tool_calls_received`是最初两个回合的计数，`first_server_tool_calls`是停服前计数。
- `cached.json`、`units.json`：缓存扣费和provider units优先级。
- `shared.json`、`inflight.json`：原生子代理及父子持久化rollout中的token_count/task_complete，含父子归属及共享root_turn_id。request role根据root用户输入标记识别，并由子rollout归属交叉验证。
- `fixture-reproducer.py`：一次性诊断脚本，使用Python标准库。运行参数为 `breach cached units shared inflight`。所有App Server有界运行并退出0，fixture关闭socket，临时CODEX_HOME/work在退出时删除；只保留此目录诊断材料。请求时间是同一fixture进程的monotonic时间，仅比较相对顺序。
- `summary.json`：对实际JSON执行断言后的精简结果：终态、每阶段计数、无Authorization、并发屏障、缓存remaining85、共享remaining10、cold完成及退出码。

第一次local bind受到sandbox限制，因此执行时使用已授权的require_escalated。初轮provider连接失败后依照已成功smoke使用 `respect_system_proxy=true`、`NO_PROXY=*`、`enable_request_compression=false`才连通；失败的0请求运行不能用于预算判断。初次shared/inflight路由匹配未识别child，修正为输入标记并以真实子rollout核验后重跑；只将修正后结果保留为上述结论证据。

## 结论范围

本实验测试100预算、默认权重与指定模拟usage；没有量化真实模型token准确率、成本或所有工具种类。动态工具只回固定字符串，没有副作用。自动同turn停止与显式新turn仍可请求是不同事实；冷恢复重置与同进程恢复保留也是不同事实。未验证恰好等于100的停止语义、任意多在途请求的最大超额或所有恢复入口，不能从本结果推成通用绝对上限。
