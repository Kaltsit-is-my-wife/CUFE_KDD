# InflMem 指标口径（metrics.md v0）

> 项目：InflMem / Agent-Induced Drift
> 产出人：@member-01（P1 Lead / 因果与评测）
> 状态：v0 草稿；Week 1 只要求 CMR / SFB 可执行，AL / OUR / CR 允许占位
> 日期：2026-11-12
> 上游：[kickoff.md](kickoff.md)、[problem.md](problem.md)、[causal_dag.md](causal_dag.md)
> 下游：P5 的 `src/inflmem/eval/metrics.py`、`scripts/run_pilot.py`、`pilot_protocol.md`

---

## 1. 目的与本周范围

本文件是 P1 对指标的唯一口径说明。每个指标必须写清四件事：

1. **定义**：公式、分母、单位；
2. **输入**：需要哪些 schema 字段或隐藏标签；
3. **归一化 / 聚合**：按事件、按用户还是按域；如何报告不确定性；
4. **失败模式**：分母为零、少写、标签缺失、指标歧义时怎么处理。

**Week 1 实现范围：**

| 指标 | Week 1 状态 | 说明 |
|---|---|---|
| CMR | **必须实现** | 主指标，含 `CMR_cond` |
| SFB | **必须实现** | 主指标，回归系数 |
| IDR | 建议实现 | 防止 writer 过度保守 |
| Quality | 建议实现最小版 | 至少任务成功率 + 多样性 |
| Coverage | **必须报告** | 防止“少写”刷低 CMR |
| AL / OUR / CR | 占位 | 可返回 `null` 或 `not_implemented` |
| Faithfulness | 占位 | Week 1 只做 `source_event_ids` 覆盖率 |

> 本周所有指标只用于 **pipeline sanity check**，不能写成“方法有效”。

---

## 2. 记号与输入

| 记号 | 含义 | 来源 |
|---|---|---|
| `C` | 被标注为 compliance 的事件集合 | 隐藏标签（simulator） |
| `I` | 被标注为 internalization 的事件集合 | 隐藏标签（simulator） |
| `X` | 被标注为 exogenous / noise / pre-existing 的事件集合 | 隐藏标签 |
| `E` | 全部被评估的 `InteractionEvent` 集合 | `InteractionEvent` |
| `M(e)` | 由事件 `e` 写出的 `MemoryRecord` 集合 | `MemoryRecord` |
| `W(e)` | 事件 `e` 是否至少写出一条 memory | `MemoryRecord` |
| `D(e)` | 事件 `e` 是否写出 **durable preference** memory | `MemoryRecord.memory_type` |
| `U_{i,t}` | 用户真实潜在偏好 | 隐藏状态 |
| `\hat U_{i,t}` | memory 推断出的偏好 | 从 `MemoryRecord` 映射 |
| `Exposure_{i,t}` | 目标属性是否被 agent 曝光 / 曝光强度 | `InteractionEvent.exposure` |

### 2.1 “durable preference” 的操作化

CMR / IDR 都依赖“这条 memory 是否把行为写成了稳定偏好”。Week 1 采用**结构化字段优先**，不用 LLM judge 判定：

```text
D(e) = 1  当且仅当存在 m ∈ M(e)，满足：
          m.memory_type == "durable"
          或（m.memory_type 缺失时）
          m.evidence_type ∈ {explicit_statement, independent_choice, repeat_purchase}
          且 m.confidence >= τ_durable
```

- `τ_durable` 暂定 `0.6`，必须在 dev set 上确定，不能在 test 上调；
- 如果 schema v1 没有 `memory_type`，P5 的 `metrics.py` 必须内置上述确定性规则，并在报告中注明；
- **不允许**用 LLM judge 判断“这句话是不是在说稳定偏好”作为主指标，只能作为人工抽检的辅助。

### 2.2 必要的 schema 字段

| 字段 | 所属 schema | 用途 | 缺失后果 |
|---|---|---|---|
| `event_id` | `InteractionEvent` | 对齐事件与 memory | 无法计算 source precision |
| `user_id` / `session_id` / `turn` | `InteractionEvent` | 用户级聚合、时间顺序 | 无法做配对/时序分析 |
| `user_response.type` | `InteractionEvent` | 识别 accept / reject / rating | 无法构造 CMR 的分母 |
| `exposure.attribute/value/propensity` | `InteractionEvent` | SFB 的自变量 | SFB 不可计算 |
| `memory_type` | `MemoryRecord` | 判断 durable / hedged / episodic | CMR 依赖 fallback 规则 |
| `action` | `WriteDecision`（推荐）或 `MemoryRecord.write_action`（fallback） | 区分 durable / hedged / episodic / abstain | Coverage 口径不清；无法区分 abstain 与未处理 |
| `evidence_type` | `MemoryRecord` | 区分推荐后接受 / 独立选择 | 无法判断证据强度 |
| `source_event_ids` | `MemoryRecord` | 反事实回放、来源审计 | 无法定位 memory 来源 |
| `attribute` / `value` / `confidence` | `MemoryRecord` | 映射 `\hat U` | SFB 不可计算 |
| `validity` | `MemoryRecord` | 上下文/时间范围 | 无法处理 scope inflation |
| `U_t` / `I_t` / 标签 | 隐藏状态 | 评测真值 | 指标不可计算（只能人工标注） |

> Coverage 的分母需要 `WriteDecision`。若 schema v1 不采纳 `WriteDecision`，P5 只能用 `MemoryRecord.source_event_ids` 反推，无法区分 `abstain` 与“未处理”，报告中必须标注该限制。详见 [schema_review.md](schema_review.md) §5 与 [decisions.md](decisions.md) `D3-001`。

> 这些字段是否进入 schema v1，需要在 D3 schema review 中逐条确认；本文件只定义指标依赖。

---

## 3. 主指标

### 3.1 CMR：Compliance Misattribution Rate

**问题**：有多少 compliance 被写成了 durable preference？

**定义**：

```text
CMR = |{ e ∈ C : D(e) = 1 }| / |C|
```

- 分母是**所有 compliance 事件**，包括没有被写入的；
- 因此“完全不写”不会让 CMR 变好：分母仍然存在，分子为 0，CMR = 0，但 Coverage 也会是 0；
- 必须同时报告 `CMR_cond` 和 `Coverage`。

**条件版本**：

```text
CMR_cond = |{ e ∈ C : D(e) = 1 }| / |{ e ∈ C : W(e) = 1 }|
```

- 分母是“至少写入了一条 memory 的 compliance 事件”；
- 用于区分“写得少”和“写得准”；
- 如果分母为 0，报告 `N/A`，不能报 0。

**归一化**：比例，范围 `[0, 1]`，越低越好。

**聚合**：先按用户计算，再对用户取平均；同时报告 `n_users`、`n_compliance_events`、`n_written_compliance_events`。

**失败模式**：

| 情况 | 处理 |
|---|---|
| C 为空（没有 compliance 事件） | 报 `N/A`，并在报告中说明该用户/域没有 compliance 事件 |
| 所有 compliance 都 abstain | CMR = 0，`CMR_cond = N/A`，Coverage = 0；必须在报告中并列展示，不能只报 CMR |
| durable 判定歧义 | 使用结构化字段 + `τ_durable`；人工抽检 100 条，报告一致率 |
| memory 文本与结构化字段冲突 | 结构化字段为主；文本 faithfulness 另算 |
| 多属性 | 按属性分别计算后宏平均；同时报告每个属性的分母 |

### 3.2 SFB：Self-Fulfilling Bias

**问题**：控制真实偏好后，memory 推断的偏好是否仍然朝 agent exposure 方向偏移？

**定义**：拟合

```text
\hat U_{i,t} = α + β · Exposure_{i,t} + γ · U_{i,t} + controls + ε
```

- `\hat U_{i,t}`：memory 推断出的偏好（从 `MemoryRecord.attribute/value/confidence` 映射，不用自由文本）；
- `Exposure_{i,t}`：目标属性是否被曝光，或曝光强度（`exposure.propensity` / 推荐位置）；
- `U_{i,t}`：隐藏真实偏好；
- `controls`：上下文、session、历史长度、用户固定效应；
- **`β` 就是 SFB**；理想值为 0，显著为正说明记忆朝曝光方向漂移。

**归一化**：

- 连续属性：标准化 `\hat U`、`U`、`Exposure`，报告标准化 `β`；
- 类别属性：对目标值做 one-hot，或定义 signed match score（推荐值 = +1，相反值 = -1，未曝光 = 0）；
- 多属性：每个属性单独回归，报告宏平均 `β` 和每个属性的 `β`。

**聚合**：

- 分析单位是用户，不是单条 memory；
- 使用 user-level paired bootstrap（≥1,000 次）报告 95% CI；
- 可报告 pooled OLS + 用户聚类标准误，但主表以 bootstrap CI 为准。

**失败模式**：

| 情况 | 处理 |
|---|---|
| 没有隐藏 `U_t` | SFB 不可计算；不能用 memory 文本代替 `U` |
| exposure 没有方差 | 无法识别；需要随机探索或换数据 |
| 类别属性编码不一致 | 固定编码规则并写入 `metrics.py`；禁止每个实验各写一套 |
| 用户数太少 | 报告 `n` 和 CI，不宣称显著性 |
| 反馈闭环导致时序相关 | 按用户聚类 / 配对 bootstrap；不要把 memory 当独立样本 |

### 3.3 IDR：Internalization Detection Rate

**问题**：真正内化的偏好，memory 有没有正确捕获？

**定义**：

```text
IDR = |{ e ∈ I : D(e) = 1 }| / |I|
```

- 分母是所有 internalization 事件；
- 分子是被正确写成 durable preference 的事件；
- 越高越好；CMR 低但 IDR 也低，说明 writer 只是过度保守。

**失败模式**：

| 情况 | 处理 |
|---|---|
| I 为空（没有 internalization 事件） | 报 `N/A` |
| internalization 标签来自 simulator | 必须说明标签生成机制；不能用行为启发式代替 |
| 一个事件对应多条 memory | 只要存在一条 durable 即计为 1；同时报告 memory 条数 |

### 3.4 Quality

**问题**：去偏之后推荐还有没有用？

**Week 1 最小版**：

| 子指标 | 定义 | 输入 |
|---|---|---|
| Task success | 下游任务成功的比例 | simulator / 规则评分 |
| NDCG@k | 推荐排序质量 | 推荐列表 + 相关性标签 |
| Diversity | 推荐属性/商品分布的熵 | 推荐列表 |
| Coverage | 至少有一条相关 memory 的 session 比例 | `MemoryRecord` + session |

**约束**：proposed 相对 best baseline 的质量下降不超过 **5%**（预注册阈值）。Week 1 只记录数值，不做显著性判断。

**失败模式**：

| 情况 | 处理 |
|---|---|
| 没有相关性标签 | 用 simulator 的规则评分；不要用 LLM judge 单独定主表 |
| diversity 与 quality 冲突 | 同时报告，不合并成单一分数 |
| 推荐列表为空 | 记为失败；不要从分母中删除 |

---

## 4. 诊断指标（Week 1 允许占位）

### 4.1 AL：Adaptation Lag

```text
AL = min{ k : |\hat U_{t+k} - U_{t+k}| < δ }
```

- 外生冲击后，memory 追上真实状态需要多少个 session；
- 若在评估窗口内从未追上，报告“censored at horizon”；
- Week 1 返回 `null`，Week 2 后再实现。

### 4.2 OUR：Over-Update Rate

```text
OUR = 由噪声/agent 影响触发、但没有真实变化的更新数 / 所有更新数
```

- 需要区分“真实变化”和“错误更新”的隐藏标签；
- Week 1 返回 `null`。

### 4.3 CR：Counterfactual Regret

```text
CR = E[Utility(W0)] - E[Utility(W1)]
```

- `W0` 无 agent 影响，`W1` 有 agent 影响；
- 需要配对世界和用户效用；
- Week 1 返回 `null`，但 schema 必须支持后续计算。

### 4.4 Faithfulness

Week 1 只检查结构化字段的覆盖率：

- `source_event_ids` 非空且能解析到真实事件的比例；
- `exposure` 是否记录；
- `validity` / `confidence` 是否记录；
- 是否存在相反证据 `counterevidence`。

文本级 faithfulness（是否保留来源、时间、上下文、置信度、反证）留到 Week 2，用 LLM judge + 人工抽检，不作为唯一证据。

### 4.5 Diversity / Coverage

- **Diversity**：推荐结果中不同属性/商品的分布熵；
- **Coverage**：至少有一条相关 memory 的 session 比例；
- 两者用于检测“记忆塌缩”和“靠少写刷低 CMR”。

---

## 5. 聚合与统计

1. **分析单位**：用户/场景，不以单条 memory 为独立样本，避免伪重复；
2. **配对设计**：同一用户的有影响/无影响世界配对比较；
3. **置信区间**：user-level paired bootstrap，至少 1,000 次重采样，报告 95% CI；
4. **混合效应模型**（Week 2+）：`metric ~ method + domain + (1 | user) + (1 | scenario)`；
5. **主指标预注册**：CMR、SFB、IDR、Quality；其余为探索性分析；
6. **多重比较**：主指标用 Holm-Bonferroni；副指标标注 `exploratory`；
7. **效应量**：报告绝对差、相对差、95% CI，不只报 p 值；
8. **样本量**：每个比例都报告分子/分母；`N/A` 与 `0` 严格区分。

**相对下降的定义**（用于 Gate 1）：

```text
relative_reduction = (CMR_naive - CMR_provenance) / CMR_naive
```

- 分母为 0 时，报 `N/A`，不能报 100% 下降；
- 必须同时报告两者的绝对值和 CI。

---

## 6. Week 1 golden fixtures 与单测

P5 的 `metrics.py` 至少要覆盖以下 fixture。每个 fixture 都要有期望输出，写入 `tests/fixtures/` 和 `tests/test_metrics.py`。

| Fixture | 构造 | 期望 |
|---|---|---|
| `obvious_miswrite` | 1 个 compliance 事件；naive 写出 durable memory | `CMR = 1.0`，`CMR_cond = 1.0`，`IDR = 0` |
| `correct_internalization` | 1 个 internalization 事件；写出 durable memory，且证据为独立选择 | `CMR = 0`（不在 `C`），`IDR = 1.0` |
| `no_exposure` | 1 个独立选择事件，无 exposure；标签为 pre-existing | 不计入 `C`；`CMR` 分母为 0 → `N/A` |
| `abstain` | 1 个 compliance 事件；writer 不写 | `CMR = 0`，`CMR_cond = N/A`，`Coverage = 0` |
| `hedged` | 1 个 compliance 事件；写出 hedged memory | `CMR = 0`，`CMR_cond = 0`，`Coverage = 1` |
| `mixed` | 2 个 compliance 事件；1 条 durable + 1 条 hedged | `CMR = 0.5`，`CMR_cond = 0.5`，`Coverage = 1` |
| `mixed_abstain` | 2 个 compliance 事件；1 条 durable + 1 条 abstain | `CMR = 0.5`，`CMR_cond = 1.0`，`Coverage = 0.5` |
| `sfb_synthetic` | 3 个用户，已知 `U`、`Exposure`、`\hat U`；`\hat U` 随 exposure 正向偏移 | `β > 0`，方向与构造一致 |

**单测要求**：

- 每个指标至少一个正常用例 + 一个边界用例（分母为零 / 空输入 / 缺失字段）；
- 测试必须能在不调用 LLM API 的情况下运行；
- 输出 `metrics.json` 时，`N/A` 用 `null` 表示，不用 `0`。

---

## 7. 报告格式

每次 run 至少输出：

```text
runs/<run_id>/
  metrics.json      # 机器可读：每个指标的 value / n / denominator / ci / per_domain
  metrics.md        # 人可读：主表 + 备注
```

`metrics.json` 的建议结构：

```json
{
  "run_id": "20261112_naive_mock_memorycd20_seed0",
  "method": "naive",
  "domain": "electronics",
  "metrics": {
    "cmr": {"value": 0.35, "numerator": 7, "denominator": 20, "ci95": [0.18, 0.55]},
    "cmr_cond": {"value": 0.41, "numerator": 7, "denominator": 17, "ci95": [0.20, 0.64]},
    "coverage": {"value": 0.85, "numerator": 17, "denominator": 20},
    "sfb": {"beta": 0.22, "ci95": [0.05, 0.39], "n": 20},
    "idr": {"value": 0.60, "numerator": 3, "denominator": 5}
  },
  "notes": "pipeline sanity check; not a scientific conclusion"
}
```

**报告规则**：

- CMR 必须与 Coverage、CMR_cond 一起出现；
- SFB 必须带 CI 和 `n`；
- IDR 必须带分母；
- 所有 `N/A` 必须说明原因；
- 区分“链路验证”与“科学结论”。

---

## 8. Gate 1 判定

| 条件 | 阈值 | 不通过时 |
|---|---|---|
| naive CMR | ≥ 20% | 调整 influence 强度 / domain |
| provenance 相对下降 | ≥ 30% | 检查 provenance 信号是否被 writer 使用 |
| Quality 下降 | ≤ 5% | 检查是否靠少写/降低推荐质量换低 CMR |
| CMR < 10% | 任一 domain | 考虑收缩为“记忆写入诊断工具” |

**Gate 1 通过时必须同时满足**：naive CMR ≥ 20%、provenance 相对下降 ≥ 30%、Quality 下降 ≤ 5%。

---

## 9. 待确认问题

1. `MemoryRecord` 是否包含 `memory_type`？是否采纳 `WriteDecision`？若没有，CMR 的 durable 判定只能走 fallback 规则，Coverage 无法区分 abstain 与未处理，需在 schema review 中决定。
2. compliance / internalization 标签是否完全由 simulator 给出？人工标注只做校验还是参与主指标？
3. `CMR` 的分母是否包含“没有触发 memory 检索”的 session？当前定义包含所有 compliance 事件，是否与 P5 实现一致？
4. `SFB` 对类别属性用 one-hot 还是 signed match score？两者结果可能不同，必须固定。
5. Quality 的 best baseline 是 naive writer 还是全部 baseline 中的最优？Gate 1 阶段建议用 naive writer。
6. 多属性时主表用宏平均还是微平均？建议宏平均，并附每个属性的分母。
7. 人工抽检 100 条的标注指南由谁写？P1 还是 P5？
8. Week 1 是否实现 IDR？如果时间不够，至少保留占位并在报告中说明。

---

## 10. 变更记录

| 日期 | 版本 | 变更 | 记录人 |
|---|---|---|---|
| 2026-11-12 | v0 | 初稿：CMR / CMR_cond / SFB / IDR / Quality / Coverage 定义、聚合、失败模式、golden fixtures、Gate 1 口径 | @member-01 |
