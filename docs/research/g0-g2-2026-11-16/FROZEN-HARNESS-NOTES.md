# Frozen harness：本机配置与原生 V2 继承核对

后续实测更新见[边界验证](boundary-validation/README.md)：三消息仍有8次用量增量、100,110总tokens；原生budget共享但非硬上限，冷恢复可重置。本文保留此前分析/校准的历史范围，不把不同任务的用量相除为优化倍数。

日期：2026-11-16。范围：只读源码、隔离临时目录中的无模型 CLI 检查；本子研究没有运行真实模型、读取凭据、修改全局配置、安装依赖或修改产品代码。末节引用主研究随后完成的一条真实机制校准，不是本子研究另起的模型调用。

## 结论与证据边界

- 实装程序：`/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex`，`codex-cli 0.169.0-alpha.11.1`。
- 本地源码：`/Users/season/workspace/github/codex`，HEAD `e241c18544bab47f729dbfea6d6f2e21531ba0a7`。没有证明这个 HEAD 就是该二进制的构建提交；下面确实发现了配置版本差异。
- `skills.enabled=false` 无效。实装 binary 的 strict 配置检查明确返回 `unknown configuration field skills.enabled`。自动 skills 提示的正确键是 `skills.include_instructions=false`。
- 本机无模型 `debug prompt-input` 实验验证：相同合成 skill，在 include_instructions=true 时出现在 input；false 时不再出现。此结果验证初始 input，不等于验证整个原生 peer 生命周期或完整 tools 数组。
- 当前源码原生 V2 fresh child 从父 turn 的有效 Config 克隆；`fork_turns=none` 选择空历史，不表示空配置。显式 skills/plugin 开关进入这个克隆。没有找到“fresh child 必然重新加载用户 config”的依据。
- 因此可以明确关闭自动 skill 注入与插件总门，并让源码中的原生 V2 继承这些设置；**还不能仅凭配置解析成功声称任意 root/peer 的完整模型输入和工具表已经相同或冻结**。模型能力、动态工具、外部环境、项目/托管层、已有历史仍须单独核验。

## 实装二进制已接受的配置键

以下完整 TOML 以隔离 HOME/CODEX_HOME 写入临时 config.toml，执行 `codex app-server --strict-config --print-startup-config`，exit 0、stderr 空：

```toml
cli_auth_credentials_store = "file"
web_search = "disabled"

[agents]
enabled = true

[skills]
include_instructions = false

[skills.bundled]
enabled = false

[cloud.skills]
enabled = false

[features]
plugins = false
apps = false
recommended_plugins = false
skill_search = false
multi_agent_v2_dynamic_tools = false

[features.multi_agent_v2]
enabled = true
```

这是一份已验证字段兼容性的隔离配置，不是万能的工具 allowlist。`cli_auth_credentials_store="file"` 是本次无凭据临时检查使用的设置，避免使用真实 HOME 下的配置与 keyring；没有把真实账户配置复制到临时目录。

| 键 | 精确语义和源码锚点（均相对 Codex repo） |
|---|---|
| `skills.include_instructions=false` | 关闭自动 skills instructions；`config/src/skills_config.rs:41` 定义，`core/src/config/mod.rs:4330` 默认 true；`ext/skills/src/extension.rs:208` 直接不贡献 thread skills，`:400` 控制 turn catalog fragment。路径前缀均为 `codex-rs/`。 |
| `skills.bundled.enabled=false` | 关闭 bundled skills，默认 true；`config/src/skills_config.rs:59`、`:138`。不能代替关闭 host/plugin/executor/cloud 来源。 |
| `skills.config=[{name="…",enabled=false}]` 或 path selector | 单个技能的禁用规则；`config/src/skills_config.rs:20`、`:165`。名称是精确相等匹配，没有通配符；规则只取 User 与 SessionFlags 层。不是所有来源的统一禁用开关。 |
| `cloud.skills.enabled=false` | 单独 cloud skills 开关；`core/src/config/mod.rs:3485`，默认 true。不能把它理解成所有 skills。 |
| `features.skill_search=false` | 禁止该实验的 skill shadow-selection 功能；`ext/skills/src/preparation.rs:92` 在 instructions 与 shadow selection 均关闭时返回空 host catalog。 |
| `features.plugins=false` | 插件总门；`core/src/config/mod.rs:1902` 将该 feature 放入 PluginsConfigInput；`core-plugins/src/manager.rs:945` 在关闭时直接返回空 PluginLoadOutcome；`:921` 关闭插件 skill snapshots。默认 true 的定义在 `features/src/lib.rs:1914`。 |
| `plugins._default.enabled=false` | 默认禁用 installed plugin，但显式 plugin enabled=true 可以覆盖；`config/src/types.rs:1157`、`:1174`。因此它不能代替上述总门。单个插件为 `plugins."id".enabled=false`。 |
| `features.apps=false` | 关闭 Apps 功能门。与 plugins 是不同开关；角色配置允许分别收紧二者，`core/src/agent/role.rs:92`。 |
| `features.recommended_plugins=false` | 推荐插件单独 feature，`features/src/lib.rs:1908`。 |
| `features.multi_agent_v2_dynamic_tools=false` | 不向 fresh V2 child 继承客户端 DynamicToolSpec；`core/src/agent/control/spawn.rs:98`。默认 false，`features/src/lib.rs:1686`。这不是禁止全部原生或 MCP 工具。 |

`skills.include_instructions=false` 不撤回旧历史中已经注入的内容，也不限制模型通过仍然开放的文件/终端工具自行读取 SKILL.md。实验的“禁止使用 skills”文字指令和自动 catalog 注入开关是两件事。

## 为什么原来的参数不足；哪些原因尚未被证实

`--ignore-user-config` 在 `codex-rs/config/src/loader/mod.rs:550` 只让用户 config 层变成空 table。系统层仍加载（`:280`），项目层另由 ignore_project_config 控制（`:345`）；它不清空 CODEX_HOME，也不等于禁用 plugins、skills、账户插件发现或宿主能力。

Exec 把此 loader override 传给内嵌 server：`codex-rs/exec/src/lib.rs:396`、`:793`。因此不能从 G2 结果直接推论“exec 丢失了 ignore_user_config”。

既有 `g2/context-audit.json` 记录：例如 market-B-1-persistent root 初始 catalog 为 4 项/2123 字符，peer 为 86 项/29210 字符；market-B-2-persistent 的 root 和 peer 初始均为 86 项/29210 字符。至少这证明 86 项不是 peer 独有状态。原始参数没有关闭上述来源，不能保证 catalog 冻结。当前源码有 catalog/snapshot/插件缓存和动态发现路径，但本次没有取得可以把那一条 G2 4→86 唯一归因到某个具体异步刷新或配置重读的证据；**不把推测写成根因**。

## V2 child 继承路径

1. `codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs:124` 调 `thread_spawn::spawn`。
2. `codex-rs/core/src/thread_spawn.rs:144` 调 `prepare_agent_spawn_config`，明确选择 V2。
3. `codex-rs/core/src/agent/child_config.rs:125` 构建 child config，`:148` 的 shared helper 从 `turn.config` clone，并保留配置层栈；刷新当前模型、reasoning、权限和 cwd。
4. fresh child 会应用角色；`core/src/agent/role.rs:72` 没有 config_file 就直接返回，`:173` 从现有 config clone 并加入 session 配置。skills/Plugins/Apps 角色规则只允许收紧（`:92`、`:109`），不是回到用户全局配置。
5. `core/src/tools/handlers/multi_agents_v2/spawn.rs:228`：none 返回无 fork mode；all 为 FullHistory。只影响历史选择，不能作为隔离配置参数。

这条链是当前源码证据。已验证二进制字段兼容性；末节主研究校准补充证明一组真实 root/peer 的 skills catalog 均已清除，未证明完整输入相等。

## 工具限制的实际边界

- 配置没有一个 `tools=[allowlist]` 式的统一原生工具白名单。`codex-rs/config/src/config_toml.rs:709` 的 ToolsToml 只包含 client_search_provider、web_search、experimental_request_user_input、update_plan。
- 关闭网络搜索使用顶层 `web_search="disabled"`。不要把 `tools.web_search=false` 当作等价物：`config/src/config_toml.rs:775` 的兼容 boolean 解析路径不返回设置。
- MCP 的精确工具名单为 `mcp_servers.<server>.enabled_tools=[…]` / `disabled_tools=[…]`；deny 在 allow 之后生效。关闭某服务器为其 `enabled=false`。定义：`codex-rs/config/src/mcp_types.rs:242`、`:291`。
- 插件 MCP 对应 `plugins."id".mcp_servers.<server>.enabled` / `enabled_tools` / `disabled_tools`：`config/src/types.rs:1225`。关闭插件总门时无需逐项列举插件 MCP。
- 独立配置中没有 MCP 项，并不自动证明系统/托管层没有 MCP。`-c mcp_servers={}` 是配置 merge，不能未经检查声称已经删除低优先级所有条目。
- 不要为减少工具而设置 `features.multi_agent_v2.disable_native_tools=true`：它关闭的是 V2 协作原生工具；`core/src/tools/spec_plan.rs:775`。这样会破坏需要 native spawn 的实验条件。
- 其它原生工具由 feature、模型信息和 spec plan 共同选择；固定模型、配置和来源之后仍应审计实际请求 tools。`debug prompt-input` 仅输出 input，不输出完整请求 tools。

## 配置读取和 schema

- 源码 config schema：`codex-rs/core/config.schema.json`；生成方法 `just write-config-schema`，recipe 在 `justfile:173`，执行 `cargo run -p codex-config-schema --bin codex-write-config-schema`。本研究未运行构建或安装。
- `codex app-server generate-json-schema` 是 **app-server 协议** schema，不能当成该二进制完整 config.toml schema 的替代物。
- `codex app-server --strict-config --print-startup-config` 做加载/字段校验，打印 appServerVersion 与 configRequirements；**不打印完整有效配置，也不证明某门在 inference 时生效**。
- 要读取有效配置可调用 app-server JSON-RPC `config/read`，参数 `{"includeLayers":true,"cwd":"/isolated/work"}`。协议定义 `codex-rs/app-server-protocol/src/protocol/v2/config.rs:392`；实现 `app-server/src/config_manager_service.rs:136` 应用 layers 与 exact requirements 并返回 config/origins/layers。仅在隔离配置运行、仅保存目标字段，不应把用户真实配置或凭据输出到研究材料。
- 当前源码 schema 与二进制不是同一份版本保证；必须像下节一样让实装 binary 验证具体字段。

## 可复现、无模型静态验证

已实际执行，两个 prompt 检查退出 0、stderr 空；使用 Python `subprocess` 传入全新 env（只有 HOME/CODEX_HOME/PATH/TMPDIR），未继承账户 token 环境变量，临时目录结束自动删除。

```python
import json, pathlib, subprocess, tempfile
binary = "/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex"
with tempfile.TemporaryDirectory(prefix="codex-freeze-prompt-") as tmp:
    root = pathlib.Path(tmp)
    home, work = root / "home", root / "work"
    home.mkdir(); work.mkdir()
    skill = home / "skills" / "frozen-probe"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: frozen-probe\ndescription: FROZEN_HARNESS_SKILL_MARKER\n"
        "---\nSynthetic static probe.\n")
    env = {"HOME": str(home), "CODEX_HOME": str(home),
           "PATH": "/usr/bin:/bin", "TMPDIR": str(root)}
    base = '''cli_auth_credentials_store = "file"
model = "gpt-6.1-sol"
model_provider = "static_fixture"
web_search = "disabled"
[model_providers.static_fixture]
name = "Static no inference"
base_url = "http://127.0.0.1:9/v1"
wire_api = "responses"
[features]
plugins = false
apps = false
skill_search = false
recommended_plugins = false
[cloud.skills]
enabled = false
[skills.bundled]
enabled = false
'''
    for enabled in (True, False):
        (home / "config.toml").write_text(
            base + "\n[skills]\ninclude_instructions = "
            + str(enabled).lower() + "\n")
        p = subprocess.run(
            [binary, "debug", "prompt-input", "STATIC_PROBE_USER_MARKER"],
            cwd=work, env=env, capture_output=True, text=True, timeout=25)
        print({"include_instructions": enabled, "exit": p.returncode,
               "skill_marker": "FROZEN_HARNESS_SKILL_MARKER" in p.stdout,
               "user_marker": "STATIC_PROBE_USER_MARKER" in p.stdout,
               "input_items": len(json.loads(p.stdout))})
```

本次结果：true → skill_marker=true、user_marker=true、7 input items、61518 输出字符；false → skill_marker=false、user_marker=true、7 input items、60783 输出字符。输出字符不是 token 测量。程序源码 `codex-rs/core/src/prompt_debug.rs:89` 明确只构建 prompt，不进入 run_turn；它不调用生成接口。这里 provider 也被指定到未运行服务的本机端口，不使用真实 provider。

另外以 strict startup check 做负对照：`[skills]\nenabled=false` → exit 1，unknown field；上文完整冻结配置 → exit 0。解析检查和 prompt 检查分别证明字段支持、初始自动目录行为，不能互相代替。

## 补充：rollout_budget 是共享预算，但不能保证绝不超额

父研究要求补查预算；本节只记录源码和无模型解析结果。

实装 alpha.11.1 接受：

```toml
[features.rollout_budget]
enabled = true
limit_tokens = 80000
reminder_at_remaining_tokens = [20000]
enforce_limit = true
```

上面与父研究校准相同的组合已静态复核：exit 0、stderr 空。另 `limit_tokens=1000` 与 `reminder_at_remaining_tokens=[]` 也通过。缺少 reminders 字段时明确报 required。

**实装 binary 不接受** `limit_budget` 或 `reminder_at_context_start`：分别加这些字段均报 FeatureToml 反序列化失败。不是 empty-array 问题。源码提交 `c8e4cbcd94`（2026-11-14，Support fractional rollout budgets and configurable context reminders #61579）才新增这两个字段；当前 HEAD schema 支持它们，不能据此认定旧 binary 支持。

共享与硬上限边界：

- 当前源码 `core/src/agent/control/runtime.rs:232` 持有 Arc<RolloutBudget>；`core/src/session/session.rs:1811`–1817 让 child 使用 native controller 的同一 Arc；`core/tests/suite/rollout_budget.rs:290` 的现有测试名为 subagent_usage_draws_from_the_shared_budget。本研究未运行该测试。
- 计费 fallback 是 output_tokens × sampling_token_weight + **non-cached** input × prefill_token_weight；provider 若给 codex_rollout_budget_units 则采用该值。两权重当前默认 1。见 `core/src/rollout_budget.rs:123`–139、`core/src/config/mod.rs:3124`。这不是直接限制所有 usage.total_tokens，也不是美元预算。
- 使用量在 response 收到后入账，再关闭新工作 gate；在途调用仍可消耗。因此不能把 limit_tokens 当作预先保留的、不可能超过的全树硬 token cap。当前源码 `core/src/rollout_budget.rs:42`、`:108`、`:158` 明确这一点。
- 新 HEAD 超过 limit（带浮点 next_up 容差）才停；`c8e4cbcd94^` 的历史实现 `core/src/rollout_budget.rs:20` 同样明示 one root-thread session tree，`:66`–73 则在 weighted_tokens_used >= limit_tokens 后 stop_new_tools。旧/新边界行为不同，不应把当前 HEAD 的精确停止语义直接套给 alpha.11.1。
- 本次没有动态测量 binary 的预算实际停止点或并发超额量。字段通过严格解析、存在预算提示、真正共享扣费、耗尽后的行为分别是不同证据等级。

## 主研究提供的一次真实校准（追加引用）

证据：本目录 `calibration-v2/settings.json` 与 `calibration-v2/observation.json`。配置关闭 skills instructions/bundled/cloud、plugins/apps、web search，并启用原生 V2、两个并发槽、80000 limit_tokens。主研究报告运行 35.62 秒、exit 0、stderr 空；以下数字直接读取 observation 文件。

- 真实 root 调用 collaboration.spawn_agent，fork_turns=none，gpt-6.1-sol/medium；恰好一个 peer，产出 PEER_OK，root 产出 ROOT_OK。
- root 三次模型调用的 input_tokens 为 11831、11927、12011；peer 一次为 11380；树合计 usage.total_tokens=47258，其中 cached_input_tokens=23552、output_tokens=109。
- root 与 peer 的 skill_catalog_blocks 均为空。这比只看退出码更直接支持“本次原生 fresh peer 没有再次注入 86 项目录”。该校准材料不同于旧 G2，不能计算质量改善率。
- 两者 base instructions SHA 相同；完整 developer context 有角色差异；additional_tools 的 SHA 不同，serialized_chars 分别 28115 与 25653。因此本次没有实现或证明 root/peer 完整工具数组相同。
- root、peer 的 developer_prefix **都列出了 `<rollout_budget>`**，各 106 字符但 hash 不同。文件同时给出 budget_marker_count 为 root=1、peer=0；它与片段存在性不等价，不能据后一个数字声称 peer 没有预算提示。具体剩余额度需按原始片段另行核对。
- 本次没有耗尽 80000 预算，不能证明预算停止行为或绝不超额；也不能用一次校准推定所有后续会话都冻结。
