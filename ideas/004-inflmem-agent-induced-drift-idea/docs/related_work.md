# InflMem Related Work 与 Baseline 沉淀

> 项目：InflMem / Agent-Induced Drift
> 产出人：@member-01（P1）
> 日期：2026-11-12
> 状态：v0；基于五篇底座论文原文核对 + 项目 Idea 说明
> 上游：[paper_reading_log.md](paper_reading_log.md)、[problem.md](problem.md)、[causal_dag.md](causal_dag.md)
> 下游：论文 related work、baseline 实现、`experiment.md`

---

## 1. 一句话定位

> **InflMem 研究的是 memory write 层的因果归因：agent 自己的推荐/曝光/措辞让用户接受了 X，memory writer 却把这次 compliance 写成用户的 durable preference。**
>
> 它不是“记忆检索 benchmark”，不是“exposure-aware 推荐”，也不是“memory poisoning 防御”；它要回答的是：**这条记忆，究竟是在记录用户，还是在记录 agent 对用户做过什么？**

三个不可替代的差异点：

1. **因果方向**：agent action 是偏好变化的因，而不是只做 post-hoc 行为统计；
2. **概念区分**：compliance vs internalization，落到 `evidence_type` / `memory_type` / `WriteDecision`；
3. **识别设计**：W0/W1 配对反事实世界，给出 CMR / SFB / IDR 的可计算 ground truth。

---

## 2. 五篇底座论文对照

| 论文 | 核心问题 | 数据 / 场景 | 方法 | 评测 | 对我们的用途 | 关键缺口 |
|---|---|---|---|---|---|---|
| **MemoryCD** | 长上下文、跨域用户记忆 | Amazon Review，12 域；主实验 4 域；4 类任务 | 14 个长上下文 LLM × 6 个 memory 方法；single / cross-domain | MAE、RMSE、NDCG、ROUGE、BLEU | Stage 1 真实历史与商品库；4 类任务可复用 | 无交互式 agent、无推荐动作、无 influence、无 hidden preference / 反事实标签 |
| **AcCoRD** | 真实偏好动态下的用户–agent 协作 | 100 购物 + 100 旅行场景；4 类偏好动态 | POMDP harness；GPT-5.1 user simulator；ReAct / UncReAct | Task completion、Outcome Score、Perfect Outcome | Stage 2 交互底座；场景生成与 simulator | 单 session；无跨会话 memory；agent 不改变 latent preference；无反事实 ground truth |
| **CALMRec** | 长程推荐中的曝光偏差与反馈循环 | WeChat-Video、MIND-small、KuaiRec | 三时间尺度记忆（短期意图/长期偏好/曝光轨迹）；semantic atoms + provenance；propensity weighting；conservative critic | 长期价值、NDCG、消融 | 方法近邻；三时间尺度、propensity、semantic atoms、counterfactual deletion | 面向推荐排序，不是自然语言 memory write；无 compliance/internalization；无 W0/W1 |
| **CAPTURE** | 真实偏好漂移 vs memory poisoning | D-PREFGUARD：2,400 episodes、5 tracks、480 held-out | 连续时间 POMDP + neural ODE；authenticity gate；多时间尺度 ledger；scope/quarantine/ask；counterfactual audit | win rate、poisoning、adherence、false update | 问题近邻；scope / quarantine / ask、多时间尺度 ledger、counterfactual audit | 核心是 drift vs poisoning，不是 agent-induced compliance；无 exposure propensity / 随机探索；无 W0/W1 |
| **ULSPB** | 日常对话导致长期状态中毒 | 350 个设置（5 类任务 × 7 模式 × 5 变体 × 2 语言）；24-turn routine | Harm Score（authorization drift / tool-use escalation / unchecked autonomy）；StateGuard writeback audit | HS、FP/FN、成本 | 现象与防御参考；writeback audit / rollback | 研究 security / authorization drift，不是 preference drift；无 compliance/internalization；无 W0/W1 |

---

## 3. 研究脉络与我们的位置

| 脉络 | 代表工作 | 已经解决什么 | 仍缺什么 |
|---|---|---|---|
| **A. 记忆评测** | MemoryCD、LongMemEval、LoCoMo、MemBench、MemoryAgentBench | 长上下文召回、跨会话问答、跨域个性化 | 不测 agent 对偏好的因果影响；不区分 compliance / internalization |
| **B. 交互式偏好** | AcCoRD、UserBench、TravelGym、ChatShop | 偏好 elicitation、四类偏好动态、user simulator | 单 session；无跨会话 memory；agent 不改变 latent preference |
| **C. 曝光偏差 / 反馈循环** | CALMRec、经典 recsys debias、IPW / doubly robust | exposure bias 识别、propensity weighting、长期价值 | 面向排序/评分，不是自然语言 memory write；无 compliance vs internalization |
| **D. 漂移 / 投毒 / 长期状态安全** | CAPTURE、ULSPB、MemConflict、Stale/Misattributed/Late | 区分真实漂移与注入；多时间尺度记忆；writeback 防御 | 把 agent action 当作偏好变化的因；无反事实 W0/W1 |
| **E. 记忆基础设施** | Mem0、Letta/MemGPT、A-MEM、MemGym | 生产级 memory 接口、检索、评测循环 | 写入策略默认“行为即偏好”；无 provenance / influence 语义 |

**我们的位置：** A 提供真实数据，B 提供交互，C 提供 exposure 校正，D 提供真实性与安全视角，E 提供 backend；但**没有一条脉络把“agent 自己的推荐导致 compliance”作为 memory write 的因果归因问题**。InflMem 站在 B × C × D 的交叉点。

---

## 4. 与每篇的正面比较（related work 可直接用）

### 4.1 vs MemoryCD

- **相同**：都关心长期、跨域用户记忆；
- **不同**：MemoryCD 评测“记忆能不能支持个性化任务”，我们评测“写入时有没有把 agent 影响误归因为用户偏好”；
- **我们借用**：真实用户历史、商品库、4 类任务、single / cross-domain 设置；
- **我们不能声称**：MemoryCD 的指标能证明因果效应；它没有交互和 hidden labels。

### 4.2 vs AcCoRD

- **相同**：都关心用户偏好会在交互中变化；
- **不同**：AcCoRD 是单 session 的 preference elicitation benchmark，agent 不改变 latent preference；我们研究跨会话 memory 写入，且 agent 的推荐会改变行为；
- **我们借用**：四类偏好动态、scenario 生成、user simulator；
- **我们不能声称**：AcCoRD 的 preference dynamics 就是 agent-induced drift；它没有 memory，也没有反事实世界。

### 4.3 vs CALMRec

- **相同**：都区分持久偏好、短期意图、曝光行为；都用 propensity / provenance 处理曝光偏差；
- **不同**：CALMRec 是推荐排序系统，LLM 只做异步 semantic compiler；我们研究自然语言 memory write，且要区分 compliance vs internalization；
- **我们借用**：三时间尺度记忆、exposure trace、propensity weighting、semantic atoms、counterfactual deletion；
- **必须强调**：CALMRec 没有 `evidence_type`（推荐后接受 vs 独立选择），没有 W0/W1，也没有 memory backend audit。

### 4.4 vs CAPTURE

- **相同**：都关心“这条记忆更新是否真实”；都用多时间尺度 ledger、quarantine、clarifying question；
- **不同**：CAPTURE 的核心是 **preference drift vs memory poisoning**；我们问的是 **agent 自己的推荐是否制造了 compliance，并被写成 preference**；
- **我们借用**：`scope` → `validity.context`；`quarantine` → `status` + `hedged`；`ask` → `abstain` / clarify；counterfactual audit → `source_event_ids` / replay；
- **必须强调**：CAPTURE 没有 exposure propensity / 随机探索，也没有 W0/W1 配对反事实；它的 authenticity 是“更新是否真实”，不是“行为是否被 agent 诱导”。

### 4.5 vs ULSPB

- **相同**：都认为良性日常交互可以累积成长期状态问题；都重视 writeback 边界的审计；
- **不同**：ULSPB 研究 authorization / tool-use / autonomy 漂移，是安全边界问题；我们研究 preference attribution；
- **我们借用**：StateGuard 的 writeback audit / rollback 思路；`WriteDecision` + `counterevidence` 可以承载审计记录；
- **必须强调**：ULSPB 没有 compliance / internalization，也没有偏好反事实；它的 Harm Score 不能替代 CMR / SFB。

---

## 5. Baseline 计划

| Baseline | 来源 | 作用 | 实现难度 | 阶段 |
|---|---|---|---|---|
| No memory | — | 下界；无跨会话个性化 | 低 | Week 2+ |
| Recency / last-write-wins | — | 最简单时序策略 | 低 | Week 2+ |
| Summarize-all | — | 直接把对话摘要写入 | 低 | Week 2+ |
| Mem0 | 生产级 memory | 真实 backend baseline | 中 | Week 2 |
| Letta / MemGPT | 生产级 memory | 分层记忆 baseline | 中 | Week 2+ |
| A-MEM | 结构化 memory | 关联记忆 baseline | 中 | Week 2+ |
| CALMRec-style IPW | CALMRec | exposure debias baseline | 中（按论文重实现） | Week 3+ |
| CAPTURE-style authenticity gate | CAPTURE | 真实性 gate baseline | 高（简化重实现） | Week 3+ |
| ULSPB StateGuard-style writeback audit | ULSPB | writeback 审计 / rollback baseline | 中 | 可选 |
| Oracle latent | simulator | 诊断上界 | 低 | Week 2+ |
| Naive writer | 本项目 | 复现现有系统默认行为 | 低 | Week 1 |
| Provenance writer | 本项目 | 本周方法对照 | 中 | Week 1 |
| Causal writer | 本项目 | 主方法（propensity + exploration + negative controls + persistence） | 高 | Week 5 |

> Week 1 只做 naive vs provenance；Week 2 Gate 1 加 3 个 memory backend；Week 3+ 才加入 CALMRec / CAPTURE 风格 baseline。不要把 baseline 数量当成进度。

---

## 6. 可直接借用的组件 → 我们的模块

| 来源 | 组件 | 映射到 InflMem |
|---|---|---|
| MemoryCD | 真实用户历史、商品库、4 类任务 | Stage 1 数据与评测 |
| AcCoRD | 场景生成、user simulator、四类偏好动态 | Stage 2 交互 harness |
| CALMRec | 三时间尺度记忆 | `memory_type` + `validity.context` + exposure trace |
| CALMRec | semantic atoms + provenance | `evidence_type` + `source_event_ids` |
| CALMRec | propensity weighting | `exposure.propensity` + IPW baseline |
| CALMRec | counterfactual deletion | 解释 faithfulness / replay |
| CAPTURE | `scope` | `validity.context` |
| CAPTURE | `quarantine` | `status` + `hedged` |
| CAPTURE | `ask` | `abstain` / clarify 记录 |
| CAPTURE | 多时间尺度 ledger | `memory_type` + decay |
| CAPTURE | counterfactual audit | `source_event_ids` + replay |
| ULSPB | StateGuard writeback audit | `WriteDecision` + `counterevidence` + `status` |
| Mem0 / Letta / A-MEM | backend 接口 | `MemoryBackend` adapter |
| MemGym | memory manager 接口 | 接口参考 |

---

## 7. Novelty 威胁与回应

| 威胁 | 回应 |
|---|---|
| “这就是 CALMRec 搬到 memory” | CALMRec 是推荐排序；它没有自然语言 memory write，没有 compliance vs internalization，没有 W0/W1。我们借用它的三时间尺度与 propensity，但研究问题不同。 |
| “这就是 CAPTURE” | CAPTURE 是 drift vs poisoning；它问“更新是否真实”，我们问“行为是否被 agent 诱导，并被误写成偏好”。因果方向不同，ground truth 也不同。 |
| “这就是普通 exposure bias” | 普通 exposure bias 关注排序/评分；我们把 memory write 形式化为因果归因，区分 compliance / internalization，并要求配对反事实。 |
| “加一句 prompt 就能解决” | prompt-only 作为 ablation；没有外生 variation 时，provenance 只能降低 overclaim，不能可靠识别 internalization。 |
| “合成用户不可信” | Stage 1 用 MemoryCD 真实历史；Stage 2 用 AcCoRD；后续 human eval 小样本；Week 1 只声明链路验证。 |
| “没有因果识别” | 模拟器保证 consistency / positivity / sequential ignorability；真实数据只做外部效度检查，不声称因果证明。 |

---

## 8. 我们能声称 / 不能声称

**可以声称（若实验结果支持）：**

- 在受控 simulator 中，naive memory 会把 agent-induced compliance 写成 durable preference；
- provenance writer 能降低 CMR / SFB，且 Quality 下降 ≤5%；
- W0/W1 配对反事实可以提供比启发式标注更可辩护的 ground truth；
- 现有 memory backend 的默认写入策略存在系统性误归因风险。

**不能声称：**

- 真实用户一定如此；
- proposed 解决所有记忆漂移；
- 模拟器中的因果效应可以直接外推到生产环境；
- CMR 降低等于用户效用提升（必须有 Quality / CR 支持）；
- “记忆写得更少”是主要卖点。

---

## 9. Related Work 草稿（可直接改写进论文）

**Memory benchmarks and systems.** MemoryCD evaluates long-context, cross-domain user memory on four personalization tasks but contains no interactive agent or exposure model. AcCoRD studies realistic preference dynamics in single-session user–agent collaboration, but does not maintain cross-session memory and does not let the agent change latent preferences. Production memory systems such as Mem0, Letta, and A-MEM optimize retrieval and storage, while implicitly treating observed behavior as preference evidence.

**Exposure bias and feedback loops.** CALMRec separates short-term intent, long-term preference, and exposure trace, and uses propensity-weighted updates to correct policy-induced exposure bias. It is a recommendation-ranking framework, however, and does not model natural-language memory writes or distinguish compliance from internalization.

**Drift, poisoning, and long-term state.** CAPTURE formulates preference-authenticity ambiguity as a continuous-time POMDP and uses a multi-timescale ledger with scope, quarantine, and clarifying questions to separate genuine drift from memory poisoning. ULSPB shows that routine, benign conversations can poison long-term state and proposes a writeback-boundary audit. Both focus on whether an update is authentic or safe, not on whether the agent's own recommendation caused the observed behavior.

**Our position.** We study memory write as causal attribution under agent influence. The agent's recommendation, exposure, and framing can induce compliance; a naive writer records that compliance as a durable preference, and subsequent retrieval amplifies the error. We formalize this with a paired counterfactual design and evaluate compliance misattribution (CMR), self-fulfilling bias (SFB), internalization detection (IDR), and quality/coverage costs.

---

## 10. 待办与开放问题

| # | 事项 | 负责人 | 截止 |
|---|---|---|---|
| 1 | 核实 MemoryCD 的 323 用户 / 167,870 商品等具体数字与数据许可 | P2 | Week 2 |
| 2 | 确认 CALMRec / CAPTURE 代码是否可得；不可得则按论文重实现简化版 | P4 | Week 3 |
| 3 | 决定 Gate 1 是否加入 CALMRec-style IPW baseline，还是留到主实验 | P1 + P4 | Week 2 |
| 4 | 补充 LongMemEval、LoCoMo、MemGym、MemConflict、OP-Bench 等引用 | P1 | 论文初稿前 |
| 5 | 把 §9 的 related work 草稿扩成论文段落，并加入引用 | P1 | Week 9 |
| 6 | 检查 ULSPB 的 LICENSE 与代码可用性 | P5 | Week 3 |

---

## 11. 变更记录

| 日期 | 版本 | 变更 | 记录人 |
|---|---|---|---|
| 2026-11-12 | v0 | 初稿：五篇论文对照、研究脉络、正面比较、baseline 计划、组件映射、novelty 威胁、related work 草稿 | @member-01 |
