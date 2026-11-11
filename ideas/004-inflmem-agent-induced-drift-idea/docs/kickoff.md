# InflMem Week 1 Kickoff（P1 产出）

> 项目：InflMem / Agent-Induced Drift
> 产出人：@member-01（P1 Lead / 因果与评测）
> 状态：v0 草稿，供 60 分钟 kickoff 逐条确认
> 日期：2026-11-12
> 依据：[Week 1 五人任务清单](references/2026-10-30_Week1_五人任务清单.md)、[项目 Idea 说明 v1.0](references/2026-10-30_Agent-Induced-Drift_研究Idea说明.md)
> 参会：P1–P5（待确认具体人员与时间）

---

## 1. 本次 kickoff 只拍板三件事

1. **研究边界**：本周问题不是“记忆漂移的一般性问题”，而是“agent 推荐被接受后，memory 是否把 compliance 写成 preference”。
2. **本周范围**：只搭最小闭环，验证“可观测、可回放、可计算”，不做完整 benchmark、不追求显著性。
3. **协作接口**：确认五个人的 schema、交接物和关键路径，避免 D2 各自实现一套字段。

会议结束时应产出：本节三条的明确结论 + 第 7 节决策表的确认/修改记录。

---

## 2. 一句话定义与本周成功画面

> **长期记忆最危险的错误，不只是“忘记”或“检索错了”，而是把 agent 自己诱导出来的服从行为，写成用户稳定偏好，并通过后续推荐不断自我强化。**

本周五必须能实际演示这条链路，而不是讲架构：

```text
MemoryCD 20 个用户
  → 1 个用户 × 2 个 session 的合成交互
  → naive writer / provenance writer
  → MemoryRecord（含来源、exposure、confidence）
  → MemoryBackend add / search / snapshot
  → CMR、SFB 指标输出
```

本周结论只能是“链路验证”，不能写成“方法有效”。

---

## 3. 本周目标

| 类型 | 目标 | 可验收产物 |
|---|---|---|
| 研究 | 固定“compliance vs. internalization”的定义与最小可测口径 | `problem.md`、`causal_dag.md`、`metrics.md` |
| 数据 | 20 用户、至少 2 个域、每用户 ≥3 条历史交互 | `pilot_users.jsonl`、`manifest.json` |
| 交互 | 1 用户 × 2 sessions 的 `InteractionEvent`，字段完整 | 事件 JSONL + `data_qa_v0.md` |
| 记忆 | 统一 `MemoryBackend`，至少一个真实 adapter 可 add/search | `memory/base.py`、`adapter_alignment.md` |
| 写入 | naive 与 provenance writer 对同一事件产出不同 `MemoryRecord` | 20 条 fixture + `prompt_v1.md` |
| 评测 | CMR / SFB 有公式、单测和固定 fixture | `metrics.py`、第一张 CMR 图 |
| 复现 | 一条命令跑通最小链路，产物可追溯 | `run_pilot.py`、`runs/<run_id>/metrics.json` |

---

## 4. 本周非目标（明确不做）

- 不跑 100 个 AcCoRD 场景；不启动 WebShop / Java 环境；不做完整 TravelGym。
- 不做 human eval；不调参追求显著效果；不写论文正文；不做 UI / dashboard。
- 不把“pipeline 跑通”表述为“方法有效”。
- 不在本周实现完整的 causal writer（propensity + exploration + negative controls + persistence）；本周只做 naive / provenance 两个 writer 的对照。
- 不接 AcCoRD：Stage 2 从第 3 周开始，第 1–2 周只做 MemoryCD Stage 1。

> 本周唯一允许的“跑不通”：外部依赖（HF 下载、Mem0/Letta 安装）被网络或环境阻塞。此时保留 mock adapter 和 blocker 记录，不停工。

---

## 5. 概念边界（P1 必须钉死）

| 概念 | 一句话定义 | 行为表现 | 记忆应如何写 |
|---|---|---|---|
| **Compliance** | 接受推荐，但潜在偏好未变 | 本次选 X；独立选择仍可能选 Y | “在 agent 推荐下接受 X；可能是情境性妥协” |
| **Internalization** | 多次、多上下文暴露后，潜在偏好真的向 X 移动 | 主动搜索、复购、新情境仍选 X | “偏好可能已向 X 移动；有跨上下文证据” |
| **Exogenous change** | 生活事件/预算/环境导致的变化，与曝光无关 | 无推荐世界也会变 | “记录外部变化；更新旧偏好” |
| **Noise** | 一次性情绪、误点、试验 | 不重复、不持续、不跨上下文 | “一次性事件；不升级为稳定偏好” |

**本周必须形成共识的两条识别边界：**

1. **单次接受不能区分 compliance 与 internalization**；仅凭 `(user, item, accept)` 无法识别，必须有独立选择、跨上下文重复、反事实世界或随机探索中的至少一种信息。
2. **没有外生 variation 时，只能做 provenance 保留，不能声称因果识别**。provenance writer 本周的定位是“减少 overclaim”，不是“解决识别问题”。

本周三个 RQ（供 `problem.md` 展开）：

- **RQ1（误写程度）**：naive writer 在多大程度上把 agent-induced compliance 写成 durable preference？CMR 是否随 exposure 增强而上升？
- **RQ2（区分机制）**：provenance、exposure propensity、persistence 等信号中，哪些对区分 compliance / internalization 最有效？
- **RQ3（效用代价）**：降低 CMR/SFB 是否损害推荐质量、覆盖率与多样性？修复能否不靠“少写”实现？

---

## 6. 五角色、接口与依赖

| 角色 | 本周最终交付 | 主要消费 | 主要提供 | 关键阻塞 |
|---|---|---|---|---|
| **P1 因果与评测** | `problem.md`、`causal_dag.md`、`metrics.md`、`pilot_protocol.md`、schema v1 签字 | 全员接口草案 | schema / 指标口径 / Gate 1 配置 | 定义不清会导致 P4/P5 返工 |
| **P2 Sim / Data** | 20 用户子集、catalog、`InteractionEvent` 生成器 | MemoryCD、catalog | 事件流、隐藏状态、manifest | HF 下载与数据字段 |
| **P3 Memory** | `MemoryBackend`、MockMemory、≥1 真实 adapter、snapshot/restore | `MemoryRecord` schema | add/search/log/snapshot | Mem0/Letta 安装与 API |
| **P4 Method** | naive / provenance writer v0、influence 规格 | 事件字段、`MemoryRecord` schema | writer 输出、prompt 变体 | 与 P2 simulator 参数对齐 |
| **P5 Eval / Analysis** | `metrics.py`、`run_pilot.py`、第一张 CMR 图 | 事件、memory、writer 输出 | 指标实现、run 日志、报告 | 指标输入字段缺失 |

**关键路径（任一延迟超过半天，当日 blocker sync 决定降级/绕过/砍掉）：**

```text
P2 InteractionEvent schema
  → P4 writer 输出 MemoryRecord
  → P3 MemoryBackend 接收/检索
  → P5 metrics 计算 CMR/SFB
  → P1 schema v1 签字
```

**交接时间：**

| 时间 | 事项 | 负责人 | 产出 |
|---|---|---|---|
| 周一 17:00 | 每人 5 条风险/依赖 | 全员 | `week1_risks.md` |
| 周二 18:00 | 接口草案互评 | P1 主持 | schema 评论汇总 |
| 周三 14:00 | Schema review | 全员 | `schema_review.md` |
| 周四 17:00 | Schema v1 冻结 | P1 | `decisions.md` 第一条 |
| 周五 16:00 | Demo + retro | P1 | `week1_review.md` |

---

## 7. D1 需要拍板的决策（建议稿，待会确认）

| ID | 决策建议 | 理由 | 负责人 | 状态 |
|---|---|---|---|---|
| D1-01 | 第 1–2 周只做 MemoryCD Stage 1；AcCoRD 第 3 周再接入 | 避免 WebShop/Java 成为关键路径 | P1 | 待确认 |
| D1-02 | `UserState` / `InteractionEvent` / `MemoryRecord` 为唯一 schema 源；周四 17:00 冻结 v1 | 防止 D2 起各写一套字段 | P1 | 待确认 |
| D1-03 | 事件粒度为 turn 级 `InteractionEvent`，session 对应一个购物任务 | 支持逐轮曝光与回放 | P1 + P2 | 待确认 |
| D1-04 | 本周方法对照只做 naive vs. provenance；完整 causal writer 延后 | 本周目标是证明“可测”，不是“显著” | P1 + P4 | 待确认 |
| D1-05 | 真实 adapter 优先 Mem0；MockMemory 始终保留为降级路径 | 网络/安装失败时不停工 | P3 | 待确认 |
| D1-06 | 本周必须实现 CMR、SFB；AL、OUR、CR 允许占位 | 主指标先可执行，诊断指标不阻塞 | P1 + P5 | 待确认 |
| D1-07 | 隐藏状态 `U_t`、shock、compliance 标签只对 evaluator 可见，绝不进入 agent prompt | 防止标签泄漏 | P1 | 待确认 |
| D1-08 | 最小链路不得依赖真实 LLM API；fixture 与 mock 必须能跑通 | 控制本周成本与不确定性 | P5 | 待确认 |
| D1-09 | `run_id = YYYYMMDD_method_model_dataset_seed`；每次 run 保存 config/events/memories/metrics/log | 保证可追溯与可回放 | P5 | 待确认 |
| D1-10 | 原始数据、adapter 原始格式、API 凭据不入 Git；只提交脚本、manifest、脱敏小样例和汇总指标 | 遵循仓库数据合规规则 | 全员 | 待确认 |

---

## 8. 主要风险与依赖（D1 17:00 前每人补 5 条）

| 风险 | 触发信号 | 影响 | 预案 | 负责人 |
|---|---|---|---|---|
| 效应太弱（CMR < 10%） | pilot 中 naive 与 provenance 几乎无差异 | 核心叙事不成立 | 调 influence 强度/domain；准备转向诊断工具 | P1 |
| MemoryCD 下载或字段不可用 | HF 网络失败、用户历史不足 3 条 | P2 阻塞，事件流无法生成 | 先用公开小样例 + 合成 catalog；记录 blocker | P2 |
| Mem0/Letta 安装失败 | 依赖冲突、需要 API key | 无真实 adapter | 保留 MockMemory；adapter 报告标注未完成 | P3 |
| Schema 反复变更 | D3 后仍有字段增删 | P3/P4/P5 集体返工 | 周四冻结；变更走 1 页 RFC + 24h 评论 | P1 |
| provenance prompt 不稳定 | 同一事件输出字段缺失/漂移 | 指标不可比 | 固定 20 条 fixture；记录 3 个 prompt 变体 | P4 |
| 指标定义歧义 | CMR 分母、compliance 判定不一致 | 结果不可解释 | P1 在 `metrics.md` 写清输入/归一化/失败模式 | P1 |
| 合成用户外部效度 | 审稿人质疑“模拟≠真实” | 结论不能外推 | 本周只声明链路验证；Stage 2 再接 AcCoRD | P1 + P2 |
| 隐藏标签泄漏 | agent prompt/记忆里出现 `U_t` 或标签 | 实验无效 | schema review 逐字段检查“agent 可见/evaluator 可见” | P1 |

---

## 9. 周五 demo 最低验收

- [ ] `pilot_users.jsonl` 至少 20 个用户，字段与 MemoryCD 对得上。
- [ ] 能生成 1 个用户 × 2 个 session 的 `InteractionEvent`。
- [ ] 同一交互经 naive / provenance writer 产出不同的 `MemoryRecord`。
- [ ] 至少一个真实 memory adapter 能 add/search；其他 adapter 可为 skeleton。
- [ ] `metrics.py` 能对固定 fixture 算出 CMR / SFB，并有单测。
- [ ] `run_pilot.py` 一条命令跑完最小链路，输出 `metrics.json`。
- [ ] 三个 schema 完成 v1 评审并冻结。
- [ ] Week 2 Gate 1 配置已写好，不临时拍脑袋。

Demo 时必须能指出**一条具体 memory 的来源事件**，并说清 naive writer 为什么可能写错。

---

## 10. D1 阅读结论：五篇底座论文

> 说明：五篇论文已于 2026-11-12 全部核对原文（见 [paper_reading_log.md](paper_reading_log.md)）。

| 论文 | 在本项目中的角色 | 可直接借用 | 关键缺口 / 风险 |
|---|---|---|---|
| **AcCoRD**（已核对原文） | Stage 2 交互真实性底座 | 100 购物 + 100 旅行场景；四类偏好动态（hard/soft/unsatisfiable/triggered）；LLM user simulator；最强模型 Perfect Outcome <30% | 单 session；无跨会话 memory；agent 不改变 latent preference；无反事实 ground truth |
| **MemoryCD**（已核对原文） | Stage 1 真实历史底座 | Amazon Review，12 域（主实验 4 域）；4 类任务；14 LLM × 6 memory 方法；真实跨年行为 | 无交互式 agent、无推荐动作、无 influence、无隐藏偏好标签；323 用户/167,870 商品待数据核实 |
| **CALMRec**（已核对原文） | 方法论近邻 / baseline | 三时间尺度记忆（短期意图/长期偏好/曝光轨迹）；semantic atoms + provenance；propensity weighting；counterfactual deletion；Proposition 1 | 面向推荐排序，不是自然语言 memory write；无 compliance/internalization；无 agent-suggested vs independent；无 W0/W1 配对反事实 |
| **CAPTURE**（已核对原文） | 概念 baseline | 连续时间 POMDP + neural ODE；多时间尺度 ledger；scope/quarantine/ask；counterfactual audit；D-PREFGUARD 2,400 episodes | 核心是 drift vs poisoning，不是 agent-induced compliance；无 exposure propensity/随机探索；无 W0/W1 配对反事实；用户研究是 replay |
| **ULSPB**（已核对原文） | 现象与防御参考 | 350 个 24-turn routine 设置；Harm Score；routine 对话会 poison memory-centric state；StateGuard writeback audit | 研究 authorization / tool-use drift，不是 preference drift；无 compliance/internalization；无 W0/W1；LICENSE 待核实 |

**阅读后要回答的一个问题：** 这五篇里，哪一篇能直接支撑“agent action 是记忆误归因的因”这一 claim？如果都不能，我们的差异化就必须落在 benchmark 的反事实设计与 writer 的 provenance 上。

---

## 11. 会前与会后行动

| 时间 | 负责人 | 动作 | 产出 |
|---|---|---|---|
| kickoff 前 24h | P1 | 发出本草案，收集异议 | 本文件批注 |
| kickoff 前 | 全员 | 读分工论文的 abstract/method/experiment；各写 5 条风险/依赖 | `week1_risks.md` |
| kickoff 中 | P1 | 逐条确认第 1、4、7 节 | 决策记录 |
| kickoff 后 | P1 | 将确认结果写入 `decisions.md` 第一条 | `decisions.md` |
| D2 18:00 | P2–P5 | 提交接口草案 | schema 评论汇总 |
| D3 14:00 | P1 | 主持 schema review | `schema_review.md` |
| D4 17:00 | P1 | schema v1 冻结并签字 | `decisions.md` |

---

## 12. 待确认问题

1. kickoff 的具体参会人与时间是否按 D1 周一 60 分钟执行？
2. InflMem 是否要登记为本仓库的正式 idea 编号并写入 `PROGRESS.md`？当前 `docs/` 是项目级文档，尚未走 `ideas/NNN-...` 流程。
3. MemoryCD 的访问方式与网络环境是否已就绪？谁负责 HF 下载与 checksum？
4. 本周 provenance writer 是否允许调用真实 LLM？若允许，模型、预算和 API key 由谁提供？
5. `UserState` / `InteractionEvent` / `MemoryRecord` 的字段级 review 是否按周三 14:00 执行？
6. 五篇论文的原文核对由谁分工？建议 P1 负责 AcCoRD + MemoryCD，P4 负责 CALMRec + CAPTURE，P5 负责 ULSPB，D1 17:00 前回填第 10 节。

---

*本文件是 kickoff 草案，不是实验结果；所有“预期”“建议”均需在会上确认后才能作为本周执行依据。*
