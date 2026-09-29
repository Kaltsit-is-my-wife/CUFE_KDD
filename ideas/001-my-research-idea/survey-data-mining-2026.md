# 数据挖掘领域现状综述（2026-09）

> **调研人**：@YuchenLiu ｜ **调研日期**：2026-09-20 ｜ **对应目录**：`ideas/001-my-research-idea/`
> **性质**：文献调研综述，非系统性综述（未做 PRISMA 流程，未做穷尽检索）
> **引用规则**：所有引用均经实际检索核实存在，链接可直接打开验证。无法确证的条目已显式标注「待核实」或不予收录。

---

## 0. 摘要

本综述覆盖数据挖掘领域十个主要方向，时间重心放在 2023–2026 年。

**一个贯穿性结论**：这十个方向在 2024–2026 年几乎**同步进入了一个「祛魅期」**。几乎每个方向都走出了同一条曲线：

> 新范式宣称碾压传统方法 → 基准与评测被系统性证伪 → 结论被迫条件化

具体表现：时序基础模型被在线岭回归和季节朴素法击败；异常检测的 SOTA 深度模型被证明未必优于一行统计基线；因果发现在真实数据上错误预测超过一半的边；语义 ID 路线的生成式推荐出现明确的 scaling 天花板；多模态模型的组合推理能力被证明接近词袋。

**第二个结论**：LLM 正在成为所有方向的**通用接口**，但它只在**语言-语义主导**的任务上形成碾压，在**结构化/数值主导**的任务上（表格、时序、异常检测）至今未取代专用方法。

**第三个结论**：**评测危机是全领域共同的元问题**。数据泄漏、基准缺陷、离线指标与真实效用脱节，在至少六个方向被独立指出。

---

## 1. LLM × 数据挖掘 / 表格基础模型

### 核心问题
表格数据长期由 GBDT（XGBoost/LightGBM）主导，深度模型难以稳定超越；特征工程、标注、清洗高度依赖人工。该方向追问：能否用 LLM 的语义知识与推理能力，替代或增强 tabular pipeline 的「特征构造—标注—推理」三个环节。

### 方法脉络
1. 2023 — **TabLLM**：表格行序列化为自然语言 prompt，做 zero/few-shot 分类，首次系统比较多种序列化方式
2. 2023 — **CAAFE**：以「代码即接口」让 LLM 迭代生成语义特征，验证集提升才保留
3. 2023 — **XTab**：FedAvg 跨表联邦预训练共享 Transformer，解决单表预训练无法泛化
4. 2024 — **TableLlama**：TableInstruct 指令微调开源表格通才模型
5. 2024 — LLM 作为标注器/合成器，形成「生成—评估—利用」三段式框架
6. 2025 — **TabPFN v2**：prior-data fitted network，用 2D attention 做表内 in-context 学习（Nature 正刊）
7. 2025 — 从「LLM 当模块」转向「LLM 当 agent 编排整条数据科学流水线」

### 关键文献

| 标题 | 一作 | 年 | Venue | 链接 |
|---|---|---|---|---|
| TabLLM: Few-shot Classification of Tabular Data with LLMs | Hegselmann | 2023 | AISTATS | arXiv:2210.10723 |
| LLMs for Semi-Automated Data Science (CAAFE) | Hollmann | 2023 | NeurIPS | arXiv:2305.03403 |
| XTab: Cross-table Pretraining for Tabular Transformers | Zhu | 2023 | ICML | arXiv:2305.06090 |
| TableLlama: Open Large Generalist Models for Tables | Zhang | 2024 | NAACL | arXiv:2311.09206 |
| Accurate predictions on small data with a tabular foundation model | Hollmann | 2025 | Nature 637:319–326 | DOI:10.1038/s41586-024-08328-6 |
| LLMs on Tabular Data: Prediction, Generation, Understanding — A Survey | Fang | 2024 | TMLR | arXiv:2402.17944 |
| LLMs for Data Annotation and Synthesis: A Survey | Tan | 2024 | EMNLP | arXiv:2402.13446 |

### 当前瓶颈
序列化后 token 爆炸，长表/多表场景失效；对数值与列语义不敏感；LLM 标注在主观/长尾任务上不如人类标签；输出幻觉与可复现性差；TabPFN 类模型推理成本高（10k 行约 0.2s vs GBDT 0.0002s）且样本规模受限。

### 关注度
持续上升。KDD 2024 有弱监督结构化知识挖掘 tutorial，KDD 2025 出现 RAG 综述，KDD 2026 已设 AI Data Scientist workshop。

### 共识 vs 争议
- **共识**：GBDT 仍是中小规模表格的强 baseline；序列化方式对结果影响巨大；LLM 在极低样本区间确有优势
- **争议**：LLM 能否在标准表格任务上取代 GBDT **尚未定论**；TabPFN 的「foundation model」地位是否成立仍有学者质疑

---

## 2. 向量检索与 RAG

### 核心问题
LLM 参数化知识无法更新、无法溯源、长尾事实易幻觉。核心问题：如何把外部非参数化记忆与生成模型有效耦合，并在检索出错、文档噪声、多跳推理时保持鲁棒。

### 方法脉络
1. 2020 — **DPR**：双塔稠密检索单靠 dense 表示即超越 BM25，奠定 dense retrieval 范式
2. 2020 — **RAG**（Lewis）：DPR + BART 端到端微调，retrieved doc 作为隐变量边缘化，开山之作
3. 2020 — **ColBERT**：late interaction，效果与效率的折中
4. 2023 — **HyDE**：生成假想文档再编码，实现零样本稠密检索
5. 2023–24 — **Self-RAG / CRAG**：反思 token 或轻量评测器做「按需检索」与「检索纠错」
6. 2024 — **GraphRAG / LightRAG**：LLM 抽实体建图 + 社区摘要，解决 corpus 级全局问题
7. 2024 — 向量数据库系统化：把 VDBMS 的查询处理、索引（表/树/图）系统化

### 关键文献

| 标题 | 一作 | 年 | Venue | 链接 |
|---|---|---|---|---|
| Dense Passage Retrieval for Open-Domain QA | Karpukhin | 2020 | EMNLP | aclanthology.org/2020.emnlp-main.550/ |
| Retrieval-Augmented Generation for Knowledge-Intensive NLP | Lewis | 2020 | NeurIPS | arXiv:2005.11401 |
| ColBERT: Contextualized Late Interaction over BERT | Khattab | 2020 | SIGIR | DOI:10.1145/3397271.3401075 |
| Generalization through Memorization (kNN-LM) | Khandelwal | 2020 | ICLR | arXiv:1911.00172 |
| Precise Zero-Shot Dense Retrieval without Relevance Labels (HyDE) | Gao | 2023 | ACL | arXiv:2212.10496 |
| Self-RAG: Learning to Retrieve, Generate, and Critique | Asai | 2023 | NeurIPS | arXiv:2310.11511 |
| From Local to Global: A GraphRAG Approach | Edge | 2024 | arXiv | arXiv:2404.16130 |
| Benchmarking LLMs in RAG (RGB) | Chen | 2024 | AAAI | arXiv:2309.01431 |
| Survey of Vector Database Management Systems | Pan | 2024 | VLDB Journal | DOI:10.1007/s00778-024-00864-x |

### 当前瓶颈
Multi-hop 与跨文档集成仍弱（RGB 显示 LLM 在 negative rejection 与 counterfactual 上严重不足）；对检索噪声的鲁棒性随噪声比例上升快速退化；GraphRAG 建图与社区摘要成本高、缺公认评测；增量更新与索引一致性未解。

### 共识 vs 争议
- **共识**：dense + sparse 混合检索优于单一；自适应/按需检索优于固定 k；单纯堆 context 长度不能解决 grounding
- **争议**：Graph 结构是否普适优于纯向量（LightRAG 质疑 GraphRAG 成本收益比）；RAG 能否真正消除幻觉；端到端可微检索 vs 解耦 pipeline 的路线之争

---

## 3. 图挖掘与图神经网络

### 核心问题
在非欧、稀疏、异质图上学习可迁移表征。三层子问题：(a) 消息传递的**表达能力天花板**（1-WL 界限）；(b) **深度与长程依赖的两难**（oversmoothing 与 oversquashing 互斥）；(c) 跨图跨域的**泛化与规模化**。

### 方法脉络
1. 2017–19 — GCN/GAT/GraphSAGE 确立消息传递范式；Morris 等用 1-WL 刻画表达力上限
2. 2019–21 — 图 Transformer（Graphormer）用全局注意力绕开局部瓶颈，但复杂度 O(N²)
3. 2022 — **GraphGPS**：局部 MPNN + 全局注意力 + 位置/结构编码，复杂度降回线性，成为事实标准骨架
4. 2022–24 — **图重连（rewiring）**成为主流：曲率、有效电阻、虚拟节点
5. 2023–25 — **图基础模型（GFM）**：从「一图一训」转向预训练-微调/零样本
6. 2024–25 — GNN 与 LLM 融合，GraphGPT 用图指令微调把图结构对齐到语言空间

### 关键文献

| 标题 | 一作 | 年 | Venue | 链接 |
|---|---|---|---|---|
| Weisfeiler and Leman Go Neural: Higher-Order GNNs | Morris | 2019 | AAAI | arXiv:1810.02244 |
| Recipe for a General, Powerful, Scalable Graph Transformer (GraphGPS) | Rampášek | 2022 | NeurIPS | arXiv:2205.12454 |
| The Heterophilic Graph Learning Handbook | Luan | 2024 | arXiv 综述 | arXiv:2407.09618 |
| Rewiring Techniques to Mitigate Oversquashing/Oversmoothing: Survey | Attali | 2024 | arXiv 综述 | arXiv:2411.17429 |
| Over-squashing in GNNs: A Comprehensive Survey | Akansha | 2025 | Neurocomputing 642 | DOI:10.1016/j.neucom.2025.130389 |
| Graph Foundation Models: Concepts, Opportunities and Challenges | Liu | 2025 | IEEE TPAMI | arXiv:2310.11829 |
| Graph Foundation Models: A Comprehensive Survey | Wang | 2025 | arXiv / KDD 2025 | arXiv:2505.15116 |
| GraphGPT: Graph Instruction Tuning for LLMs | Tang | 2024 | SIGIR | arXiv:2310.13023 |

### 当前瓶颈
oversmoothing / oversquashing 的权衡**无解**（重连缓解一个会加剧另一个）；**评测与理论脱节**——Lutzeyer 等 2025 指出 oversmoothing 在图级任务上未必有害，社区缺乏区分「oversmoothing」与「无效感受野」的指标；GFM 尚无统一的跨域结构对齐方案。

### 关注度
经典 GNN 架构创新在 KDD/WWW 明显退潮；增量集中在三个出口：异质/异配图、图基础模型与 scaling law、Graph+LLM。纯理论表达力论文转向 ICML/NeurIPS 理论 track。

### 共识 vs 争议
- **共识**：1-WL 是 MPNN 的表达力上界；图重连可缓解长程信息瓶颈；位置/结构编码对大图模型必要
- **争议**：oversmoothing 是否真的损害实际性能；GFM 应基于 GNN 还是 LLM 为主干；k-WL 类高阶模型的收益是否值得组合爆炸的代价

---

## 4. 推荐系统

### 核心问题
从稀疏隐式反馈中刻画用户偏好。近年的根本转向是：**推荐能否被统一为序列生成任务**，从而复用 LLM 的 scaling law。

### 方法脉络
1. 2016–18 — GRU4Rec 引入 RNN 会话建模；SASRec 用因果自注意力取代 RNN
2. 2019 — BERT4Rec 引入双向编码 + Cloze 掩码目标
3. 2020 — **LightGCN** 证明特征变换与非线性激活对协同过滤无益，只保留邻域聚合
4. 2022 — **P5** 提出「统一文本到文本」的推荐范式，开启 LLM4Rec
5. 2023 — **TIGER** 用 RQ-VAE 生成 **Semantic ID**，把检索变成自回归解码
6. 2024 — **HSTU** 把推荐重构成生成式推荐，报告工业级 scaling law
7. 2025 — **OneRec** 在快手落地端到端生成式推荐，替代多级级联架构

### 关键文献

| 标题 | 一作 | 年 | Venue | 链接 |
|---|---|---|---|---|
| Session-based Recommendations with RNNs (GRU4Rec) | Hidasi | 2016 | ICLR | arXiv:1511.06939 |
| Self-Attentive Sequential Recommendation (SASRec) | Kang | 2018 | ICDM | arXiv:1808.09781 |
| BERT4Rec | Sun | 2019 | CIKM | arXiv:1904.06690 |
| LightGCN | He | 2020 | SIGIR | arXiv:2002.02126 |
| GNNs in Recommender Systems: A Survey | Wu | 2022 | ACM CSUR 55(5) | DOI:10.1145/3535101 |
| Recommendation as Language Processing (P5) | Geng | 2022 | RecSys | arXiv:2203.13366 |
| A Survey on LLMs for Recommendation | Wu | 2023 | arXiv 综述 | arXiv:2305.19860 |
| Recommender Systems with Generative Retrieval (TIGER) | Rajput | 2023 | NeurIPS | arXiv:2305.05065 |
| Actions Speak Louder than Words (HSTU) | Zhai | 2024 | ICML | arXiv:2402.17152 |
| OneRec Technical Report | Deng | 2025 | arXiv 技报 | arXiv:2506.13695 |
| **Understanding Generative Recommendation with Semantic IDs from a Model-scaling View** | Liu | 2026 | **KDD 2026** | arXiv:2509.25522 ／ DOI:10.1145/3770855.3817976 |

### 当前瓶颈（2026 年最新争议焦点）
**Semantic ID 的语义容量天花板**。KDD 2026 那篇论文实测表明：SID-based 生成式推荐在 encoder、tokenizer、RS **三个方向均快速饱和**——modality encoder 扩大无增益；tokenizer 在约 3 codebooks × 256 处最优；RS 超过约 13M 参数即饱和。作者定位根因是 **SID 本身的信息容量限制了 LLM 知识向下游推荐器的迁移**。作为替代，**LLM-as-RS**（直接以 LLM 作推荐器）展现出更优的 scaling 性质，最高领先 20% 且未见饱和；该文同时挑战了「LLM 学不好协同过滤信号」的流行观点。

> ⚠️ **注意**：该文作者本人声明，这**不等于** LLM-as-RS 全面更优——其计算成本显著更高。这是「scaling 性质」的对比，不是「性价比」的对比。

其他瓶颈：Semantic ID 工程问题（ID 碰撞、语义扁平化、解码合法性约束）；工业推理延迟约束（OneRec-V2 需砍掉 94% 算力才可扩展到 8B）。

### 共识 vs 争议
- **共识**：生成式/LLM 范式是明确方向；Semantic ID 是连接物品空间与语言空间的有效中介；scaling law 在推荐上成立（HSTU、OneRec 独立验证）
- **争议**：**SID-based 还是 LLM-as-RS** 是核心分歧；LLM 能否建模协同过滤信号；端到端生成式是否终将取代多级级联

---

## 5. 时序与序列挖掘

### 核心问题
从有序、连续、强分布漂移的数值序列中建模时间依赖与跨变量相关。近年重心转向「能否用一个大规模预训练模型（TSFM）零样本覆盖跨域任务」。

### 方法脉络
1. 统计基线（ARIMA/ETS）：单序列拟合，无法跨序列迁移
2. **DeepAR** 等 RNN + 概率输出：首次大规模跨序列训练，但每数据集一模型
3. Transformer 长序列（Informer→Autoformer→FEDformer）：稀疏注意力降复杂度
4. **反证时刻**：DLinear 用一条线性层证明前述复杂架构的先验可能过强
5. Patch + 通道独立（**PatchTST**）与倒置变量注意力（**iTransformer**）：确立当前监督式预测两大主流范式
6. 通用 TSFM（**Chronos / TimesFM / Moirai / MOMENT**）：大规模预训练 + 零样本预测
7. 评测与质疑期（2025–2026）：基准建设与「零样本不如朴素基线」的证伪

### 关键文献

| 标题 | 一作 | 年 | Venue | 链接 |
|---|---|---|---|---|
| Are Transformers Effective for Time Series Forecasting? (DLinear) | Zeng | 2023 | AAAI | DOI:10.1609/aaai.v37i9.26317 |
| A Time Series is Worth 64 Words (PatchTST) | Nie | 2023 | ICLR | arXiv:2211.14730 |
| iTransformer | Liu | 2024 | ICLR Spotlight | arXiv:2310.06625 |
| TimesNet | Wu | 2023 | ICLR | arXiv:2210.02186 |
| Chronos: Learning the Language of Time Series | Ansari | 2024 | TMLR | arXiv:2403.07815 |
| A decoder-only foundation model for TS forecasting (TimesFM) | Das | 2024 | ICML | arXiv:2310.10688 |
| Unified Training of Universal TS Forecasting Transformers (Moirai) | Woo | 2024 | ICML | arXiv:2402.02592 |
| MOMENT: A Family of Open Time-series Foundation Models | Goswami | 2024 | ICML | PMLR v235 |
| TS2Vec: Towards Universal Representation of Time Series | Yue | 2022 | AAAI | DOI:10.1609/aaai.v36i8.20881 |
| Foundation Models for Time Series: A Survey | Kottapalli | 2025 | arXiv 综述 | arXiv:2504.04011 |
| GIFT-Eval: A Benchmark for General TS Forecasting Model Evaluation | Aksu | 2024 | NeurIPS'24 Workshop | arXiv:2410.10393 |

### 当前瓶颈
**预训练数据泄漏与规模不透明**——GIFT-Eval 被迫引入 non-leaking 预训练集；多变量与协变量能力弱（多数 TSFM 本质单变量，Chronos-2 才用 group attention 补齐）；长 horizon 上概率校准普遍退化（CRPS 退化）；评测不可比。

### 共识 vs 争议
- **共识**：patching + 通道独立/倒置注意力是监督式预测的强基线；朴素线性模型不可忽视；零样本 TSFM 在训练分布内数据上确实有效
- **争议（核心）：「零样本预测能否真超越传统方法」——现有证据偏向否定或高度条件化**
  - *Performance of Zero-Shot TSFMs on Cloud Data*（arXiv:2502.12944）发现知名 TSFM 被**在线岭回归与季节朴素法一致击败**；最佳模型 VisionTS 只是因为「输出近乎等于季节朴素法」
  - *How Foundational are Foundation Models for TS Forecasting?*（NeurIPS 2025）指出零样本能力**强绑定预训练领域**，微调后不显著优于小专用模型
  - 反方证据：Chronos-2 自称在 GIFT-Eval 预训练模型榜第一——**但为自报结果，需第三方复现**

---

## 6. 异常检测

### 核心问题
在标签稀缺、异常极罕见且形态未知的前提下，从高维、多变量、含噪、非平稳数据中定位点/段/图级异常。

### 方法脉络
1. 2018 — **Deep SVDD**：把单类分类目标做进深度网络，确立「为异常检测而训练」的范式
2. 2019 — **OmniAnomaly**（KDD）：随机潜变量 + normalizing flow + POT 阈值，奠定多变量重构标准流程
3. 2022 — Transformer 化：Anomaly Transformer 用关联差异、TranAD 用自条件注意力建模长程依赖
4. 2023–24 — **基准证伪**：Wu & Keogh 揭示数据集与度量缺陷；TSB-AD 改以 VUS-PR 为主
5. 2024 — 图异常检测体系化：GNN backbone + 代理任务 + 异常度量三分法
6. 2024–25 — LLM/基础模型介入：LLM 作 encoder / detector / interpreter

### 关键文献

| 标题 | 一作 | 年 | Venue | 链接 |
|---|---|---|---|---|
| Deep One-Class Classification (Deep SVDD) | Ruff | 2018 | ICML | icml.cc/virtual/2018/poster/2483 |
| Robust AD for MTS via Stochastic RNN (OmniAnomaly) | Su | 2019 | KDD | DOI:10.1145/3292500.3330672 |
| Anomaly Transformer | Xu | 2022 | ICLR Spotlight | arXiv:2110.02642 |
| TranAD | Tuli | 2022 | VLDB | DOI:10.14778/3514061.3514067 |
| Current TS AD Benchmarks are Flawed… | Wu / Keogh | 2023 | IEEE TKDE | arXiv:2009.13807 |
| The Elephant in the Room: Towards A Reliable TS AD Benchmark (TSB-AD) | Liu / Paparrizos | 2024 | NeurIPS D&B | github.com/TheDatumOrg/TSB-AD |
| Deep Graph Anomaly Detection: A Survey | Qiao | 2024 | arXiv（TKDE 接收） | arXiv:2409.09957 |
| AD in Dynamic Graphs: A Comprehensive Survey | Ekle | 2024 | arXiv（TKDD 接收） | arXiv:2406.00134 |
| LLMs for Anomaly and OOD Detection: A Survey | Xu / Ding | 2025 | Findings of NAACL | aclanthology.org/2025.findings-naacl.333/ |
| Can LLMs Understand Time Series Anomalies? | Zhou / Yu | 2025 | ICLR | arXiv:2410.05440 |
| Foundation Models for Anomaly Detection: Vision and Challenges | Ren | 2025 | arXiv ／ AI Magazine 46(4) | arXiv:2502.06911 |

### 当前瓶颈
**评测本身不可靠**——Wu & Keogh 指出 Yahoo/NASA/OMNI 等基准存在平凡性、密度失真、错标；**深度模型未必优于简单方法**——TSB-AD 结论直接挑战「神经网络架构优越性」的传统认知；**LLM 路线证据偏弱**——Zhou & Yu（ICLR'25）发现 LLM 理解时序**图像化优于文本化**、CoT 反而降效、只能识别 trivial 异常，对细微真实异常**无证据**。

### 共识 vs 争议
- **共识**：旧基准（SMD/SMAP/MSL/Yahoo）存在严重缺陷，须以 VUS-PR 等度量评估；多变量场景深度学习有价值，单变量点异常上统计方法已足够
- **争议**：Transformer/深度架构是否真优于简单统计方法（TSB-AD 给出**否定倾向**）；LLM 是否具备真实时序异常理解能力（ICLR'25 倾向怀疑）

---

## 7. 因果推断与数据挖掘

### 核心问题
从观测数据中区分「相关」与「因果」。三问：(a) 因果结构能否被恢复（causal discovery）；(b) 干预/反事实效果能否被量化（CATE）；(c) 高维非结构数据背后的因果潜变量能否被学出来（CRL）。

### 方法脉络
1. 约束/评分搜索时代：PC、GES 基于条件独立性检验或评分搜索
2. 2018 — **NOTEARS**：用 $h(W)=\mathrm{tr}(e^{W\circ W})-d$ 把无环约束变成光滑等式约束，把组合搜索变为连续优化
3. 2020–21 — 潜在混杂与 CRL：CausalVAE 将 SCM 植入 VAE 支持 do-operation；Schölkopf 等提出 CRL 纲领
4. 2021 — **DiBS**：在潜图空间做变分推断，可处理非线性依赖并给出后验不确定性
5. 2019–21 — 元学习器成熟：X-learner、R-learner、causal forest 形成 CATE 标准工具箱
6. 2024–25 — LLM 融合与**基准反思**

### 关键文献

| 标题 | 一作 | 年 | Venue | 链接 |
|---|---|---|---|---|
| DAGs with NO TEARS | Zheng | 2018 | NeurIPS | arXiv:1803.01422 |
| Estimation and Inference of HTE using Random Forests | Wager & Athey | 2018 | JASA | arXiv:1510.04342 |
| Metalearners for estimating heterogeneous treatment effects (X-learner) | Künzel | 2019 | PNAS | DOI:10.1073/pnas.1804597116 |
| Quasi-oracle estimation of heterogeneous treatment effects (R-learner) | Nie & Wager | 2021 | Biometrika | DOI:10.1093/biomet/asaa076 |
| Toward Causal Representation Learning | Schölkopf | 2021 | Proc. IEEE | DOI:10.1109/JPROC.2021.3058954 |
| DiBS: Differentiable Bayesian Structure Learning | Lorch | 2021 | NeurIPS | arXiv:2105.11839 |
| The Landscape of Causal Discovery Data | Brouillard | 2025 | CLeaR | arXiv:2412.01953 |
| Since Faithfulness Fails: Performance Limits of Neural Causal Discovery | — | 2025 | ICML | arXiv:2502.16056 |
| Causal Inference in Recommender Systems: Survey | Gao | 2024 | ACM TOIS | DOI:10.1145/3639048 |

### 当前瓶颈
**因果发现在真实数据上准确率极低**——ICML 2025 基准显示所测神经方法（DCDI/SDCD/DiBS/BayesDAG）**错误预测超过一半的边**，且增加样本量并不能稳定改善；**可信 ground truth 稀缺**——真实数据集几乎从不带已知因果图，评估严重依赖合成数据；假设不可检验（faithfulness、因果充分性、无混杂在真实数据中普遍被违反）。

### 共识 vs 争议
- **共识**：无额外假设的因果发现是 ill-posed 的；合成基准会高估方法性能；元学习器 + 正交化 + cross-fitting 是 CATE 标准做法
- **争议（最尖锐）**：**因果发现在真实数据上是否可靠**。领域主流仍以合成 benchmark 报告 SOTA，但 2024–2025 多篇工作（ECML/ICML/CLeaR）直接指出这些结论**不可迁移到真实场景**，要求范式转变；尚未形成替代评估标准

---

## 8. 隐私保护与联邦学习

### 核心问题
在不集中原始数据的前提下完成训练与推断，并给出可量化的隐私保证。

### 方法脉络
1. 2016–17 — **FedAvg**：本地 SGD + 参数平均，通信轮数降 10–100×，成为 FL 基石
2. 2016 — **DP-SGD**：逐样本梯度裁剪 + 高斯噪声 + 隐私会计师
3. 2017 — **安全聚合**：使服务器只能看到聚合结果，成为 FL 隐私底线组件
4. 2019 — **Deep Leakage from Gradients**：表明「只传梯度」并不安全，可从梯度反演出像素级原图
5. 2023–25 — 联邦大模型（FedLLM）：PEFT/LoRA + FL 成为主流路线
6. 2024–25 — **审计与反思**：SoK 类工作系统质疑 MIA 评估有效性与梯度反演的严重性

### 关键文献

| 标题 | 一作 | 年 | Venue | 链接 |
|---|---|---|---|---|
| Communication-Efficient Learning from Decentralized Data (FedAvg) | McMahan | 2017 | AISTATS | arXiv:1602.05629 |
| Deep Learning with Differential Privacy (DP-SGD) | Abadi | 2016 | ACM CCS | DOI:10.1145/2976749.2978318 |
| Practical Secure Aggregation for Privacy-Preserving ML | Bonawitz | 2017 | ACM CCS | DOI:10.1145/3133956.3133982 |
| Deep Leakage from Gradients | Zhu, Liu & Han | 2019 | NeurIPS | arXiv:1906.08935 |
| SoK: Membership Inference Attacks on LLMs are Rushing Nowhere | Meeus | 2025 | SaTML（最佳论文） | arXiv:2406.17975 |
| SoK: On Gradient Leakage in Federated Learning | — | 2024 | arXiv | arXiv:2404.05403 |
| A Survey on Federated Fine-tuning of LLMs | Wu | 2025 | arXiv | arXiv:2503.12016 |
| Recent Advances of DP in Centralized Deep Learning: A Systematic Survey | Demelius | 2025 | ACM CSUR | DOI:10.1145/3712000 |

### 当前瓶颈
隐私—效用—公平三角（DP 的性能退化在弱势子群上不成比例）；Non-IID 漂移（真实异构下 FL 精度落后集中式 9–15 个百分点，且加再多通信也补不回来）；LLM 场景的通信/算力瓶颈；**评估方法学缺陷**——多数 LLM MIA 在 post-hoc 数据集上评测，成员/非成员存在分布偏移，报告的 AUC 可能被高估。

### 共识 vs 争议
- **共识**：单独 FL 不提供 DP 级别的隐私保证，必须叠加安全聚合/DP；梯度共享可泄漏数据；安全聚合是工业部署必要组件
- **争议一：FL 相对集中式训练的收益是否被高估 —— 倾向「是」**。2025 年多篇医疗、IoT、金融实证显示 FL 常弱于甚至不优于本地训练，当单一机构数据量足够时「几乎无增益」；FL 的价值主要在于**合规与跨机构数据不可汇集**，而非精度
- **争议二**：梯度反演的真实威胁程度——SoK 认为远比宣传中脆弱，但线性层泄漏攻击仍显示可扩展，双方未收敛
- **争议三**：成员推断攻击的有效性——SaTML 2025 最佳论文直接质疑大量 LLM MIA 结果的分布偏移问题，动摇了一批既有结论

---

## 9. 多模态数据挖掘

### 核心问题
在同一语义空间中表示并对齐异质模态，使模型能跨模态检索、推理与生成。根本矛盾是**模态鸿沟**：对比学习只能对齐「整体相似度」，难以对齐组合结构（对象-属性-关系）。

### 方法脉络
1. 2019 — **MMGCN**：用户-物品二部图 + 多模态特征图卷积，开创多模态推荐
2. 2021 — **CLIP**：4 亿图文对 + 对称对比损失，零样本迁移，成为通用视觉-语言骨干
3. 2022 — **Flamingo**：冻结视觉编码器 + 门控交叉注意力，实现任意交错图文序列的 few-shot 学习
4. 2023 — **LLaVA / BLIP-2**：轻量投影器把视觉特征接入 LLM，确立「视觉编码器 + 适配器 + LLM」主流架构
5. 2022–23 — **Winoground / ARO**：暴露 CLIP 系模型近似「词袋匹配」
6. 2024–25 — **MMVP** 指出瓶颈在视觉编码器而非语言侧

### 关键文献

| 标题 | 一作 | 年 | Venue | 链接 |
|---|---|---|---|---|
| Learning Transferable Visual Models From Natural Language Supervision (CLIP) | Radford | 2021 | ICML | arXiv:2103.00020 |
| Flamingo: a Visual Language Model for Few-Shot Learning | Alayrac | 2022 | NeurIPS | arXiv:2204.14198 |
| Visual Instruction Tuning (LLaVA) | Liu | 2023 | NeurIPS Oral | arXiv:2304.08485 |
| Winoground: Probing VLMs for Visio-Linguistic Compositionality | Thrush | 2022 | CVPR | arXiv:2204.03162 |
| When and Why VLMs Behave like Bags-of-Words (ARO) | Yuksekgonul | 2023 | ICLR Oral | arXiv:2210.01936 |
| Eyes Wide Shut? Visual Shortcomings of Multimodal LLMs (MMVP) | Tong | 2024 | CVPR | arXiv:2401.06209 |
| Unveiling the Compositional Ability Gap in Vision-Language Reasoning | Li | 2025 | NeurIPS | arXiv:2505.19406 |
| Does Multimodality Improve Recommender Systems as Expected? | Zhou | 2025 | arXiv | arXiv:2508.05377 |

> BLIP-2 的 arXiv 编号本次未核实，故只记录 ICML 2023 官方页，不给出编号。

### 当前瓶颈
**视觉编码器瓶颈**——MMVP 证明扩大 CLIP 规模只能改善 9 类视觉模式中的 2 类，ImageNet 零样本精度与细粒度视觉能力**不相关**；组合推理与绑定失败（对象/属性/关系扰动下接近随机）；幻觉源于语言先验过强、视觉 grounding 弱；**评测不可靠**——MMMU 类基准存在选项捷径、无图可答、约 2% 标注噪声。

### 共识 vs 争议
- **共识**：对比预训练是有效通用对齐范式；「视觉编码器 + 适配器 + LLM」是主流可扩展架构；CLIP 系组合性不足、存在模态鸿沟与幻觉
- **争议一：MLLM 是否具备真正的组合推理？** 一方认为失败源于视觉编码器叠加与融合偏差，属可修复的表征问题；另一方认为模型只是在高频模式上做统计匹配，是**机制性缺陷**
- **争议二：多模态对齐评测是否可靠？** 多数基准可用语言先验或无图捷径刷分；尚无公认的抗捷径评测协议
- **争议三：多模态一定提升下游效果？** 已有批判性工作表明，**将多模态嵌入替换为噪声有时几乎不影响精度**，说明部分收益来自架构伪影而非真正的多模态学习

---

## 10. KDD 会议与 KDD Cup 趋势

### 会议概况

| 年份 | 地点 | Track 设置 | 备注 |
|---|---|---|---|
| KDD 2023 | Long Beach | Research + ADS | 投稿 1,416 / 接收 313（22.1%）¹ |
| KDD 2024 | Barcelona | Research + ADS | 合计投稿 2,784 / 接收 562（20.2%）¹ |
| KDD 2025 | Toronto | Research + ADS + **Datasets & Benchmarks** | 三轨制 ² |
| KDD 2026 | 济州岛 | 三轨 + **AI for Sciences Track** + Blue Sky Ideas | 双轮投稿 ² |

¹ 录用率数据来自第三方统计（CS Conf Stats 等），非官方发布，仅供参考
² 会议日期、场馆、track 设置来自 kdd.org 官方页面

**趋势判断**：投稿量持续上升、录用率下降；新增轨反映对**可复现评测**与 **AI4Science** 的倾斜；LLM/Agent、多模态、RAG、可信 AI 为新增热点，传统图/推荐/时序仍是最大基本盘。

> ⚠️ KDD 2025 录用论文高频词统计（Learning/Graph 各 119 次、Model 87 次、Recommendation 52 次等）来自社区二手分析，非官方数据。

### KDD Cup 赛题演进

| 年份 | 赛题 | 主题 | 关键信息 |
|---|---|---|---|
| 2023 | Amazon KDD Cup '23 | 会话式推荐 + 多语种商品标题生成 | 6 语种、3 任务；NVIDIA-Merlin 包揽三项冠军 ¹ |
| 2024 | Meta CRAG | 基于网络的 RAG 问答 | 3 任务、4,409 QA、5 大领域；北大 db3 队三项第一 ¹ |
| 2025 | Meta CRAG-MM | 多模态、多轮 RAG（Ray-Ban Meta 自视角图像） | 3 任务；北大 db3 队蝉联总冠军 ¹ |
| 2026 | **Tencent UNI-REC** + **HKUST Data Agents** | 统一推荐建模 / 数据智能体 | 见下 ² |

¹ 夺冠信息来自主办方与参赛方报道（NVIDIA 官方博客、北大官网、AIcrowd 官方页）
² 来自 kdd2026.kdd.org 官方 KDD Cup 提案页面

**KDD Cup 2026 两个赛道**（官方确认）：

- **Tencent UNI-REC Challenge**：大规模推荐中的统一序列建模与特征交叉。任务是目标广告**点击后转化率（pCVR）预测**，需联合建模多域用户行为序列与非序列多字段特征。指标 ROC-AUC，且带**硬性推理延迟约束**——超时的提交直接判无效，因此架构效率本身就是评分维度。数据规模约 1.2 亿训练事件（二轮）。
- **HKUST Data Agents Challenge**：构建自主 AI Agent，在异构数据源（数据库/CSV/JSON/PDF/图表）上分解复杂分析问题、多步推理并给出答案。分 Leaderboard 与 Creative 两个 subtrack。基准为 DataAgent-Bench，平台 dataagent.top。

> ⚠️ 两赛道的奖金数额在不同来源间存在冲突（如 Data Agents 赛道有 $30,000 与 ¥120,000 两种说法），未采信具体数字。

**趋势解读**：赛题从推荐系统（2023）→ 文本 RAG/幻觉抑制（2024）→ 多模态多轮 RAG（2025）→ **数据智能体 + 统一推荐建模（2026）**。评价重心从准确率转向**可信度/抗幻觉**，并日益强调 **Agent 与多模态能力**。

---

## 11. 横向综合：三条贯穿性主线

### 主线一：全领域同步进入「祛魅期」

把十个方向的「争议」栏排在一起，会发现同一条曲线：

| 方向 | 新范式宣称 | 被证伪/修正为 |
|---|---|---|
| 时序 | TSFM 零样本预测通用 | 被在线岭回归与季节朴素法一致击败 |
| 异常检测 | 深度架构优于传统方法 | TSB-AD 挑战「架构优越性」认知 |
| 因果推断 | 神经方法恢复因果结构 | 真实数据上错误预测超过一半的边 |
| 推荐 | Semantic ID 生成式推荐可 scaling | 三个组件全部快速饱和 |
| 多模态 | MLLM 具备组合推理 | ARO/Winoground/MMVP 上系统性失败 |
| 隐私 | 联邦学习优于集中式 | 单一机构数据量足够时几乎无增益 |
| 表格 | LLM 将取代 GBDT | 至今未定论，GBDT 仍是强基线 |

**这不是巧合**。共同机制是：**合成/公开基准与真实场景的系统性偏差**。当基准本身有缺陷（数据泄漏、分布偏移、平凡解可刷分）时，方法在基准上的增益无法迁移。

**对团队的实践含义**：任何「新方法提升 X%」的结论，第一优先级的验证不是复现，而是**质疑基准**——检查是否有泄漏、是否有平凡基线、指标是否与业务目标对齐。

### 主线二：LLM 是通用接口，但不是通用解法

LLM 在**语言-语义主导**的任务上形成碾压（RAG、标注、多模态理解、推荐中的语义建模）；在**结构化/数值主导**的任务上至今未取代专用方法（表格 GBDT、时序简单基线、异常检测统计方法）。

这个边界正在移动，但移动速度比 2023–2024 年的预期**慢得多**。

### 主线三：从「模型创新」转向「系统与 Agent」

KDD 2026 增设 AI for Sciences track、KDD Cup 2026 一个赛道直接考数据处理 Agent、各方向都在提 "X Agents"——**领域的重心正从「设计一个更好的模型」转向「编排一条更可靠的流水线」**。

这也意味着：**评测与可靠性研究的机会窗口正在打开**。当所有人都发现基准不可信时，「如何可信地评测」本身就是高价值的贡献。

---

## 12. 可能的切入点（供团队讨论，非结论）

基于以上综合，几个可能成立的方向：

1. **评测与基准方向**：主线一揭示了全领域的基准危机。**金融/经济领域的数据挖掘基准是否也存在同类缺陷？** 中央财经大学的背景在这个问题上可能是差异化优势——公开的金融数据集（如信用评分、欺诈检测）在数据泄漏与时间切分上的问题可能比 CV/NLP 领域更严重。

2. **KDD Cup 2026 参赛**：UNI-REC 赛道（pCVR 预测 + 延迟约束）与团队的推荐/表格数据背景契合；Data Agents 赛道与当前 Agent 主线契合。两者都是有明确评测标准的落地入口。

3. **「LLM 在结构化数据上的边界」**：表格、时序、异常检测三个方向共享同一个未解问题。系统性地刻画「在什么条件下 LLM 能/不能取代专用方法」是一个横跨三个方向、且当前缺乏统一答案的题目。

4. **因果 × 推荐的交叉**：因果推断在真实数据上不可靠，而推荐系统恰恰是少数有**干预数据**（A/B 测试）的场景。这个交叉点可能绕开因果发现的核心困境——因为可以拿到真实干预而非依赖观测数据。

---

## 13. 方法论说明与局限

### 本综述怎么做的

1. **范围界定**：确立 10 个方向与 2023–2026 时间窗口
2. **并行检索**：6 个独立检索任务分别覆盖各方向，检索工具为 WebSearch / WebFetch
3. **来源核验**：对每篇文献核验标题、作者、年份、venue、可访问链接；标记存疑项
4. **交叉综合**：横向比对各方向的共识与争议，提炼贯穿性主线
5. **显式标注**：所有无法确证的条目显式标注，不予收录或以「待核实」呈现

### 明确的局限

- **非系统性综述**：未做 PRISMA 流程，未穷尽数据库，未做双人独立筛选。本综述适合作为**方向感与选题参考**，不适合作为引用依据
- **检索偏差**：以 WebSearch 为主，覆盖度受搜索引擎索引限制；领域内最新（2026 年下半年）的工作可能有遗漏
- **二手数据**：KDD 录用率、投稿量、高频词统计来自第三方，非官方发布；此类数据仅供趋势参考
- **定性判断**：各方向的「关注度变化」部分包含定性推断，未做严格的论文计数统计
- **语言偏差**：以英文文献为主，可能低估中文社区的工作

### 标注为「待核实」而未正式引用的条目

| 条目 | 状态 |
|---|---|
| ICML 2026 *Foundations without Fundamentals: Zero-Shot Blind Spots in TS FMs* | 仅见于会议 virtual 页/第三方笔记，未见正式 proceedings |
| ICLR 2026 *When Foundation Models Are One-Liners* | 同上 |
| BLIP-2 的 arXiv 编号 | 未核实，仅保留 ICML 2023 官方页 |
| KDD 2026 各赛道奖金数额 | 来源冲突，未采信具体数字 |
| KDD 2025 / 2026 录用率与投稿量 | 第三方统计，非官方发布 |

---

## 14. AI 使用声明

本综述的文献检索、来源核验与初稿撰写过程中使用了 AI 辅助研究工具（Claude Code + deep-research 工作流）。所有引用均经过显式检索核验，核验状态在第 13 节中说明。文中判断与综合观点由 AI 生成，**建议团队在将其作为决策依据前进行人工复核**，尤其是第 12 节的方向建议部分。

---

*本文件是 `ideas/001-my-research-idea/` 调研累积的第一篇。相关笔记见 [`notes.md`](notes.md)，索引见 [`README.md`](README.md)。*
