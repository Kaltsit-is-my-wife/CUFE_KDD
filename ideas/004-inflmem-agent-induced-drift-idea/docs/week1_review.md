# InflMem Week 1 复盘与 D5 Demo（P1 草稿）

> 项目：InflMem / Agent-Induced Drift
> 产出人：@member-01（P1）
> 状态：**draft**；demo 尚未实际运行，P2–P5 的产物尚未到位
> 日期：2026-11-12
> 上游：[kickoff.md](kickoff.md)、[pilot_protocol.md](pilot_protocol.md)、[schema_v1_proposal.md](schema_v1_proposal.md)
> 说明：本文件先固定复盘结构与 demo 脚本；等 P2–P5 产物到位后补实际结果，不能把“计划”写成“已完成”。

---

## 1. 本周目标回顾

Week 1 的目标不是显著结果，而是搭出一个**可观测、可回放的最小闭环**，证明：

```text
MemoryCD 20 用户
  → 1 用户 × 2 sessions 的合成交互
  → naive writer / provenance writer
  → MemoryRecord（含来源、exposure、confidence）
  → MemoryBackend add / search / snapshot
  → CMR、SFB 指标输出
```

**当前判断：P1 负责的定义层已完成；闭环尚未跑通，因为数据、adapter、writer、runner 还未交付。**

---

## 2. 已完成

| 产出 | 状态 | 说明 |
|---|---|---|
| `kickoff.md` | 完成 v0 | 目标、非目标、风险、D1 决策草案 |
| `problem.md` | 完成 v0 | compliance / internalization 定义、蓝色耳机例子、RQ1–RQ3 |
| `causal_dag.md` | 完成 v0 | 节点、边、后门路径、W0/W1 配对世界、识别假设 |
| `metrics.md` | 完成 v0 | CMR / CMR_cond / SFB / IDR / Quality / Coverage、失败模式、fixtures、Gate 1 口径 |
| `schema_review.md` | 完成 v0 | 三个 schema 的字段级评审、hidden state 泄漏审计、D4 冻结检查表 |
| `schema_v1_proposal.md` | 完成 v0 | 四个 schema 的 P1 提案（含 `WriteDecision`）、示例、校验规则、指标映射 |
| `pilot_protocol.md` | 完成 v0 | Week 1 最小链路、Week 2 Gate 1 矩阵、控制与公平性 |
| `gate1_config.yaml` | 完成 v0 | 20 用户 × 5 sessions；3 memory × 2 writer × 5 seeds；阈值 |
| `decisions.md` | 完成 2 条 | D3-001 schema review；D4-001 pilot 协议与 Gate 1 配置 |

---

## 3. 未完成 / 阻塞

| 依赖 | 负责人 | 当前状态 | 阻塞原因 | 需要什么才能继续 |
|---|---|---|---|---|
| 20 用户子集 + manifest | P2 | 未开始 | MemoryCD 未下载 / 字段未核对 | HF 访问、下载脚本、checksum |
| 1 用户 × 2 sessions `InteractionEvent` | P2 | 未开始 | 依赖 20 用户子集与 simulator | schema v1 确认 |
| MockMemory + 真实 adapter | P3 | 未开始 | 依赖 schema v1；Mem0/Letta 安装未验证 | `MemoryRecord` 字段冻结 |
| naive / provenance writer | P4 | 未开始 | 依赖事件 schema 与 writer 模型 | `InteractionEvent` 字段冻结；model/API |
| `metrics.py` + `run_pilot.py` | P5 | 未开始 | 依赖事件、memory、writer 输出 | P2–P4 的最小产物 |
| schema v1 冻结 | P1 + P2–P4 | 未完成 | 需要 P2–P4 的实际 schema 实现 | 采纳或修改 `schema_v1_proposal.md` |
| 周五 demo | 全员 | 未运行 | 上述依赖未就绪 | 最小链路跑通 |

---

## 4. D5 Demo 脚本（30 分钟）

> 按 Week 1 任务清单第 7 节执行；以下每项都需要实际文件，不接受 PPT 讲架构。

| 时间 | 负责人 | 展示内容 | 需要的文件 | 当前状态 |
|---|---|---|---|---|
| 5 min | P2 | 打开 `pilot_users.jsonl`，展示 20 个用户和一个用户的 2 个 session | `data/processed/pilot_users.jsonl`、`manifest.json` | 待产出 |
| 5 min | P3 | 展示 `add` / `search`，以及一条 memory 的 `source_event_ids` | adapter smoke 记录、`memories.jsonl` | 待产出 |
| 5 min | P4 | 同一条交互：naive 写成 “User prefers blue.”，provenance 写成“接受推荐，可能是 compliance” | `prompt_v1.md`、两组 `MemoryRecord` | 待产出 |
| 5 min | P5 | 展示 `metrics.json` 和第一张 CMR 图，声明只是 sanity check | `metrics.json`、PNG | 待产出 |
| 5 min | P1 | 讲清楚本周验证了什么、没验证什么、Week 2 Gate 1 怎么跑 | `week1_review.md`、`pilot_protocol.md` | 本文件 |
| 5 min | 全员 | 定三个下周阻塞项和负责人 | 待办表 | 待填 |

**Demo 通过标准：**

- [ ] 实际跑出文件，不是只讲架构；
- [ ] 能指出一条具体 memory 的来源事件；
- [ ] 能说清 naive writer 为什么可能错；
- [ ] 能说清下周什么结果会让项目继续或转向。

---

## 5. 当前已知的三个问题

### 5.1 数据与 adapter 依赖未验证

- MemoryCD 的 HF 下载、字段、用户历史长度尚未核对；
- Mem0 / Letta 的安装与 API 访问未验证；
- 预案：保留 MockMemory；Gate 1 至少一个真实 adapter；记录 blocker，不停工。

### 5.2 schema v1 尚未冻结

- `memory_type`、`WriteDecision`、`InteractionEvent.context`、`exposure.source/position` 仍待 P2–P4 确认；
- 若继续用口头字段，P5 的 CMR/Coverage 会出现口径分歧；
- 下一步：P2–P4 按 [schema_v1_proposal.md](schema_v1_proposal.md) 确认或修改，D4 17:00 冻结。

### 5.3 writer 模型与指标实现未定

- Gate 1 是否允许真实 LLM API、用哪个模型、预算多少，尚未决定；
- `AL` / `CR` 可能来不及实现，需要明确 `not_implemented` 的报告方式；
- 下一步：P4 在 D5 前固定 model id / prompt v1；P5 先实现 CMR / SFB。

---

## 6. Week 2 任务草案

| 角色 | Week 2 任务 | 产出 | 截止 |
|---|---|---|---|
| P1 | 冻结 schema v1；主持 Gate 1 预注册；检查指标口径 | `decisions.md` D4-002；Gate 1 protocol | 第 2 周周一 |
| P2 | 20 用户 × 5 sessions 的完整事件流；data QA | `events.jsonl`、`data_qa_v1.md` | 第 2 周周二 |
| P3 | 3 个 memory 系统可 add/search；snapshot/restore | adapter 报告、`memories.jsonl` | 第 2 周周三 |
| P4 | writer v1（naive/provenance）稳定输出；prompt v1 冻结 | `prompt_v1.md`、writer 输出 | 第 2 周周三 |
| P5 | `run_pilot.py` 跑 30 runs；CMR/SFB 汇总 | `metrics.json`、主表、图 | 第 2 周周四 |
| 全员 | Gate 1 评审 | Go/No-Go 记录 | 第 2 周周五 |

**Gate 1 配置**：见 [pilot_protocol.md](pilot_protocol.md) §4 与 [gate1_config.yaml](gate1_config.yaml)。

---

## 7. Gate 1 预演

| 结果 | 判定 | 下一步 |
|---|---|---|
| naive CMR ≥ 20%，provenance 相对下降 ≥ 30%，Quality 下降 ≤ 5% | **通过** | 进入 Stage 1 主实验（100 用户 × 10 sessions） |
| naive CMR 10%–20% | **边缘** | 调整 influence 强度 / domain；不扩实验 |
| naive CMR < 10% | **不通过** | 收缩为“记忆写入诊断工具”或转向 |
| CMR 降但 Coverage 接近 0 | **无效修复** | 判为“少写”，重新设计 writer |
| 只在 mock memory 上成立 | **工程问题** | 检查 adapter 对齐，不进入主实验 |

---

## 8. 决策与待办

| # | 事项 | 负责人 | 截止 | 状态 |
|---|---|---|---|---|
| 1 | 确认或修改 schema v1 提案 | P2–P4 | D4 17:00 | 待办 |
| 2 | 记录 schema v1 冻结决定 `D4-002` | P1 | D4 17:00 | 待办 |
| 3 | 20 用户子集与 manifest | P2 | D4 | 待办 |
| 4 | MockMemory + 真实 adapter smoke | P3 | D4 | 待办 |
| 5 | writer 模型 / prompt v1 | P4 | D5 | 待办 |
| 6 | `metrics.py` + `run_pilot.py` | P5 | D5 | 待办 |
| 7 | 周五 demo + retro | P1 | D5 16:00 | 待办 |
| 8 | Gate 1 运行 | P1 + P5 | 第 2 周末 | 待办 |

---

## 9. 变更记录

| 日期 | 版本 | 变更 | 记录人 |
|---|---|---|---|
| 2026-11-12 | v0-draft | 初稿：Week 1 状态、demo 脚本、三个问题、Week 2 任务草案、Gate 1 预演 | @member-01 |
