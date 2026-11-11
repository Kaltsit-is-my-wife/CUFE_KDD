# InflMem 论文阅读记录（D1 / 原文核对）

> 项目：InflMem / Agent-Induced Drift
> 整理人：@member-01（P1）
> 日期：2026-11-12
> 来源：`sandbox/member-01/papers/`（本地 PDF，不提交 Git）
> 状态：**5/5 已核对原文**
> 沉淀：完整对照、研究脉络、baseline 计划与 related work 草稿见 [related_work.md](related_work.md)。

---

## 1. 下载与核对状态

| # | 本地文件 | 论文 | 状态 | 说明 |
|---|---|---|---|---|
| 1 | `2608.27818v1.pdf` | AcCoRD | **已核对原文** | 完整 PDF；见 §4.1 |
| 2 | `2603.25973v1.pdf` | MemoryCD | **已核对原文** | 完整 PDF；见 §4.2 |
| 3 | `3_CALMRec.pdf` | CALMRec | **已核对原文** | 文本可提取；见 §2 |
| 4 | `4_CAPTURE.pdf` | CAPTURE | **已核对原文** | 文本可提取；见 §3 |
| 5 | `2605.06731v1.pdf` | ULSPB | **已核对原文** | 完整 PDF；见 §4.3 |

---

## 2. CALMRec（已核对）

**完整标题：** *CALMRec: Causally Aligned Language Memory for Long-Horizon Recommendation*
**作者：** Gengyu Zhan（Shenzhen University）
**版本：** arXiv:2607.23647v1 [cs.LG]，2026-07-26；页面含 AAAI 2026 版权标记
**本地文件：** `3_CALMRec.pdf`

### 2.1 问题

当前 LLM 推荐器常把三类东西混成一个用户画像：

- **持久偏好**（durable preference）；
- **短期意图**（transient intent）；
- **曝光导致的行为**（exposure-induced behavior）。

这会导致反馈循环：重复曝光被误认为偏好，即时点击压过延迟满意度，流畅的解释不一定反映排序决策。

### 2.2 方法

- 用**冻结的多模态语言模型**把商品内容和反馈编译成**语义原子**（semantic atoms），每个原子带来源（item ID、内容片段、模态、反馈类型）和 grounding confidence；
- **三时间尺度记忆**：
  - `S_t`：短期意图，高衰减；
  - `L_t`：长期偏好，低衰减；
  - `E_t`：曝光轨迹，记录系统展示过什么，不等于用户喜欢什么；
- **propensity-weighted updates**：用 logging propensity 校正曝光偏差；
- **conservative offline critic**：在行为支持约束下重排候选，兼顾即时相关性和延迟满意度；
- **evidence-constrained explanations**：解释只使用有来源的原子，并用 counterfactual deletion 检查解释是否真的影响排序。

### 2.3 关键结果

- 三个环境（WeChat-Video、MIND-small、KuaiRec）、10 seeds：相对最强 baseline，discounted long-term value 分别提升 **6.1% / 7.6% / 6.7%**；
- 20-seed paired ablation：去掉 propensity correction 后价值下降 **0.739 ± 0.191**；去掉 conservative support regularization 后下降 **0.523 ± 0.234**；
- 语义原子 NDCG 在 held-out paraphrase benchmark 上超过 TF-IDF 两倍以上；
- 给出 Proposition 1：在 propensity 已知、positivity 成立、权重不裁剪时，self-normalized 估计对 reference-policy semantic evidence 是一致的。

### 2.4 与 InflMem 的关系

**可直接借鉴：**

- 三时间尺度记忆：短期意图 / 长期偏好 / 曝光轨迹；
- propensity weighting 处理曝光偏差；
- 语义原子 + provenance；
- counterfactual deletion 做解释忠实度。

**关键差异（我们的生存空间）：**

1. CALMRec 是**推荐排序**，不是自然语言 memory write；
2. 没有 compliance vs internalization 的区分，也没有 `evidence_type`（推荐后接受 vs 独立选择）；
3. 没有 agent-suggested vs independent 的证据权重；
4. 没有 W0/W1 配对反事实世界；
5. 没有 memory backend / 跨会话 memory audit。

> **威胁：** 审稿人可能说“这就是把 CALMRec 的 exposure memory + propensity 搬到 memory write”。因此我们的贡献必须锚定在 **compliance 被误写成 preference**，而不是“exposure-aware memory”。

---

## 3. CAPTURE（已核对）

**完整标题：** *CAPTURE: Disentangling Preference Drift from Memory Poisoning in Personalized LLM Agents*
**作者：** S M Asif Hossain, Ruksat Khan Shayoni, Md Kishor Morol
**版本：** arXiv:2609.02265v1 [cs.LG]，2026-09-02
**本地文件：** `4_CAPTURE.pdf`

### 3.1 问题

个性化 agent 的记忆同时是攻击面。面对一条与既有信念冲突的陈述，agent 无法区分：

- 用户真的改变了偏好；
- 临时上下文切换；
- 讽刺/玩笑；
- 通过检索文档注入的指令。

作者称之为 **preference-authenticity ambiguity**。现有方法一边倒：

- 个性化方法假设所有更新都是真实的，容易被注入；
- 注入防御拒绝不可信来源，但会拒绝合法的偏好变化。

### 3.2 方法

- 把记忆更新形式化为**连续时间 POMDP**，对 latent user state 做 belief tracking；
- 用 neural ODE 建模事件之间的连续时间演化；
- **authenticity gate** 在六种动作上做选择：retain / add / scope / revise / quarantine / ask；
- **多时间尺度 ledger**：stable / contextual / transient 三层，各自有 decay rate；
- **quarantine**：可疑更新先写入但不可检索，等待佐证；
- **clarifying question**：belief 熵过高时向用户提问；
- **safety-bounded selection**：安全约束在个性化循环之外；
- **counterfactual audit**：删除被引用的记忆节点后重新解码，测量解释的因果影响。

### 3.3 Benchmark 与结果

- **D-PREFGUARD**：2,400 条 longitudinal episodes，5 个 track（stationary、genuine drift、benign ambiguity、contamination、safety conflict）；480 条 held-out；96 users；3 位标注者验证 300 条，Krippendorff's α ≈ 0.70；
- 主结果（480 条 held-out）：
  - CAPTURE win rate **71.5%**，supervised transformer 69.3%，StateMem 66.1%；
  - fixed-policy poisoning **11.5%**，provenance-only 20.0%；
  - genuine-update adherence **83.5%**，provenance-only 74.1%；
  - false update **8.9%**；
  - adaptive attack 下 poisoning 升至 **24.7%**，此时 provenance-only 22.1%，两者不再可靠分开；
- 额外外部效度：HorizonBench zero-shot；40 名用户、2–3 周历史 replay；每 turn 约 630 ms。

### 3.4 与 InflMem 的关系

**可直接借鉴：**

- 把“真实性”作为 latent variable，而不是二值规则；
- 多时间尺度 ledger；
- `scope` 动作（把偏好限制到上下文）——对应我们的 `validity.context` / scope inflation；
- `quarantine`——对应我们的 `hedged` / `status=pending`；
- `ask`（clarifying question）——对应我们的 `abstain` 或主动澄清；
- counterfactual audit——对应我们的 `source_event_ids` / replay。

**关键差异（我们的生存空间）：**

1. CAPTURE 的核心是 **preference drift vs memory poisoning**，不是 **agent-induced compliance**；
2. 它没有把 **agent 的推荐/曝光/措辞** 作为偏好变化的因；
3. 没有 exposure propensity、随机探索、negative controls；
4. 没有 W0/W1 配对反事实 ground truth；
5. 用户研究是历史 replay，不是实时 agent 交互；
6. 它关心“这条更新是否真实”，我们关心“这次接受是否只是 compliance”。

> **威胁：** CAPTURE 已经在做多时间尺度记忆、scope、quarantine、clarifying question，且有自己的 benchmark。我们的差异化必须回答：**“agent 自己的推荐造成的 compliance，如何被 memory 误写成 preference？”** 这是 CAPTURE 没有覆盖的因果方向。

---

## 4. AcCoRD / MemoryCD / ULSPB（已核对）

### 4.1 AcCoRD（已核对）

**完整标题：** *ACCORD: Evaluating User-Agent Collaboration Under Realistic User Preference Dynamics*
**作者：** Tejas Srinivasan, Shikib Mehri, Nandita Naik, Anirban Das, William M. Campbell, Jesse Thomason（USC / Contextual AI / Capital One / Georgia Tech）
**版本：** arXiv:2608.27818v1 [cs.AI]，2026-08-28；Preprint
**本地文件：** `2608.27818v1.pdf`

- **Benchmark：** 两个域各 100 个场景：ACCORD-Shop（WebShop）和 ACCORD-Travel（TravelGym）；四类偏好动态：
  - hard underspecification（需要主动询问）；
  - soft underspecification（可协商）；
  - unachievable（需要 fallback/negotiation）；
  - triggered（只有 agent 暴露相关信息后才出现）。
- **User simulator：** GPT-5.1 + consistency checking；每个 episode 最多 50 个环境步、20 轮对话；5 个前沿 LLM，ReAct 与 UncReAct 两种 prompting。
- **结果：**
  - 最强模型 Claude-Sonnet-4.5 的 Perfect Outcome Rate 仍 **低于 30%**；
  - hard / soft underspecification 得分较高（约 0.7–0.95），**unachievable 和 triggered 最难**；
  - UncReAct prompting 基本不改善结果，说明 prompting 不足以解决偏好动态。
- **与 InflMem 的关系：**
  - 可借鉴：四类偏好动态、user simulator、scenario 生成、preference scoring；
  - 关键缺口：**单 session、无跨会话 memory、agent 不改变 latent preference、无反事实 ground truth**；
  - 它是“偏好 elicitation benchmark”，不是 memory write 或 agent-induced compliance 的研究。
- **链接：** [arXiv:2608.27818](https://arxiv.org/abs/2608.27818)；代码 [tejas1995/accord_benchmark](https://github.com/tejas1995/accord_benchmark)。

### 4.2 MemoryCD（已核对）

**完整标题：** *MemoryCD: Benchmarking Long-Context User Memory of LLM Agents for Lifelong Cross-Domain Personalization*
**作者：** Weizhi Zhang, Xiaokai Wei, Wei-Chieh Huang, Zheng Hui, Chen Wang, Michelle Gong, Philip S. Yu（Roblox / University of Illinois Chicago / University of Cambridge）
**版本：** arXiv:2603.25973v1 [cs.CL]，2026-03-26；Published as a workshop paper in Lifelong Agent @ ICLR 2026
**本地文件：** `2603.25973v1.pdf`

- **数据：** 基于 Amazon Review，12 个域；主实验用 4 个域（Personal Care、Books、Electronics、Home & Kitchen）；每个用户保留长历史（Table 1 报告 context length 400K、1K+ sessions）。
- **任务：** 4 类个性化任务：
  - personalized rating prediction（MAE / RMSE）；
  - personalized item ranking（NDCG@K）；
  - personalized review summarization（ROUGE-L / BLEU-1）；
  - personalized review generation（ROUGE-L / BLEU-1）。
- **设置：** single-domain memory 与 cross-domain memory；14 个长上下文 LLM × 6 个 memory 方法。
- **结果：**
  - 没有单一 memory 方法在所有任务上占优；
  - 整体指标仍远未达到用户满意；
  - long-context prompting 在 rating 上很强；Mem0 / LoCoMo / ReadAgent / MemoryBank / A-Mem 各有优势；
  - 跨域 memory 的效果高度依赖源域与目标域的语义对齐，不相关域会引入噪声。
- **与 InflMem 的关系：**
  - 可借鉴：真实跨年用户历史、商品库、4 类任务、single/cross-domain 设置；
  - 关键缺口：**无交互式 agent、无推荐动作、无 influence model、无 hidden preference / 反事实标签**；
  - 注意：Idea 说明中的“323 用户 / 167,870 商品”未在已读页中出现，需在下载数据后核实。
- **链接：** [arXiv:2603.25973](https://arxiv.org/abs/2603.25973)；代码 [AgentMemoryWorld/MemoryCD](https://github.com/AgentMemoryWorld/MemoryCD)；数据 [HF: WZDavid/MemoryCD](https://huggingface.co/datasets/WZDavid/MemoryCD)。

### 4.3 ULSPB（已核对）

**完整标题：** *When Routine Chats Turn Toxic: Unintended Long-Term State Poisoning in Personalized Agents*
**作者：** Xiaoyu Xu, Minxin Du, Qipeng Xie, Haobin Ke, Qingqing Ye, Haibo Hu（The Hong Kong Polytechnic University / HKUST (Guangzhou)）
**版本：** arXiv:2605.06731v1 [cs.CR]，2026-05-07；Preprint
**本地文件：** `2605.06731v1.pdf`

- **问题：** 个性化 agent 的长期状态会被日常、良性的交互逐渐改写，削弱确认边界、扩大工具默认权限、增加自主行为；作者称为 **unintended long-term state poisoning**。
- **Benchmark：** ULSPB，350 个设置 = 5 类辅助任务 × 7 种交互模式 × 5 种对话变体（1 routine + 4 single-injection）× 2 语言；每个 routine 24 轮；真实种子子集来自 WildChat / LMSYS-Chat-1M。
- **指标：** Harm Score（HS），衡量 authorization drift、tool-use escalation、unchecked autonomy。
- **结果：**
  - routine conversations 本身就能显著 poison 长期状态，风险主要集中在 memory-centric artifacts（`MEMORY.md`、`memory/`）；
  - 真实种子对话也会产生非平凡的 risky state updates；
  - 提出 StateGuard：在 writeback 边界审计 state diff，选择性回滚；Targeted-Ensemble 可把 HS 降到接近 0，成本低于 $0.004/run。
- **与 InflMem 的关系：**
  - 支持“良性日常交互会累积成长期状态”的大前提；
  - StateGuard 的 **writeback audit + rollback** 与我们的 provenance writer / 反事实回放思路相近；
  - 关键差异：它研究 **security / authorization drift**，不是 **preference drift**；没有 compliance vs internalization，也没有 W0/W1 配对反事实。
- **注意：** 已读页未给出 LICENSE；使用代码前需核实仓库许可。
- **链接：** [arXiv:2605.06731](https://arxiv.org/abs/2605.06731)；代码 [XiaoyuXU1/ULSPB](https://github.com/XiaoyuXU1/ULSPB)。

---

## 5. 对 InflMem 的直接影响

1. **Novelty 不能落在“exposure-aware memory”**：CALMRec 已经做了 exposure trace + propensity + semantic atoms；
2. **Novelty 不能落在“drift vs poisoning”**：CAPTURE 已经做了 authenticity gate + multiscale ledger + D-PREFGUARD；
3. **Novelty 也不能落在“routine interaction 会改变长期状态”**：ULSPB 已经系统化了 benign routine → state poisoning；
4. **我们的差异化必须落在：**
   - agent 自己的推荐/曝光/措辞导致 compliance；
   - memory writer 把 compliance 误写成 durable preference；
   - W0/W1 配对反事实 ground truth；
   - 同时评估 CMR / IDR / Quality / Coverage，避免“少写”作弊。
5. **底座分工：**
   - MemoryCD：Stage 1 真实用户历史与商品库；但它没有交互和 influence，不能单独支撑核心 claim；
   - AcCoRD：Stage 2 交互真实性底座；但它是单 session、无跨会话 memory，需要外挂 memory 和 influence；
   - CALMRec：方法近邻，借鉴三时间尺度、曝光轨迹、propensity；
   - CAPTURE：问题近邻，借鉴 scope / quarantine / ask、多时间尺度 ledger；
   - ULSPB：现象与防御参考，借鉴 writeback audit / rollback，但它研究 security 而非 preference。
6. **schema 可直接吸收：**
   - CALMRec 的三时间尺度 → `memory_type` + `validity.context` + exposure trace；
   - CAPTURE 的 `scope` → `validity.context`；
   - `quarantine` → `status` + `hedged`；
   - `ask` → `abstain` / clarify 记录；
   - ULSPB 的 writeback audit → `WriteDecision` + `counterevidence`。
7. **风险：** 五篇都是 2026 年新工作（CALMRec 页面含 AAAI 2026 版权，MemoryCD 为 ICLR 2026 workshop，CAPTURE / ULSPB 为 arXiv 预印本），novelty 窗口很窄；必须在 related work 中正面比较，而不是只引用。

---

## 6. 变更记录

| 日期 | 变更 | 记录人 |
|---|---|---|
| 2026-11-12 | 初稿：核对 CALMRec / CAPTURE 原文；记录 AcCoRD / MemoryCD / ULSPB PDF 损坏与重下建议 | @member-01 |
| 2026-11-12 | 重新下载 AcCoRD / MemoryCD / ULSPB 完整 PDF；5/5 全部核对原文，补齐三篇摘要与对 InflMem 的影响 | @member-01 |
