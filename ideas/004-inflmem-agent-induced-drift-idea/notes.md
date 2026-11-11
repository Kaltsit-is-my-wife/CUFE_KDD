# [004] InflMem 研究笔记与讨论

> 本文件记录文献笔记、数据观察、头脑风暴、讨论和被否决的方向。完整项目说明见
> [`docs/references/2026-10-30_Agent-Induced-Drift_研究Idea说明.md`](docs/references/2026-10-30_Agent-Induced-Drift_研究Idea说明.md)，
> Week 1 任务见 [`docs/references/2026-10-30_Week1_五人任务清单.md`](docs/references/2026-10-30_Week1_五人任务清单.md)。

## 文献笔记

### AcCoRD（arXiv:2608.27818）

- **研究问题**：在真实用户偏好动态下评测用户–agent 协作。
- **数据集/环境**：100 个购物场景 + 100 个旅行场景；LLM user simulator；四类偏好动态（hard/soft underspecification、unachievable、triggered）。
- **方法**：交互式 harness，含 satisfaction / task success 评测、consistency checking 和 rollout。
- **对本 idea 的启发**：适合做 Stage 2 交互真实性底座；四类偏好动态可以测试不同 failure mode。
- **差异/风险**：单 session；无跨会话 memory；agent 不改变 latent preference；无反事实 ground truth。
- **可复现实验**：先 text-only 读取场景 JSON，不启动 WebShop/Java。

### MemoryCD（arXiv:2603.25973）

- **研究问题**：长上下文用户记忆的跨域个性化评测。
- **数据集**：323 用户、167,870 商品、12 域；真实跨年行为；4 类任务（rating prediction、review summarization、review generation、item ranking）。
- **对本 idea 的启发**：Stage 1 的真实历史与商品库底座；用真实商品标题、类别、价格和历史交互减少纯合成 persona 的审稿风险。
- **差异/风险**：无交互式 agent、无推荐动作、无 influence model、无隐藏偏好与反事实标签。
- **可复现实验**：从 Hugging Face 下载，记录版本、checksum、用户数、item 数、字段；原始数据不入 Git。

### CALMRec（arXiv:2607.23647）

- **研究问题**：推荐系统中的 exposure bias 与反馈循环。
- **方法**：identification + propensity-weighted 更新；电商/新闻/短视频模拟。
- **对本 idea 的启发**：方法论近邻；propensity weighting 可用于 memory writer 的 exposure 校正。
- **差异/风险**：面向推荐排序，不处理自然语言 memory write；无 compliance/internalization 概念；代码可得性未确认。
- **可复现实验**：若代码不可得，按论文重实现简化版 IPW baseline。

### CAPTURE（arXiv:2609.02265）

- **研究问题**：区分真实偏好漂移与 memory poisoning。
- **方法**：POMDP belief tracking。
- **对本 idea 的启发**：概念 baseline；belief tracking 可作为“记忆中的偏好估计”参照。
- **差异/风险**：未把 agent action 当作偏好变化的因；代码未找到。

### ULSPB（arXiv:2605.06731）

- **研究问题**：routine chats 导致授权边界漂移。
- **对本 idea 的启发**：现象与任务设计参考；说明“长期交互会改变状态”不限于偏好。
- **差异/风险**：无 LICENSE；偏好不是安全状态；不直接复用代码。

### Mem0 / Letta / A-MEM

- **作用**：真实 memory backend / baseline。
- **差异/风险**：写入策略默认“行为即偏好”；适配成本主要在接口和 metadata。
- **Week 1 计划**：优先接 Mem0；若安装/API 阻塞，保留 MockMemory 并记录 blocker。

### MemGym（arXiv:2605.20833）

- **作用**：memory manager 接口与标准评测循环参考。
- **差异/风险**：缺少 influence 场景与反事实。

## 数据观察

- **数据版本/快照**：MemoryCD 尚未下载；下载后记录 commit、HF revision、checksum。
- **样本量与字段**：待核实；重点检查用户 ID、item ID、评分、评论、时间戳、域、类别。
- **缺失、异常与分布**：待检查；Week 1 需要每个 pilot 用户至少 3 条历史交互。
- **标签质量**：MemoryCD 无 agent 交互标签；compliance / internalization 标签由自建 simulator 提供。
- **潜在泄漏**：`U_t`、shock、internalization 标签绝不能进入 agent prompt；用户级划分，避免跨用户共享 memory。
- **观察日期**：待下载后填写。

## 头脑风暴

- [2026-11-12] @member-01：把问题锁定为“memory write 的因果归因”，而不是“通用记忆漂移 benchmark”；否则范围会失控。
- [2026-11-12] @member-01：Week 1 只做 naive vs. provenance 两个 writer；完整 causal writer 留到 Week 5。
- [2026-11-12] @member-01：配对反事实世界是 benchmark 的核心；没有 W0/W1，CMR 只能靠启发式标注。
- [2026-11-12] @member-01：必须同时报告 Coverage 和 Quality，否则“少写”会刷低 CMR。

## 讨论记录

### [2026-11-12] 主题：Week 1 P1 范围与指标口径

- **参与人**：@member-01（待 P2–P5 确认）
- **讨论问题**：Week 1 是否接 AcCoRD？是否实现完整 causal writer？CMR 的分母怎么定？
- **支持观点**：先做 MemoryCD Stage 1，成本低、可控、容易做消融；Week 1 只验证链路。
- **反对观点**：只用合成 simulator 的外部效度不足；需要尽早接 AcCoRD。
- **决策**：Week 1–2 只做 MemoryCD Stage 1；AcCoRD 第 3 周再接入；Week 1 只做 naive vs. provenance。
- **待办**：[P1] 完成 schema review；[P5] 实现 CMR/SFB + fixtures；[P2] 产出 20 用户子集；[P3] 接 Mem0 或 MockMemory；[P4] writer v0。

## 被否决或暂缓的方向

| 日期 | 方向 | 原因 | 是否可在未来重启 |
|---|---|---|---|
| 2026-11-12 | 做“通用记忆漂移 benchmark” | 方向拥挤，缺少 agent 因果归因的差异化 | 否 |
| 2026-11-12 | Week 1 接 AcCoRD / WebShop | 环境重，容易拖 1–2 周；不是核心变量 | 是，第 3 周 text-only |
| 2026-11-12 | Week 1 实现完整 causal writer | 本周目标是证明“可测”，不是“显著” | 是，Week 5 |
| 2026-11-12 | 用 LLM judge 作为 CMR 主判定 | 偏差不可控；主指标应使用结构化字段 | 否，只能做辅助 |
| 2026-11-12 | 把“记忆写得更少”作为卖点 | 会牺牲 coverage / quality，且不能证明识别 | 否 |

## 术语与约定

| 术语 | 定义 | 备注 |
|---|---|---|
| Compliance | 接受推荐，但潜在偏好未变 | 行为层面的配合，不是偏好改变 |
| Internalization | 多次、多上下文暴露后，潜在偏好真的向推荐值移动 | 需要独立/持续证据 |
| Exogenous change | 生活事件/预算/环境导致的变化，与曝光无关 | 不能误标为 compliance |
| CMR | Compliance Misattribution Rate | 见 `docs/metrics.md` |
| CMR_cond | 条件版 CMR，分母为已写入的 compliance 事件 | 用于区分“少写”与“写得准” |
| SFB | Self-Fulfilling Bias，控制真实偏好后 memory 推断偏好对 exposure 的回归系数 | 理想为 0 |
| IDR | Internalization Detection Rate | 防止 writer 过度保守 |
| Provenance | 记忆的来源、曝光、agent action、置信度、有效期 | `MemoryRecord` 的核心字段 |
| durable / hedged / episodic / abstain | 四种写入动作 | 见 `docs/metrics.md` 与 idea 说明 §7.7 |
