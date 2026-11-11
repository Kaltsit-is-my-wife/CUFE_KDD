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
| schema v1 冻结并签字 | P1 | D4 17:00 | 本文件追加 `D4-002` |

### 签字

| 角色 | 姓名/编号 | 结论 | 日期 |
|---|---|---|---|
| P1 Lead / 因果与评测 | @member-01 | 提出并主持 | 2026-11-12 |
| P2 Sim / Data | 待定 | 待确认 | — |
| P3 Memory | 待定 | 待确认 | — |
| P4 Method | 待定 | 待确认 | — |
| P5 Eval / Analysis | 待定 | 待确认 | — |

---

## D4-001：Pilot 协议与 Gate 1 配置 v0

| 字段 | 内容 |
|---|---|
| 决策编号 | `D4-001` |
| 日期 | 2026-11-12 |
| 主持人 | @member-01（P1） |
| 参与人 | P1–P5（待确认） |
| 状态 | `proposed`（待 P2–P5 确认；不阻塞 Week 1 实现） |
| 影响范围 | Week 1 pilot、Week 2 Gate 1、P2–P5 的实现与运行 |
| 关联文档 | [pilot_protocol.md](pilot_protocol.md)、[gate1_config.yaml](gate1_config.yaml)、[metrics.md](metrics.md) |

### 结论

1. 采用 [pilot_protocol.md](pilot_protocol.md) v0 与 [gate1_config.yaml](gate1_config.yaml) v0。
2. Gate 1 运行矩阵：**20 用户 × 5 sessions；3 个 memory 系统（`mock` / `mem0` / `letta`）× 2 个 writer（naive / provenance）× 5 seeds = 30 runs**。
3. 主指标 CMR；副指标 SFB / AL / CR；必须并列报告 Coverage / IDR / Quality。
4. Gate 1 阈值：naive CMR ≥ 20%；provenance 相对下降 ≥ 30%；Quality 下降 ≤ 5%。
5. 20 个 pilot 用户全部用于 Gate 1；阈值与 `τ_durable` 预注册，不在 Gate 1 上调参。
6. `AL` / `CR` 若未实现，报告 `not_implemented`，不得用替代指标冒充。
7. 若 `letta` 不可用，用 `a-mem` 替换并记录；真实 adapter 至少保留一个。

### 依据

- D4 需要固定 pilot 协议与 Gate 1 配置，避免 D5/Week 2 临时拍脑袋；
- CMR / SFB 需要统一的用户数、session 数、memory budget 和 seed；
- 3 memory × 2 writer × 5 seeds 可以在可接受成本内回答“writer 是否有效、后端是否稳健”；
- 预注册阈值可以防止在 test 上调参。

### 未决问题

| # | 问题 | 负责人 | 截止 |
|---|---|---|---|
| 1 | `letta` 是否可用？不可用时是否用 `a-mem` 替换 | P3 | D5 |
| 2 | Writer 模型选哪个？Gate 1 是否允许真实 LLM API | P4 | D5 |
| 3 | `AL` / `CR` 是否在 Gate 1 实现 | P5 | D5 |
| 4 | MemoryCD 的 HF revision / checksum | P2 | D5 |
| 5 | schema v1 冻结（`D4-002`） | P1 + P2–P4 | D4 17:00 |

### 后续动作

| 动作 | 负责人 | 截止 | 产出 |
|---|---|---|---|
| 产出 20 用户子集与 manifest | P2 | D4 | `pilot_users.jsonl` / `manifest.json` |
| MockMemory + 一个真实 adapter 可 add/search | P3 | D4 | adapter smoke 记录 |
| 固定 writer 模型与 prompt v1 | P4 | D5 | `prompt_v1.md` |
| 实现 CMR/SFB 与 runner | P5 | D5 | `metrics.py` / `run_pilot.py` |
| 主持 D5 demo 与复盘 | P1 | D5 | `week1_review.md` |

### 签字

| 角色 | 姓名/编号 | 结论 | 日期 |
|---|---|---|---|
| P1 Lead / 因果与评测 | @member-01 | 提出并主持 | 2026-11-12 |
| P2 Sim / Data | 待定 | 待确认 | — |
| P3 Memory | 待定 | 待确认 | — |
| P4 Method | 待定 | 待确认 | — |
| P5 Eval / Analysis | 待定 | 待确认 | — |

---

## D4-002：Schema v1 冻结（默认全组使用）

| 字段 | 内容 |
|---|---|
| 决策编号 | `D4-002` |
| 日期 | 2026-11-12 |
| 主持人 | @member-01（P1） |
| 参与人 | P1 签字；P2–P5 默认接受 |
| 状态 | `frozen` |
| 影响范围 | P2/P3/P4/P5 的所有 schema 实现、P5 指标实现、反事实回放 |
| 关联文档 | [schema_v1_proposal.md](schema_v1_proposal.md)、[schema_review.md](schema_review.md)、[metrics.md](metrics.md) |

### 结论

1. **以 [schema_v1_proposal.md](schema_v1_proposal.md) 作为 schema v1 的最终默认版本。**
2. P2–P5 **直接按此实现**，不再等待逐字段确认；默认设置即全组设置。
3. 四个 schema 的职责固定：
   - `UserState`：hidden/evaluator only，含 `U_t`、shock、counterfactual、labels；
   - `InteractionEvent`：agent 可见的交互事件；
   - `MemoryRecord`：可检索、可审计的记忆记录；
   - `WriteDecision`：写入/abstain 的审计记录。
4. 关键默认值：
   - `MemoryRecord` 必须含 `memory_type`、`status`、`source_event_ids`、`counterevidence`、`validity.context`、`supersedes`；
   - `InteractionEvent` 必须含 `context`、`agent_action.text`、`agent_action.candidate_set`、`exposure.source`、`exposure.position`；
   - hidden label 只能存在于 `UserState`，不得进入 `InteractionEvent` / `MemoryRecord` / agent prompt；
   - `text` 必填；多属性写成多条 `MemoryRecord`；`turn` 在每个 session 内从 0 开始。
5. **变更流程**：任何成员发现字段不可实现或缺失，必须写 1 页 RFC，24 小时评论期，经 P1 签字后修改；不得静默改字段或各自实现一套。

### 依据

- 项目决定：当前 P1 使用的 schema 设置即其他成员默认使用的最终设置，减少等待和口径分歧；
- `metrics.md` 的 CMR / CMR_cond / SFB / IDR / Coverage 依赖这些字段；
- 反事实回放依赖 `source_event_ids`、`status`、`supersedes` 和 `WriteDecision`；
- hidden label 隔离是实验有效性的硬前提。

### 风险与边界

| 风险 | 处理 |
|---|---|
| P2–P4 发现某字段难以实现 | 提 RFC，说明替代方案；默认 v1 不变 |
| 多属性场景需要列表 | 先用多条 `MemoryRecord`；若不够，提 RFC |
| `influence_prob` 估计不准 | 记录估计方法；在报告中做敏感性分析，不修改 schema |
| `letta` 等后端字段映射缺失 | 在 adapter 层做映射，不把后端原始格式泄露到 `MemoryRecord` |

### 后续动作

| 动作 | 负责人 | 截止 | 产出 |
|---|---|---|---|
| 按 schema v1 实现 `InteractionEvent` | P2 | D5 | 事件生成器 + 校验 |
| 按 schema v1 实现 `MemoryRecord` / `WriteDecision` / backend | P3 | D5 | MockMemory + adapter |
| 按 schema v1 实现 naive / provenance writer | P4 | D5 | writer 输出 |
| 按 schema v1 实现 CMR / SFB / Coverage | P5 | D5 | `metrics.py` |
| 任何字段变更走 RFC | 全员 | 持续 | RFC + `decisions.md` 记录 |

### 签字

| 角色 | 姓名/编号 | 结论 | 日期 |
|---|---|---|---|
| P1 Lead / 因果与评测 | @member-01 | 已签字，v1 冻结 | 2026-11-12 |
| P2 Sim / Data | 待定 | 默认接受；如有阻塞提 RFC | 2026-11-12 |
| P3 Memory | 待定 | 默认接受；如有阻塞提 RFC | 2026-11-12 |
| P4 Method | 待定 | 默认接受；如有阻塞提 RFC | 2026-11-12 |
| P5 Eval / Analysis | 待定 | 默认接受；如有阻塞提 RFC | 2026-11-12 |

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
