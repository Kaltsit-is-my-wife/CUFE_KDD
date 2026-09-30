# 三条 idea 走廊的领域调研

> **调研人**：@YuchenLiu ｜ **日期**：2026-09-21 ｜ **对应目录**：`ideas/001-my-research-idea/`
> **性质**：对 [`kdd-ai-survey-2026.md`](kdd-ai-survey-2026.md) 提出的三条 idea 走廊做领域深挖，判断哪条真能落地
> **核验状态**：见第 6 节。大量 2026 年 arXiv 编号仅经摘要命中，未逐一打开正文

---

## 0. 判决摘要（先看这个）

| 走廊 | 判决 | 关键依据 |
|---|---|---|
| **A. 生成式推荐的 SID × 时序泄漏** | ✅ **可选，首选** | 具体自变量「tokenizer 的训练数据范围」**从未被隔离实验过**；实验成本最低 |
| **B. Agent 记忆的驱逐与可逆性** | ❌ **已塌，勿正面对撞** | 2026-06~09 已密集出现 EMBER / Reclaim / CrystalMem，实质占位 |
| **C. GraphRAG 的图构建质量** | ⚠️ **可选，但缝窄且有强对手** | XMU 团队（GraphRAG-Bench + MemGraphRAG 同批人）是直接威胁；LLM API 成本是硬门槛 |

**一句话**：走廊 A 的缝最真实、成本最低、但抢发风险最高（窗口 3–6 个月）；走廊 B 建议放弃或彻底改切口；走廊 C 可做但要做好被 XMU 抢先的心理准备。

---

## 1. 走廊 A：生成式推荐（SID）× 时序泄漏

### 1.1 领域现状：生成式推荐社区至今无人改过切分协议

| 事实 | 数据 | 核验 |
|---|---|---|
| LOO 是绝对主流 | 75 篇（RecSys / SIGIR / CIKM 2022–24）中 **77.3% 用 LOO 类切分**，仅 6.7% 用全局时序切分 | B |
| 顶会仍在用 | RecSys 2024 **7/9** 篇全长序列推荐论文用 temporal LOO | B |
| 泄漏代价（已确立） | 纠正后 nDCG@10 跌 **21.7–73.4%**，**7/8 组数据集×指标的最优模型换位**，模型可移动 4–5 名 | A（代码仓已核） |
| **生成式推荐是否例外** | **否**。TIGER / GRID / MiniOneRec **全线继承 LOO**；GRID 提供的 Amazon 数据即 P5 的 LOO 格式 | A（GRID README） |

**泄漏机制**：temporal LOO 按**用户本地时间轴**切分，跨用户全局时序不闭合，他人的未来交互泄入训练集。
**出处**：*Don't Get Ahead of Yourself*（Le / Liu / Medlar / Glowacka, U Helsinki, **RecSys 2025**, DOI 10.1145/3705328.3759329），代码 `github.com/yangl-iml/SRS_data_leakage`。

### 1.2 空白确认：缝真实，但只剩一半

最接近的三篇，**各自只握住假设的一半，且互不引用**：

| # | 工作 | 做了什么 | **没做什么（缺口所在）** |
|---|---|---|---|
| 1 | **How Well Does Generative Recommendation Generalize?**<br>Ding et al.（CMU / UCSD / Meta + McAuley）<br>arXiv:2603.19809，KDD 2026 | item 级泛化拆为 memorization / symmetry / transitivity / substitutability；**核心论断：item 级泛化大量退化为 token 级前缀记忆**（>99% 测试样本存在 1-gram 前缀记忆）；TIGER vs SASRec | ❌ 用**标准 leave-last-out 切分**，完全无时序协议<br>❌ 无泄漏实验<br>❌ 不引用 *Don't Get Ahead of Yourself* |
| 2 | **Can Generative Recommendation Reach Cold Items? A Temporal Perspective**<br>Peng et al.（阿里）<br>arXiv:2607.21101，2026-07-23 | **绝对时间滑窗协议**；TIGER vs SASRec 在同一时序切分下对比；7 数据集；token 级冷度分类 + oracle-prefix 探针 | ❌ **无 LOO 对照臂**，因此**没量化泄漏放大倍数**<br>❌ 不引用 *Don't Get Ahead of Yourself*<br>❌ 泄漏仅作定性动机 |
| 3 | **How Reliable Are Semantic-ID Tokenizer Comparisons?**<br>arXiv:2605.25330，2026-05 | SID 碰撞率 **8.5%–30.5%**；SID 级 Hit@10 最高**虚高 103%**，足以翻转 tokenizer 排名；提出 CCE / ZCR 纠偏 | ❌ 讲的是**碰撞**（同 SID 映射多物品），**不是训练/测试切分泄漏**<br>❌ 不涉及时间维度 |

**可写的增量命题**（这是走廊 A 的真正位置）：
> 在 LOO 下，SID 模型的虚高幅度是否**显著大于** ID 模型？若把 SID tokenizer 也按时间截止训练，token 级记忆通道是否坍缩？

### 1.3 SID 方法线：自变量从未被隔离

**四条技术路线**

| 路线 | 代表 | 原理 | tokenizer 训练数据范围 |
|---|---|---|---|
| 残差量化 RQ-VAE | TIGER (NeurIPS'23)、LC-Rec (ICDE'24)、LETTER (CIKM'24) | 内容 embedding 逐层残差量化，3×256 码本 | 在**物品语料全量**上拟合；**未见论文显式限定训练集切分**（B，属推断） |
| 聚类量化 RK-Means | GRID (Snap, CIKM'25 手册) | 残差 K-Means，免训练迭代更少 | 同上 |
| 结构感知 OT | ReSOT (KDD'26, DOI 10.1145/3770855.3817834) | GWOT 保关系结构 + UOT 软量化降碰撞 | 未明确（C） |
| 上下文个性化 SID | Pctx (2510.21276)、DECOR (2509.10468)、UniGCRec (KDD'26) | 同物品在不同用户上下文→不同 SID | 仍基于全量物品；Pctx 还依赖全量用户历史（B） |

**关键空白**：码本生命周期的三件事里，**前两件已有专文，第三件无人做**——

| 议题 | 现状 |
|---|---|
| 新物品的码位分配 / 码本漂移 | ✅ 已有专文：**DACT**（arXiv:2603.29705, SIGIR'26, 复旦）——新物品导致 ID 碰撞与漂移，微调 tokenizer 会让 **>90% 存量物品改码**；**Dynamic single-level codebook**（arXiv:2608.21012）——exposure-aware 动态码本 |
| **切分对 tokenizer 的影响** | ❌ **无人专门做** ← 这就是缺口 |

### 1.4 实验基础设施（本走廊最大优势：便宜）

**数据**

| 数据集 | 规模 | 状态 |
|---|---|---|
| Amazon 2014 Beauty | 22,363 用户 / 12,101 物品 / 198,502 交互 | B（多源一致） |
| Amazon 2014 Sports | 35,598 / 18,357 / 296,337 | B |
| Amazon 2014 Toys | 19,412 / 11,924 / 167,597 | B |
| ML-1M / Steam / Yelp | — | `SRS_data_leakage` 已含 |
| **预处理** | **GRID 直接提供 P5 预处理版 Amazon beauty / sports / toys**（Google Drive） | A — **省去最大工作量** |

**代码**

| 仓库 | star（2026-09-21 实测） | 说明 |
|---|---|---|
| **snap-research/GRID** | **742** | ⭐ **首选**。模块化 tokenizer，三种算法可换（RK-Means / RVQ / RQ-VAE），RK-Means 秒级拟合可反复重跑 |
| AkaliKong/MiniOneRec | **1,836** | 完整框架需 4–8×A100/H100；1.5B 变体单卡 ≥48GB 可训 |
| RUCAIBox/LC-Rec | **238** | LLaMA-7B 微调，单卡吃力 |
| XiaoLongtaoo/TIGER | 252 | **TIGER 官方从未开源**；此为社区复现（指标普遍低于原文 10–20%） |
| torch-rechub | 1,220 | 含 `tiger.py` + RQ-VAE 脚本 |
| HomesAmaranta/DACT | 12 | 含 RQ-VAE 训练脚本 |

**RQ-VAE tokenizer 本身极轻**：几层 512/256/128 MLP + 3×256×32 码本，20k 步、batch 1024，**单卡分钟级到小时级**。瓶颈在下游 seq 模型（**TIGER 仅 ~13M 参数，单卡友好**；LLM 版才重）。

### 1.5 竞争与抢发风险：高

| 危险度 | 谁 | 差什么 |
|---|---|---|
| **最危险** | **Ding et al.（McAuley 组 + Meta）**，arXiv:2603.19809 | 已证明「token 记忆伪装 item 泛化」，**只差换上时序切分**；KDD'26 在审 |
| **次危险** | **Peng et al.（阿里）**，arXiv:2607.21101 | 已做时序切分 + TIGER/SASRec 对比，**只差 LOO 对照臂** |
| 活跃社区 | Helsinki 泄漏组（Le / Liu / Medlar）；*Time to Split* 组；Jannach / Dacrema 复现组 | 截至 2026-09 **尚无 SID × 泄漏的直接论文** |

**近 6 个月（2026-03 起）直接相关预印本至少 9 篇**：2603.19809、2604.13665、2605.25330、2606.10375、2606.14260、2607.03918、2607.21101、2608.21012、2608.28905。热度极高。

**窗口期估计：3–6 个月。**
**投稿出口**：RecSys 2026 有 **ROEGEN** 工作坊（生成式推荐的风险与评测），可作为备选出口。

### 1.6 可行性：单卡，数天

**推荐的最小可行实验**（用 GRID 的 RK-Means tokenizer，唯一自变量）：

| 组 | 设定 |
|---|---|
| A | tokenizer 在**全量目录**上拟合（复现现状） |
| B | tokenizer **只在训练期物品**上拟合，测试物品用最近邻码位分配 |
| C | 测试期物品**不入码本**，走「未分配」分支 |

对比 **CCE 纠偏后**的 ItemHit@K，即可直接量化「token 级记忆伪装」的幅度。

**组合**：4 数据集 × {SASRec, TIGER/GRID} × {LOO, split-by-timepoint}，单一元变量。
**算力**：单张 24GB 卡，每配置约 1–2 天（**此为估计，未实测**）。

---

## 2. 走廊 B：Agent 记忆的驱逐与可逆性 —— ❌ 已塌

### 2.1 判决：原假设的「空白」不成立

2026-06 ~ 09 已密集出现 **4+ 篇**「固定预算下可逆驱逐 / 恢复」工作，**EMBER 与 Reclaim 几乎已覆盖「保留 provenance 存根 + 按需恢复」这一设想**。

### 2.2 占位者（均已核验，A 级）

| 工作 | 已做 | 未做 |
|---|---|---|
| **EMBER** arXiv:2606.05894 | **evidence capsule** = 逐字源摘录 + 检索键 + 更新元数据；固定预算内保可恢复；Retain-Recall / Read-Recall 双指标 | 无 restore 反事实审计 |
| **Reclaim** arXiv:2606.25449 | 同预算下「**留源不留结论**」换回可纠正性 | 无 provenance 存根形式化 |
| **CrystalMem** arXiv:2608.00303 | **四态可逆阶梯** + verified recrystallization；证明 keep-or-drop 存在 **residual-deficit 下界** | 未上标准对话基准 |
| 旁证 | Blast Radius（2608.07440）逐字归档可逆驱逐；Forgetting Without Restarting（2609.04875）provenance 图 + KV cache 裁剪 | — |

### 2.3 若仍要保留此走廊：唯一可行差异点

> **把 2609.08279 的 restore 反事实审计当「评测工具」**，而不是再提一个新的可逆方案。
> 即：不做第 4 个可逆驱逐机制，而是做**「如何评测可逆性」的方法学**。这两个方向目前的交叉尚无人做。

这是一个**降级**方案——从「提出方法」变成「提出评测」，更适合 D&B track。

### 2.4 领域现状与基础设施（供参考）

**标准三段流程**：写入（抽取事实 → 与相似记忆比对 → ADD / UPDATE / DELETE / NOOP）→ 检索（向量 / 图 / 词法）→ 驱逐（超 token 预算时 FIFO / LRU / 重要性 / 冗余淘汰）。

| 系统 | 驱逐 / 遗忘做法 |
|---|---|
| Mem0 (2504.19413) | 显式 `DELETE` 即**硬删除**；TTL / LRU / 显著性 / 取代四策略出自其**官方博客**而非论文 |
| Zep / Graphiti (2501.13956) | 时序知识图谱，冲突关系**标记失效**而非物理删除 |
| A-MEM (2502.12110) | Zettelkasten 链接 + memory evolution，**摘要无驱逐机制** |
| MemoryBank (2305.10250) | 艾宾浩斯遗忘曲线 + 重要性衰减 |

| 资源 | 规模 | 位置 |
|---|---|---|
| LongMemEval | 500 题 / 5 能力；S≈115k tok（~40 会话） | `xiaowu0162/LongMemEval`（1.1k★） |
| LoCoMo | 均 300 轮 / 9K tok / ≤35 会话 | arXiv:2402.17753 |
| Mem0 | — | `mem0ai/mem0`（65.8k★） |
| A-MEM | — | `agiresearch/A-mem`（1.2k★） |
| Zep | — | `getzep/graphiti`（31.1k★） |
| MemoryAgentBench | 四能力，含 selective forgetting | `HUST-AI-HYZ/MemoryAgentBench`（458★） |

**可行性**：LongMemEval 全 500 题**单卡可跑**（7–8B 本地模型 + 检索，约 1–3 天）；走 API 则读取侧约 10⁷ token，成本约 **¥100–1000**。

**竞争方**：EverMind（EverMemOS + MSA）、agiresearch（UCSD McAuley）、HUST-AI-HYZ、getzep、UIUC Jiawei Han 组。

---

## 3. 走廊 C：GraphRAG 的图构建质量 —— ⚠️ 窄缝，有强对手

### 3.1 判决：不是空白，但有明确的窄缝

真正的占位者是 **XMU 团队**——同一批人（Xiang / Wu / Zhang / Su）**既做了 GraphRAG-Bench（2506.05690），又在 KDD'26 发了 MemGraphRAG（2606.00610）正面做构建侧净化**。这既是最大抢发风险，也说明问题被公认。

### 3.2 主流构建流程

| 系统 | 构建流程 |
|---|---|
| MS GraphRAG (2404.16130) | LLM 抽实体/关系 → Leiden 社区检测 → 社区摘要；**仓库已进维护模式** |
| LightRAG (2410.05779, EMNLP'25) | LLM 抽 entity/relation，**无显式社区检测** |
| HippoRAG (NeurIPS'24) | 实体节点 + 同义边，PPR 图激活；HippoRAG2 加 phrase / passage 节点 |
| **MemGraphRAG (KDD'26, 2606.00610)** | **构建侧净化**：主题去噪（schema 稳定性筛选）+ 冲突检测/消解 Agent + 结构统一 |
| **LinearRAG (ICLR'26, 2510.10114)** | **免 LLM**：spaCy NER + sentence-transformer，无关系抽取的 Tri-Graph |
| NaviRAG (2604.12766) | 非三元组图，是层级 Knowledge Tree，与实体消歧无关 |

### 3.3 空白确认：最接近的三篇

| 工作 | 做过什么 | **没做什么** |
|---|---|---|
| **MemGraphRAG** (KDD'26) | 构建侧去噪 + 消歧 + 冲突消解，索引 295.45s / 896k tokens，图密度最高 | 与**新检索算法捆绑**，**不是**「固定检索器、只改构建」的对照 |
| **CORE-KG** (2510.26512) | 消融量化：去 coref → 重复节点 +28%；去结构化 prompt → 噪声节点 +73.3% | 只测提取指标，**未做端到端 QA**，未固定检索器 |
| **RAGU** (2607.11683) | 抽离「提取/合并」，DBSCAN 去重，7B 微调超 Qwen2.5-32B | 提案整套引擎，非受控干预 |

**判定**：GraphRAG-Bench 自身只把构建质量当**诊断维度**（efficiency / cost / organization = 非孤立节点占比），**未提净化方法**。
**「固定检索器 + 仅干预构建 + 受控噪声注入」的对照实验——检索未命中。缝真实，但窄且易被 XMU 顺手做掉。**

### 3.4 实验基础设施

| 项 | 事实 |
|---|---|
| GraphRAG-Bench 仓 | `GraphRAG-Bench/GraphRAG-Benchmark` = **496★** |
| 四级任务 | Fact Retrieval / Complex Reasoning / Contextual Summarization / Creative Generation；指标 Acc / ROUGE-L / Coverage / Factual |
| 数据规模 | GraphRAG-Bench 内：MuSiQue ~2K、HotpotQA ~10K、2Wiki ~12K 题（B 级） |
| 基线仓库 star | microsoft/graphrag **36,053**；HKUDS/LightRAG **39,798**；HippoRAG **4,018**；LinearRAG **548**；MemGraphRAG **218** |

### 3.5 可行性：**这是本走廊最大的风险**

| 问题 | 结论 |
|---|---|
| **构建成本** | MuSiQue（5.64MB 语料）上 MS-GraphRAG：**~$2.30 到 ~$24.94**，**11× 差异仅来自 chunk size**；PopQA 上 MS-GraphRAG **1,847.9M tokens**、LightRAG 1,400.3M（成本数字为第三方重构，非官方披露） |
| **免 LLM 路径** | ✅ **有**：LinearRAG（spaCy + 句向量，索引零 token，比 RAPTOR 快 15.1×）、Democratizing GraphRAG (2602.23372, CPU-only)、Lazy GraphRAG |
| **单卡 7B 替代 API** | ⚠️ **能跑但质量退化**：8GB VRAM + Q4_K_M 可跑完整 MS 流程；**~7B 是硬下限**（3.8B 结构化输出直接失败） |
| **可转向的点** | **「7B 构建质量差」这一现象本身可反过来作为研究变量**——即研究构建质量如何随模型规模退化 |

**竞争方**：① **XMU**（GraphRAG-Bench + MemGraphRAG 同团队）——最大威胁；② **MSU**（Han Haoyu / Ma Li / Jiliang Tang）：KDD'26 两篇 + 2601.14662；③ HK PolyU（LinearRAG）。
**近 6 个月新预印本**：RAGU 2607.11683、TRIAGE 2607.03447、Hypergraph-RAG 2607.20506、MemGraphRAG 2606.00610、UnWeaving 2603.29875、CrossAug 2605.28004 等——**构建质量已是活跃战场，但多为「新引擎 / 新诊断」，少见隔离对照**。

---

## 4. 三条走廊横向对比

| 维度 | A：SID × 泄漏 | B：记忆可逆驱逐 | C：GraphRAG 构建质量 |
|---|---|---|---|
| **缝是否真实** | ✅ 是（具体自变量从未被隔离实验） | ❌ 否（已被 3 篇实质占位） | ⚠️ 是，但窄 |
| **窗口期** | 3–6 个月 | — | 很短 |
| **最大威胁** | McAuley 组（2603.19809）/ 阿里（2607.21101） | EMBER / Reclaim / CrystalMem | **XMU 团队**（同批人占两头） |
| **算力门槛** | **低**：单卡 24GB，数天 | 低：单卡 1–3 天 | **高**：LLM API 成本是瓶颈 |
| **基础设施成熟度** | **高**：GRID 模块化 + 数据已预处理 | 高 | 中 |
| **与「改进 A」策略的契合** | **最高**：A = MemGen-GR / GRID，弱点明确 | 低：需降级为「评测方法学」 | 中：A = MemGraphRAG / GraphRAG-Bench |
| **综合建议** | **首选** | 放弃或降级 | 备选 |

---

## 5. 推荐与下一步

### 5.1 推荐：走廊 A，且应尽快动手

理由：**缝的真实性最高 + 实验成本最低**。而且它满足「改进 A」策略的关键条件——被攻击的弱点（LOO 泄漏）**已被正式论文确立**，你要做的只是把**没人做过的那个自变量**（tokenizer 的训练范围）隔离出来。

**预判审稿人的两个质疑，提前准备**：
1. 「这不就是 *Don't Get Ahead of Yourself* 换个模型跑一遍？」→ 回应：那篇测的是 ID 模型与切分协议，**从未触及 SID tokenizer 这一层**；你的贡献是发现 SID 把泄漏**放大**了，机制不同。
2. 「增量太小」→ 回应：必须给出**机制解释**（token 共享 → 记忆伪装），不能只报数字。

### 5.2 立即要做的三件事

1. **精读 2603.19809 与 2605.25330 全文**——这两篇定义了指标与归因口径（CCE 纠偏、token 级记忆率），你的实验设计要建立在其之上，否则会被说是重复。
2. **确认 GRID 的 RK-Means 能否「仅在训练期物品上 fit」**——这是整个方案的技术前提，需要看代码确认可改造。
3. **对 Tokenizer 训练范围做一次代码级核实**：现有实现到底是不是在全量目录上训的？若原文/代码已限定为训练集，**整条走廊的前提就塌了**——这是唯一的赌注点，必须先验。

### 5.3 备选路径

若走廊 A 的赌注点被证伪（现有实现其实已经只在训练集上训 tokenizer），则转走廊 C，但需先解决成本问题（走 LinearRAG 免 LLM 路径，或把「7B 构建质量退化」本身当研究变量）。

**走廊 B 不建议继续投入**，除非接受降级为「可逆性评测方法学」。

---

## 6. 核验与未核实项

### 6.1 核验分级

- **A**（已打开官方页 / arXiv abs / GitHub 仓库实际核验）：全部 GitHub 链接与 star 数（2026-09-21 实测）；GRID / DACT / MiniOneRec 仓库存在性；LongMemEval 仓与评测脚本；GraphRAG-Bench 四级任务与仓信息；EMBER / Reclaim / CrystalMem / What Eviction Destroys 等摘要页。
- **B**（仅摘要或二手命中）：绝大多数论文的方法描述与数字；77.3% LOO 统计；RecSys'24 7/9；Amazon 2014 数据规模；GraphRAG-Bench 数据集题数；GraphRAG 成本数字（来自第三方重构，**MS GraphRAG 原文从未公布任何美元数字**）；7B 构建质量结论。
- **C**（未能核实）：各工作 tokenizer 的**确切训练数据范围**（原文普遍不写，属推断）；TIGER 单卡训练时长；GRID 显存占用；部分仓库 star 数的多源冲突项。

### 6.2 明确不可引用的条目

| 条目 | 原因 |
|---|---|
| **Deg-Rag** | 仅见 CSDN 博客，无 arXiv / 论文可查 |
| **EVOKE**（「可逆 KV 驱逐」） | 仅见非 arXiv 镜像，未在 arXiv 核到 |
| `graphrag-accelerator` 仓库 | 不存在（404） |
| MS GraphRAG 的美元成本数字 | 原文未公布，市面数字均为第三方重构 |

### 6.3 存疑项

- arXiv:2608.05153、2602.23372 的 arXiv API 返回 ID 与 published 日期存在**月分不一致异常**（标题一致），引用前需复核。
- 走廊 A 的单卡训练时长（「每配置 1–2 天」）为**估计值，未实测**。

---

## 7. 对前序文档的影响

- [`kdd-ai-survey-2026.md`](kdd-ai-survey-2026.md) 走廊 B 的建议**作废**——该走廊已被 EMBER / Reclaim / CrystalMem 占位。
- 走廊 A、C 的表述需按本文件收窄（A 的缺口从「没人测过 SID × 泄漏」精确到「没人隔离过 tokenizer 的训练范围」）。

---

*相关文档：[KDD 2026 AI 方向调研](kdd-ai-survey-2026.md) ｜ [领域现状综述](survey-data-mining-2026.md) ｜ [选题地图](topic-landscape-2026.md) ｜ [调研笔记](notes.md) ｜ [目录索引](README.md)*
