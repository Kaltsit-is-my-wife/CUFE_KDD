# InflMem 决策记录（decisions.md）

> 项目：InflMem / Agent-Induced Drift
> 维护人：@member-01（P1）
> 规则：只追加，不删除；每条决策记录日期、参与人、结论、依据、影响范围和后续动作。
> 状态：`proposed` → `accepted` → `frozen` → `superseded`
> 上游：[kickoff.md](kickoff.md)、[schema_review.md](schema_review.md)、[metrics.md](metrics.md)
> 依据：[Week 1 五人任务清单](references/2026-10-30_Week1_五人任务清单.md) 的 D3 要求

---

## D3-001：Schema v0 review 结论与 v1 变更清单

| 字段 | 内容 |
|---|---|
| 决策编号 | `D3-001` |
| 日期 | 2026-11-12 |
| 主持人 | @member-01（P1） |
| 参与人 | P1–P5（待确认） |
| 状态 | `proposed`（待 D4 17:00 schema v1 冻结时转为 `frozen`） |
| 影响范围 | `UserState`、`InteractionEvent`、`MemoryRecord`、`WriteDecision`、`metrics.md`、P2/P3/P4 实现、P5 指标 |
| 关联文档 | [schema_review.md](schema_review.md)、[metrics.md](metrics.md)、[causal_dag.md](causal_dag.md) |

### 结论

1. **保持三个 schema 的职责分离**：
   - `UserState`：evaluator / simulator only，包含 `U_t`、shock、反事实和标签；
   - `InteractionEvent`：agent 可见的交互事件；
   - `MemoryRecord`：agent 可检索、evaluator 可审计的记忆记录。

2. **`MemoryRecord` 必须新增以下字段**：
   - `memory_type`：`durable` / `hedged` / `episodic` / `hypothesis`；
   - `status`：`active` / `retracted` / `superseded`；
   - `counterevidence`：相反证据列表；
   - `validity.context`：记忆生效的上下文；
   - `supersedes`：被替换的旧记忆 ID；
   - `created_at` / `updated_at`。

3. **`InteractionEvent` 必须新增以下字段**：
   - `context`：任务、预算、domain 等上下文；
   - `agent_action.text`：agent 的措辞；
   - `agent_action.candidate_set`：候选集合；
   - `exposure.source`：`recommendation` / `organic`；
   - `exposure.position`：曝光位置。

4. **新增 `WriteDecision` 审计 schema**（建议采纳）：
   - 字段：`decision_id`、`event_id`、`user_id`、`session_id`、`action`（`durable` / `hedged` / `episodic` / `abstain`）、`reason`、`influence_prob`、`confidence`、`memory_id`、`timestamp`；
   - 目的：让 CMR / Coverage 的分母可确定性计算，区分 `abstain` 与“未处理”，并支持反事实回放。

5. **Hidden state 禁止进入 agent-visible schema**：
   - `U_t`、shock、internalization、compliance 标签只能存在于 `UserState` 或 evaluator 专用日志；
   - `exposure.propensity` 和 `influence_prob` 可以由可观测字段估计，但不能由 hidden label 直接计算；
   - 任何从 hidden label 直接计算 writer 输入的实现，视为泄漏，实验无效。

6. **冻结时间**：schema v1 在 D4 17:00 冻结，由 P1 签字；冻结后字段变更必须写 1 页 RFC，24 小时评论期。

### 依据

- CMR / IDR 需要 `memory_type` 才能确定性判断“是否写成 durable preference”；
- Coverage 需要 `WriteDecision` 才能区分“少写”和“没处理”；
- SFB 需要 `exposure.source` / `position` / `propensity` 才能构造 exposure 变量；
- 反事实回放需要 `source_event_ids`、`status`、`supersedes` 和 `snapshot` / `restore`；
- `context` / `validity.context` 用于检测 scope inflation；
- 隐藏标签泄漏会让所有指标失去意义。

### 未决问题

| # | 问题 | 负责人 | 截止 |
|---|---|---|---|
| 1 | `memory_type` / `evidence_type` 的最终枚举值 | P4 | D3 14:00 |
| 2 | `exposure.propensity` 是否允许 writer 使用；若允许，如何在方法中说明 | P1 + P4 | D3 14:00 |
| 3 | `WriteDecision` 是否本周采纳；若不采纳，Coverage 的 fallback 口径 | P1 + P4 + P5 | D3 14:00 |
| 4 | `MemoryRecord.text` 是否为必需字段；主指标是否只依赖结构化字段 | P3 + P5 | D4 17:00 |
| 5 | `InteractionEvent.turn` 从 0 还是 1 开始；跨 session 是否重置 | P2 | D3 14:00 |
| 6 | 多属性场景下 `attribute` / `value` 是单值还是列表 | P3 + P4 | D4 17:00 |

### 后续动作

| 动作 | 负责人 | 截止 | 产出 |
|---|---|---|---|
| 按本决策修改三个 schema | P2 / P3 / P4 | D4 17:00 | schema v1 草案 |
| 更新 `metrics.md` 的 schema 依赖（含 `WriteDecision`） | P1 / P5 | D3 14:00 | `metrics.md` v1 |
| 实现 user scope 隔离测试 | P3 | D5 | 测试用例 |
| schema v1 冻结并签字 | P1 | D4 17:00 | 本文件追加 `D4-001` |

### 签字

| 角色 | 姓名/编号 | 结论 | 日期 |
|---|---|---|---|
| P1 Lead / 因果与评测 | @member-01 | 提出并主持 | 2026-11-12 |
| P2 Sim / Data | 待定 | 待确认 | — |
| P3 Memory | 待定 | 待确认 | — |
| P4 Method | 待定 | 待确认 | — |
| P5 Eval / Analysis | 待定 | 待确认 | — |

---

## 后续决策条目模板

> 复制以下结构追加，不要删除历史条目。

```text
## D<day>-<seq>：<一句话决策>

| 字段 | 内容 |
|---|---|
| 决策编号 | D<day>-<seq> |
| 日期 | YYYY-MM-DD |
| 主持人 | @member-xx |
| 参与人 | ... |
| 状态 | proposed / accepted / frozen / superseded |
| 影响范围 | ... |
| 关联文档 | ... |

### 结论
### 依据
### 未决问题
### 后续动作
### 签字
```
