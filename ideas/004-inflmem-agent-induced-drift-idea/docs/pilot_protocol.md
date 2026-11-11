# InflMem Pilot 协议与 Week 2 Gate 1 配置（D4）

> 项目：InflMem / Agent-Induced Drift
> 产出人：@member-01（P1 Lead / 因果与评测）
> 状态：v0 草案；Week 1 pilot 可执行，Week 2 Gate 1 待 P2–P5 接口就绪
> 日期：2026-11-12
> 上游：[kickoff.md](kickoff.md)、[problem.md](problem.md)、[causal_dag.md](causal_dag.md)、[metrics.md](metrics.md)、[schema_review.md](schema_review.md)、[decisions.md](decisions.md)
> 机器可读配置：[gate1_config.yaml](gate1_config.yaml)
> 下游：P5 的 `scripts/run_pilot.py`、`runs/<run_id>/`、`docs/week1_review.md`

---

## 1. 目的与边界

本文件定义两个阶段的执行协议：

| 阶段 | 目的 | 结论性质 |
|---|---|---|
| **Week 1 pilot** | 验证数据、事件、memory、writer、指标能串成最小闭环 | 只做 pipeline sanity check，不验证效应 |
| **Week 2 Gate 1** | 判断 naive memory 是否产生可测的 CMR，provenance 是否能降低它 | go/no-go；不是论文主结果 |

**明确不声称：**

- Week 1 的 CMR/SFB 不是科学结论；
- Gate 1 通过不等于方法有效，只说明值得进入主实验；
- 20 用户 pilot 不用于外推到真实用户。

---

## 2. 固定参数

| 参数 | 值 | 说明 |
|---|---|---|
| 数据集 | MemoryCD | Stage 1；只提交下载脚本与 manifest |
| 域 | Electronics + Books | 至少 2 个域；每域 ≥8 个用户 |
| 用户数 | 20 | Week 1 pilot 与 Gate 1 共用 |
| 每用户 session 数 | 5 | Gate 1；Week 1 smoke 只用 2 |
| Memory 系统 | `mock`、`mem0`、`letta` | 若 Letta 不可用，用 `a-mem` 替换并记录 |
| Writer | `naive`、`provenance` | 本周只做这两个 |
| Prompt 版本 | `v1` | P4 在 D5 前冻结 |
| Writer 模型 | 待 P4 固定 | 必须记录 model id、temperature、max_tokens |
| Temperature | `0.0` | 可复现优先 |
| Seeds | `20261101`–`20261105` | 5 个 |
| `top_k` | 5 | 三个 memory 系统一致 |
| 每用户 memory 上限 | 50 | 防止后端差异导致预算不同 |
| Simulator `p_shock` | `0.1` | 每 session 外生冲击概率 |
| Simulator `eta` | `0.3` | 内化强度默认值；灵敏度分析再调 |
| Simulator `p_noise` | `0.05` | 一次性行为噪声 |
| 运行总数 | 30 | 3 memory × 2 writer × 5 seeds |

---

## 3. Week 1 pilot 协议

### 3.1 最小链路

```text
MemoryCD 20 用户
  → 选 1 个用户
  → session 1：生成 InteractionEvent → naive/provenance writer → MemoryRecord → MemoryBackend.add
  → session 2：MemoryBackend.search → 生成 InteractionEvent → writer 再写
  → metrics.py 对固定 fixture 计算 CMR / SFB
  → runs/<run_id>/metrics.json
```

### 3.2 执行步骤

1. **数据**：P2 产出 `pilot_users.jsonl`（20 用户，≥2 域，每用户 ≥3 条历史）和 `manifest.json`。
2. **事件**：P2 用 simulator 生成 1 用户 × 2 sessions 的 `InteractionEvent`；字段必须通过 schema v1 校验。
3. **写入**：P4 对同一事件分别跑 naive 和 provenance writer；两者输出不同的 `MemoryRecord`。
4. **存储**：P3 用 MockMemory 接收；至少一个真实 adapter（优先 Mem0）能 add/search。
5. **检索**：session 2 用同一 query 从两个 writer 的 memory 中检索，记录 top_k 与 `source_event_ids`。
6. **指标**：P5 用固定 fixture 计算 CMR / SFB；不要求真实 LLM judge。
7. **产物**：P5 保存 `runs/<run_id>/` 下的 config、events、memories、write_decisions、metrics、log。

### 3.3 Week 1 验收

- [ ] `pilot_users.jsonl` 至少 20 个用户，字段与 MemoryCD 对得上；
- [ ] 1 用户 × 2 sessions 的 `InteractionEvent` 可生成、可回放；
- [ ] naive 与 provenance writer 对同一事件产出不同 `MemoryRecord`；
- [ ] 至少一个真实 memory adapter 能 add/search；其他可为 skeleton；
- [ ] `metrics.py` 能对固定 fixture 算出 CMR / SFB，并有单测；
- [ ] `run_pilot.py` 一条命令跑完最小链路，输出 `metrics.json`；
- [ ] 三个 schema 完成 v1 评审并冻结；
- [ ] `gate1_config.yaml` 已评审，不临时拍脑袋。

> Week 1 唯一允许的“跑不通”：HF 下载、Mem0/Letta 安装被网络或环境阻塞。此时保留 MockMemory 和 blocker 记录，不停工。

---

## 4. Week 2 Gate 1 协议

### 4.1 运行矩阵

```text
3 个 memory 系统（mock, mem0, letta）
× 2 个 writer（naive, provenance）
× 5 个 seeds（20261101–20261105）
= 30 runs
```

每个 run 使用同一批 20 个用户、每用户 5 sessions、相同的事件流与 seed。不同 writer 之间共享事件与用户；不同 memory 系统之间共享 events，但 memory 状态独立。

### 4.2 评估口径

- **评估集**：20 用户 × 5 sessions 全部用于 Gate 1；
- **阈值预注册**：`τ_durable = 0.6`、Gate 1 门槛在运行前固定，不在 Gate 1 上调参；
- **主指标**：CMR；
- **副指标**：SFB、AL、CR；AL / CR 若未实现，报告 `not_implemented`，不得用替代指标冒充；
- **必须并列报告**：Coverage、IDR、Quality；
- **统计**：user-level paired bootstrap ≥1,000 次；95% CI；副指标 Holm-Bonferroni；按 domain 拆分。

### 4.3 Gate 1 判定

| 条件 | 阈值 | 不通过时 |
|---|---|---|
| naive CMR | ≥ 20% | 调整 influence 强度 / domain；若 <10%，考虑收缩为诊断工具 |
| provenance 相对下降 | ≥ 30% | 检查 provenance 信号是否真的被 writer 使用 |
| Quality 下降 | ≤ 5% | 检查是否靠少写/降低推荐质量换低 CMR |
| Coverage | 不得塌缩 | 若 provenance 的 CMR 低但 Coverage 接近 0，判为“少写”而非“识别” |

**相对下降**：

```text
relative_reduction = (CMR_naive - CMR_provenance) / CMR_naive
```

分母为 0 时报告 `N/A`。

### 4.4 停止 / 转向条件

- naive CMR 在所有 domain < 10% → 效应太弱，收缩为“记忆写入诊断工具”；
- provenance prompt 单独解决 80% 以上问题 → 复杂因果机制不必要，转向轻量诊断；
- proposed 的收益完全来自少写 → 方法无价值，需要重新设计；
- 只在 mock memory 上成立 → 检查 adapter 对齐，不进入主实验。

---

## 5. 控制与公平性

1. **同一事件流**：naive / provenance 使用同一批 `InteractionEvent`，只改 writer；
2. **同一 seed**：同一 seed 下，用户、shock、曝光序列一致；
3. **同一 memory budget**：`top_k=5`、每用户上限 50；
4. **同一 retrieval 协议**：三个 memory 系统使用同一 query 构造方式；
5. **隐藏标签隔离**：`U_t`、shock、compliance/internalization 标签不进入 writer prompt；
6. **禁止 test 调参**：Gate 1 阈值和 `τ_durable` 预注册；prompt v1 在 D5 前冻结；
7. **必须报告成本**：Coverage、IDR、Quality、Diversity 与 CMR 同时出现；
8. **adapter 对齐**：P3 记录字段映射、缺失字段和绕过方式；不同后端的检索差异单独报告。

---

## 6. Run 目录与复现

```text
runs/<run_id>/
  config.yaml
  events.jsonl
  memories.jsonl
  write_decisions.jsonl
  metrics.json
  stdout.log
```

- `run_id = YYYYMMDD_<writer>_<memory>_memorycd20_seed<seed>`；
- 示例：`20261120_provenance_mem0_memorycd20_seed20261101`；
- `config.yaml` 必须记录：dataset revision、writer model、prompt version、temperature、top_k、seed、memory backend version；
- 原始 MemoryCD 数据、模型权重、API 凭据不入 Git；
- 每个 run 的 `metrics.json` 必须包含分子/分母、CI、per-domain 结果。

---

## 7. 角色与交接

| 角色 | D4–D5 交付 | 依赖 | 截止 |
|---|---|---|---|
| P1 | `pilot_protocol.md`、`gate1_config.yaml`、schema v1 签字 | P2–P4 的 schema | D4 17:00 |
| P2 | 20 用户子集、manifest、1 用户 × 5 sessions simulator | MemoryCD 下载 | D4 |
| P3 | MockMemory + ≥1 真实 adapter、snapshot/restore | schema v1 | D4 |
| P4 | naive / provenance writer v0、prompt v1、model 固定 | 事件 schema | D5 |
| P5 | `metrics.py`、`run_pilot.py`、`metrics.json`、第一张 CMR 图 | 事件 + memory + writer | D5 |

**交接时间**：D4 17:00 schema v1 冻结；D5 16:00 demo + retro。

---

## 8. 风险与阻塞

| 风险 | 触发信号 | 预案 | 负责人 |
|---|---|---|---|
| MemoryCD 下载失败 | HF 网络/字段不可用 | 用公开小样例 + 合成 catalog；记录 blocker | P2 |
| Mem0/Letta 安装失败 | 依赖冲突、需要 API key | 保留 MockMemory；Gate 1 用 `mock` + 一个真实 adapter | P3 |
| Writer 模型未定 | API/预算未确认 | Week 1 用 fixture/mock writer；Gate 1 前必须固定 | P4 |
| schema v1 冻结后仍有 RFC 变更 | 有人提出字段变更 | 按 RFC 流程评审；默认 v1 不变 | P1 |
| AL / CR 未实现 | 指标返回 `null` | 报告 `not_implemented`，不阻塞 Gate 1 主判定 | P5 |
| 20 用户样本太小 | CI 过宽 | Gate 1 只做 go/no-go；主实验扩到 100 用户 | P1 |

---

## 9. D4 完成标准与未决问题

**本次完成：**

- [x] `pilot_protocol.md` v0；
- [x] `gate1_config.yaml` v0；
- [x] Week 1 / Gate 1 的指标、阈值、run 矩阵、产物路径已定义；
- [x] schema v1 冻结（`D4-002`，默认全组使用）。

**未完成（依赖 P2–P5）：**

- [ ] writer 模型与 prompt v1 固定（P4）；
- [ ] 真实 adapter 的字段映射（P3）；
- [ ] `metrics.py` 与 `run_pilot.py`（P5）；
- [ ] 20 用户子集与 manifest（P2）。

**未决问题：**

1. Gate 1 的 3 个 memory 系统中，`letta` 是否可用？若不可用，是否用 `a-mem` 替换？
2. Writer 模型选哪个？是否允许 Gate 1 调用真实 LLM API？预算多少？
3. `AL` / `CR` 在 Gate 1 是否必须实现，还是允许 `not_implemented`？
4. 20 用户是否全部用于 Gate 1，还是保留 8 个用户作为 test？当前协议选择“全部用于 Gate 1，阈值预注册”。
5. MemoryCD 的 HF revision / checksum 由谁记录？

---

## 10. 变更记录

| 日期 | 版本 | 变更 | 记录人 |
|---|---|---|---|
| 2026-11-12 | v0 | 初稿：Week 1 pilot 最小链路、Week 2 Gate 1 矩阵、阈值、控制、产物、角色 | @member-01 |
