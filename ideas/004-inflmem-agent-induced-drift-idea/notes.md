# [004] InflMem 研究笔记与讨论

> 本文件记录文献笔记、数据观察、头脑风暴、讨论和被否决的方向。完整项目说明见
> [`docs/references/2026-10-30_Agent-Induced-Drift_研究Idea说明.md`](docs/references/2026-10-30_Agent-Induced-Drift_研究Idea说明.md)，
> Week 1 任务见 [`docs/references/2026-10-30_Week1_五人任务清单.md`](docs/references/2026-10-30_Week1_五人任务清单.md)。
> PDF 核对状态：5/5 已核对原文。详见 [docs/paper_reading_log.md](docs/paper_reading_log.md)；完整对照、研究脉络与 baseline 计划见 [docs/related_work.md](docs/related_work.md)。

## 文献笔记

### AcCoRD（arXiv:2608.27818，已核对原文）

- **完整标题/作者**：*ACCORD: Evaluating User-Agent Collaboration Under Realistic User Preference Dynamics*；Tejas Srinivasan, Shikib Mehri, Nandita Naik, Anirban Das, William M. Campbell, Jesse Thomason（USC / Contextual AI / Capital One / Georgia Tech）。
- **研究问题**：在真实用户偏好动态下评测用户–agent 协作。
- **数据集/环境**：ACCORD-Shop 100 个场景 + ACCORD-Travel 100 个场景；四类偏好动态（hard/soft underspecification、unachievable、triggered）；GPT-5.1 user simulator + consistency checking。
- **方法**：POMDP 交互 harness；5 个前沿 LLM × ReAct / UncReAct；最多 50 环境步、20 轮对话。
- **关键结果**：最强 Claude-Sonnet-4.5 的 Perfect Outcome Rate 仍低于 30%；unachievable / triggered 最难；UncReAct prompting 基本不改善。
- **对本 idea 的启发**：适合做 Stage 2 交互真实性底座；四类偏好动态可以测试不同 failure mode。
- **差异/风险**：单 session；无跨会话 memory；agent 不改变 latent preference；无反事实 ground truth。
- **可复现实验**：先 text-only 读取场景 JSON，不启动 WebShop/Java。

### MemoryCD（arXiv:2603.25973，已核对原文）

- **完整标题/作者**：*MemoryCD: Benchmarking Long-Context User Memory of LLM Agents for Lifelong Cross-Domain Personalization*；Weizhi Zhang, Xiaokai Wei, Wei-Chieh Huang, Zheng Hui, Chen Wang, Michelle Gong, Philip S. Yu（Roblox / UIC / Cambridge）。
- **研究问题**：长上下文用户记忆的跨域个性化评测。
- **数据集**：Amazon Review，12 域；主实验 4 域（Personal Care、Books、Electronics、Home & Kitchen）；Table 1 报告 400K context length、1K+ sessions；4 类任务（rating prediction、item ranking、review summarization、review generation）。
- **方法**：single-domain / cross-domain memory；14 个长上下文 LLM × 6 个 memory 方法（long-context、Mem0、LoCoMo、ReadAgent、MemoryBank、A-Mem）。
- **关键结果**：没有单一 memory 方法在所有任务上占优；整体指标仍远未达到用户满意；跨域 memory 效果高度依赖源域与目标域的语义对齐。
- **对本 idea 的启发**：Stage 1 的真实历史与商品库底座；4 类任务可用于个性化评测。
- **差异/风险**：无交互式 agent、无推荐动作、无 influence model、无隐藏偏好与反事实标签；Idea 说明中的“323 用户 / 167,870 商品”未在已读页核实。
- **可复现实验**：从 Hugging Face 下载，记录版本、checksum、用户数、item 数、字段；原始数据不入 Git。

### CALMRec（arXiv:2607.23647，已核对原文）

- **完整标题/作者**：*CALMRec: Causally Aligned Language Memory for Long-Horizon Recommendation*；Gengyu Zhan（Shenzhen University）；页面含 AAAI 2026 版权标记。
- **研究问题**：LLM 推荐器把持久偏好、短期意图、曝光导致的行为混成一个画像，造成反馈循环。
- **方法**：冻结多模态 LM 编译 semantic atoms；三时间尺度记忆（短期意图 / 长期偏好 / 曝光轨迹）；propensity-weighted updates；conservative offline critic；counterfactual deletion 解释；Proposition 1 给出识别条件。
- **关键结果**：三个环境 10 seeds，长期价值 +6.1% / +7.6% / +6.7%；去掉 propensity correction 价值降 0.739 ± 0.191；语义原子 NDCG 超 TF-IDF 两倍以上。
- **对本 idea 的启发**：三时间尺度、exposure trace、propensity、provenance、counterfactual deletion 都可借鉴。
- **差异/风险**：推荐排序而非自然语言 memory write；无 compliance/internalization；无 agent-suggested vs independent；无 W0/W1 配对反事实；无 memory backend。
- **可复现实验**：代码可得性仍待确认；若不可得，按论文重实现简化版 IPW baseline。

### CAPTURE（arXiv:2609.02265，已核对原文）

- **完整标题/作者**：*CAPTURE: Disentangling Preference Drift from Memory Poisoning in Personalized LLM Agents*；S M Asif Hossain, Ruksat Khan Shayoni, Md Kishor Morol。
- **研究问题**：preference-authenticity ambiguity；recency/provenance 规则无法区分真实漂移、上下文切换、讽刺和注入。
- **方法**：连续时间 POMDP + neural ODE；authenticity gate 六动作（retain / add / scope / revise / quarantine / ask）；多时间尺度 ledger；safety-bounded selection；counterfactual audit。
- **关键结果**：D-PREFGUARD 2,400 episodes、480 held-out；win rate 71.5%；fixed-policy poisoning 11.5%；adherence 83.5%；adaptive attack 24.7%；40 用户 2–3 周 replay；HorizonBench zero-shot。
- **对本 idea 的启发**：`scope` 可映射到 `validity.context`；`quarantine` 可映射到 `status` + `hedged`；`ask` 可映射到 `abstain` / clarify；多时间尺度 ledger 可借鉴。
- **差异/风险**：核心是 drift vs poisoning，不是 agent-induced compliance；无 exposure propensity / 随机探索；无 W0/W1 配对反事实；用户研究是 replay。

### ULSPB（arXiv:2605.06731，已核对原文）

- **完整标题/作者**：*When Routine Chats Turn Toxic: Unintended Long-Term State Poisoning in Personalized Agents*；Xiaoyu Xu, Minxin Du, Qipeng Xie, Haobin Ke, Qingqing Ye, Haibo Hu（PolyU / HKUST (Guangzhou)）。
- **研究问题**：routine user-agent 交互会逐渐改写长期状态，削弱确认边界、扩大工具默认权限、增加自主行为；称为 unintended long-term state poisoning。
- **方法/数据**：ULSPB 350 个设置（5 类辅助任务 × 7 种交互模式 × 5 种对话变体 × 2 语言）；每个 routine 24 轮；Harm Score 衡量 authorization drift / tool-use escalation / unchecked autonomy；OpenClaw + 4 个 LLM。
- **关键结果**：routine conversations 本身就能 poison 长期状态，风险集中在 `MEMORY.md` / `memory/`；真实种子对话也有效；StateGuard 在 writeback 边界审计并回滚，Targeted-Ensemble 可把 HS 降到接近 0，成本 <$0.004/run。
- **对本 idea 的启发**：支持“良性日常交互会累积成长期状态”；StateGuard 的 writeback audit / rollback 与 provenance writer / 反事实回放思路相近。
- **差异/风险**：研究 security / authorization drift，不是 preference drift；无 compliance/internalization；无 W0/W1；LICENSE 待核实。

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
