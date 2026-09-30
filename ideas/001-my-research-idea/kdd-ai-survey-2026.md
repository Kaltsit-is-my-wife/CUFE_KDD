# KDD 2026 AI 方向调研与 idea 候选

> **调研人**：@YuchenLiu ｜ **日期**：2026-09-21 ｜ **对应目录**：`ideas/001-my-research-idea/`
> **性质**：方向调研 + idea 候选清单，目标是在 KDD 的 AI 方向里选出可做、可证伪的课题
> **配套文档**：[`survey-data-mining-2026.md`](survey-data-mining-2026.md)（领域综述）、[`topic-landscape-2026.md`](topic-landscape-2026.md)（选题地图）
> **核验状态**：见第 6 节，部分 2026 年 arXiv 编号与开源性未逐条核实

---

## 0. 数据来源与可信度

**一手来源**：KDD 2026 官方论文页 <https://kdd2026.kdd.org/papers/> 把全部录用论文以 JSON 内嵌在 HTML 里。实抓解析后得到 **1415 篇**（去重后 1408 条唯一标题，差 7 条原因未核实）。

| Track | 篇数 |
|---|---|
| Research (rtp) | 787 |
| **AI for Sciences (ais)** | 243 |
| ADS | 186 |
| Datasets & Benchmarks (dtb) | 182 |
| Blue Sky (bsi) | 17 |

**取不到的来源**：ACM DL proceedings 返回 403（Cloudflare）；DBLP 被 Anubis 反爬拦截。故本文对 KDD 论文的核验到「官方页 JSON 的标题/作者/DOI」为止，**未逐篇打开正文**。

**本报告的核验分级**：
- **A** = 已打开官方页 / arXiv abs / GitHub 仓库实际核验
- **B** = 仅搜索摘要或聚合站命中
- **C** = 未能核实

---

## 1. AI 在 KDD 2026 的大盘

Research 主轨 787 篇中，**标题命中 AI 关键词的约 300 篇（≈38%）**（标题关键词计数，有重叠，属量级判断）。

| 子方向 | RT 标题命中数 | 活跃度 |
|---|---|---|
| 多模态 | 51 | 多 |
| 生成式模型（扩散 / Semantic ID） | 49 | 多 |
| **LLM4Rec / 生成式推荐** | 36+ | **爆** |
| **Agent 系统** | 35 | **爆** |
| 检索与 RAG | 21 | 多 |
| 评测 / 基准 / 方法论反思 | 17 | 中 |
| 基础模型（表格/时序/图） | 15 | 中 |

**与往届趋势对比**（第三方分析，**B 级**）：LLM 41→131、agent 19→76、reasoning 17→80、benchmark 29→89、RAG 3→18、generative rec **1→20**、KG 11→27。**唯一负增长：GNN 29→13。**

**Track 录取率对比**：Research 二轮 ~3252 投稿 / **18.5%**；**D&B 二轮 566 投稿 / 153 录用 / 27%**；Blue Sky（首设）72 投稿 / 17 录用 / 23.6%。D&B 录取率高出 Research 近 9 个百分点，且 CFP 明确把 benchmark、curation、**evaluation methodology**、开源工具列为一等公民。

---

## 2. 四个子方向调研

### 2.1 Agent 记忆 / 长上下文 / 状态管理

**KDD 2026 代表论文**（DOI/标题取自官方 JSON，开源性未逐条核验）：

| 论文 | 一作（单位） | 出处 |
|---|---|---|
| Evaluating Long-Horizon Memory for Multi-Party Collaborative Dialogues | Chuanrui Hu (EverMind) | DTB / arXiv:2602.01313 |
| Advancing Multimodal Agent Reasoning with Long-Term Neuro-Symbolic Memory | Rongjie Jiang (UNSW) | RTP / 10.1145/3770855.3817643 |
| MemGraphRAG: Memory-based Multi-Agent System for GraphRAG | Chuanjie Wu (厦大) | RTP / …3818074 |
| DREAM: Event-Aware Memory Graph | Zhihao Xiao (北航) | RTP / …3818027 |
| EvoDS: Self-Evolving DS Agent with Context Management | Zherui Yang (HKUST-GZ) | RTP / …3818002 |
| TAMEing Long Contexts in Personalization | Rongpei Hong (UESTC) | RTP / …3780214 |
| Explicit v.s. Implicit Memory（多跳个性化推理） | Zeyu Zhang (人大) | RTP / …3780184 |
| Learning to Forget: Emotional Salience as Compression | — | Blue Sky / …3818653 |

**开源基座（已核验）**：Mem0（65.7k★ Apache-2.0）、A-MEM（1.18k★ MIT）、Zep（4.9k★ Apache-2.0）、LongMemEval（1.1k★ MIT）、NoLiMa（203★）、MemoryAgentBench（458★ MIT）。

**方法脉络（4 条路线）**
- **A 结构化写入-检索**（Mem0 / Zep / A-MEM / GraphRAG）：抽取 → 图/向量 → 检索
- **B 预算压缩/驱逐**（摘要、KV 压缩、遗忘）
- **C 长上下文直读 vs 外部记忆**
- **D 多智能体共享记忆**（同步、污染、仲裁）

**共识**：瓶颈是**跨会话与状态演化**，长上下文 ≠ 长记忆。
**争议**：结构化记忆是否真带来增益；驱逐是否可逆；写入时机（快写 vs 慢整合）。

**已证伪点（A 级，已读原文摘要）**
- **NoLiMa**（ICML 2025, arXiv:2502.05167）：13 个 128K 模型，<1K 表现好；**32K 时 11 个掉到自身短上下文基线的 50% 以下**（GPT-4o 99.3%→69.7%）。机制：无字面匹配时注意力难以定位，CoT / 推理增强**无效**。
- **LongMemEval**（ICLR 2025, arXiv:2410.10813）：500 题 5 类能力；商用助手与长上下文 LLM **跨会话记忆出现 30% 准确率下降**。
- **同类祛魅工作**：ReFind（arXiv:2608.12888）——原始日志 + agent 主动搜索 ≈ 结构化记忆，增益多来自检索能力；What Eviction Destroys（arXiv:2609.08279）——用 restore 反事实区分「不可逆删除」与「可恢复检索失败」；STALE（arXiv:2605.06527）——隐式冲突。

---

### 2.2 检索与 RAG

**KDD 2026 代表论文**（约 21 篇）

| 论文 | 一作 | 编号 | 开源 |
|---|---|---|---|
| RAG vs. GraphRAG: Systematic Evaluation | Haoyu Han (MSU) | 10.1145/3770855.3817575 / arXiv:2502.11371 | 未找到 |
| Why RAG Fails: A Graph Perspective | Kai Guo | 10.1145/3770855.3818101 / arXiv:2605.14192 | 未找到 |
| **When Hard Negatives Hurt (CausalNeg)** | Zhicheng Zhang | 10.1145/3770855.3818118 / arXiv:2606.01304 | ✅ mzhangzhicheng/CausalNeg（3★） |
| **Training Dense Retrievers w/ Multiple Positive Passages** | — | arXiv:2602.12727 | ✅ Trustworthy-Information-Access/Multi-Positive-Passages（2★） |
| CoRank: Compact Reranking for Scientific Retrieval | — | 10.1145/3770855.3818844 | ✅ runchu-tian/CoRank（1★） |
| EmoRAG: RAG Robustness to Symbolic Perturbations | — | 10.1145/3770854.3780238 | 未找到 |
| DocRetriever / MM-BRIGHT / CRAG-MM | — | 3817680 / 3817457 / 3817544 | 未找到 |

**方法脉络**

| 路线 | 核心问题 |
|---|---|
| bi-encoder 召回 + rerank | 瓶颈已从「负例数量」转向「负例质量」；生成式硬负例有分布偏移 |
| 多正例对比学习 | 等权池化抹平「部分相关 / 完全相关」 |
| agentic 多轮检索 | 小语料占优、大语料被 BM25 反超，token 成本线性膨胀 |
| 图结构增强 | **构造墙**：图质量上限即系统上限 |
| RAG 安全/鲁棒性 | 符号扰动与投毒均未被有效防御 |

**共识**：全局候选排序 > 顺序探索；图增强收益高度条件化。

**已证伪点**
- **When to use Graphs in RAG**（**ICLR 2026**, arXiv:2506.05690；代码 GraphRAG-Bench-Benchmark，496★）：GraphRAG 在 Natural Questions 上比 vanilla RAG **低 13.4%**，时效性查询低 **16.6%**，延迟 **2.3×**。
- **BM25 Wins at Scale**（arXiv:2607.26497，Pengyu Wang 等，2026-07-29）：约 10M 语料 token 处 BM25 反超 agentic search，大规模时差距近 20 分。⚠️ **仅为 arXiv 预印本（cs.CL），无任何会议标注，不是顶会论文**——引用需谨慎。
- **Unbiased Evaluation Framework for GraphRAG**（arXiv:2506.06331）：实证现有 GraphRAG 增益被评估偏差夸大。
- **Do We Still Need GraphRAG?**（arXiv:2604.09666）：agentic search 缩小 GraphRAG 优势。

---

### 2.3 生成式推荐 / LLM4Rec / Semantic ID

**KDD 2026 代表论文（A 级核验）**

| 论文 | 一作 | 编号 | 开源 |
|---|---|---|---|
| **How Well Does GR Generalize?（MemGen-GR）** | Yijie Ding (CMU) | arXiv:2603.19809 / 10.1145/3770855.3818148 | ✅ Jamesding000/MemGen-GR |
| Understanding Gen. Rec. with Semantic IDs（model-scaling 视角） | Jingzhe Liu (MSU) | arXiv:2509.25522 | 未发现 |
| Reasoning over Semantic IDs Enhances GR（SIDReasoner） | Yingzhi He (NUS) | arXiv:2603.23183 / …3818122 | ✅ HappyPointer/SIDReasoner |
| ReSOT: Re-balance Semantic ID with Optimal Transport | Renwu Geng (ZJU) | …3817834（无 arXiv） | ✅ grw-zju/ReSOT |
| FORGE: Forming Semantic Identifiers（工业） | Kairui Fu (ZJU + 淘宝) | arXiv:2509.20904 / …3817477 | ✅ selous123/al_sid |
| HiST: Hierarchical Semantic Tree Augmentation | Bocheng Pan (中科院微电子所) | …3817719 | 未发现 |

**SID 构造四条路线**：①残差量化（RQ-VAE，TIGER 系）；②聚类量化（RK-Means，GRID 实证优于 RQ-VAE）；③结构感知/最优传输（ReSOT）；④**上下文/个性化 SID（Pctx / DECOR / UniGCRec）——已被占满，勿碰**。

**争议**：GR 自称「语义泛化」，但 **MemGen 证明其优势只出现在泛化型样本**；ID 模型在记忆型样本更强，且 **GR 的「item 级泛化」常退化为 token 级记忆**。

**已证伪点（A 级）**
- **Diffusion Recommender Models and the Illusion of Progress**（ACM TORS 2026, arXiv:2505.09364；代码 remaplab/TORS26_Reproducibility-DDPMs）：复现 4 篇 SIGIR'23/24 论文衍生的 9 个 DDPM 推荐算法，**仅 25% 结果完全可复现**；CF-Diff **12 个指标只复现 1 个**，偏差达 40%；GiffCF 在测试集上调参；**调优后的 GF-CF / MultVAE / EASE-R / SLIM 稳定胜出**。
- **序列推荐的时序泄漏**（*Don't Get Ahead of Yourself*, **RecSys 2025**, DOI 10.1145/3705328.3759329；代码 yangl-iml/SRS_data_leakage）：**nDCG@10 跌 21.7–73.4%**，**7/8 组数据集×指标的最优模型发生换位**，模型可移动 4–5 名。机制：时序 LOO 按**用户本地时间轴**切分，跨用户全局时序不闭合，他人未来交互泄入训练集。姊妹作 *Time to Split*（10.1145/3705328.3748164）统计 2022–24 三会 75 篇中 **77.3% 用 LOO**。

---

### 2.4 图挖掘 × LLM / 图基础模型

**KDD 2026 代表论文**：标题含图类关键词 290 篇，其中**图×LLM 交叉 52 篇**。

| 论文 | 一作（单位） | DOI | 开源 |
|---|---|---|---|
| MemGraphRAG: Memory-based Multi-Agent System for GraphRAG | Chuanjie Wu（厦大） | …3818074 | ✅ XMUDeepLIT/MemGraphRAG（218★） |
| Generalizing Graph Foundation Models via Hyperbolic RAG | Yifan Jin（中科院软件所） | …3817750 | ✅ jyf123/HyRAG |
| **GRIP: In-Parameter Graph Reasoning through Fine-Tuning LLMs** | Jiarui Feng (WashU) | …3817895 | ✅ JiaruiFeng/GRIP（4★） |
| Both Topology and Text Matter: LLM-guided OOD Detection on TAG | Yinlin Zhu（中山大学） | …3817900 | 未找到 |
| Towards Next Graph Token Prediction: Discrete Graph Tokenization | Zhonghao Wang（浙大） | …3818177 | 未找到 |
| MOBI: Monolithic Graph-Language Modeling | Zhiyao Zhou（浙大） | …3818175 | 未找到 |

**三条路线**：**(a) GraphRAG**（图作检索索引，多智能体/记忆化是当前增量）；**(b) 图基础模型**（跨图零样本迁移，新转向双曲几何与联邦）；**(c) GNN+LLM 融合**（从「提示图」转向「把结构压进 LLM」：图 token 化、参数内推理、单模图-语言建模）。

**共识**：纯检索式图增益不稳。**争议焦点**：结构该放**检索端**还是**参数端**。

**已证伪点**
- **When to use Graphs in RAG**（ICLR 2026）：摘要原文承认 *"GraphRAG frequently underperforms vanilla RAG"*。⚠️ **注意结论有边界**：vanilla 赢简单事实检索，**GraphRAG 赢多跳与全局摘要**——不是「全面不如」。
- **ProG**（NeurIPS 2024 D&B；代码 sheldonresearch/ProG，588★）：发现 **GPPT 存在负迁移**。
- **Do We Still Need GraphRAG?**（arXiv:2604.09666）、**Universal Pathologies, Conditional Consequences**（arXiv:2608.05153）：胜者「语料条件化」，单评判员不可靠。

---

## 3. 横切发现：四个子方向同步「祛魅」

这是本次调研最重要的结论——**四个子方向各自出现了一次「整个类别被证伪」的时刻，模式高度一致：宣称的增益，追查下去来自混杂因素或评测缺陷。**

| 子方向 | 祛魅内容 | 被指出的真实来源 |
|---|---|---|
| Agent 记忆 | 长上下文 ≠ 长记忆（NoLiMa / LongMemEval） | 增益多来自检索能力，非记忆结构 |
| 检索 / RAG | GraphRAG 多数任务不如 vanilla RAG | 评估偏差 + 构造墙；agentic 大规模被 BM25 反超 |
| 生成式推荐 | 扩散推荐 75% 不可复现；GR 优势或为 token 级记忆 | 内容信息预算混杂；LOO 时序泄漏 |
| 图 × LLM | 图提示存在负迁移 | 结构放检索端收益不稳，语料条件化 |

**对选题的含义**：当前 AI/DM 领域最容易被接受的贡献形态不是「再提一个新模块」，而是
**「指出旧结论的混杂来源 → 给出可判定条件 → 在新条件下验证」**。这与本仓库要求的【核心假设】句式天然契合。

---

## 4. idea 候选（带【核心假设】）

### 走廊 A：生成式推荐的评测泄漏 → SID 放大效应 ⭐ 首推

**A1｜SID 是时序泄漏的放大器**
> **【核心假设】** 如果把 LOO 切分换成严格的时间截断切分（split-by-timepoint），并让 SID tokenizer **只在截断日之前**的物品上训练，那么相对于「标准 LOO + 全量目录 tokenizer」的生成式推荐基线，**生成式推荐模型（TIGER / GRID）的 nDCG@10 跌幅将显著大于 item-ID 模型（SASRec / BERT4Rec）**，因为 SID 在全量目录上学到的 code 与测试期物品共享 token，使 **token 级记忆伪装成 item 级泛化**。

| 项 | 内容 |
|---|---|
| 基线 | TIGER、GRID、MiniOneRec-0.5B；对照组 SASRec / BERT4Rec |
| 数据集 | Amazon Beauty / Sports / Toys（GRID 已预处理）、Yelp、ML-1M |
| 主指标 | ΔnDCG@10（两类模型的跌幅差）、token 级记忆率、无效 SID 率 |
| 可能证伪 | 若 GR 跌幅不显著大于 ID 模型 → 假设死 |
| 算力 | **单卡可行**（RQ-VAE 数分钟，TIGER 级模型数 GPU·时） |
| 为何非红海 | 红海是「LLM benchmark 污染检测」；此处是**推荐离线协议的 tokenizer 诱导伪影**，机制与对象均不同 |

**A2｜GR 的优势是「内容信息预算」混杂**（最省算力）
> **【核心假设】** 如果给 item-ID 基线喂入与 GR **等量的冻结内容嵌入**（文本/图像编码器输出的等量特征），那么 GR 相对 ID 模型的 nDCG@10 优势将大幅收窄甚至消失，因为现有对比中 **GR 多拿了内容模态这一份互信息**，优势来自信息预算而非生成式范式。

- 基线：纯 ID 的 SASRec/BERT4Rec vs. 加等量内容特征的同一模型 vs. GR
- 证伪：若 GR 仍显著领先 → 生成式范式优势为真
- 算力：**单卡，最省**；KDD 2026 已收 *From Tokenizer Bias to Backbone Capability* 这类 controlled study，口味对口

---

### 走廊 B：Agent 记忆的可逆性

**B1｜可逆驱逐**
> **【核心假设】** 如果在固定 token 预算下把记忆驱逐从「单向删除」改为「**保留 provenance 存根 + 按需 restore**」，那么相对同预算的单向驱逐基线，**不可逆丢失率将显著下降**，因为当前损失的一部分是**检索失败**而非信息必然损失。

| 项 | 内容 |
|---|---|
| 基线 | Mem0 / A-MEM / 滚动窗口 / 全 transcript |
| 数据集 | LongMemEval（500 题，可本地全跑）、LoCoMo（arXiv:2402.17753） |
| 主指标 | 不可逆丢失率、QA 准确率、预算-精度曲线 AUC |
| 可能证伪 | restore 后召回不回升，或存根开销吃掉全部收益 |
| 算力 | **单卡可行** |

**B2｜隐式冲突的写入-验证协议**
> **【核心假设】** 如果在写入阶段引入「**状态版本图 + 把后续观测对旧记忆的隐含否定显式化为边**」，那么隐式冲突场景下的 stale 答案率将下降，因为失效根因是「**没有显式否定就不触发更新**」。

- 数据集：STALE（arXiv:2605.06527）、LongMemEval 的 knowledge-update 子集
- 主指标：stale 率、更新后 N 轮保持率
- 证伪：LLM 判定器在隐式冲突上接近随机，或误更新率超收益

---

### 走廊 C：GraphRAG 的构建质量

**C1｜查询无关的图构建净化**
> **【核心假设】** 如果**只**在图构建阶段做查询无关的实体消歧 + 高置信边剪枝（**检索端完全不动**），那么相对 LightRAG / 微软 GraphRAG 的默认构建，**多跳 QA 精确率与 token 成本将同时改善**，因为 GraphRAG-Bench 显示失败源在**构建噪声**而非检索器。

- 基线：vanilla RAG、LightRAG、Microsoft GraphRAG
- 数据集：GraphRAG-Bench 四级任务（496★ 开源）+ MuSiQue
- 主指标：EM / LLM-judge 准确率 + token 成本
- 证伪：Level 3–4（全局摘要）剪枝后反降，或增益 < vanilla RAG
- 算力：LLM API 构建 + 小 reranker

---

### 走廊 D（备选）：检索训练的鲁棒性

**D1｜符号扰动一致性正则**
> **【核心假设】** 如果在稠密检索器的对比学习中加入「**同文档符号扰动视图的嵌入一致性正则**」，那么相对于标准 InfoNCE，在 EmoRAG 类符号扰动下 nDCG@10 提升 ≥10 分，因为现有编码器把**格式标记当作强判别特征**，正则强制其聚焦语义内容。

- 证伪：若扰动仅改变 tokenizer 边界 → 增益为零
- 算力：单卡 24G 可做

---

## 5. 最适合当「论文 A」的开源论文

| 排序 | 论文 | 出处 | 开源 | 为什么适合当 A |
|---|---|---|---|---|
| **1** | **MemGen-GR** | KDD 2026 Oral，arXiv:2603.19809 | ✅ Jamesding000/MemGen-GR | 自带记忆/泛化样本划分代码，是 A1/A2 的天然基线；其划分本身用 LOO 协议，正是可攻击点 |
| **2** | **LongMemEval** | ICLR 2025，arXiv:2410.10813 | ✅ MIT 1.1k★ | 500 题可本地全跑，单卡可复现；跨会话 30% 下降已量化，三阶段框架提供明确改进接口 |
| **3** | **GRIP** | KDD 2026，DOI …3817895 | ✅ JiaruiFeng/GRIP | 7B 级可跑，暴露「规模泛化」软肋 |
| 4 | **Mem0** | arXiv:2504.19413 | ✅ 65.7k★ Apache-2.0 | 实现完整、LoCoMo 数字可比；弱点是单向 LLM 抽取写入 |
| 5 | **GraphRAG-Bench** | ICLR 2026，arXiv:2506.05690 | ✅ 496★ | 自带「何时该用图」结论与四级任务，省去重建 benchmark 的算力 |

**不建议**：扩散推荐（8 篇 KDD 2026 均为纯方法增量，直面 *Illusion of Progress* 风险）；FORGE 的 AL-GR（140 亿交互 / 2.5 亿物品，单卡不可行）。

---

## 6. 修正与未核实项

### 6.1 对前序报告的修正（重要）

1. **`topic-landscape-2026.md` §4.2 ④（异常检测 FM selector）应标记为「已关闭」**。ICLR 2026《When Foundation Models are One-Liners》已核实（A 级），其结论是基础模型与一行基线**无显著差异**——即**没有可路由的东西**。前序报告把它当作该方向的 motivation，**属读反**。
2. **前序核查中关于 GraphPrompt 的弱点（Cora IMP=0.0、CiteSeer −5.7、Flickr −21.2）未核实**。arXiv:2505.16903 的真实标题是 *Freeze, Prompt, and Adapt: A Framework for Source-free Unsupervised GNN Prompting*（UGPrompt），**并非**「Unsupervised Prompting for GNNs」；上述数字未在正文核对。引用前必须打开 PDF 复核。
3. **`topic-landscape-2026.md` 第 134 行**的「survivorship 1.2% / look-ahead 26.8%」两个分项数字**查不到**，ICML 2026 那篇 position paper（arXiv:2602.14233，已核实被接收）摘要中只有「无单一 bias 讨论率超 28%」。

### 6.2 本文未核实项

| 条目 | 状态 |
|---|---|
| KDD 2026 论文正文 | ❌ 未打开（ACM DL 403）；核验止于官方页 JSON 的标题/作者/DOI |
| 2.1 节多数 KDD 论文的开源性 | 未逐条核验 |
| *BM25 Wins at Scale*（arXiv:2607.26497） | 真实存在，但**仅预印本、非顶会** |
| 官方 1415 篇 vs 去重 1408 条 | 差 7 条，原因未核实 |
| 第三方趋势分析（LLM 41→131 等） | B 级，非官方口径 |

### 6.3 二手来源纠错

- 武大新闻稿称 AI4Science track「790 篇投稿」——**非官方口径，未核实**。
- 某新闻列出的 "Baldwinian PINNs"——**在官方 1415 篇里查无此文**（全 track 均无），勿引用。

---

## 7. 下一步

1. 从走廊 A / B / C 中选 1 条，把对应「论文 A」读穿（正文 + 代码），**验证其弱点是否真实存在**——这是整个方案唯一的赌注点。
2. 选定的 idea 应新开正式编号（如 `ideas/002-xxx-idea/`）并登记进 `PROGRESS.md`。
3. 目标投稿 track 建议：**Datasets & Benchmarks**（27% 录取率、供给稀缺、CFP 无硬门槛）优于 Research。

---

*相关文档：[领域现状综述](survey-data-mining-2026.md) ｜ [选题地图](topic-landscape-2026.md) ｜ [调研笔记](notes.md) ｜ [目录索引](README.md)*
