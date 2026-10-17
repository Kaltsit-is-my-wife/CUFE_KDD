# 外部代码仓库

本目录用于保存本地阅读、对比和实验所需的第三方代码仓库。外部仓库源码不纳入
`CUFE_KDD` 的 Git 提交；`.gitignore` 只保留本清单，避免把第三方历史、依赖缓存、
数据集或模型文件提交到本仓库。

## 已导入仓库

| 项目 | 本地目录 | 来源 | 本地快照 | 用途 |
|---|---|---|---|---|
| MARTI | `external/marti/` | [TsinghuaC3I/MARTI](https://github.com/TsinghuaC3I/MARTI) | `main` @ `093c151ecab8c10fc0d25491fc2aeac3c693209a` | 多智能体强化训练与推理 |
| ChatDev | `external/chatdev/` | [OpenBMB/ChatDev](https://github.com/OpenBMB/ChatDev) | `main` @ `a2ea4a263cebe9a7abd01ee3b5b0bf95698ed328` | 通信式多智能体软件开发 |
| ChatDev / Puppeteer | `external/chatdev/` | [OpenBMB/ChatDev/tree/puppeteer](https://github.com/OpenBMB/ChatDev/tree/puppeteer) | `puppeteer` @ `b24e6e6bd00bb04d317e0447cb7acb1e4973c83a` | 动态编排器版本 |
| OxyGent | `external/oxygent/` | [jd-opensource/OxyGent](https://github.com/jd-opensource/OxyGent) | `main` @ `cd96268de5814dfb4e0444cfd687f97508cf996a` | 模块化、可观测多智能体系统 |
| SYMPHONY | `external/symphony/` | [ZHUWEI-hub/SYMPHONY](https://github.com/ZHUWEI-hub/SYMPHONY) | `main` @ `3fbe29839285cd4e4b6f26fa1a639b3dc4c94937` | 异构模型协同规划 |
| AgentNet | `external/agentnet/` | [zoe-yyx/AgentNet](https://github.com/zoe-yyx/AgentNet) | `main` @ `325d39f2a940be5fa903d28c411bd3426b8007f5` | 去中心化演化式协调 |
| AgentVerse | `external/agentverse/` | [OpenBMB/AgentVerse](https://github.com/OpenBMB/AgentVerse) | `main` @ `f90c4bd9680fdd3bcff8c52c9170911a59b23478` | 多智能体协作与涌现行为 |
| MetaGPT | `external/metagpt/` | [FoundationAgents/MetaGPT](https://github.com/FoundationAgents/MetaGPT) | `main` @ `11cdf466d042aece04fc6cfd13b28e1a70341b1f` | 角色化软件开发协作 |

以上本地副本按浅克隆方式导入，用于固定当前代码快照；如需完整历史，应在对应外部
仓库目录中单独执行 Git 操作。

## 使用规则

1. 外部仓库只用于阅读、基线比较和实验验证，不直接作为正式实验依赖提交。
2. 正式实验代码应放入对应的 `experiments/NNN-short-name/`，只迁移实际需要且可审阅的
   代码，并在实验 README 中记录来源、许可证、commit、修改内容和运行方式。
3. 外部仓库中的数据集、模型权重、密钥、缓存和大日志不得复制到本仓库。
4. 使用或改编代码前，先阅读该项目的许可证和引用要求；许可证文件仍以外部仓库副本为准。
5. 若外部仓库被删除后重新导入，应更新本文件中的快照 commit，并在相关实验文档中同步版本。
