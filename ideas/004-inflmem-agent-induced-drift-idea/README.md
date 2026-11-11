# [004] InflMem：Agent 诱导的偏好漂移与记忆误归因 Idea

> 本 idea 由 @member-01 发起，研究“agent 推荐被接受后，memory writer 是否把 compliance 误写成用户稳定偏好”。
> Week 1 的 P1 文档在 [`docs/`](docs/)；可运行实验尚未开始，对应实验目录计划为 `experiments/004-inflmem/`。

## 1. 基本信息

| 字段 | 内容 |
|---|---|
| Idea 编号 | `004` |
| 标题 | InflMem：Agent 诱导的偏好漂移与记忆误归因 |
| 状态 | `idea` |
| 负责人 | @member-01 |
| 协作者 | 待定（P2–P5） |
| 创建日期 | 2026-11-12 |
| 最近更新 | 2026-11-12 |
| 对应实验 | `not-started`（计划 `experiments/004-inflmem/`） |
| 讨论入口 | 本 idea 的 Pull Request / Week 1 kickoff |

## 2. 一句话摘要

长期记忆系统最危险的错误，不只是“忘记”或“检索错了”，而是把 agent 自己诱导出来的服从行为（compliance）写成用户稳定偏好，并通过后续推荐不断自我强化。本 idea 把 memory write 形式化为**因果归因问题**，用 provenance-aware 写入、配对反事实世界和 CMR/SFB 指标来测量并降低这种误归因。

## 3. 问题与背景

- **科研问题**：跨会话记忆系统普遍假设“用户选择了 X，就说明用户偏好 X”。但在 agent 交互中，用户接受 X 可能只是因为 X 是唯一展示的选项、被放在显眼位置、用户信任 agent 或只想尽快结束任务。这些是 compliance，不一定是 internalization。
- **为什么现在值得研究**：跨会话记忆正成为 LLM agent 的默认能力；记忆写入层的因果上下文（agent 做了什么、用户看到了什么）通常在 LLM 摘要时丢失；错误记忆会通过“推荐 → 接受 → 写入 → 再推荐”形成自我强化闭环。
- **已知方法的不足**：现有工作分别研究记忆召回、记忆冲突、记忆投毒、过度个性化或推荐曝光偏差，但没有把 **agent action 作为偏好变化的因**，也没有把 **compliance 与 internalization 的区分**落到 memory write 决策上。
- **预期使用者或下游场景**：长期个性化 agent、跨会话推荐、记忆系统审计、agent 运行时监控。

## 4. 【核心假设】

**核心假设：** 如果 memory writer 在写入时保留 provenance（`source_event_ids`、agent action、exposure、`influence_prob`），区分“推荐后接受”与“独立选择/跨上下文重复”，并用 persistence / negative controls 决定 `durable` / `hedged` / `episodic` / `abstain`，那么相对于 naive writer，它将在推荐质量下降不超过 5% 的前提下降低 CMR 和 SFB，因为 naive writer 只看行为 `B` 就把 agent 的影响误归因为用户偏好 `U`。

- **关键变量/处理**：writer 是否保留 provenance；是否区分 `evidence_type`；是否使用 persistence / negative controls；memory 类型（durable / hedged / episodic / abstain）。
- **预期方向**：CMR 降低、SFB 降低、IDR 不显著下降；Quality 下降 ≤ 5%；Coverage / Diversity 不塌缩。
- **可能证伪的结果**（任一命中即需重新评估）：
  1. naive CMR 在所有 domain 都低于 10% → agent 诱导效应太弱，核心叙事不成立；
  2. provenance prompt 单独解决 80% 以上问题 → 复杂因果机制不必要，应收缩为诊断工具；
  3. proposed 的收益完全来自“少写” → Coverage / Quality 大幅下降，方法没有真正识别；
  4. 只在合成 simulator 中成立 → 外部效度不足，需要真实数据或 human study。
- **最小验证实验**：Week 1 的 20 用户 MemoryCD pilot + 受控 influence simulator；Week 2 Gate 1 检查 naive CMR ≥ 20%、provenance 相对下降 ≥ 30%。

## 5. 研究问题

1. **RQ1（误写程度）**：naive writer 在多大程度上把 agent-induced compliance 写成 durable preference？CMR 是否随 exposure 增强而上升？
2. **RQ2（区分机制）**：provenance、exposure propensity、随机探索、negative controls、persistence test 中，哪些信号对区分 compliance 与 internalization 最有效？
3. **RQ3（效用代价）**：降低 CMR/SFB 是否损害推荐质量、覆盖率和多样性？能否不靠“少写”实现修复？

> 完整项目还有 RQ4（泛化到不同 backend/domain）和 RQ5（跨模型稳健性）；Week 1 只锁定 RQ1–RQ3。

## 6. 数据集

| 数据集 | 来源/许可 | 版本或快照 | 规模 | 标签/字段 | 划分方式 | 获取说明 |
|---|---|---|---|---|---|---|
| MemoryCD | Hugging Face / Amazon Reviews 2023 派生；仓库 MIT | 待下载后记录 commit 与 checksum | 323 用户、167,870 商品、12 域 | 用户历史、商品、评分/评论；无 agent 交互 | Week 1 pilot：20 用户；主实验 100 用户 | 只提交下载脚本与 manifest，原始数据不入 Git |
| AcCoRD | arXiv:2608.27818；MIT | Stage 2 再接入 | 100 购物 + 100 旅行场景 | LLM user simulator、四类偏好动态 | Stage 2：10 → 50 → 100 场景 | 先 text-only，不启动 WebShop/Java |
| 受控 influence simulator | 自建 | Week 1 v0 | 1 用户 × 5 sessions 起步 | 隐藏 `U_t`、shock、internalization 标签 | seed 固定；用户级独立 | 只提交生成脚本与脱敏小样例 |

- **数据敏感性/合规备注**：以公开数据和合成交互为主；若后续接入真实系统日志需重新评估隐私与授权。
- **允许提交到 Git**：数据字典、下载/预处理脚本、manifest、脱敏小样例、统计摘要。
- **禁止提交**：原始数据、模型权重、大日志、API 凭据、受限字段。

## 7. 文献与相关工作

| 引用 | 关键方法/结论 | 与本 idea 的关系 | 待验证差异 |
|---|---|---|---|
| AcCoRD (arXiv:2608.27818, 已核对) | 100 购物 + 100 旅行场景；四类偏好动态；LLM user simulator；最强模型 Perfect Outcome <30% | Stage 2 交互底座 | 单 session；无跨会话 memory；agent 不改变 latent preference |
| MemoryCD (arXiv:2603.25973, 已核对) | Amazon Review，12 域；4 类任务；14 LLM × 6 memory 方法 | Stage 1 真实历史底座 | 无交互、无推荐动作、无 influence 标签 |
| CALMRec (arXiv:2607.23647, 已核对) | 三时间尺度记忆 + semantic atoms + propensity weighting；长期价值 +6.1%~7.6% | 方法论近邻 / baseline | 推荐排序而非 memory write；无 compliance/internalization；无 W0/W1 |
| CAPTURE (arXiv:2609.02265, 已核对) | 连续时间 POMDP + 多时间尺度 ledger + scope/quarantine/ask；D-PREFGUARD | 概念 baseline | 核心是 drift vs poisoning，不是 agent-induced compliance；无 W0/W1 |
| ULSPB (arXiv:2605.06731, 已核对) | 350 个 24-turn routine 设置；Harm Score；routine 对话 poison 长期状态；StateGuard writeback audit | 现象与防御参考 | 研究 security / authorization drift，不是 preference drift；LICENSE 待核实 |

> 五篇论文已于 2026-11-12 全部核对原文，详见 [`docs/paper_reading_log.md`](docs/paper_reading_log.md)；完整对照、研究脉络、baseline 计划与 related work 草稿见 [`docs/related_work.md`](docs/related_work.md)。
| Mem0 / Letta / A-MEM | 生产级 memory 接口与检索 | 真实 backend / baseline | 写入策略默认“行为即偏好” |
| MemGym (arXiv:2605.20833) | memory manager 接口、标准评测循环 | 接口参考 | 缺少 influence 场景与反事实 |

完整调研见 [`docs/references/2026-10-30_Agent-Induced-Drift_研究Idea说明.md`](docs/references/2026-10-30_Agent-Induced-Drift_研究Idea说明.md) 与 [`notes.md`](notes.md)。

## 8. 实验方案概览

- **方法/特征/模型**：naive writer（只从行为写偏好）vs. provenance writer（保留来源、exposure、influence、confidence）；后续加入 causal writer（propensity + exploration + negative controls + persistence）。
- **基线**：Week 1 只做 naive vs. provenance；后续加入 No memory、Recency、Summarize-all、Mem0、Letta、A-MEM、CAPTURE-style、CALMRec-style IPW、Oracle latent。
- **主要指标**：CMR、SFB、IDR、Quality（任务成功率 / NDCG / 多样性）；必须同时报告 Coverage。
- **次要指标**：AL、OUR、CR、Faithfulness、Diversity。
- **消融或对照**：去掉 provenance / propensity / exploration / negative controls / persistence；prompt-only；不同 `ε`、`η`、`p_shock`、memory budget、LLM。
- **预期资源与时间**：Week 1 最小闭环不依赖真实 LLM API；Week 2 Gate 1 使用 MemoryCD 20 用户 × 5 sessions × 5 seeds。
- **成功标准**：Gate 1 中 naive CMR ≥ 20%、provenance 相对下降 ≥ 30%、Quality 下降 ≤ 5%。
- **停止条件**：CMR 在所有 domain < 10%，或 provenance prompt 单独解决 80% 以上问题 → 收缩为诊断工具或转向。

详细指标口径见 [`docs/metrics.md`](docs/metrics.md)，schema review、v1 提案与决策见 [`docs/schema_review.md`](docs/schema_review.md)、[`docs/schema_v1_proposal.md`](docs/schema_v1_proposal.md)、[`docs/decisions.md`](docs/decisions.md)，pilot 协议与 Gate 1 配置见 [`docs/pilot_protocol.md`](docs/pilot_protocol.md)、[`docs/gate1_config.yaml`](docs/gate1_config.yaml)，Week 1 复盘、风险与交接见 [`docs/week1_review.md`](docs/week1_review.md)、[`docs/week1_risks.md`](docs/week1_risks.md)、[`docs/week1_handoff.md`](docs/week1_handoff.md)，原文核对与 related work 见 [`docs/paper_reading_log.md`](docs/paper_reading_log.md)、[`docs/related_work.md`](docs/related_work.md)，Week 1 计划见 [`experiment.md`](experiment.md)。

## 9. 风险与限制

- **效应风险**：agent 诱导效应可能太弱，CMR 低于 10%；预案是调 influence 强度 / 换 domain / 收缩为诊断工具。
- **方法风险**：provenance prompt 可能已经解决大部分问题；必须把 prompt-only 作为 ablation，并强调无外生 variation 的识别边界。
- **外部效度风险**：合成用户不等于真实用户；Week 1 只声明链路验证，Stage 2 再接 AcCoRD。
- **识别风险**：真实数据无法完全满足 sequential ignorability；模拟器做识别，真实数据只做外部效度检查。
- **工程风险**：MemoryCD 下载、Mem0/Letta 安装可能被网络或环境阻塞；保留 MockMemory 和 blocker 记录。
- **评测风险**：LLM judge 可能偏向长文本/自信语气；主指标使用结构化字段，judge 只做辅助。
- **伦理风险**：研究在模拟用户和公开数据上进行；不设计欺骗性说服，不针对脆弱人群，不隐藏关键选项。

## 10. 决策记录

| 日期 | 参与人 | 决策/讨论结论 | 依据 | 后续动作 |
|---|---|---|---|---|
| 2026-11-12 | @member-01 | 创建 idea 004，定位为“memory write 的因果归因”，不是通用记忆漂移 benchmark | 现有工作空白 + 团队 Week 1 计划 | 完成 P1 Week 1 文档 |
| 2026-11-12 | @member-01 | Week 1–2 只做 MemoryCD Stage 1；AcCoRD 第 3 周再接入 | 避免 WebShop/Java 成为关键路径 | 先跑 20 用户 pilot |
| 2026-11-12 | @member-01 | 本周指标先实现 CMR / SFB；AL / OUR / CR 允许占位 | 本周目标是证明“可测”，不是“显著” | P5 实现 `metrics.py` |
| 2026-11-12 | @member-01 | 建议三个 schema 周四 17:00 冻结 v1；字段变更走 RFC（待 kickoff 确认） | 防止 D2 后各自实现一套字段 | D3 schema review |
| 2026-11-12 | @member-01 | D3 schema review v0 完成；v1 变更清单见 `docs/decisions.md` 的 `D3-001`，D4 17:00 冻结；已按 `D4-002` 冻结，默认全组使用 | CMR/IDR 需要 `memory_type`；Coverage 需要 `WriteDecision`；SFB 需要 exposure | P2–P4 按 v1 实现 |
| 2026-11-12 | @member-01 | D4 pilot 协议与 Gate 1 配置 v0 完成：20 用户 × 5 sessions；3 memory × 2 writer × 5 seeds；主指标 CMR；阈值预注册 | 需要固定 Gate 1 口径，避免临时拍脑袋 | P2–P5 按协议实现；schema v1 待冻结 |
| 2026-11-12 | @member-01 | 完成 schema v1 提案与 week1_review 草稿；schema v1 已按 `D4-002` 冻结 | 先固定字段与复盘结构，避免 D5 临时补 | P2–P5 按 v1 实现；D5 跑 demo |
| 2026-11-12 | @member-01 | Schema v1 按 `D4-002` 冻结；默认全组使用，变更需 RFC | 当前 P1 设置即最终设置，避免逐字段等待和口径分歧 | P2–P5 直接按 v1 实现 |

## 11. 结论与后续

- **当前结论**：尚无实验结论。已完成问题定义、因果 DAG、指标口径和 Week 1 kickoff 草案。
- **支持/反驳核心假设的证据**：暂无。
- **已知限制**：compliance / internalization 的标签目前只能由 simulator 提供；真实数据上的识别假设只能部分满足；Week 1 只验证链路，不验证效应。
- **下一步**：
  1. D3 schema review，确认 `memory_type` / `write_action` / `exposure` 等字段进入 v1；
  2. 写 `pilot_protocol.md` 和 Week 2 Gate 1 配置；
  3. P5 实现 `metrics.py` + golden fixtures；
  4. 周五 demo：20 用户子集、1 用户 × 2 sessions、naive vs. provenance、CMR/SFB 输出。
- **若归档**：归档日期、原因、继承该 idea 的编号：待填写。
