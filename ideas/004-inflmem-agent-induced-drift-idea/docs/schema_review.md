# InflMem Schema Review（D3）

> 项目：InflMem / Agent-Induced Drift
> 主持人：@member-01（P1）
> 参与人：P1–P5（待确认）
> 日期：2026-11-12
> 状态：v0 review；schema v1 已于 2026-11-12 按 [decisions.md](decisions.md) 的 `D4-002` 冻结（默认全组使用）
> 上游：[kickoff.md](kickoff.md)、[problem.md](problem.md)、[causal_dag.md](causal_dag.md)、[metrics.md](metrics.md)
> 依据：项目 Idea 说明 §6.6 的三个 schema 示例；P2–P4 的 v0 实现如与 v1 有差异，走 RFC

---

## 1. Review 目标与规则

本次 review 只审三个 schema：

| Schema | 角色 | 可见性 |
|---|---|---|
| `UserState` | 隐藏真实状态与反事实标签 | evaluator / simulator only |
| `InteractionEvent` | agent 可见的交互事件 | agent + evaluator |
| `MemoryRecord` | 可审计的记忆记录 | agent 可检索；evaluator 可审计 |

每个字段必须回答四个问题：

1. 这个字段是 **agent 可见** 还是 **evaluator 可见**？
2. 这个字段能否支持 **反事实回放**？
3. 这个字段是否 **泄露 hidden state**（`U_t`、shock、internalization、compliance 标签）？
4. 这个字段是否支持 **user scope 隔离** 和 **来源追溯**？

**冻结规则：**

- D4 17:00 冻结 schema v1；
- 冻结后任何字段变更必须写 1 页 RFC，24 小时评论期；
- 谁改 schema，谁负责改所有 consumer 和测试。

---

## 2. `UserState` 字段评审

> `UserState` 是 evaluator-only schema。除 `user_id` / `session_id` 可作为不透明标识外，其余字段绝不能进入 agent prompt 或 `MemoryRecord`。

| 字段 | 可见性 | 反事实回放 | 泄漏风险 | 结论 |
|---|---|---|---|---|
| `user_id` | evaluator；agent 只可见不透明 ID | 需要 | 低 | 保留；agent 侧使用 pseudonymous ID |
| `session_id` | evaluator / agent | 需要 | 低 | 保留 |
| `attributes`（`U_t`） | hidden | 需要 | **高**：泄露真实偏好 | 只允许 evaluator 读取；不得写入 prompt |
| `shock.occurred/type` | hidden | 需要 | **高**：泄露外生冲击标签 | 只允许 evaluator 读取 |
| `counterfactual` | hidden | 需要 | **高**：泄露 W0/W1 反事实 | 只允许 evaluator 读取 |
| `labels`（compliance/internalization/exogenous/noise） | hidden | 需要 | **高**：直接泄露答案 | 建议新增；只允许 evaluator 读取 |
| `context`（任务、预算、场景） | 部分 agent 可见 | 需要 | 中 | 拆成 agent-visible 的 `InteractionEvent.context` 与 hidden 的完整上下文 |

**新增建议：**

- 增加 `labels` 字段，明确四类标签；
- 增加 `internalization` 的 latent 值或概率，供 IDR / SFB 使用；
- 保留 `counterfactual`，但只允许 evaluator 访问。

---

## 3. `InteractionEvent` 字段评审

| 字段 | 可见性 | 反事实回放 | 泄漏风险 | 结论 |
|---|---|---|---|---|
| `event_id` | agent + evaluator | 需要 | 低 | 保留；全局唯一 |
| `user_id` | agent + evaluator | 需要 | 低 | 使用 pseudonymous ID |
| `session_id` | agent + evaluator | 需要 | 低 | 保留 |
| `turn` | agent + evaluator | 需要 | 低 | 保留；明确从 0 还是 1 开始 |
| `agent_action.type` | agent + evaluator | 需要 | 低 | 保留 |
| `agent_action.item_id` | agent + evaluator | 需要 | 低 | 保留 |
| `agent_action.attributes` | agent + evaluator | 需要 | 低 | 保留 |
| `agent_action.text` | agent + evaluator | 需要 | 低 | **建议新增**；措辞本身是干预 |
| `agent_action.candidate_set` | agent + evaluator / logged | 需要 | 低 | **建议新增**；支持 propensity 与曝光分析 |
| `user_response.type` | agent + evaluator | 需要 | 低 | 保留；明确 accept/reject/rating/clarify |
| `user_response.item_id` | agent + evaluator | 需要 | 低 | 保留 |
| `user_response.utterance` | agent + evaluator | 需要 | 低 | 保留 |
| `exposure.attribute/value` | agent + evaluator / logged | 需要 | 低 | 保留 |
| `exposure.propensity` | evaluator / logged | 需要 | 中 | 保留；若 writer 使用，必须在方法中说明 |
| `exposure.source`（recommendation/organic） | agent + evaluator | 需要 | 低 | **建议新增**；区分推荐曝光与自然曝光 |
| `exposure.position` | agent + evaluator / logged | 需要 | 低 | **建议新增**；位置影响接受率 |
| `timestamp` | agent + evaluator | 需要 | 低 | 保留；统一 UTC / 时区 |
| `context`（任务、预算、domain） | agent + evaluator | 需要 | 低 | **建议新增**；当前 schema 缺少上下文 |
| hidden `U_t` / shock / labels | **禁止出现** | — | **高** | 绝不能写入 `InteractionEvent` |

**关键问题：**

1. 当前 `InteractionEvent` 没有 `context`，无法区分“通勤耳机”和“运动耳机”，会导致 scope inflation 无法检测；
2. 当前 `exposure` 只有 `propensity`，没有 `source` / `position`，无法区分“agent 推荐”与“用户自己看到”；
3. 当前 `agent_action` 没有 `text` / `candidate_set`，无法把“措辞”和“候选集合”作为干预分析；
4. `user_response` 缺少“是否独立于推荐”的标记，但这个信息更适合放在 `MemoryRecord.evidence_type` 或 `WriteDecision`，而不是事件本身。

---

## 4. `MemoryRecord` 字段评审

| 字段 | 可见性 | 反事实回放 | 泄漏风险 | 结论 |
|---|---|---|---|---|
| `memory_id` | agent + evaluator | 需要 | 低 | 保留；全局唯一、稳定 |
| `user_id` | agent + evaluator | 需要 | 低 | 保留；必须做 user scope 隔离 |
| `attribute` / `value` | agent + evaluator | 需要 | 低 | 保留；SFB 的输入 |
| `evidence_type` | agent + evaluator | 需要 | 低 | 保留；枚举值需冻结 |
| `source_event_ids` | agent + evaluator | 需要 | 低 | 保留；至少一个，且必须能解析 |
| `influence_prob` | agent + evaluator | 需要 | 中 | 保留；不得由 hidden label 直接计算 |
| `confidence` | agent + evaluator | 需要 | 低 | 保留；`τ_durable` 依赖它 |
| `validity.start/end` | agent + evaluator | 需要 | 低 | 保留 |
| `validity.context` | agent + evaluator | 需要 | 低 | **建议新增**；支持 scope inflation 检测 |
| `text` | agent + evaluator | 需要 | 中 | 保留；但 `text` 不得成为唯一事实来源 |
| `memory_type` | agent + evaluator | 需要 | 低 | **必须新增**：durable / hedged / episodic / hypothesis |
| `status` | agent + evaluator | 需要 | 低 | **建议新增**：active / retracted / superseded |
| `counterevidence` | agent + evaluator | 需要 | 低 | **建议新增**；相反证据列表 |
| `created_at` / `updated_at` | agent + evaluator | 需要 | 低 | **建议新增**；时间顺序 |
| `supersedes` | agent + evaluator | 需要 | 低 | **建议新增**；旧记忆降权/替换关系 |
| hidden `U_t` / labels | **禁止出现** | — | **高** | 绝不能写入 memory |

**关键问题：**

1. **缺少 `memory_type`**：CMR / IDR 无法确定性判断“是否写成 durable preference”；
2. **缺少 `status` / `supersedes`**：用户明确纠正后，旧记忆无法被标记为 retracted，反事实回放会读到过期记忆；
3. **缺少 `counterevidence`**：无法表达“已有相反证据”，也无法测试 `explicit_correction` 的降权；
4. **`text` 不应是唯一事实来源**：主指标必须用结构化字段，`text` 只用于 faithfulness；
5. **`source_event_ids` 必须非空**：否则无法定位来源，也无法做反事实回放。

---

## 5. 缺失的 `WriteDecision` 审计记录

CMR 的分母包含“没有被写入的 compliance 事件”，Coverage 也需要知道每个事件是否被写入。仅靠 `MemoryRecord` 的缺席无法区分：

- writer 明确选择 `abstain`；
- writer 处理了但失败；
- 该事件根本没有进入 writer。

**建议新增 `WriteDecision` schema（evaluator / audit only）：**

| 字段 | 类型 | 说明 |
|---|---|---|
| `decision_id` | string | 全局唯一 |
| `event_id` | string | 对应 `InteractionEvent` |
| `user_id` / `session_id` | string | 作用域 |
| `action` | enum | `durable` / `hedged` / `episodic` / `abstain` |
| `reason` | string | 写入/不写的理由 |
| `influence_prob` | float | 本次行为受 agent 影响的估计 |
| `confidence` | float | 作为稳定偏好的置信度 |
| `memory_id` | string / null | 若写入，对应的 `MemoryRecord` |
| `timestamp` | string | 决策时间 |

**收益：**

- CMR / Coverage 的分母可确定性计算；
- 可以区分“少写”与“没处理”；
- 支持反事实回放：删除一条 memory 后，重放同一 query，并对照 `WriteDecision`；
- 不把 `abstain` 强行塞进 `MemoryRecord`，保持“记录即已写入”的语义。

> 如果本周不新增 `WriteDecision`，P5 只能用 `MemoryRecord.source_event_ids` 反推 coverage，无法区分 abstain 与未处理；必须在 `metrics.md` 中标注该限制。

---

## 6. Hidden state 泄漏审计

| 检查项 | 结论 |
|---|---|
| `U_t` 是否出现在 `InteractionEvent` | 不允许 |
| `U_t` 是否出现在 `MemoryRecord` | 不允许 |
| shock / internalization / compliance 标签是否出现在 agent prompt | 不允许 |
| `counterfactual` 是否出现在 agent prompt | 不允许 |
| `exposure.propensity` 是否允许 writer 使用 | 允许，但必须在方法中说明；不得由 hidden label 直接计算 |
| `source_event_ids` 是否允许 agent 检索 | 允许；它是审计字段，不含 hidden label |
| `influence_prob` 是否允许 agent 使用 | 允许；但必须由可观测字段估计，不能用 hidden label |
| 日志/结果是否包含 hidden label | 可以，但只放在 evaluator 专用目录，不进入 writer 输入 |

**硬性要求：**

- `UserState` 只进入 evaluator / simulator，不进入 agent 上下文；
- `InteractionEvent` 与 `MemoryRecord` 的 schema 中不能有 hidden label 字段；
- 任何“从 hidden label 直接计算 `influence_prob`”的实现都视为泄漏，实验无效。

---

## 7. 反事实回放支持

要支持“删除/替换一条 memory 后重放同一 query”，schema 和 backend 至少需要：

| 能力 | 依赖字段/接口 | 负责人 |
|---|---|---|
| 定位每条 memory 的来源事件 | `MemoryRecord.source_event_ids` | P4 |
| 删除/停用一条 memory | `MemoryRecord.status` / `supersedes` | P3 |
| 保存/恢复 memory 状态 | `MemoryBackend.snapshot` / `restore` | P3 |
| 重放同一 query | 记录 retrieval query 与 top_k | P3 / P5 |
| 区分 abstain 与未处理 | `WriteDecision.action` | P4 / P5 |
| 对齐时间顺序 | `timestamp` / `session_id` / `turn` | P2 |
| 用户隔离 | `user_id` scope + 隔离测试 | P3 |

**最小回放实验（Week 1）：**

1. 跑完 session 1 的写入；
2. 保存 snapshot；
3. session 2 检索并推荐；
4. 删除一条 memory，restore snapshot 后重放同一 query；
5. 比较两次推荐/检索结果，记录差异。

---

## 8. 待办与负责人

| # | 待办 | 负责人 | 截止 | 状态 |
|---|---|---|---|---|
| 1 | 在 `MemoryRecord` 增加 `memory_type`、`status`、`counterevidence`、`validity.context`、`supersedes` | P3 / P4 | D4 17:00 | 已纳入 v1 |
| 2 | 在 `InteractionEvent` 增加 `context`、`agent_action.text`、`agent_action.candidate_set`、`exposure.source`、`exposure.position` | P2 | D3 14:00 | 已纳入 v1 |
| 3 | 决定是否新增 `WriteDecision` schema | P1 + P4 + P5 | D3 14:00 | 已采纳 |
| 4 | 定义 `evidence_type` / `memory_type` 的枚举值 | P4 | D3 14:00 | 已定义（proposal §4.1） |
| 5 | 确认 `exposure.propensity` 是否允许 writer 使用 | P1 + P4 | D3 14:00 | 已允许（需说明来源） |
| 6 | 写 user scope 隔离测试 | P3 | D5 | 待办 |
| 7 | schema v1 冻结并由 P1 签字 | P1 | D4 17:00 | 已完成（D4-002） |

---

## 9. D4 冻结检查表（已完成）

- [x] 三个 schema 的每个字段都标注 agent 可见 / evaluator 可见 / hidden；
- [x] `InteractionEvent` 和 `MemoryRecord` 中没有任何 hidden label；
- [x] `MemoryRecord.source_event_ids` 非空且可解析；
- [x] `memory_type` / `status` / `counterevidence` 已定义；
- [x] `WriteDecision` 是否采纳已决定（采纳）；
- [x] `InteractionEvent.context` / `exposure.source` / `exposure.position` 已定义；
- [x] snapshot / restore / replay 的最小接口已定义；
- [x] user scope 隔离测试已安排；
- [x] P1 已在 `decisions.md` 记录 schema v1 冻结决定（`D4-002`）。

---

## 10. 签字

| 角色 | 姓名/编号 | 结论 | 日期 |
|---|---|---|---|
| P1 Lead / 因果与评测 | @member-01 | 已签字（`D4-002`，v1 冻结） | 2026-11-12 |
| P2 Sim / Data | 待定 | 默认接受；如有阻塞提 RFC | 2026-11-12 |
| P3 Memory | 待定 | 默认接受；如有阻塞提 RFC | 2026-11-12 |
| P4 Method | 待定 | 默认接受；如有阻塞提 RFC | 2026-11-12 |
| P5 Eval / Analysis | 待定 | 默认接受；如有阻塞提 RFC | 2026-11-12 |
