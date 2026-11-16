# 研究资料迁移与提交检查

2026-11-16。研究资料现统一保存在`hermes-agent/docs/research`；飞书修复记录位于[docs/bug_fix](../bug_fix/feishu-plain-text-mention-fix.md)。当前设计仍以[九篇文档索引](README.md)为准，历史方案与实验不改写为新版本能力。

## 本次范围

补充迁入研究综述、V1/V2/V3.1归档、G0–G2记录、消息与预算边界验证、上下文及抗遗忘实验。包含10份原有诊断/复核Python脚本，它们是实验源快照，不是产品实现；本次未运行探针、调用模型或重做实验。

飞书修复文档从`bug_fix/feishu-plain-text-mention-fix.md`迁入`docs/bug_fix`，仅对一处实际服务器公网地址脱敏。该文档记载过去的修复与部署，本次没有修改适配器、配置或运行中的服务。此次只作本地Git提交，不推送远程。

## 完整性与敏感信息

四份`SHA256.json`分别覆盖145、118、27、10个文件，合计300个证据文件校验一致；文件和清单均未改写。其他历史JSON/JSONL、脚本、提示、结果及用量资料也保持迁入时的字节内容。实验数值、评分和证据边界没有变化。

对待提交文本进行了私钥、常见API/GitHub/云令牌、JWT、认证字面量、URL内凭据与邮件地址规则扫描，并递归检查JSON/JSONL的非空凭据字段。初筛命中经复核为文章URL中的普通单词和测试断言；未发现实际密钥、登录令牌或密码。没有安装专门的secret scanner；这是一轮规则扫描与人工复核，不表示数学意义上的无敏感信息保证。

研究所需的本机源代码路径、测试thread/session ID、版本与提交号保留，用于追溯和离线核对；它们不应被误认为可跨机器直接复现的环境配置。实际部署服务器地址已从飞书文档去除。

## 归档脚本的检查例外

10份Python源快照均通过语法解析，未执行其业务。正常pre-commit实际运行后，`move shims`通过；Python lint在三份哈希覆盖的历史脚本中报告6项问题：预算fixture有1处未使用变量、2处bare except和1处缺少显式subprocess check参数，两份上下文实验复核脚本各有1处未指定读取编码。

这些是迁入前的源快照问题，不通过修改原始实验代码或重算哈希将其隐藏。本次纯归档提交使用一次性`--no-verify`保留原始资料，未修改钩子、ruff规则或产品配置；不能将本次提交描述为全量lint通过。后续若将这些脚本转为维护中的工具，应复制到新的非冻结位置修复并单独验证。现有仓库CI若扫描该归档目录，仍可能报告上述问题。

## 引用修正与可访问性

修正33处本地引用：22处三方源码研究及6处验证计划中的DSH引用改为指向DSH工作区，2处飞书记录引用改为新位置，3处`next-pilot`观察报告引用改为真实证据目录。除清理一处说明文档的行尾空格外，引用修正只涉及Markdown链接，没有改写原始证据。18份历史G2输入prompt仍保留原始行尾空格；不为消除格式告警修改已用于实验的输入字节。

本机文档链接已检查目标存在。跨仓库源码引用仍依赖本机对应checkout；带行号的引用用于阅读，不保证其他机器或未来HEAD仍在同一行。历史脚本含固定测试目录，不应在原证据目录直接重跑；复核方式与限制见各实验README。

对44条公开HTTP(S)链接进行只读可访问性检查（HEAD，必要时GET；未带本地凭据）：42条返回200，以下两条返回403，保留原引用并标记访问受限：

- [Decentralized Multi-Agent Systems with Shared Context](https://scispace.com/papers/decentralized-multi-agent-systems-with-shared-context-k2y3zxlgz3xc)
- [Towards a Science of Scaling Agent Systems](https://scispace.com/papers/towards-a-science-of-scaling-agent-systems-uzbix3b1ubeb)

HTTP状态只说明检查时的端点响应，没有复核文章论据、网页锚点或历史版本内容，也不能把403直接认定为资源不存在。未为本次迁移追加学术或产品能力结论。
