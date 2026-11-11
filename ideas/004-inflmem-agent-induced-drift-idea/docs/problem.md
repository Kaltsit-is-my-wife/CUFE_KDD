# InflMem 问题定义（problem.md v0）

> 项目：InflMem / Agent-Induced Drift
> 产出人：@member-01（P1 Lead / 因果与评测）
> 状态：v0 草稿，待 D2 接口互评与 D3 schema review
> 日期：2026-11-12
> 上游：[kickoff.md](kickoff.md)
> 下游：[causal_dag.md](causal_dag.md)、`metrics.md`、`pilot_protocol.md`
> 依据：[项目 Idea 说明 v1.0](references/2026-10-30_Agent-Induced-Drift_研究Idea说明.md)、[Week 1 五人任务清单](references/2026-10-30_Week1_五人任务清单.md)

---

## 1. 问题陈述

跨会话记忆系统普遍隐含一个假设：**用户选择了 X，就说明用户偏好 X；重复选择 X，就说明 X 是稳定偏好。**

但在长期 agent 交互中，用户接受 X 可能只是因为：

- X 是 agent 唯一展示的选项；
- X 被放在更显眼的位置；
- 用户信任 agent，懒得继续比较；
- 用户当时只想尽快结束任务；
- X 是“这次可以接受”，但不是“以后都想要”。

这些情况是 **compliance（服从/配合）**，不一定是 **internalization（内化）**。如果 memory writer 把两者混为一谈，就会把一次妥协固化成用户 trait，并通过后续推荐不断自我强化：

```text
agent 推荐 X
  → 用户接受 X
  → memory 写成 “User prefers X”
  → 下一次更强地推荐 X
  → 用户再次接受
  → memory 置信度更高
  → 用户的选择空间越来越窄
```

**本项目要回答的核心问题不是“记忆检索得准不准”，而是：**

> **这条记忆，究竟是在记录用户，还是在记录 agent 自己对用户做过什么？**

换句话说，memory write 不是“事实转录”，而是一次 **因果归因**：写入者必须判断，这次行为变化是用户真实偏好变化、上下文变化、一次性噪声，还是 agent 的曝光/推荐/措辞造成的；如果是 agent 造成的，还要判断它是暂时的 compliance，还是已经内化为 durable preference。

---

## 2. 运行例子：蓝色耳机

### Session 1：一次缺货妥协

用户：

> “我想买一副通勤用的耳机，黑色比较百搭，预算 1000 以内。”

agent 发现黑色缺货，推荐蓝色：

> “黑色暂时没货，这款蓝色同配置，今天 899。”

用户：

> “行吧，蓝色也可以。”

**隐藏状态**：`U = {color: black, price_sensitivity: 0.7}`，没有变化。
**行为**：接受蓝色。
**标签**：`compliance`。

| Writer | 输出 |
|---|---|
| naive | `User prefers blue headphones.` |
| provenance | `User accepted blue after agent recommendation because black was out of stock; prior preference black; possible compliance; confidence 0.3; context: commute headphones.` |

### Session 2：重复暴露

agent 检索到 “prefers blue”，只展示蓝色：

> “根据你之前的偏好，这几款蓝色耳机更适合你。”

用户：

> “可以，就这个。”

**隐藏状态**：仍然 `color: black`。
**标签**：`compliance`（重复暴露，不是独立证据）。

| Writer | 输出 |
|---|---|
| naive | `User strongly prefers blue; repeated acceptance confirms.` |
| provenance | `Second acceptance occurred under agent-initiated blue-only recommendation; not independent evidence; confidence remains low.` |

### Session 3：用户明确纠正

用户主动说：

> “其实我还是想要黑色，上次是没货才买的蓝色。”

**标签**：`explicit correction`。
**正确行为**：旧蓝色记忆降权，新增“用户明确纠正，黑色是首选”；不把纠正当成一次性噪声。

### Session 4：真正的 internalization

几周后，用户在没有推荐的情况下主动搜索蓝色，并在不同场景（运动耳机）选择蓝色；跨两个上下文、两次独立选择。

**标签**：`internalization`。
**正确行为**：将蓝色从 hedged 升级为 durable，但保留“最初由推荐引入”的 provenance。

### 这个例子说明什么

1. 单次接受不能区分 compliance 与 internalization；
2. 重复接受也可能是 agent 造成的；
3. 真正的 internalization 需要独立、跨上下文、持续的证据；
4. 记忆应能表达“不确定”和“有条件”，而不是二值化为“喜欢/不喜欢”。

---

## 3. 核心定义

### 3.1 潜在偏好 `U_t`

用户在第 `t` 个会话的真实偏好状态，是一个属性向量（如 `color`、`size`、`price_sensitivity`、`brand`）。

- 对 agent **不可见**，只对 evaluator 和模拟器可见；
- 可以由行为、复购、澄清或 probe 近似测量，但不能被单次行为直接等同；
- 会因内化（`internalization`）或外生冲击（`shock`）而变化。

### 3.2 Compliance

> 用户接受了 agent 推荐的 X，但潜在偏好没有改变。

- 行为表现：这次选了 X；下次独立选择可能仍选 Y；
- 记忆应写成：“在 agent 推荐下接受了 X；可能是情境性妥协；不等于偏好 X”；
- 关键：compliance 是 **行为层面的配合**，不是偏好层面的改变。

### 3.3 Internalization

> 用户在多次、多上下文暴露后，潜在偏好真的向 X 移动。

- 行为表现：不仅接受推荐，还会主动搜索、复购、在新情境中选择 X；
- 记忆应写成：“偏好可能已向 X 移动；有跨上下文证据；置信度中等”；
- 关键：internalization 需要 **独立于 agent 推荐** 的证据，或至少需要跨上下文、跨时间的持续证据。

### 3.4 Exogenous change

> 用户因为生活事件、预算、环境变化而改变偏好，与 agent 曝光无关。

- 行为表现：在无推荐世界也会改变；
- 记忆应写成：“记录了外部变化；需要更新旧偏好”；
- 关键：不能把它误标为 compliance，也不能把它当成 agent 的功劳。

### 3.5 Noise

> 一次性情绪、误点、试验、随机波动。

- 行为表现：不重复、不持续、不跨上下文；
- 记忆应写成：“一次性事件；不升级为稳定偏好”；
- 关键：不要因为一次异常行为触发 durable update。

### 3.6 记忆误归因的四种形式

| 类型 | 定义 | 例子 | 主要指标 |
|---|---|---|---|
| **Overclaim** | 把一次接受写成稳定偏好 | “User loves blue” ← 一次缺货妥协 | CMR |
| **Provenance loss** | 结论可能对，但来源、时间、条件丢了 | 记录“喜欢蓝色”，但没记录“仅在运动场景” | Faithfulness |
| **Scope inflation** | 把某上下文的偏好扩散到所有场景 | 工作时用 Python，被写成“User prefers Python”并用于业余项目 | Faithfulness |
| **Confidence inflation** | 重复曝光被当成独立证据，置信度虚高 | agent 连续三次推荐蓝色，用户三次接受，被写成“strongly prefers blue” | SFB |

CMR 主要测第 1 类，SFB 测第 4 类，Faithfulness 测第 2/3 类。

---

## 4. 为什么“接受”不能直接当“偏好”

### 4.1 两个世界可以产生完全相同的观测

```text
世界 W0：U 不变，agent 推荐 X，用户接受 X
世界 W1：U 向 X 移动，agent 推荐 X，用户接受 X
```

如果只看 `(user, item, accept)`，W0 和 W1 无法区分。naive writer 把 `B_t` 直接写成 `M_t`，等于假设“接受 = 偏好”，而这个假设在两种世界中都成立，因此它无法识别真正的因果状态。

### 4.2 要区分，至少需要一种额外信息

- 未来的独立选择；
- 不同上下文中的重复出现；
- 反事实世界：如果没有推荐，用户会不会选 X；
- 随机化探索：有时推荐 X，有时不推荐 X；
- 用户的主动澄清或纠正；
- 对未曝光属性的 negative control。

这也解释了为什么“更好的摘要 prompt”不够：**没有因果变化，就没有可识别的因果信息。**

### 4.3 为什么这是 LLM-specific 的放大机制

普通推荐系统已有曝光偏差和 feedback loop 的研究，但 LLM agent 引入了额外放大机制：

1. **自然语言压缩损失 provenance**：结构化日志能保留“曝光了哪些 item”，LLM 摘要通常只留下“用户喜欢 X”；
2. **措辞本身就是干预**：“你可以试试蓝色”与“你之前喜欢蓝色”对用户的影响不同；
3. **记忆写成 trait，而不是 evidence**：LLM 擅长写“User is detail-oriented”，却不保留“这是一次任务中的临时选择”；
4. **跨会话置信度复利**：一次接受被写成偏好，下一次接受被当成“再次确认”，再下一次变成“strongly prefers”；
5. **记忆同时是记录器和行动者**：记忆影响推荐，推荐改变行为，行为再被写回记忆。

因此，本项目不能简单归类为“推荐系统 debias”，必须把 **自然语言记忆写入**、**跨会话累积**、**agent 措辞干预** 放进同一个模型。

---

## 5. 形式化：memory write 是因果归因

### 5.1 变量

对用户 `i`、会话 `t`：

| 符号 | 含义 | 可见性 |
|---|---|---|
| `U_{i,t}` | 真实潜在偏好状态 | evaluator / simulator |
| `C_{i,t}` | 上下文（任务、场景、预算、时间） | 部分 agent 可见 |
| `H_{i,t}` | 历史交互 | agent 可见 |
| `A_{i,t}` | agent action（推荐集合、排序、措辞、是否提问） | agent 可见 |
| `E_{i,t}` | exposure（用户实际看到的属性/商品） | 可记录 |
| `B_{i,t}` | 用户可观测行为（接受、拒绝、评分、复购） | agent 可见 |
| `M_{i,t}` | 写入的记忆 | 可审计 |
| `R_{i,t}` | 后续推荐/行动 | agent 可见 |
| `Y_{i,t}` | 用户效用/任务成功 | evaluator |

### 5.2 潜在偏好演化

```text
U_{i,t+1} = U_{i,t}
          + η · 1[internalize] · (A_{i,t} - U_{i,t})
          + ξ · 1[shock] · Δ_{i,t}
          + noise
```

其中 `η` 是 agent 影响导致内化的强度，`ξ` 是外生冲击强度，`1[internalize]` 是隐藏标签，不能从单次行为直接观测。

### 5.3 行为与记忆写入

```text
P(B_{i,t} = accept | U_{i,t}, C_{i,t}, A_{i,t}, E_{i,t})

M_{i,t} = W(H_{i,t}, B_{i,t}, A_{i,t}, E_{i,t}, ...)
```

naive writer 的问题在于：它近似只使用了 `B`，忽略了 `A` 和 `E` 的因果角色。

### 5.4 目标估计量

naive writer 实际估计的是：

```text
P(U | B)
```

但我们真正需要的是：

```text
P(U | do(E), B, H)
```

两者之间至少有三类偏差：

- **Exposure bias**：用户看到的选项不是随机分配的；
- **Confounding by user state**：agent 本来就会根据用户偏好选择推荐，导致 `U → A`；
- **Reverse causality / feedback**：过去的记忆影响现在的推荐，现在的推荐影响未来的行为。

此外还有 **selection bias**：用户只在某些场景下接受推荐，接受者本身可能更信任 agent、更偏好省事，或更不愿意搜索。

### 5.5 识别边界

> **如果没有外生 variation，也没有额外假设，那么“用户真的变了”和“agent 让用户看起来变了”在观测上是不可区分的。**

这不是工程实现问题，而是识别性问题。它决定了 benchmark 必须包含：

- 随机化曝光；
- 配对反事实世界；
- 隐藏的 internalization 标签；
- 至少一个“无 agent 影响”的对照。

---

## 6. 三个研究问题

### RQ1（误写程度）

> 现有 memory writer 在多大程度上把 agent-induced compliance 写成 durable preference？CMR 是否随 exposure 强度系统上升？

- **操作化**：`CMR = 被写成 durable preference 的 compliance 事件数 / 所有 compliance 事件数`；
- **条件版本**：`CMR_cond = 被写成 durable preference 的 compliance 事件数 / 所有被写入的 compliance 事件数`；
- **假设 H1**：在控制真实潜在偏好后，naive writer 的 CMR 随 agent exposure 强度上升；
- **证伪条件**：CMR 在所有 domain 都低于 10%，或 CMR 与 exposure 无系统关系。

### RQ2（区分机制）

> provenance、exposure propensity、随机探索、negative controls、persistence test 中，哪些信号对区分 compliance 与 internalization 最有效？

- **操作化**：在同一批事件上比较不同 writer 的 CMR、IDR、SFB；
- **假设 H2**：仅靠 prompt 保留 provenance 能降低 overclaim，但在没有外生 variation 时无法可靠区分 compliance 与 internalization；
- **证伪条件**：provenance prompt 单独解决 80% 以上问题，或所有信号组合都不优于 naive。

### RQ3（效用代价）

> 降低 CMR/SFB 是否会损害推荐质量、覆盖率和多样性？能否不靠“少写”实现修复？

- **操作化**：同时报告 CMR、IDR、Quality（任务成功率、NDCG、多样性）、Coverage；
- **假设 H3**：proposed writer 相对 best baseline 的质量下降不超过 5%，且 coverage/diversity 不塌缩；
- **证伪条件**：CMR 的下降完全来自少写，或 Quality 下降超过预注册阈值。

> 说明：完整项目还有 RQ4（泛化）和 RQ5（跨 backend/domain），本周只锁定 RQ1–RQ3，避免范围漂移。

---

## 7. 范围与非目标

### 本周做的

- 用 MemoryCD 真实历史 + 受控 influence simulator 验证“可观测、可回放、可计算”；
- 固定 `UserState` / `InteractionEvent` / `MemoryRecord` 三个 schema；
- 实现 naive / provenance 两个 writer 的对照；
- 实现 CMR / SFB 的可执行版本和单测；
- 产出 20 用户子集、1 用户 × 2 sessions 的事件流、一条命令的 pilot。

### 本周明确不做

- 不接 AcCoRD / WebShop / Java 环境；
- 不做完整 causal writer（propensity + exploration + negative controls + persistence）；
- 不做 human eval、不调参追求显著效果、不写论文正文；
- 不把“pipeline 跑通”表述为“方法有效”；
- 不宣称从真实日志中“证明”了因果效应。

### 项目层面的非目标

- 不是“再做一个通用记忆漂移 benchmark”；
- 不是“再做一个记忆治理框架”；
- 不是“所有记忆都应该少写”；
- 不是“用户只要接受推荐就是被操纵”；
- 不是“用 LLM judge 给记忆文本打分”这么简单；
- 不是“检索层加一个时间衰减”就能解决。

---

## 8. 验收标准

### 本周（Week 1）

- `problem.md`、`causal_dag.md`、`metrics.md`、`pilot_protocol.md` 均可读；
- DAG 能解释“为什么 acceptance 不能直接当 preference”；
- schema v1 有 P1 签字；
- Week 2 Gate 1 配置不需要再补关键定义。

### Week 2 Gate 1

- **通过条件**：naive CMR ≥ 20%，且 provenance 相对下降 ≥ 30%；
- **不通过**：调整 influence 强度或换 domain；若 CMR < 10%，考虑把项目收缩为“记忆写入诊断工具”。

---

## 9. 关键假设与限制

1. **模拟器限制**：用户行为由模型生成，可能与真实人类不同；本周结论只能是链路验证。
2. **数据限制**：MemoryCD 是 Amazon Reviews 派生数据，存在选择偏差；真实历史不等于真实交互。
3. **识别限制**：真实数据无法完全满足 sequential ignorability；模拟器可以做识别，但不能直接外推到生产环境。
4. **测量限制**：潜在偏好 `U_t` 只能近似测量；单次行为不能等同偏好。
5. **Judge 限制**：LLM judge 可能偏向长文本、自信语气或特定模型；必须配合人工抽样校验。
6. **范围限制**：购物场景不能代表医疗、金融、法律等高风险领域。

---

## 10. 待确认问题

1. compliance 的 ground truth 是否完全由 simulator 的隐藏状态给出？人工标注只用于校验还是参与主指标？
2. `durable preference` 的判定阈值（跨几个 session、几个上下文、几次独立证据）在 dev set 上如何选？
3. `CMR` 的分母是否包含“未被写入”的 compliance 事件？当前定义包含，是否与 P5 的指标实现一致？
4. 本周是否允许调用真实 LLM 做 writer？若不允许，fixture 的 20 条事件由谁标注？
5. RQ2 的信号对比是否本周只做 provenance，还是也要做 exposure propensity 的占位版本？

---

## 11. 变更记录

| 日期 | 版本 | 变更 | 记录人 |
|---|---|---|---|
| 2026-11-12 | v0 | 初稿：问题陈述、蓝色耳机例子、四个定义、识别边界、RQ1–RQ3 | @member-01 |
