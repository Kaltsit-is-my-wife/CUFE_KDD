# InflMem Schema v1 提案（P1）

> 项目：InflMem / Agent-Induced Drift
> 产出人：@member-01（P1）
> 状态：**proposed，未冻结**；需 P2–P4 确认后由 P1 在 D4 17:00 签字
> 日期：2026-11-12
> 上游：[schema_review.md](schema_review.md)、[decisions.md](decisions.md) 的 `D3-001`、[metrics.md](metrics.md)
> 下游：P2 `InteractionEvent`、P3 `MemoryRecord` / `WriteDecision`、P4 writer、P5 `metrics.py`
> 说明：本文件是 P1 的字段提案，不是 P2–P4 的最终实现；字段命名和枚举值以确认后的 v1 为准。

---

## 1. 约定

- 字段名统一 `snake_case`；JSON 中不出现 `U_t` 这类数学符号。
- 时间统一 ISO 8601 UTC，例如 `2026-11-12T10:00:00Z`。
- ID 统一字符串，全局唯一；不允许空字符串。
- 可见性标记：
  - **A**：agent 可见，可进入 prompt；
  - **E**：evaluator 可见，用于评测/审计；
  - **H**：hidden，只允许 simulator/evaluator 读取，绝不进入 agent prompt 或 `MemoryRecord`。
- 本提案中的 `labels`、`shock`、`attributes`（真实 `U_t`）、`counterfactual` 均为 **H**。

---

## 2. `UserState` v1 提案

> 用途：保存真实潜在状态、外生冲击、反事实和标签。只允许 evaluator / simulator 读取。

| 字段 | 类型 | 必填 | 可见性 | 说明 |
|---|---|---|---|---|
| `user_id` | string | 是 | A/E | 不透明 ID；agent 只用它做 memory scope |
| `session_id` | string | 是 | A/E | 当前 session |
| `t` | integer | 是 | E/H | session 序号，从 0 开始 |
| `attributes` | object | 是 | H | 真实 `U_t`，如 `{"color":"black","price_sensitivity":0.7}` |
| `shock` | object | 是 | H | `{"occurred":false,"type":null,"delta":{}}` |
| `counterfactual` | object | 是 | H | `{"attributes":{...}}`，W0/W1 反事实状态 |
| `labels` | object | 是 | H | `compliance` / `internalization` / `exogenous` / `noise` 四个布尔值 |
| `internalization_prob` | number | 否 | H | 内化的 latent 概率，供 IDR / SFB 诊断 |
| `context_hidden` | object | 否 | H | 未进入 `InteractionEvent.context` 的隐藏上下文 |

```json
{
  "user_id": "u001",
  "session_id": "s003",
  "t": 3,
  "attributes": {"color": "black", "size": "M", "price_sensitivity": 0.7},
  "shock": {"occurred": false, "type": null, "delta": {}},
  "counterfactual": {"attributes": {"color": "blue", "size": "M", "price_sensitivity": 0.7}},
  "labels": {"compliance": false, "internalization": false, "exogenous": false, "noise": false},
  "internalization_prob": 0.12
}
```

**校验规则：**

- `attributes` 与 `counterfactual.attributes` 的键集合一致；
- `labels` 四个键必填，且最多一个为 `true`（`noise` 与 `exogenous` 可同时为 false）；
- `UserState` 不得被序列化进 `InteractionEvent` 或 `MemoryRecord`。

---

## 3. `InteractionEvent` v1 提案

> 用途：agent 可见的交互事件；也是 writer 和 evaluator 的共同输入。

| 字段 | 类型 | 必填 | 可见性 | 说明 |
|---|---|---|---|---|
| `event_id` | string | 是 | A/E | 全局唯一 |
| `user_id` | string | 是 | A/E | 不透明 ID |
| `session_id` | string | 是 | A/E | 会话 ID |
| `turn` | integer | 是 | A/E | session 内从 0 开始，单调递增 |
| `timestamp` | string | 是 | A/E | ISO 8601 UTC |
| `context` | object | 是 | A/E | `task`、`domain`、`budget`、`scenario_id` |
| `agent_action` | object | 是 | A/E | 推荐/提问/澄清/无动作 |
| `user_response` | object | 是 | A/E | 接受/拒绝/评分/澄清/无响应 |
| `exposure` | object | 是 | A/E | 属性、值、propensity、来源、位置 |

### 3.1 `context`

```json
{"task": "headphone_purchase", "domain": "electronics", "budget": 1000, "scenario_id": "sc_012"}
```

### 3.2 `agent_action`

```json
{
  "type": "recommend",
  "item_id": "i123",
  "attributes": {"color": "blue", "size": "M"},
  "text": "黑色暂时没货，这款蓝色同配置，今天 899。",
  "candidate_set": [
    {"item_id": "i123", "attributes": {"color": "blue"}, "rank": 1},
    {"item_id": "i124", "attributes": {"color": "black"}, "rank": 2}
  ],
  "rank": 1
}
```

- `type`：`recommend` / `ask` / `clarify` / `no_action`；
- `candidate_set` 允许为空数组（非推荐动作）；
- `text` 是措辞干预的一部分，不能省略。

### 3.3 `user_response`

```json
{"type": "accept", "item_id": "i123", "utterance": "行吧，蓝色也可以。", "rating": null}
```

- `type`：`accept` / `reject` / `rating` / `clarify` / `no_response`；
- `rating` 仅当 `type == "rating"` 时非空。

### 3.4 `exposure`

```json
{"attribute": "color", "value": "blue", "propensity": 0.82, "source": "recommendation", "position": 1}
```

- `source`：`recommendation` / `organic` / `unknown`；
- `propensity` 允许为 `null`；若 writer 使用，必须在方法中说明；
- `position` 从 1 开始；非推荐曝光可为 `null`。

**禁止字段：** `U_t`、`shock`、`labels`、`internalization`、`compliance` 不得出现在 `InteractionEvent` 的任何层级。

---

## 4. `MemoryRecord` v1 提案

> 用途：agent 可检索、evaluator 可审计的记忆记录。

| 字段 | 类型 | 必填 | 可见性 | 说明 |
|---|---|---|---|---|
| `memory_id` | string | 是 | A/E | 全局唯一、稳定 |
| `user_id` | string | 是 | A/E | 必须与来源事件一致 |
| `session_id` | string | 是 | A/E | 写入所在 session |
| `attribute` | string | 是 | A/E | 如 `color` |
| `value` | string / number | 是 | A/E | 如 `blue` |
| `memory_type` | enum | 是 | A/E | `durable` / `hedged` / `episodic` / `hypothesis` |
| `evidence_type` | enum | 是 | A/E | 见 4.1 |
| `source_event_ids` | array[string] | 是 | A/E | 非空，且每个 ID 可解析 |
| `influence_prob` | number | 是 | A/E | `[0,1]`，由可观测字段估计 |
| `confidence` | number | 是 | A/E | `[0,1]`，作为稳定偏好的置信度 |
| `validity` | object | 是 | A/E | `start` / `end` / `context` |
| `counterevidence` | array[string] | 否 | A/E | 相反证据的 event_id 或 memory_id |
| `status` | enum | 是 | A/E | `active` / `retracted` / `superseded` |
| `supersedes` | array[string] | 否 | A/E | 被替换的旧 memory_id |
| `text` | string | 是 | A/E | 自然语言记录；不得作为唯一事实来源 |
| `created_at` | string | 是 | A/E | ISO 8601 UTC |
| `updated_at` | string | 是 | A/E | ISO 8601 UTC |

### 4.1 `evidence_type` 枚举

| 值 | 含义 | 初始信任 |
|---|---|---|
| `explicit_statement` | 用户主动说“我喜欢 X” | 高 |
| `independent_choice` | 没有推荐时用户选择 X | 中高 |
| `repeat_purchase` | 跨时间、跨上下文复购 X | 高 |
| `agent_suggested_accepted` | agent 推荐后接受 X | 低到中 |
| `inferred` | agent 从行为推断 | 低 |
| `corrected` | 用户明确纠正旧记忆 | 高，触发旧记忆降权 |

```json
{
  "memory_id": "m001",
  "user_id": "u001",
  "session_id": "s001",
  "attribute": "color",
  "value": "blue",
  "memory_type": "hedged",
  "evidence_type": "agent_suggested_accepted",
  "source_event_ids": ["e001"],
  "influence_prob": 0.72,
  "confidence": 0.35,
  "validity": {"start": "2026-11-12", "end": null, "context": "commute_headphones"},
  "counterevidence": [],
  "status": "active",
  "supersedes": [],
  "text": "User accepted blue after agent recommendation; prior preference black; may be compliance.",
  "created_at": "2026-11-12T10:00:00Z",
  "updated_at": "2026-11-12T10:00:00Z"
}
```

**校验规则：**

- `source_event_ids` 非空，且每个 ID 存在于对应 user 的 `InteractionEvent`；
- `memory_type == durable` 时，`confidence >= τ_durable`（默认 0.6）；
- `evidence_type == corrected` 时，`counterevidence` 至少一项，且 `supersedes` 非空；
- `status == retracted` 的记忆不可被检索；
- `text` 不得包含 hidden label 或 `counterfactual` 内容；
- 同一 `user_id` 下 `memory_id` 唯一。

---

## 5. `WriteDecision` v1 提案

> 用途：记录 writer 对每个事件的写入决策，支持 CMR / Coverage 的分母和反事实回放。只对 evaluator/audit 可见。

| 字段 | 类型 | 必填 | 可见性 | 说明 |
|---|---|---|---|---|
| `decision_id` | string | 是 | E | 全局唯一 |
| `event_id` | string | 是 | E | 对应 `InteractionEvent` |
| `user_id` | string | 是 | E | 作用域 |
| `session_id` | string | 是 | E | 作用域 |
| `action` | enum | 是 | E | `durable` / `hedged` / `episodic` / `abstain` |
| `reason` | string | 是 | E | 写入/不写的理由 |
| `influence_prob` | number | 是 | E | `[0,1]` |
| `confidence` | number | 是 | E | `[0,1]` |
| `memory_id` | string / null | 条件 | E | `action != abstain` 时必填 |
| `timestamp` | string | 是 | E | ISO 8601 UTC |

```json
{
  "decision_id": "d001",
  "event_id": "e001",
  "user_id": "u001",
  "session_id": "s001",
  "action": "hedged",
  "reason": "agent recommended blue; black out of stock; single acceptance not enough for durable",
  "influence_prob": 0.72,
  "confidence": 0.35,
  "memory_id": "m001",
  "timestamp": "2026-11-12T10:00:01Z"
}
```

**校验规则：**

- `action != abstain` 时 `memory_id` 必须非空，且能在 `MemoryRecord` 中找到；
- `action == abstain` 时 `memory_id` 必须为 `null`；
- 每个 `event_id` 至少有一条 `WriteDecision`（包括 abstain），否则无法计算 Coverage；
- `WriteDecision` 不进入 agent prompt。

---

## 6. 与指标的映射

| 指标 | 需要的字段 | 计算口径 |
|---|---|---|
| CMR | `UserState.labels.compliance`、`MemoryRecord.memory_type`、`source_event_ids` | compliance 事件中被写成 durable 的比例 |
| CMR_cond | 同上 + `WriteDecision.action` | 分母为 `action != abstain` 的 compliance 事件 |
| Coverage | `WriteDecision.action` | 至少有一条非 abstain 记录的事件/用户比例 |
| IDR | `UserState.labels.internalization`、`memory_type` | internalization 事件中写成 durable 的比例 |
| SFB | `MemoryRecord.attribute/value/confidence`、`InteractionEvent.exposure`、`UserState.attributes` | 控制真实偏好后，memory 推断偏好对 exposure 的回归系数 |

> 具体公式与失败模式见 [metrics.md](metrics.md)。

---

## 7. 最小校验清单

- [ ] 所有必填字段存在且非空；
- [ ] `InteractionEvent` / `MemoryRecord` 不含 hidden label；
- [ ] `source_event_ids` 可解析；
- [ ] `WriteDecision` 覆盖每个事件（含 abstain）；
- [ ] `MemoryRecord.user_id` 与来源事件一致；
- [ ] `status == retracted` 的记忆不可检索；
- [ ] `confidence` / `influence_prob` / `propensity` 在 `[0,1]`；
- [ ] 时间戳可排序，`turn` 在 session 内唯一。

---

## 8. 待 P2–P4 确认的问题

| # | 问题 | 负责人 | 截止 |
|---|---|---|---|
| 1 | `memory_type` / `evidence_type` 枚举是否最终确定 | P4 | D4 17:00 |
| 2 | `candidate_set` 是否需要保存完整候选及排序 | P2 | D4 17:00 |
| 3 | `attribute` / `value` 是单值还是列表（多属性） | P3 + P4 | D4 17:00 |
| 4 | `text` 是否作为必填字段，是否允许为空 | P4 | D4 17:00 |
| 5 | `influence_prob` 的估计方法（规则/LLM/混合） | P4 | D5 |
| 6 | `exposure.propensity` 是否允许 writer 使用 | P1 + P4 | D4 17:00 |
| 7 | `turn` 是否跨 session 重置（当前提案：重置） | P2 | D4 17:00 |

---

## 9. 变更记录

| 日期 | 版本 | 变更 | 记录人 |
|---|---|---|---|
| 2026-11-12 | v1-proposal | 初稿：四个 schema 的字段、枚举、示例、校验规则、指标映射 | @member-01 |
