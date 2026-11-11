# [004] InflMem 实验设计

> 本文件是想法阶段的实验方案；可运行代码和实际结果计划放在 `experiments/004-inflmem/`。
> Week 1 只做最小闭环（pipeline sanity check），不追求显著结果。

## 1. 实验目标

- **要验证的【核心假设】**：如果 memory writer 保留 provenance 并区分“推荐后接受”与“独立选择”，那么相对 naive writer，它将在推荐质量下降 ≤5% 的前提下降低 CMR 和 SFB。
- **实验问题**：RQ1（误写程度）、RQ2（区分机制）、RQ3（效用代价）。
- **最小可行验证**：20 用户 MemoryCD pilot + 受控 influence simulator；1 用户 × 2 sessions smoke；naive vs. provenance 的 CMR/SFB 对照。

## 2. 变量与对照

| 类型 | 内容 |
|---|---|
| 自变量/处理 | writer 类型（naive / provenance）；后续：propensity / exploration / negative controls / persistence 的开关 |
| 因变量/目标指标 | CMR、SFB、IDR、Quality、Coverage |
| 控制变量 | 同一用户、同一初始 `U_0`、同一外生冲击序列、同一商品库、同一 seed、同一 memory budget |
| 对照组 | naive writer；后续 No memory、Recency、Summarize-all、Mem0、Letta、A-MEM、CAPTURE-style、CALMRec-style IPW、Oracle latent |
| 预期机制 | naive writer 只看到行为 `B`，把 agent 影响误归因为偏好；provenance writer 保留 `A` / `E` / `source_event_ids`，降低 overclaim |

## 3. 数据与切分

- **数据集及版本**：MemoryCD（HF；下载后记录 revision / checksum）；Week 1 pilot 20 用户，覆盖 Electronics + Books 两个域。
- **训练/验证/测试划分**：用户级划分；per-user memory 不跨用户共享；dev 选阈值，test 只报告。
- **时间切分或交叉验证策略**：用过去 session 建 memory，预测未来 session；不能用未来信息写过去 memory。
- **去重和泄漏检查**：`U_t`、shock、compliance/internalization 标签绝不进入 agent prompt；检查同一 item / 同一模板是否跨划分。
- **样本过滤规则**：每个 pilot 用户至少 3 条历史交互；缺失严重或无法映射属性的用户剔除并记录原因。

## 4. 基线

| 基线 | 实现/论文 | 配置 | 选择理由 | 预期结果 |
|---|---|---|---|---|
| 简单基线 | naive writer | 只从 `B_t` 写 “User prefers X” | 复现现有记忆系统的默认行为 | CMR 较高 |
| 强基线 | provenance writer | 保留 `source_event_ids`、exposure、influence_prob、confidence、validity | 本周方法对照 | CMR / SFB 下降 |
| 目标方法（后续） | causal writer | provenance + propensity + exploration + negative controls + persistence | Week 5 主方法 | 进一步降低 CMR/SFB |
| 上界（诊断） | Oracle latent | 直接使用真实 `U_t` | 诊断上界，不作为可部署方法 | CMR 接近 0 |
| 生产 baseline（后续） | Mem0 / Letta / A-MEM | 默认写入策略 | 回答“现有系统有多严重” | CMR 待测 |

## 5. 指标与验收标准

| 指标 | 定义 | 优化方向 | 报告方式 | 成功阈值 |
|---|---|---|---|---|
| CMR | 被写成 durable preference 的 compliance / 所有 compliance | 越低越好 | 用户级均值 + 95% bootstrap CI + Coverage | Gate 1：naive ≥ 20% |
| CMR_cond | 分子同上 / 已写入的 compliance | 越低越好 | 与 CMR、Coverage 并列 | 仅诊断 |
| SFB | 控制 `U` 后，memory 推断偏好对 exposure 的回归系数 | 越低越好 | β + 95% CI + n | 方向为负/不显著更好 |
| IDR | 正确写成 durable 的 internalization / 所有 internalization | 越高越好 | 比例 + 分母 | 不低于 naive 太多 |
| Quality | 任务成功率 / NDCG / 多样性 | 越高越好 | 相对 best baseline 的变化 | 下降 ≤ 5% |
| Coverage | 至少有一条相关 memory 的 session 比例 | 不能塌缩 | 比例 + 分母 | 与 CMR 并列报告 |

- **统计检验或不确定性估计**：user-level paired bootstrap ≥1,000 次；主指标 Holm-Bonferroni；副指标 exploratory。
- **核心假设被支持的条件**：naive CMR ≥ 20%，provenance 相对下降 ≥ 30%，Quality 下降 ≤ 5%。
- **核心假设被证伪的条件**：CMR 在所有 domain < 10%；或 provenance prompt 单独解决 80% 以上问题；或收益完全来自少写。

## 6. 消融与稳健性

- **去掉关键模块**：provenance、propensity、randomized exploration、negative controls、persistence test。
- **替换数据切分**：不同用户子集、不同 domain、不同 seed。
- **不同随机种子**：Week 2 Gate 1 使用 5 seeds。
- **子群体/时间段/难例分析**：按 domain、用户历史长度、exposure 强度拆分。
- **失败案例分析**：naive 写对但 provenance 写错、provenance 过度保守、明确纠正后未降权。
- **参数敏感性**：`η`（内化强度）、`p_shock`（外生冲击）、`ε`（探索率）、memory budget、session 长度。

## 7. 资源与复现

- **Python/框架版本**：待定；Week 1 不依赖真实 LLM API，Pandas + 标准库即可跑最小链路。
- **运行命令**：`python scripts/run_pilot.py --config configs/pilot.yaml`（计划）。
- **随机种子**：Week 1 固定 `seed=0`；Gate 1 使用 5 seeds。
- **预计硬件与时间**：CPU 即可；MemoryCD 下载与 Mem0 适配是主要时间风险。
- **外部数据/权重位置及校验信息**：MemoryCD 放外部存储；记录 HF revision、checksum、下载脚本 commit。
- **允许提交的结果摘要/图片**：`metrics.json`、汇总 CSV、小型 PNG、脱敏 fixture；不提交原始数据和大日志。
- **run 目录约定**：`runs/<run_id>/`，`run_id = YYYYMMDD_method_model_dataset_seed`。

## 8. 里程碑

| 阶段 | 负责人 | 截止日期 | 完成标准 | 状态 |
|---|---|---|---|---|
| D1 kickoff / 论文阅读 | P1 | 2026-11-12 | `kickoff.md` 可评审 | 完成 |
| D2 问题定义 / DAG | P1 | 2026-11-12 | `problem.md`、`causal_dag.md` 可评审 | 完成 |
| D3 指标口径 / schema review | P1 | 2026-11-12 | `metrics.md` v0；`schema_review.md`；`decisions.md` D3-001 | 完成（v0 review） |
| D4 pilot 协议 / Gate 1 配置 | P1 | 2026-11-12 | `pilot_protocol.md`；`gate1_config.yaml`；schema v1 提案 | 部分完成（协议/配置 + schema 提案；schema v1 待签字） |
| D5 Demo / 复盘 | P1 | 2026-11-15 | demo 通过；`week1_review.md` | 草稿（demo 待 P2–P5 产物） |
| Week 2 Gate 1 | P1 + P5 | 第 2 周末 | naive CMR ≥ 20%；provenance 相对下降 ≥ 30% | not-started |

## 9. 当前状态

- 已完成：问题定义、因果 DAG、指标口径 v0、schema review v0、schema v1 提案、`decisions.md` D3-001/D4-001、pilot 协议与 Gate 1 配置 v0、`week1_review.md` 草稿、Week 1 kickoff 草案。
- 尚未完成：schema v1 冻结、`metrics.py`、20 用户子集、simulator、memory adapter、demo。
- 当前结论：尚无实验结论；本文件中的数值均为待验证假设。
