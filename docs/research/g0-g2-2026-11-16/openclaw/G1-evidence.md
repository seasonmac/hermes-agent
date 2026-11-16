# G1 OpenClaw 实例与原生接口验证

**2026-11-16 · 已按用户要求延后，非当前阶段阻塞项。** 以下保留此前有界环境检查结果；不再继续动态验证。 当前工作环境中未找到可用于隔离会话测试的 OpenClaw Gateway。下列检查只涵盖常用安装位置和已知入口。自定义前缀、其他端口或未记录的远端部署状态未知。

| 检查 | 实际观察 |
| --- | --- |
| CLI 和包管理器 | `command -v openclaw` 无结果。`node`、`npm`、`bun` 和 `docker` 未在当前 PATH，存在 Codex 捆绑的 Node 和 pnpm fallback。捆绑运行时下未找到 npm 或全局 OpenClaw 包。 |
| 常用安装与服务路径 | Homebrew 和 `/usr/local` 的 bin/global `node_modules`、用户 npm/pnpm/Bun/Volta 路径、常用 Node 版本管理器目录、`~/.openclaw` 本地前缀、macOS app 与 LaunchAgent/LaunchDaemon 文件均无匹配。项目的同级目录中未发现 OpenClaw checkout。沙箱中的 `pgrep` 无法取得进程列表，未用它判断服务是否存在。 |
| 项目文档与环境 | `README.md`、`docs/006-deployment.md` 和现有飞书协作研究无已部署 OpenClaw 入口，研究中的 OpenClaw 链接指向公开资料。已检查 Gateway 地址及状态目录覆写的环境变量是否存在，未读取其值。 |
| 官方客户端入口 | 只检查 `127.0.0.1:18789`（默认）与 `127.0.0.1:19001`（dev 默认）。沙箱内均返回 `EPERM`，自动审查放行后同一只读 TCP 检查均返回 `ECONNREFUSED`。因此在检查时该 IPv4 地址的两个已知端口没有可连接的服务。 [官方端口说明](https://docs.openclaw.ai/gateway#port-and-bind-precedence) |

未发送 Gateway RPC。会话创建及输入幂等、忙时 `followup`/`steer`、工具事件与用量、运行级取消、重连重附着全部待测。G1 需要一个可访问且已有测试权限的 Gateway，具备会话读/写权限和可用模型，并允许使用无飞书投递路由的隔离会话。静态接口参考版本为官方 `v2026.11.3`，提交为 `847611dcaa3bf0e2783335f961dd1fd0580e4d9f`。 [发行记录](https://github.com/openclaw/openclaw/releases/tag/v2026.11.3) · [Gateway 客户端接口](https://docs.openclaw.ai/gateway/clients)
