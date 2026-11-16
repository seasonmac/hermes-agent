# 独立协作运行时设计已分类整理

当前设计统一维护在[九篇分类文档](README.md)，V3.2补齐执行契约与适配路径，并区分内核切片和完整首版，保留此前需求与实验证据边界。文档现位于Hermes的`docs/research`。本文件只保留旧链接入口，不维护另一份规范。

| 文档 | 内容 |
|---|---|
| [000 Philosophy](000-philosophy.md) | 目标、原则与首版边界 |
| [001 Domain](001-domain.md) | 对象、协作关系与上下文 |
| [002 Authorization](002-authorization.md) | 准入、知识接受与人工控制 |
| [003 Execution](003-execution.md) | 工作流、mention、费用与月级恢复 |
| [004 Prompts](004-prompts.md) | Router、上下文包、缓存与提示版本 |
| [005 Panel](005-panel.md) | 飞书协作、状态与人的决策 |
| [006 Deployment](006-deployment.md) | 建议拓扑、节点恢复与验收关卡 |
| [007 Architecture](007-architecture.md) | 模块、记录与适配契约 |
| [008 Cookbook](008-cookbook.md) | 接入、场景与验证指南 |

证据见[三方源码对照](MULTI-AGENT-SOURCE-REVIEW.md)和[研究索引](README.md)。原文保存在[V3.1单篇归档](archive/collaboration-runtime-v3.1-2026-11-16.md)。
