# G0 飞书链路验证状态 — 2026-11-16

最新状态：已确认仓库存在 e7b9eb6c7d 飞书纯文本 @ → 原生 mention 补丁，且有既有验证/部署记录；仅作为临时修复和现状证据；正式 mention 机制以架构讨论为准。下述为本轮环境探测记录，F1–F5 未复验，不应解读为 mention 功能缺失。没有发送任何飞书测试消息。

- `hermes gateway status`：launchd 托管服务运行，提示服务定义相对当前安装陈旧。未执行 start/recover/restart。
- 运行态 gateway_state：运行代码 18e659dfc93ef319771d51441573e3fa31b8f5b7，版本 0.23.1；审计源码与 live 版本不同；当时 active_agents=1。
- 已连接平台为 default:feishu、reverse-engineering:feishu。served profiles 列表不等于各 profile 均有连接机器人。
- default channel directory 只有标记为 dm 的主会话及话题；只读查询 default 和 reverse-engineering 的 sessions 渠道元数据同样均为 dm。未读取用户消息正文。quant-research、data-steward 未发现飞书 session。
- `hermes -p data-steward send --list feishu` 和 quant-research 同命令均返回 no targets found。
- 旧部署文档提到的 `/Users/season/investment-lab/deployment/feishu/roster.json` 当前不存在。未据旧文档连接远程设备或假定群身份。

后续群内验收所需信息（不阻塞当前设计）：测试群 chat_id（或可定位的群名）和两个机器人身份/profile。已向用户请求。不能把 dm 元数据作为现有群发送授权的目标，也不能把源码中的 include_bot/allow_bots 行为充作真实投递证据。

审批记录：一次整段平台配置读取被自动审批拒绝，原因是可能输出 app secret/token。未执行该命令，未尝试绕过；继续使用仅含会话来源/类型等非敏感元数据的只读核对。

F1 真实人类与 bot mention、F2 群内话题身份、F3 忙时群消息归属、F4 群侧重复/停止、F5 bot 转述不能解除人类停止全部未测。G1 原生接口结果不能替代这些群链路证据。
