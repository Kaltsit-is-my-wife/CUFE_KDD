# InflMem Week 1 → Week 2 交接说明（P1 → P2–P5）

> 写给：P2 Sim/Data、P3 Memory、P4 Method、P5 Eval/Analysis
> 抄送：P1 Lead
> 日期：2026-11-12
> 版本：v1
> 状态：**schema v1 已冻结（`D4-002`）；请直接按 v1 实现，不要再等逐字段确认**
> 必读：[schema_v1_proposal.md](schema_v1_proposal.md)、[pilot_protocol.md](pilot_protocol.md)、[metrics.md](metrics.md)、[week1_review.md](week1_review.md)、[related_work.md](related_work.md)

---

## 0. 一句话

Schema v1 已经冻结，默认就是全组设置。P2–P5 从今天起按 v1 并行实现；**D5 前交付最小产物，周五跑 demo；demo 通过后进入 Week 2 Gate 1。**

---

## 1. 当前状态

| 角色 | 当前状态 | 本轮目标 |
|---|---|---|
| P1 | 文档、schema v1、pilot 协议、Gate 1 配置、论文核对、related work 已完成 | 支持 P2–P5；主持 D5 demo 与 Gate 1 |
| P2 | 未开始 | MemoryCD loader、20 用户子集、catalog、simulator、事件流 |
| P3 | 未开始 | `MemoryBackend`、MockMemory、至少一个真实 adapter、snapshot/restore |
| P4 | 未开始 | naive / provenance writer、prompt v1、20 条 fixture |
| P5 | 未开始 | `metrics.py`、`run_pilot.py`、golden fixtures、第一张 CMR 图 |

**P1 已交付的文档：**

- 问题定义：`problem.md`
- 因果 DAG：`causal_dag.md`
- 指标口径：`metrics.md`
- schema 评审与提案：`schema_review.md`、`schema_v1_proposal.md`
- 决策记录：`decisions.md`（`D3-001`、`D4-001`、`D4-002`）
- pilot 协议：`pilot_protocol.md`、`gate1_config.yaml`
- 复盘与风险：`week1_review.md`、`week1_risks.md`
- 论文核对与定位：`paper_reading_log.md`、`related_work.md`

---

## 2. 统一约定（所有人）

1. **schema v1 是默认**：直接按 [schema_v1_proposal.md](schema_v1_proposal.md) 实现。字段不可实现或缺字段，写 1 页 RFC，24 小时评论，P1 签字；**不要静默改字段或各自实现一套**。
2. **hidden label 隔离**：`U_t`、shock、compliance / internalization / exogenous / noise 标签只能存在 `UserState` 或 evaluator 专用日志；不得进入 `InteractionEvent`、`MemoryRecord`、agent prompt。
3. **ID / 时间**：ID 用字符串、全局唯一；时间用 ISO 8601 UTC；`turn` 在每个 session 内从 0 开始。
4. **N/A ≠ 0**：指标分母为零时报告 `null` / `N/A`，不要报 0；比例必须同时报告分子/分母。
5. **轻量资产入库**：不提交原始数据、模型权重、大日志、API 凭据、PDF；`sandbox/member-01/papers/` 不要 `git add`。
6. **分支与 PR**：一人一分支，使用 `experiment/member-0X-004-<scope>`；完成后 PR 到 `main`，至少一人 review，禁止直接 push `main`。
   - P2：`experiment/member-02-004-data`
   - P3：`experiment/member-03-004-memory`
   - P4：`experiment/member-04-004-writer`
   - P5：`experiment/member-05-004-eval`
7. **阻塞上报**：任何依赖阻塞超过半天，在当日 sync 说明；先用 mock/fallback 继续，不停工。

---

## 3. 角色任务与 Definition of Done

### 3.1 P2 — Sim / Data

**任务：**

1. **MemoryCD loader**
   - 读用户、item、交互；统一字段名，保留原始 ID；
   - 记录 dataset revision、下载时间、checksum、用户数、item 数、域。
2. **Catalog**
   - 先做 Electronics + Books；
   - 字段：`item_id`、`title`、`category`、`attributes`、`price`。
3. **20 用户子集**
   - `data/processed/pilot_users.jsonl`：20 用户，≥2 域，每用户 ≥3 条历史交互；
   - `data/processed/manifest.json`：版本、用户数、item 数、checksum、生成脚本 commit；
   - 缺失值检查，剔除不可用用户并记录原因。
4. **Simulator v0**
   - 隐藏状态 `theta_t`：`color`、`size`、`price_sensitivity`、`brand`；
   - 每 session 以 `p_shock=0.1` 产生外生冲击；
   - agent 推荐后，用户以概率接受；接受后以概率 internalize；
   - 生成 1 用户 × 5 sessions 的事件流；先做 1 用户 × 2 sessions smoke。
5. **事件字段**
   - 必须符合 `InteractionEvent` v1：`event_id`、`user_id`、`session_id`、`turn`、`timestamp`、`context`、`agent_action`、`user_response`、`exposure`。

**Definition of Done：**

- [ ] loader 能在干净环境复现；
- [ ] 20 用户子集与 manifest 已生成；
- [ ] simulator 能稳定生成 1 用户 × 5 sessions；
- [ ] 所有事件通过 schema v1 校验；
- [ ] 原始数据没有提交进 Git。

**依赖：** MemoryCD 下载 / HF 访问；schema v1。

---

### 3.2 P3 — Memory

**任务：**

1. **`MemoryBackend` 接口**
   - `add(record)`、`search(query, user_id, top_k)`、`get_all(user_id)`、`delete(memory_id)`、`snapshot(user_id)`、`restore(snapshot)`。
2. **MockMemory**
   - 内存 dict 实现；add/search/delete/snapshot 基本行为；
   - 单测。
3. **真实 adapter**
   - 优先 Mem0；安装/API 阻塞时接 Letta 或 A-MEM；
   - 统一输入输出为 `MemoryRecord`，不泄露后端原始格式；
   - 写 `adapter_alignment.md`：字段映射、缺失字段、绕过方式。
4. **日志与反事实回放**
   - 每次 add/search 记录输入、输出、耗时、memory_id；
   - 实现 snapshot / restore；支持删除一条 memory 后重放同一 query；
   - 写 `counterfactual_replay` 雏形。
5. **用户隔离**
   - 确保 user scope 不跨用户泄漏；
   - 写隔离测试。

**Definition of Done：**

- [ ] `MemoryBackend` 接口冻结；
- [ ] 至少一个真实 adapter 能 add/search；
- [ ] 事件日志能定位每条 memory 的来源事件；
- [ ] snapshot / restore 可用；
- [ ] 有 user scope 隔离测试。

**依赖：** `MemoryRecord` / `WriteDecision` schema v1；Mem0/Letta 安装。

---

### 3.3 P4 — Method

**任务：**

1. **naive writer**
   - 看到“用户接受了蓝色耳机”，写成 “User prefers blue.”
2. **provenance writer**
   - 写成 “User accepted blue after agent recommendation; prior preference black; may be compliance.”
   - 保留 `source_event_ids`、`exposure`、`influence_prob`、`confidence`、`validity`。
3. **fixture**
   - 20 条手写/合成事件，产出 20 条 `MemoryRecord`；
   - 至少覆盖：明显误写、正确内化、无 exposure、abstain、hedged。
4. **Influence 规格 v0**
   - 定义 exposure 强度；
   - 区分 acceptance 与 internalization；
   - 标清观测变量 vs 隐藏变量；
   - 与 P2 simulator 的概率参数对齐，不要各写一套。
5. **Prompt 变体**
   - 严格 provenance / 中等 provenance / 纯摘要；
   - 记录输出差异，不急着选“最好”；
   - 输出 `prompt_v1.md`。

**Definition of Done：**

- [ ] naive / provenance 两个 writer 都能产出合法 JSON；
- [ ] provenance writer 不把 acceptance 直接写成 preference；
- [ ] 20 条 fixture 的输出可被 P3 的 MockMemory 接收；
- [ ] influence 规格与 P2 的 simulator 参数一致；
- [ ] 有 3 个 prompt 变体的对比记录。

**依赖：** `InteractionEvent` schema v1；writer 模型 / API；P3 的 `MemoryRecord`。

---

### 3.4 P5 — Eval / Analysis

**任务：**

1. **`metrics.py`**
   - 必须实现：`compliance_misattribution_rate`、`cmr_cond`、`self_fulfilling_bias`、`coverage`；
   - 建议实现：`idr`、`quality`（task success / NDCG / diversity）；
   - 允许占位：`adoption_lag`、`overuse_rate`、`counterfactual_regret`（返回 `null` / `not_implemented`）。
2. **Golden fixtures + 单测**
   - 覆盖 `metrics.md` §6 的 8 个 fixture；
   - 每个指标至少一个正常用例 + 一个边界用例；
   - 不调用 LLM API 也能跑。
3. **Run logging**
   - `run_id = YYYYMMDD_method_model_dataset_seed`；
   - 每次 run 写 `config.yaml`、`events.jsonl`、`memories.jsonl`、`write_decisions.jsonl`、`metrics.json`、`stdout.log`。
4. **`run_pilot.py`**
   - 串起 P2 事件、P3 memory、P4 writer；
   - 先不用真实 LLM 也能跑（fixture / mock）；
   - 输出 `runs/<run_id>/metrics.json`。
5. **第一张图**
   - CMR：naive vs provenance；
   - 横轴可以是 exposure 强度，纵轴 CMR；
   - 写 `pilot_v0.md`，明确区分“链路验证”和“科学结论”。

**Definition of Done：**

- [ ] CMR / SFB 有明确公式和单测；
- [ ] `run_pilot.py` 能一条命令跑通最小链路；
- [ ] 每次 run 的输入、输出、配置可追溯；
- [ ] 有一张能看懂的第一版图；
- [ ] 报告明确区分“链路验证”和“科学结论”。

**依赖：** P2 事件、P3 memory、P4 writer；`metrics.md`。

---

### 3.5 P1 — Lead / 因果与评测

**本轮继续负责：**

- schema v1 的解释与 RFC 签字；
- `pilot_protocol.md` / `gate1_config.yaml` 的解释；
- 主持 D5 demo、记录 `week1_review.md` 的实际结果；
- 主持 Week 2 Gate 1、`decisions.md`；
- 解决跨角色接口争议。

**Definition of Done：**

- [ ] D5 demo 按脚本跑完；
- [ ] `week1_review.md` 补实际结果，不把计划写成结果；
- [ ] Gate 1 配置不再需要补关键定义；
- [ ] 所有 schema 变更都有 `decisions.md` 记录。

---

## 4. 接口与数据流

```text
P2 simulator
  ├── UserState（hidden / evaluator only）
  └── InteractionEvent（agent 可见）
          ↓
      P4 writer
          ├── MemoryRecord
          └── WriteDecision
          ↓
      P3 memory backend
          ↓
      P5 metrics（CMR / CMR_cond / SFB / IDR / Coverage / Quality）
```

**字段所有权：**

| Schema | 产生者 | 主要消费者 | 备注 |
|---|---|---|---|
| `UserState` | P2 | P5 / evaluator | hidden；不得进入 prompt |
| `InteractionEvent` | P2 | P4 / P3 / P5 | agent 可见；必须含 `context`、`exposure.source` |
| `MemoryRecord` | P4 | P3 / P5 | 必须含 `memory_type`、`source_event_ids`、`status` |
| `WriteDecision` | P4 | P5 / evaluator | 必须覆盖每个事件（含 abstain） |
| `MemoryBackend` | P3 | P4 / P5 | 统一 add/search/snapshot/restore |
| `metrics` | P5 | P1 / 全员 | 输出 `metrics.json`，N/A 用 `null` |

---

## 5. D5 Demo 验收（30 分钟）

按 [week1_review.md](week1_review.md) §4 执行：

1. **P2（5 min）**：打开 `pilot_users.jsonl`，展示 20 个用户和一个用户的 2 个 session。
2. **P3（5 min）**：展示 `add` / `search`，以及一条 memory 的 `source_event_ids`。
3. **P4（5 min）**：同一条交互，naive 写成 “User prefers blue.”，provenance 写成“接受推荐，可能是 compliance”。
4. **P5（5 min）**：展示 `metrics.json` 和第一张 CMR 图，声明只是 sanity check。
5. **P1（5 min）**：讲清楚本周验证了什么、没验证什么、Week 2 Gate 1 怎么跑。
6. **全员（5 min）**：定三个下周阻塞项和负责人。

**Demo 通过标准：**

- [ ] 实际跑出文件，不是只讲架构；
- [ ] 能指出一条具体 memory 的来源事件；
- [ ] 能说清 naive writer 为什么可能错；
- [ ] 能说清下周什么结果会让项目继续或转向。

---

## 6. Week 2 Gate 1

- 配置：[gate1_config.yaml](gate1_config.yaml)
- 协议：[pilot_protocol.md](pilot_protocol.md) §4
- 矩阵：20 用户 × 5 sessions；3 memory × 2 writer × 5 seeds = **30 runs**
- 主指标：CMR；副指标：SFB / AL / CR；必须并列报告 Coverage / IDR / Quality
- 阈值：naive CMR ≥20%；provenance 相对下降 ≥30%；Quality 下降 ≤5%

---

## 7. 阻塞与升级

| 阻塞 | 负责人 | 预案 |
|---|---|---|
| MemoryCD 下载/字段不可用 | P2 | 用公开小样例 + 合成 catalog；记录 blocker |
| Mem0/Letta 安装或 API 失败 | P3 | 保留 MockMemory；Gate 1 用 `mock` + 一个真实 adapter |
| writer 模型/API 未定 | P4 | Week 1 用 fixture/mock writer；Gate 1 前必须固定 |
| `AL` / `CR` 未实现 | P5 | 报告 `not_implemented`，不阻塞 CMR 主判定 |
| schema 字段不可实现 | 提出者 | 写 RFC（24h 评论 + P1 签字）；默认 v1 不变 |
| 任何阻塞超过半天 | 全员 | 当日 sync 上报；P1 决定降级/绕过/砍掉 |

---

## 8. 立即行动（D2–D3）

| 时间 | 负责人 | 动作 | 产出 |
|---|---|---|---|
| D2 | P2 | 下载 MemoryCD，记录 revision/checksum，读 5 个用户 | `data_notes.md` v0 |
| D2 | P3 | 写 `MemoryBackend` + MockMemory + 单测 | `memory/base.py`、`memory/mock.py` |
| D2 | P4 | 写 naive / provenance prompt v0；准备 20 条 fixture | writer v0 |
| D2 | P5 | 写 `metrics.py` 骨架 + golden fixtures | `eval/metrics.py` |
| D3 | 全员 | 接口互评；确认 `InteractionEvent` / `MemoryRecord` / `WriteDecision` 的实现 | 接口评论汇总 |
| D3 | P2 | 产出 20 用户子集与 manifest | `pilot_users.jsonl`、`manifest.json` |
| D3 | P3 | 接第一个真实 adapter | adapter smoke |
| D4 | P1 | 确认 schema v1 无需 RFC 变更；收集 blocker | `decisions.md` 更新 |
| D5 | 全员 | 跑 demo + retro | `week1_review.md` 实际结果 |

---

## 9. 文档索引

| 文档 | 用途 |
|---|---|
| [schema_v1_proposal.md](schema_v1_proposal.md) | **实现 schema 的唯一依据** |
| [metrics.md](metrics.md) | 指标定义、输入、聚合、失败模式 |
| [pilot_protocol.md](pilot_protocol.md) | Week 1 pilot 与 Gate 1 协议 |
| [gate1_config.yaml](gate1_config.yaml) | Gate 1 机器可读配置 |
| [problem.md](problem.md) | 问题定义与 RQ |
| [causal_dag.md](causal_dag.md) | 因果假设与反事实设计 |
| [week1_review.md](week1_review.md) | D5 demo 脚本与复盘 |
| [week1_risks.md](week1_risks.md) | 风险与依赖清单 |
| [related_work.md](related_work.md) | 论文对照、baseline、novelty 定位 |
| [paper_reading_log.md](paper_reading_log.md) | 五篇论文原文核对 |
| [decisions.md](decisions.md) | schema / protocol 决策记录 |

---

## 10. 变更记录

| 日期 | 版本 | 变更 | 记录人 |
|---|---|---|---|
| 2026-11-12 | v1 | 初稿：P2–P5 任务、DoD、接口、demo、Gate 1、阻塞与立即行动 | @member-01 |
