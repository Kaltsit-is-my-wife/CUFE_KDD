# DriftHunter 论文精读 × Web Agent 多模态调研（2026-09-27）

> **归属**：`ideas/001-my-research-idea/`（个人调研容器）
> **对应**：`README.md` 调研文章索引 **#5**；`notes.md`【调研 #4】
> **本文件回答三件事**：
> 1. 用一句话讲清 DriftHunter（ICDM 2025）的优点与不足
> 2. 从哪些方面可以改进它
> 3. Web Agent × 多模态这条线上已有什么、缝隙在哪

---

## 0. 一句话评价

> **DriftHunter 的价值在于把「intent–slot 跨轮转移」做成可微、可端到端训练的累积模块，第一次让意图漂移成为可检测的在线信号；但它的评测把漂移退化成了「相邻两句话题是否相同」的二分类，又缺少「不做跨轮累积也能打平」的强基线，导致这套核心机制的必要性从未被真正证明。**

- **优点（可信）**：可微、可插拔、支持端到端；去 drift 子任务会导致 ATIS 的 slot filling 精度暴跌 21 点，这条消融是干净的正向证据。
- **不足（硬伤）**：合成数据的构造方式使任务自我简化；无关键基线；输入含 $u_{k+1}$ 使其成为后验判定而非在线预测。

---

## 1. DriftHunter 论文精读

**文献信息**：Yue Wang, Dehang Fu, Jie Tan, Junxiao Han, Yao Wan, Lixin Cui, Lu Bai†, Philip S. Yu.
*Detecting Intent Drift in Continuous Conversation via Temporal Transition Accumulation.*
**ICDM 2025**, pp. 773–782. DOI 10.1109/ICDM65498.2025.00085
单位：中央财经大学信息学院（@cufe.edu.cn）、杭州城市大学、华中科技大学、北京师范大学、UIC。
代码/数据：`https://github.com/FDHTJ/DriftHunter`

> 注：**这是本校本组团队的论文**，应作为「已有武器」而非「外部对手」来读。

### 1.1 问题与动机

LLM 聊天机器人让用户习惯**单会话长时间连续对话**（人不会主动点「新会话」按钮）。于是同一个 session 内会出现**无显式线索的意图跳变**，即 intent drift。

论文的 motivating example 是全篇最有价值的观察：

> 用户先连问三轮「自闭症」相关问题（intent = *inquire about autism*），突然追问「SFT training」。
> SFT 在自闭症语境里指 **Skill-Based Treatment**，在机器学习语境里指 **Supervised Fine-Tuning**——
> **同一个词、两个意图**。模型若吃满整个对话历史，就会被旧上下文带偏。

现有方法的三类缺陷：
| 方法族 | 代表 | 缺陷 |
|---|---|---|
| 单轮 SLU | BERT joint | 只看当前 utterance，无跨轮动态 |
| 多轮上下文融合 | RNNContextual / AGLCF | 只捕捉相邻轮依赖或固定长度上下文，处理不了任意位置漂移 |
| 异构图 | DHLG | 用**离线统计**建全局 intent–slot 图，**不含时间维度**，统计量训练前冻结 |

### 1.2 问题定义

session 内 utterance 序列 $U=(u_1,\dots,u_n)$。若 $u_1..u_k$ 意图为 $c_k$，而 $u_{k+1}$ 意图为 $c'\neq c_k$，则第 $k$ 轮发生漂移（$o_k=1$）。检测器为二分类：

$$g_\theta(u_1,\dots,u_k,u_{k+1}) \to \{0,1\}$$

⚠️ **关键细节**：输入**包含 $u_{k+1}$**。因此这本质是「这两轮之间意图变了吗」的**后验判定**，而不是「下一轮会不会漂移」的**在线预测**。这与 intro 中宣称的 "online switching mechanism" 存在落差。（详见 §1.5 缺陷 ③）

### 1.3 方法：DriftHunter 四组件

整体为 encoder–decoder 多任务架构（intent + slot + drift 三头），DriftHunter 夹在 encoder 与 decoder 之间。

**① Local Representation Learning（式 4–7）**
- token 级：$h_t=\mathrm{softmax}(W_2\tanh(e_u^\top W_1))e_u$
- utterance 级：$h_u=(e_u^\top W_3)e_u$
- 自适应融合：$h=\alpha h_t+(1-\alpha)h_u$，$\alpha$ 由双 Sigmoid 归一化得到（非固定超参）

**② Intent–Slot Transition Accumulation（核心，式 8–11）**

把 intent 标签集 $I$ 与 slot 标签集 $S$ **拼入同一联合标签空间**：

$$M_t=\{m_{i,j}\}_{(|I|+|S|)\times(|I|+|S|)}$$
$$h_t = M_{t-1}^\top h W_\tau + h$$
$$M'_t=\mathrm{Activation}(\mathrm{Similarity}(h_{t-1},h_t))$$
$$\boxed{M_t=\lambda M_{t-1}+(1-\lambda)M'_t}$$

**这是全文最"实"的一步**：$\lambda$ 指数平滑递归累积历史转移，$\lambda=0.2$ 表示偏向当前轮；整个 $M_t$ **可微**，故可端到端训练——这正是相对 DHLG（离线统计图）的核心区别。

**③ Global Transition Incorporation（式 12–14）**
滑窗（窗口 32）聚历史表示 $E$，注入 $M_t$：$h_t=M_t^\top H W_2 \oplus h_t$

**④ Token-level Enhanced Representation（式 15–16）**
$e_u=\mathrm{softmax}(e_u h_t^\top)h_t+e_u$，再做邻域聚合 $\mathrm{Adj}(\cdot)$

**训练目标（式 17–20）**：$L=\alpha L_{drift}+\beta L_{intent}+\gamma L_{slots}$，$\alpha+\beta+\gamma=1$。
作者经验：**任务越难权重越高**，推荐 $(\alpha,\beta,\gamma)\approx(0.05,0.25,0.7)$——drift 仅占 5%。
超参：$\lambda=0.2$，窗口 32，最大 token 128，BERT-uncased（D=768），AdamW，lr=1e-5，单卡 4090。

### 1.4 实验与结果

| 项 | 内容 |
|---|---|
| 数据集 | ATIS（单轮）、SIM（多轮，平均同意图长度 **15.35**）、MultiWOZ（1 万+ 对话 / 8 域） |
| 数据构造 | 原始数据 + **合成长会话**（随机打乱对话后拼接，逐句标 drift） |
| 基线 | BERT、RNNContextual、AGLCF、DHLG、DeepSeek-R1-8B |
| 主结果 | 接入 DriftHunter（`-DH`）后平均 F1：**drift +6.4% / intent +4.6% / slot +7.3%** |

值得记住的现象：

1. **DeepSeek-R1-8B 在 drift 上几乎不会判"没漂移"**：MultiWOZ P=45.7 / R=96.5；ATIS P=35.8 / R=95.9。**Recall 高得离谱、Precision 崩盘**，说明它倾向一律回答"变了"。
2. **上下文越长增益越大**——核心卖点。
3. **消融**：transition accumulation 主要提 recall；global incorporation 主要提 precision/F1。
4. **去 drift 子任务 → ATIS slot filling P 从 83.7 → 62.5（−21 点）**，SIM −1.5，MultiWOZ −0.3。这是全文最有说服力的消融。
5. **Case study（图 4/5）**：$M_t$ 热力图显示用户从「买电影票 BMT」漂到「订餐厅 RR」时对应转移权重上升；意图稳定时自转移保持高值。

### 1.5 诊断：五个具体缺陷

| # | 缺陷 | 证据 | 严重度 |
|---|---|---|---|
| ① | **合成长会话使任务退化** | 随机打乱对话再拼接，使 drift ≡「相邻两句是否同一话题」。这正是 SIM 上 AGLCF-DH 能刷到 99.9/100.0/99.8 的原因——任务被自我简化，与 intro 里"SFT 一词两义"的真实难点脱节 | 🔴 高 |
| ② | **缺少关键基线** | 没有「只用 $(u_k, u_{k+1})$ 相邻两句」的强对照，也没做「滑窗但不累积 $M_t$」的消融。**因此无法证明"跨轮累积"是必要的** | 🔴 高 |
| ③ | **后验判定 ≠ 在线预测** | 输入含 $u_{k+1}$，检测发生在"漂移已经发生之后"。intro 宣称的 online switching mechanism 名不副实 | 🟠 中高 |
| ④ | **对照表被异常值污染** | DHLG 在 ATIS 的 slot filling 仅 29.6（P）/ 29.6（F1），明显是标签体系未对齐，使 Table V 的横向比较失真 | 🟠 中 |
| ⑤ | **λ 递归的病态性未测** | 式 11 是固定 λ 的指数平滑 ≡ 一阶 IIR / 简化的 RNN，理论上长序列梯度消失、被 λ 主导。论文未做 >100 轮的长程测试 | 🟡 中 |

---

## 2. 改进方向（六个候选，按「成本 / 信息量」排序）

> 遵循本仓库要求：每条给出【核心假设】句式与可证伪结果。
> **选型原则**（沿用 `notes.md` 调研 #3 的判断）：优先选**作者结构上不会做**的改进——即会推翻其自身结论的那些。

### 方向 A（首选）：用「相邻两句」强基线检验累积机制的必要性
- **动作**：补两组对照：(a) 仅输入 $(u_k,u_{k+1})$ 的 BERT 分类器；(b) 滑窗但不做 $M_t$ 递归累积。
- **【核心假设】** 如果**把 DriftHunter 的跨轮累积换成"只看相邻两句"，那么相对于原 DriftHunter，drift 检测 F1 将不显著下降（gap < 1 点），因为合成数据的漂移标签本身只依赖相邻两句的语义差异，累积历史不提供额外信息。**
- **基线**：原 DriftHunter（`-DH` 系列）
- **数据集**：ATIS / SIM / MultiWOZ 的合成长会话（复现论文 V-B 构造步骤）
- **主指标**：Intent Drift Detection F1
- **可能证伪的结果**：若 (a) 与 DriftHunter 差距 < 1 点 → **整个 ② 号组件的动机崩塌**，论文的核心卖点不成立。
- **成本**：极低（一个 BERT 分类器 + 一次推理）/ **信息量**：极高
- **为什么作者不会做**：这条会直接削弱他们自己的核心贡献。

### 方向 B：把评测从「话题变化」拉回「真实意图漂移」
- **动作**：构造三类**真正的漂移**数据，替代随机拼接：(i) 一词多义型（SFT / Python / Apple 这类跨域同形词，用 intro 的例子）；(ii) 渐进型（意图经多轮逐渐偏移而非突跳）；(iii) 领域迁移型（直接用 MultiWOZ 天然的 domain transition）。
- **【核心假设】** 如果在**一词多义型漂移**数据上评测，那么相对于随机拼接的合成长会话，所有模型的 drift F1 将显著下降（预计 >15 点），且 DriftHunter 相对基线的增益将比论文报告值缩小，因为随机拼接数据中的漂移可由词汇重叠直接判定，不需要意图层面的建模。
- **基线**：DriftHunter、AGLCF、DHLG、DeepSeek-R1-8B
- **主指标**：drift F1 + 各模型的 P/R 失衡程度
- **可能证伪的结果**：若模型在新数据上 F1 仍 >90%，说明任务确实简单，此前的高分不是评测问题。
- **成本**：中（需构造数据集）/ **信息量**：高

### 方向 C：从后验判定改为在线漂移预警
- **动作**：把任务改为 $g_\theta(u_1,\dots,u_k) \to$ 预测"下一轮是否漂移"，或输出连续漂移倾向分数。
- **【核心假设】** 如果**把输入从 $(u_1..u_{k+1})$ 改为 $(u_1..u_k)$**，那么相对于后验判定，drift 检测 AUC 将下降（预计 5–15 点），因为漂移的语义线索主要存在于 $u_{k+1}$ 本身；而 DriftHunter 的累积结构在此设定下的相对增益将**大于**后验设定，因为累积历史是唯一的可用信息源。
- **主指标**：AUC / 提前 k 轮的预警命中率
- **为什么值得做**：这才是 intro 宣称的 online switching 真正需要的能力，且现有工作是空白。
- **成本**：中 / **信息量**：高

### 方向 D：λ 从固定超参改为输入相关门控
- **动作**：把式 11 的固定 λ 换成 learnable gate（GRU 式：$\lambda_t=\sigma(f(h_t,h_{t-1}))$），或用注意力回溯替代递归累积。
- **【核心假设】** 如果**把固定 λ 换成输入相关门控**，那么在超长序列（>100 轮）上，相对于固定 λ=0.2，drift 检测 F1 将显著提升，因为固定衰减会让远距离的意图转移信号在累积中被指数抹平，而门控可以在"意图稳定期"提高历史权重、在"漂移期"降低。
- **主指标**：F1 vs 对话轮数的曲线（重点看长尾）
- **成本**：低（改几行）/ **信息量**：中
- **顺带**：这也回应了缺陷 ⑤，是论文自己留下的口子。

### 方向 E（最大机会）：迁移到多模态 Web/GUI Agent
- **动作**：把 intent–slot 转移矩阵推广为 **(子目标, 界面状态) 转移矩阵**；在多模态观测下，slot 可扩展为"界面元素 / UI 状态"这一类二级状态。
- **【核心假设】** 如果**把 DriftHunter 的转移累积搬到 GUI agent 的动作–观察序列上**，那么相对于纯文本的 agent 状态跟踪，在用户中途改变目标的场景下，漂移检测的召回率将提升，因为多模态观测保留了纯文本的历史压缩会丢弃的界面证据。
- **独立贡献点（纯文本工作无法覆盖）**：验证 **"视觉证据被退化为文本"是否是漂移漏检的成因之一**。调研发现 WorldMemArena 已指出"记忆维护仍是 append-only，视觉证据多被退化成文本"[未核实] —— 这条线索可与之对接。
- **风险**：⚠️ PIRA-Bench（`2603.08013`）[未核实] 的状态转移语义与本方法**高度同构**；ScenDroid（ICLR'26）的"时间演化 GUI agent"补个检测器即闭环。**预计窗口 ≤ 6 个月**。
- **成本**：高 / **信息量**：高（但需先确认缝隙还在）

### 方向 F：评测可信度审计（对接本组强项）
- **动作**：复现论文 V-B 的合成长会话构造，对其 drift 标签做**语义效度审计**——抽样统计"被标为 drift 的样本中，有多少是话题相同但意图不同 / 话题不同但意图相同"。
- **【核心假设】** 如果**对论文的合成漂移标签做语义效度审计**，那么被标为 drift 的样本中将有相当比例（预期 >30%）并不能反映意图层面的变化，因为标签仅由相邻 utterance 的语义差异决定，而语义差异与意图变化并不等价。
- **主指标**：标签噪声率 / 人工一致性
- **为什么值得做**：直接连到本组主线「评测危机是全域元问题」（见 `survey-data-mining-2026.md`），且成本最低、几乎不会失败。

### 优先级建议

| 顺序 | 方向 | 理由 |
|---|---|---|
| 1 | **A** | 极低成本、极高信息量，且是"会推翻作者结论"的改进 |
| 2 | **F** | 成本最低，对接本组差异化优势（评测审计） |
| 3 | **B** | 为 A/B 提供更可靠的评测地基 |
| 4 | **D** | 顺手修论文的漏洞，可作为 A/B 的副产品 |
| 5 | **C** | 有独立价值，但需重定义任务 |
| 6 | **E** | 潜在回报最高，但需先确认缝隙（见 §4） |

---

## 3. Web Agent × 多模态调研

> **可信度声明**：2026 年的若干条目（尤其 `26xx.xxxxx` 编号）来自搜索摘要，标注 **[未核实]** 者**引用前必须在 arXiv 核对**。
> 参照 `notes.md` 的前车之鉴：曾因"读反摘要"把 ICLR 2026 的结论弄反。

### 3.1 主线 A：多模态 Web Agent（网页场景）

| 工作 | 出处 | 关键点 |
|---|---|---|
| WebArena | CMU, ICLR'24, `2307.13854` | 自托管真实站点，GPT-4 仅 14.4%，人类 78.2% |
| Mind2Web | OSU, NeurIPS'23, `2306.06070` | 2350 任务 / 137 真实网站，含跨站泛化划分 |
| VisualWebArena | CMU, ACL'24, `2401.13649` | 910 视觉接地任务；**给出四种观测的官方消融** |
| WebVoyager | 浙大/腾讯, ACL'24, `2401.13919` | 真实开放网站，GPT-4V-as-judge |
| SeeAct | OSU, `2401.01614` | **明确指出 SoM 对复杂网页无效**，grounding 是瓶颈 |
| Set-of-Mark | MSR, `2310.11441` | 给可交互元素打编号，激发视觉 grounding |
| AgentOccam | Amazon, ICLR'25, `2410.13825` | **纯文本 AXTree 剪枝即达 SOTA**（较前 +9.8） |
| UGround | OSU, ICLR'25 Oral, `2410.05243` | 纯视觉 agent 反超"视觉+文本"，grounding +20 点 |
| UI-TARS / UI-TARS-2 | 字节, `2501.12326` / `2509.02544` | 端到端纯截图，OSWorld 24.6 → 47.5 |

### 3.2 主线 B：GUI / Computer-Use Agent（桌面、手机）

| 工作 | 出处 | 关键点 |
|---|---|---|
| OSWorld | NeurIPS'24 D&B, `2404.07972` | 真实三 OS 环境，人类 72.4% vs 最佳 12.2% |
| CogAgent | CVPR'24 Highlight, `2312.08914` | 18B + 高分辨率 cross-attn，1120×1120 |
| AguVis | ICML'25, `2412.04454` | 纯视觉跨平台统一动作空间 |
| Mobile-Agent v3 | 阿里, `2508.15144` | 四 agent 协作，AndroidWorld 73.3 |
| Gemini 2.5 / Claude Computer Use | Google / Anthropic | 产品级，**无正式论文** |

**GUI 视觉 grounding 两条路线**：① OCR/检测 + Set-of-Marks（开放坐标 → 闭集选 ID）；② 端到端回归坐标（Ferret-UI `2404.05719`、ShowUI `2411.17465`、OS-Atlas `2410.23218`、UGround `2410.05243`）。
**天花板**：ScreenSpot-Pro 上最好的专门模型 **< 20%**。

### 3.3 核心争议：视觉到底有没有用？

VisualWebArena 官方消融（同为 GPT-4V）——**这是全领域最硬的数字**：

| 配置 | 成功率 |
|---|---|
| 纯文本 | 7.25% |
| 文本 + 图像描述 | 12.75% |
| 视觉截图 | 15.05% |
| 视觉 + SoM | **16.37%** |
| 人类 | 88.7% |

**视觉有增益但不神奇（+8 点）**；且：
- AgentOccam 证明**纯文本剪枝就能反超**多模态方案；
- `2504.08942` 发现**同时给截图 + a11y 反而不如只给截图**（额外信息干扰）。

> **结论**：领域共识不是"多模态无用"，而是 —— **视觉是必要非充分，grounding 才是真瓶颈，且现有基准分数系统性虚高。**

### 3.4 评测可信度：全领域的元问题

- **WebArena-Verified**（ServiceNow, ICLR'26）：审计 812 个任务发现 **299 个评测错误**，并**弃用 LLM-as-judge**；
- 有检查表工作称 **10 个 agent 基准里 8 个有缺陷**，τ-bench 上"空操作 agent"能拿 38%；
- LLM-judge 一致率仅 ~85%，且存在家族自偏好偏差。

→ **与本组 `survey-data-mining-2026.md` 的"评测危机"判断完全吻合，失效模式相同：公开基准与真实场景的系统性偏差。**

### 3.5 主线 C：与 DriftHunter 直接相关的交叉线

| 工作 | 出处 | 与本文的关系 |
|---|---|---|
| **NoLiMa** | ICML'25, `2502.05167` | 去字面匹配后多数模型有效上下文仅 ~2K——**"长上下文 ≠ 长记忆"最强证据** |
| **LongMemEval** | ICLR'25, `2410.10813` | 五项能力含 **Knowledge Updates** 与跨会话推理，直指"时间演化" |
| Evaluating Goal Drift in LM Agents | AIES'25, `2505.02709` | agent 的 goal drift；上下文越长越严重 |
| LLMs Get Lost in Evolving User Intent | `2607.20734` **[未核实]** | 意图逐步揭示/修订的多轮对话；**与 DriftHunter 设定最近** |
| PIRA-Bench | `2603.08013` **[未核实]** | 截图流上做主动意图推荐，用 CREATE/RESUME/UPDATE/IDLE 刻画**意图线程状态转移**——与 DriftHunter 的转移矩阵**高度同构** |
| IDSS | `2608.15755` **[未核实]** | 无需训练的"意图驱动情境状态"，跟踪 active/pending/completed/blocked 意图；**非多模态** |

### 3.6 核心阅读清单（顶会 + 大组 + 高引用）

> **数据来源**：Semantic Scholar Graph API，检索日期 **2026-09-27**。
> 引用量为 `citationCount`，**动态变化**，仅用于排序参考；S2 对纯 arXiv 论文的计数口径与 Google Scholar 有差异。
> ⚠️ 标注 **[需核对]** 者，S2 记录分裂，数字不可用。

#### A. 多模态底座（所有多模态 agent 的视觉基座）

| 论文 | 出处 | 引用 | 大组 |
|---|---|---|---|
| **Visual Instruction Tuning (LLaVA)** `2304.08485` | NeurIPS 2023 | **11,180** | UW-Madison + MSR (Haotian Liu / Yong Jae Lee) |
| **Qwen2.5-VL Technical Report** `2502.13923` | arXiv 2025 | **5,900** | 阿里 Qwen (Shuai Bai / Junyang Lin) |

#### B. Web Agent — 环境与基准（奠基层，引用最高）

| 论文 | 出处 | 引用 | 大组 |
|---|---|---|---|
| **WebGPT** `2112.09332` | arXiv 2021 (OpenAI) | **2,081** | OpenAI (Nakano / John Schulman) |
| **WebArena** `2307.13854` | ICLR 2024 | **2,062** | CMU (Shuyan Zhou / **Graham Neubig**) |
| **Mind2Web** `2306.06070` | NeurIPS 2023 | **1,453** | OSU (**Yu Su**) |
| **WebShop** `2207.01206` | NeurIPS 2022 | **1,380** | Princeton (**Shunyu Yao** / Karthik Narasimhan) |
| **VisualWebArena** `2401.13649` | ACL 2024 | **[需核对]** | CMU (Jing Yu Koh / Daniel Fried) |

#### C. Web Agent — 方法

| 论文 | 出处 | 引用 | 大组 |
|---|---|---|---|
| **SeeAct** (GPT-4V is a Generalist Web Agent, if Grounded) `2401.01614` | ICML 2024 | **636** | OSU (Boyuan Zheng / **Yu Su**) |
| **WebVoyager** `2401.13919` | ACL 2024 | **455** | 浙大 / 腾讯 (Dong Yu) |
| **Set-of-Mark Prompting** `2310.11441` | arXiv 2023 | **274** | MSR (Jianwei Yang / **Jianfeng Gao**) |
| **WebLINX / WebLlama** `2402.05930` | ICML 2024 | **189** | McGill / Mila (Siva Reddy) |
| **AgentOccam** `2410.13825` | ICLR 2025 | **133** | Amazon (Ke Yang / Huzefa Rangwala) |
| **Mind2Web 2** `2506.21506` | NeurIPS 2025 | **76** | OSU (**Yu Su**) |

#### D. GUI / Computer-Use Agent

| 论文 | 出处 | 引用 | 大组 |
|---|---|---|---|
| **OSWorld** `2404.07972` | NeurIPS 2024 D&B | **1,198** | 港大 (Tianbao Xie / **Tao Yu**) |
| **CogAgent** `2312.08914` | CVPR 2024 **Highlight** | **881** | 清华 THUDM (**Jie Tang**) |
| **UI-TARS** `2501.12326` | arXiv 2025 | **581** | 字节 Seed (Yujia Qin) |
| **AppAgent** `2312.13771` | CHI 2025 | **534** | 腾讯 (Chi Zhang / Gang Yu) |
| **AndroidWorld** `2405.14573` | ICLR 2025 | **440** | Google DeepMind (Christopher Rawles) |
| **AITW (Android in the Wild)** `2307.10088` | NeurIPS 2023 | **380** | Google DeepMind |
| **Mobile-Agent** `2401.16158` | ICLR 2024 W | **342** | 阿里通义 (Junyang Wang / Jitao Sang) |
| **AguVis** `2412.04454` | ICML 2025 | **279** | 港大 + Salesforce (Yiheng Xu / Caiming Xiong) |
| **ShowUI** `2411.17465` | CVPR 2025 | **263** | NUS (**Mike Zheng Shou**) |
| **OmniParser** `2408.00203` | arXiv 2024 | **217** | MSR (Yadong Lu / Ahmed Awadallah) |
| **Ferret-UI** `2404.05719` | ECCV 2024 | **213** | Apple (Keen You / Zhe Gan) |
| **ScreenAgent** `2402.07945` | IJCAI 2024 | **120** | 吉林大学 (Runliang Niu / Qi Wang) |

#### E. 视觉 Grounding（GUI 场景的瓶颈环节）

| 论文 | 出处 | 引用 | 大组 |
|---|---|---|---|
| **UGround** (Navigating the Digital World as Humans Do) `2410.05243` | ICLR 2025 **Oral** | **419** | OSU (**Yu Su**) |
| **OS-Atlas** `2410.23218` | ICLR 2025 | **376** | 上海 AI Lab (Zhiyong Wu / Yu Qiao) |

#### 观察（对本组选题的含义）

1. **两大课题组主导这条线**：**OSU (Yu Su)** 一家占了 Mind2Web / SeeAct / UGround / Mind2Web 2 / AguVis 五篇；**CMU (Graham Neubig, Daniel Fried)** 占 WebArena / VisualWebArena。这两组是绕不开的对手，也是最好的 baseline 来源。
2. **「引用量高」与「近年」天然冲突**：引用 >1000 的六篇里，四篇是 2021–2023 的奠基工作。**若严格按"近年 + 高引用"筛，实际落在 2024–2025 的只有 CogAgent / UI-TARS / AppAgent / AndroidWorld / UGround 等**。
3. **中文大组存在感强**：清华 THUDM、字节 Seed、阿里通义、上海 AI Lab、港大 Tao Yu 组——国内团队在这条线上是主力，**与本组的合作/竞争关系值得单独评估**。
4. **对 DriftHunter 的迁移（方向 E）最该精读的三篇**：**WebVoyager**（真实网站、多轮、对话式）、**AgentOccam**（反多模态的强基线，用来证明视觉到底有没有用）、**AguVis**（纯视觉统一 agent，观察序列建模）。

---

## 4. 交叉缝隙判断

**问题**：「多模态 web/GUI agent + 用户意图漂移检测」这条缝还在不在？

**判断**：**是缝隙，不是真空白，且窗口正在快速关闭（预计 ≤ 6 个月）。**
- **未被整体占位**：纯文本侧的意图漂移已成熟（DriftHunter / goal drift / evolving intent）；多模态侧只做到**意图提取 / 推荐 / 记忆防漂移**；**没有人用"跨轮转移累积"做多模态漂移检测**。
- **两侧正在逼近**：
  - PIRA-Bench 的状态转移语义"稍加延伸即可覆盖"；
  - ScenDroid（ICLR'26）的"时间演化 GUI agent"补个检测器即闭环。
- **可信度**：本判断为**推断**（基于摘要级检索），置信度中等。**必须打开 PIRA-Bench 与 ScenDroid 原文核实后才能立项。**

**差异化点（若立项）**：
1. 多模态观测使 DriftHunter 的"槽位"可扩展为**界面元素 / 子目标的二级状态**；
2. 可验证纯文本工作无法覆盖的独立命题：**"视觉证据被退化为文本"是否是漂移漏检的成因之一**。

---

## 5. 下一步与待核实清单

### 立即动作
1. 跑 **方向 A**（相邻两句强基线）——成本最低、信息量最高，且能直接判断 DriftHunter 的累积机制是否必要。
2. 读穿两篇最接近的工作：`2505.02709`（goal drift，已核实）与 `2607.20734`（evolving user intent，[未核实]）。

### 待核实清单（引用前必须核对）
| 条目 | 状态 | 追查方式 |
|---|---|---|
| PIRA-Bench `2603.08013` | 仅见搜索摘要 | arXiv 核对标题/作者/日期 |
| ScenDroid（ICLR'26） | 见 ICLR virtual 页 | 确认是否含漂移检测器 |
| `2607.20734` / `2608.15755` / `2605.18652` | 未核实 | arXiv 逐条核对 |
| WorldMemArena "视觉证据被退化为文本" | 未核实 | 找原文确认结论方向 |
| WebArena-Verified 的 299 个错误 | 见 GitHub 仓库 | 核对是否为 ICLR'26 正式发表 |
| 各厂商自报分数（Gemini 88.9% 等） | 来自博客 | **勿引用**，非同行评议 |

### 不做的事（避免重蹈覆辙）
- ❌ 不继承论文的**合成长会话构造**（随机打乱拼接会让任务退化）；
- ❌ 不把"R 高 P 低"直接解读为"LLM 不会判漂移"（更可能是 prompt 未校准，见缺陷表旁注）。

---

## 附录：来源

**论文本体**
- DriftHunter, ICDM 2025：`DOI 10.1109/ICDM65498.2025.00085`；代码 `https://github.com/FDHTJ/DriftHunter`
- PDF 本地位置：`相关论文/Detecting Intent Drift in Continuous Conversation via Temporal Transition Accumulation.pdf`

**Web Agent / GUI Agent**
- WebArena `2307.13854`｜VisualWebArena `2401.13649`｜Mind2Web `2306.06070`｜Mind2Web 2 `2506.21506`
- WebVoyager `2401.13919`｜SeeAct `2401.01614`｜Set-of-Mark `2310.11441`｜AgentOccam `2410.13825`｜UGround `2410.05243`
- WebPilot `2408.15978`｜WebLlama/WebLINX `2402.05930`｜WebShop `2207.01206`｜Web-Shepherd `2505.15277`｜WebGen-Bench `2505.03373`
- Online-Mind2Web / Illusion of Progress `2504.01382`
- OSWorld `2404.07972`｜CogAgent `2312.08914`｜AguVis `2412.04454`｜UI-TARS `2501.12326` / UI-TARS-2 `2509.02544`｜AppAgent `2312.13771`｜ScreenAgent `2402.07945`
- Mobile-Agent v3 `2508.15144`｜Qwen2.5-VL `2502.13923`｜AutoGLM/GLM-PC `2411.00820`
- Ferret-UI `2404.05719` / Ferret-UI Lite `2509.26539`｜ShowUI `2411.17465`｜OS-Atlas `2410.23218`
- ScreenSpot `2312.13108` / ScreenSpot-Pro `2504.07981`｜AITW `2307.10088`｜AndroidWorld `2405.14573`｜WindowsAgentArena `2409.08264`
- WebArena-Verified：`https://github.com/ServiceNow/webarena-verified`

**意图漂移 / Agent 记忆**
- NoLiMa `2502.05167`｜LongMemEval `2410.10813`｜Evaluating Goal Drift `2505.02709`
- MMLongBench `2505.10610`｜MementoGUI `2605.18652` **[未核实]**
- LLMs Get Lost in Evolving User Intent `2607.20734` **[未核实]**｜PIRA-Bench `2603.08013` **[未核实]**｜IDSS `2608.15755` **[未核实]**

---

| 字段 | 内容 |
|---|---|
| 精读/调研日期 | 2026-09-27 |
| 调研人 | @YuchenLiu |
| 覆盖规模 | 1 篇精读论文 + 约 35 篇周边文献 |
| 方法 | 论文全文提取（pymupdf）+ 3 路并行 WebSearch/WebFetch 调研 |
| 主要局限 | 2026 年条目多为预印本/摘要级，**未逐篇打开原文**；缝隙判断为推断，无实验证据 |
