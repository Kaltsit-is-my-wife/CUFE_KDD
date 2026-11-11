# Agent-Induced Drift：用户偏好、记忆写入与自我实现循环

> 项目代号：**InflMem**（Influence-aware Memory）  
> 文档版本：v1.0  
> 日期：2026-10-30  
> 文档性质：研究 idea 说明 / 方案设计，不代表实验已经完成  
> 关联文档：`2026-10-30_Agent-Induced-Drift_5人10周项目计划.md`、`2026-10-30_Week1_五人任务清单.md`

---

## 0. 摘要

### 0.1 一句话

> **长期记忆系统最危险的错误，不只是“忘记”或“检索错了”，而是把 agent 自己诱导出来的服从行为，写成了用户稳定偏好，并通过后续推荐不断自我强化。**

我们把这一现象称为 **Agent-Induced Drift（代理诱发的偏好漂移）**。

### 0.2 问题

跨会话记忆让 agent 能够记住用户的历史、偏好和约束，从而提供更连续的个性化服务。但现有记忆系统普遍隐含一个假设：

> 用户选择了 X，就说明用户偏好 X；重复选择 X，就说明 X 是稳定偏好。

这个假设在长期交互中不成立。用户接受 agent 推荐的 X，可能是因为：

- X 是 agent 唯一展示的选项；
- X 被放在了更显眼的位置；
- 用户信任 agent，懒得继续比较；
- 用户当时只想尽快结束任务；
- X 是“这次可以接受”，但不是“以后都想要”。

这些情况是 **compliance（服从/配合）**，不一定是 **internalization（内化）**。如果记忆系统把两者混为一谈，就会把一次妥协固化成用户 trait：

```text
agent 推荐 X
    → 用户接受 X
    → memory 写成 “User prefers X”
    → 下一次更强地推荐 X
    → 用户再次接受
    → memory 置信度更高
    → 用户的选择空间越来越窄
```

这不是普通的 retrieval 问题，而是一个 **动态因果系统中的内生性问题**：agent 的行为既是用户行为的因，也是记忆形成的因；而记忆又反过来影响 agent 的行为。

### 0.3 核心洞察

现有工作大多在问：

- 记忆能不能检索到？
- 记忆是否过期？
- 记忆是否互相冲突？
- 记忆是否被投毒？
- 记忆是否被过度应用？

我们问一个更上游的问题：

> **这条记忆，究竟是在记录用户，还是在记录 agent 自己对用户做过什么？**

记忆写入不是一个“事实转录”步骤，而是一个 **因果归因** 步骤。写入者必须回答：

1. 这个行为变化，是用户真实偏好变化吗？
2. 是上下文变化吗？
3. 是一次性噪声吗？
4. 是 agent 的曝光、推荐、措辞造成的吗？
5. 如果是 agent 造成的，它是暂时的 compliance，还是已经内化为 durable preference？

### 0.4 方案概要

我们提出一套面向 memory write 的因果记忆框架，包含四个部分：

1. **Provenance-aware memory schema**：记忆不只存“用户喜欢什么”，还存“这个结论来自哪次事件、当时 agent 做了什么、用户是主动选择还是接受推荐、置信度多少、有效期是什么”。
2. **Influence-aware benchmark**：在同一个用户、同一个外生冲击下，构造“有 agent 影响”和“无 agent 影响”的反事实世界，给出 compliance / internalization / exogenous change / noise 的隐藏标签。
3. **Causal memory writer**：把写入决策建模为因果估计，使用 exposure propensity、随机探索、negative controls、persistence test，决定写什么、怎么写、写多确信，甚至是否不写。
4. **Quality-faithfulness evaluation**：同时测偏好归因错误、推荐质量、记忆忠实度和多样性，避免“少写记忆”通过降低覆盖率来刷低错误率。

### 0.5 预期贡献

- **问题形式化**：首次把 agent-induced preference drift 明确为 memory write 层的因果归因问题，区分 compliance 与 internalization。
- **Benchmark**：一个带反事实 ground truth 的跨会话偏好漂移评测，结合 MemoryCD 的真实历史与 AcCoRD 的真实交互动态。
- **方法**：一个 provenance-aware、propensity-aware 的 causal memory writer，以及可复现的 baseline 套件。
- **实证发现**：现有记忆系统在多大程度上会把 agent 诱导的行为写成用户偏好；修复能带来多少收益、付出多少质量代价。

### 0.6 可行性判断

**可以做，但不能把它做成泛化的“记忆漂移 benchmark”。** 泛化方向已经非常拥挤；本 idea 的生存空间在于：

- 研究对象是 **agent 自己造成的行为变化**；
- 评价对象是 **memory write 的因果归因**；
- 数据设计有 **反事实 ground truth**；
- 方法必须处理 **compliance 与 internalization 不可直接观测** 的问题。

如果实验发现 naive memory 的 CMR 很低（例如低于 10%），或者 provenance 本身就能解决大部分问题，那么这个 idea 应该及时收缩为“记忆写入诊断工具”，而不是硬撑成一篇因果方法论文。

---

## 1. 研究背景

### 1.1 跨会话记忆正在成为默认能力

过去的 LLM 应用大多是 stateless 的：每次对话从零开始。现在越来越多的 agent 具备跨会话记忆：

- 记住用户是谁、做什么工作、偏好什么；
- 记住过去的任务、决策和约束；
- 在新会话中自动召回相关记忆；
- 根据记忆调整语气、推荐、工具调用和工作流。

这带来一个结构性变化：**agent 不再只是响应当前输入，而是在响应一个由自己参与塑造的“用户历史”。**

记忆系统的典型流水线是：

```text
observe → extract → write → store → retrieve → apply → observe ...
```

现有研究和工程大量关注 `retrieve` 与 `apply`：

- 检索是否相关；
- 上下文是否装得下；
- 记忆是否被正确使用；
- 是否过度个性化；
- 是否被投毒；
- 是否过期。

但 `write` 这一层经常被当成简单的抽取：

```text
对话 → LLM 摘要 → “User prefers X” → 存入向量库
```

问题在于：**写入时的因果上下文，往往在这一步被丢掉了。**

### 1.2 现有记忆系统的隐含假设

大多数记忆写入策略隐含了三个假设：

**假设 1：行为等于偏好。**  
用户点了、买了、接受了，就被写成“喜欢”。

**假设 2：重复等于稳定。**  
同一行为出现多次，就被升级为高置信度偏好。

**假设 3：时间是主要噪声。**  
只要新记忆覆盖旧记忆，或者加上时间衰减，就能处理变化。

这三个假设在短期、低风险、选择空间充分的情境下可能近似成立。但在长期 agent 交互中，它们会失效：

- 用户可能没有看到其他选项；
- 用户可能看到了但没有精力比较；
- 用户可能因为信任而接受；
- 用户可能只是在某个上下文里妥协；
- 重复可能是 agent 自己造成的，而不是用户自发的。

### 1.3 一个最小例子

假设用户第一次说：

> “我想买一副耳机，黑色比较百搭。”

agent 发现黑色缺货，于是推荐蓝色：

> “黑色暂时没货，蓝色是同款，今天有折扣。”

用户回答：

> “行，那就蓝色吧。”

naive memory 写入：

> “User prefers blue headphones.”

这句话至少丢失了四个事实：

1. 用户最初偏好黑色；
2. 蓝色是 agent 先推荐的；
3. 用户接受蓝色时，黑色不可得；
4. 用户的“行”可能只是任务性妥协。

第二次会话，agent 检索到“User prefers blue”，于是只推荐蓝色。用户再次接受。naive memory 更新为：

> “User strongly prefers blue; repeated purchases confirm.”

第三次会话，用户说：

> “其实我一直想要黑色，上次是没货才买的蓝色。”

这时系统才发现自己记错了。但如果没有这次纠正，错误可能会持续数月。

更隐蔽的情况是：用户后来真的开始觉得蓝色也不错。此时蓝色从 compliance 变成了 internalization。**两种情况的早期行为完全一样，单看一次接受无法区分。** 这正是问题难点，也是 benchmark 必须提供反事实和纵向观测的原因。

### 1.4 为什么这是 LLM-specific 的放大机制

经典的推荐系统反馈循环（feedback loop）已经研究过“曝光偏差”和“自我实现推荐”。但 LLM agent 引入了几个额外放大机制：

1. **自然语言压缩损失 provenance。**  
   结构化推荐日志可以保留“曝光了哪些 item”，但 LLM 摘要通常只留下“用户喜欢 X”。

2. **措辞本身就是干预。**  
   “你可以试试蓝色”与“你之前喜欢蓝色”对用户的影响不同。记忆检索结果会改变 agent 的措辞，措辞又改变用户反应。

3. **记忆写成 trait，而不是 evidence。**  
   LLM 很擅长写“User is a detail-oriented person”这类人格化总结，却不一定保留“这是一次任务中的临时选择”。

4. **跨会话的置信度累积。**  
   一次接受被写成偏好，下一次接受被当成“再次确认”，再下一次变成“strongly prefers”。错误会获得复利。

5. **记忆同时是记录器和行动者。**  
   记忆影响推荐，推荐改变行为，行为再被写回记忆。这是一个闭环，不是单向检索。

因此，我们不能把这个问题简单归类为“推荐系统 debias”。必须把 **自然语言记忆写入**、**跨会话累积**、**agent 措辞干预** 三个因素放进同一个模型。

---

## 2. 核心概念与定义

### 2.1 现象定义

> **Agent-Induced Drift**：agent 的推荐、曝光、措辞或交互策略，系统性地改变用户的可观测行为；记忆系统把这种由 agent 引起的行为变化误归因为用户偏好变化，并在后续交互中依据该错误记忆继续行动，形成自我强化循环。

这个定义有三个关键词：

- **系统性**：不是一次随机误判，而是随 exposure 增加而增强的偏差。
- **误归因**：行为变化可能真实存在，但原因被记错了。
- **自我强化**：错误记忆改变未来 action，未来 action 又制造支持错误记忆的新证据。

### 2.2 Compliance 与 Internalization

这是整个 idea 的核心区分。

| 概念 | 定义 | 行为表现 | 记忆应该怎么写 |
|---|---|---|---|
| **Compliance** | 用户接受了 agent 推荐的 X，但潜在偏好没有改变 | 这次选了 X；下次独立选择可能仍选 Y | “在 agent 推荐下接受了 X；可能是情境性妥协；不等于偏好 X” |
| **Internalization** | 用户在多次、多上下文暴露后，潜在偏好真的向 X 移动 | 不仅接受推荐，还会主动搜索、复购、在新情境中选择 X | “偏好可能已向 X 移动；有跨上下文证据；置信度中等” |
| **Exogenous change** | 用户因为生活事件、预算、环境变化而改变偏好 | 与 agent 曝光无关；在无推荐世界也会改变 | “记录了外部变化；需要更新旧偏好” |
| **Noise** | 一次性情绪、误点、试验、随机波动 | 不重复、不持续、不跨上下文 | “一次性事件；不升级为稳定偏好” |

关键难点：

> **Compliance 和 internalization 在发生时刻可能产生完全相同的行为。**

用户这次选了蓝色，可能是因为 agent 推荐，也可能是因为真的喜欢蓝色。仅凭 `(user, item, accept)` 无法区分。要区分，至少需要以下一种信息：

- 未来的独立选择；
- 不同上下文中的重复出现；
- 反事实世界：如果没有推荐，用户会不会选 X；
- 随机化探索：有时推荐 X，有时不推荐 X；
- 用户的主动澄清或纠正；
- 对未曝光属性的 negative control。

这也解释了为什么“更好的摘要 prompt”不够：**没有因果变化，就没有可识别的因果信息。**

### 2.3 记忆误归因

我们把 memory write 的错误分成四类：

1. **Overclaim**：把一次接受写成稳定偏好。  
   例：“User loves blue” ← 一次缺货妥协。

2. **Provenance loss**：结论可能对，但来源、时间和条件丢了。  
   例：正确记录“喜欢蓝色”，但没记录“仅在运动场景”。

3. **Scope inflation**：把某个上下文中的偏好扩散到所有场景。  
   例：工作时用 Python，被写成“User prefers Python”并用于业余项目推荐。

4. **Confidence inflation**：重复曝光被当成独立证据，置信度虚高。  
   例：agent 连续三次推荐蓝色，用户三次接受，被写成“strongly prefers blue”。

CMR 主要测第 1 类，SFB 测第 4 类，Faithfulness 测第 2/3 类。

### 2.4 这不是什么

为了避免范围漂移，明确本 idea **不是**：

- 不是“再做一个通用记忆漂移 benchmark”；
- 不是“再做一个记忆治理框架”；
- 不是“所有记忆都应该少写”；
- 不是“用户只要接受推荐就是被操纵”；
- 不是“用 LLM judge 给记忆文本打分”这么简单；
- 不是“检索层加一个时间衰减”就能解决。

我们关注的是一个很窄但很关键的动作：**当 agent 把交互写成记忆时，它是否把 agent 的影响错误地归因为用户属性。**

---

## 3. 研究问题与假设

### 3.1 研究问题

- **RQ1（误写程度）**：现有 memory writer 在多大程度上把 agent-induced compliance 写成 durable preference？CMR 是否随 exposure 强度系统上升？
- **RQ2（区分机制）**：provenance、exposure propensity、随机探索、negative controls、persistence test 中，哪些信号对区分 compliance 与 internalization 最有效？
- **RQ3（可识别性）**：在什么观测和假设下，agent-induced drift 可以被识别？没有外生 variation 时，哪些结论必须放弃？什么时候 abstain 比写入更优？
- **RQ4（效用代价）**：降低 CMR/SFB 是否会损害推荐质量、覆盖率和多样性？能否在不牺牲用户长期效用的前提下修复记忆？
- **RQ5（泛化）**：修复效果能否跨 memory backend、跨 domain、跨模型成立，还是只在某个 simulator 配置下有效？

### 3.2 研究假设

### H1：naive memory 会把 compliance 写成 durable preference

**预测**：在控制真实潜在偏好后，naive writer 的 CMR 随 agent exposure 强度上升。

**如果为假**：说明现有记忆系统已经隐含处理了 provenance，或者 compliance 效应太弱，需要重新设计 interaction。

### H2：存在自我实现偏差

**预测**：在回归中控制真实偏好 `U_t` 后，记忆推断出的偏好 `\hat U_t` 仍与 agent exposure 正相关（SFB > 0）。

**意义**：这说明错误不是随机噪声，而是系统性地朝 agent 的推荐方向漂移。

### H3：provenance-aware causal writer 能降低 CMR/SFB

**预测**：相对于 naive writer，proposed writer 显著降低 CMR 和 SFB，同时推荐质量下降不超过 5%。

**关键**：不是“少写”导致指标变好。必须同时报告 coverage、utility 和 diversity。

### H4：仅靠 prompt 不够，必须有外生 variation

**预测**：只让 LLM “注意 provenance” 能降低 overclaim，但在没有随机探索或反事实信息时，无法可靠区分 compliance 与 internalization；加入 exploration / negative controls 后收益更大。

**意义**：这是把工程 trick 提升为研究问题的地方。否则审稿人会说“加一句 prompt 就行了”。

### H5：效果跨底座成立

**预测**：在 MemoryCD 的真实历史底板上成立，在 AcCoRD 的交互场景上也成立；至少两个 domain 方向一致。

**风险**：如果只在合成 simulator 中成立，外部效度不足。

### H6：修复存在质量-忠实度权衡

**预测**：越保守的写入策略 CMR 越低，但 coverage 和个性化质量可能下降；proposed 应位于 Pareto 前沿，而不是简单牺牲效用。

---

## 4. 形式化与因果模型

### 4.1 变量

对用户 `i`、会话 `t`：

| 符号 | 含义 | 是否可见 |
|---|---|---|
| `U_{i,t}` | 真实潜在偏好状态（属性向量） | 评测可见，agent 不可见 |
| `C_{i,t}` | 上下文（任务、场景、预算、时间） | 部分可见 |
| `H_{i,t}` | 历史交互 | agent 可见 |
| `A_{i,t}` | agent action（推荐集合、排序、措辞、是否提问） | agent 可见 |
| `E_{i,t}` | exposure（用户实际看到的属性/商品） | 可记录 |
| `B_{i,t}` | 用户可观测行为（接受、拒绝、评分、复购） | agent 可见 |
| `M_{i,t}` | 写入的记忆 | 可审计 |
| `R_{i,t}` | 后续推荐/行动 | agent 可见 |
| `Y_{i,t}` | 用户效用/任务成功 | 评测可见 |

潜在偏好可以写成：

```text
U_{i,t+1} = U_{i,t}
           + η · 1[internalize] · (A_{i,t} - U_{i,t})
           + ξ · 1[shock] · Δ_{i,t}
           + noise
```

其中：

- `η`：agent 影响导致内化的强度；
- `ξ`：外生冲击导致偏好跳变的强度；
- `Δ`：冲击方向；
- `1[internalize]` 是隐藏标签，不能从单次行为直接观测。

用户行为由潜在偏好、上下文、agent action 共同决定：

```text
P(B_{i,t} = accept | U_{i,t}, C_{i,t}, A_{i,t}, E_{i,t})
```

记忆写入是一个函数：

```text
M_{i,t} = W(H_{i,t}, B_{i,t}, A_{i,t}, E_{i,t}, ...)
```

naive writer 的问题在于，它近似只使用了 `B`，而忽略了 `A` 和 `E` 的因果角色。

### 4.2 因果 DAG

```text
                 ┌──────────────┐
                 │ 真实偏好 U_t │
                 └──────┬───────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
    agent action A_t  上下文 C_t   行为 B_t
          │             │             │
          ▼             │             │
      exposure E_t ─────┘             │
          │                           │
          └──────────► memory M_t ◄───┘
                        │
                        ▼
                  future action R_t
                        │
                        ▼
                  future behavior B_{t+1}
```

关键路径：

1. `U_t → A_t`：agent 根据真实偏好做推荐。
2. `A_t → E_t → B_t`：agent 的推荐影响用户看到什么、选什么。
3. `B_t → M_t`：记忆把行为写成偏好。
4. `M_t → R_t → B_{t+1}`：记忆影响未来推荐，未来推荐制造新行为。
5. `U_t → B_t`：真实偏好也影响行为，这是混杂路径。

如果 memory writer 只看 `B_t → M_t`，就会把 `A_t → B_t` 的效果误记成 `U_t` 的属性。

### 4.3 目标估计量

我们关心两类量。

**（A）个体层面的归因概率**

```text
τ_i,t = P(internalize | E_{i,t}, B_{i,t}, H_{i,t})
```

即：在观察到这次曝光和行为后，用户真正内化 X 的概率。

**（B）总体层面的因果效应**

```text
ATE = E[ U_{i,t+1}(E=1) - U_{i,t+1}(E=0) ]
```

即：同一用户、同一时刻，有曝光与无曝光两种世界下，潜在偏好的差异。

在模拟器中，我们可以构造配对世界，直接估计 ATE；在真实数据中，只能依赖识别假设和代理指标。这一点必须在论文中写清楚。

---
### 4.4 识别假设

要在观测数据中估计 exposure 对潜在偏好的因果效应，至少需要以下假设：

1. **Consistency**：观测到的 outcomes 对应实际 exposure 水平。
2. **Positivity**：对每个用户/上下文，有正概率出现不同 exposure 水平。
3. **Sequential ignorability**：在给定历史、上下文和可观测变量后，exposure 与潜在结果条件独立。
4. **No interference**：一个用户的 exposure 不影响另一个用户的潜在偏好。
5. **Measurement**：我们能用行为、复购、澄清或 probe 近似测量潜在偏好。

在模拟器中，1–4 可以由设计保证；5 由隐藏状态和反事实标签保证。  
在真实数据中，1–5 都只能部分满足。**因此本文不宣称从真实日志中“证明”了因果效应，而是用模拟器做识别，用真实数据做外部效度检查。**

### 4.5 为什么 naive memory 有偏

令 `B` 为用户接受行为，`U` 为真实偏好，`E` 为 agent exposure。naive writer 估计的是：

```text
P(U | B)
```

但它实际需要的是：

```text
P(U | do(E), B, H)
```

两者之间至少有三类偏差：

- **Exposure bias**：用户看到的选项不是随机分配的；
- **Confounding by user state**：agent 本来就会根据用户偏好选择推荐，导致 `U → A`；
- **Reverse causality / feedback**：过去的记忆影响现在的推荐，现在的推荐影响未来的行为。

此外还有 **selection bias**：用户只在某些场景下接受推荐，接受者本身可能更信任 agent、更偏好省事，或者更不愿意搜索。

因此，仅靠“让 LLM 更谨慎地写 memory”不能解决问题。必须让写入过程获得关于 `A` 和 `E` 的额外信息，或者通过随机化制造外生 variation。

### 4.6 可识别性的边界

一个重要的负面结论是：

> **如果没有外生 variation，也没有额外假设，那么“用户真的变了”和“agent 让用户看起来变了”在观测上是不可区分的。**

因为两种世界可以产生完全相同的行为序列：

```text
世界 1：U 不变，agent 推荐 X，用户接受 X
世界 2：U 向 X 移动，agent 推荐 X，用户接受 X
```

如果没有“无推荐世界”的反事实，或者没有跨上下文/独立选择，观测数据无法区分两者。

这不是工程实现问题，而是识别性问题。它决定了 benchmark 必须包含：

- 随机化曝光；
- 配对反事实世界；
- 隐藏的 internalization 标签；
- 至少一个“无 agent 影响”的对照。

这也是本 idea 与“再加一个 memory prompt”最本质的区别。

---

## 5. 与现有工作的关系

> 以下判断基于 2026-10-30 前的公开检索。2026 年论文多为预印本，未经同行评审；代码可用性以实际仓库为准。

### 5.1 相关工作地图

| 方向 | 代表工作 | 已经解决什么 | 仍缺什么 |
|---|---|---|---|
| 长程记忆评测 | LongMemEval、LoCoMo、MemoryAgentBench | 记忆召回、跨会话问答、增量交互 | 不测 agent 对偏好的因果影响 |
| 真实用户长期偏好 | **MemoryCD**（arXiv:2603.25973） | 323 用户、167,870 商品、12 域、4 任务；真实跨年历史 | 无交互、无 agent action、无 influence |
| 交互式偏好动态 | **AcCoRD**（arXiv:2608.27818） | 100 购物 + 100 旅行场景；LLM user simulator；四类偏好动态；MIT 代码 | 单 session；无跨会话 memory；agent 不改变 latent preference；无因果 ground truth |
| 推荐中的 exposure bias | **CALMRec**（arXiv:2607.23647） | identification + propensity-weighted 更新；电商/新闻/短视频模拟 | 面向推荐系统，不是自然语言 memory write；代码未确认可得 |
| 偏好漂移 vs 投毒 | **CAPTURE**（arXiv:2609.02265） | POMDP belief tracking；真实漂移与 memory poisoning 的区分 | 未把 agent action 作为偏好变化的因；代码未找到 |
| 记忆冲突/时序 | MemConflict、TANGLE、Stale/Misattributed/Late | 冲突检测、时序有效性、错误发生位置 | 不区分 compliance / internalization |
| 过度个性化 | OP-Bench、PRAGMA | 记忆该不该用、是否过度应用 | 关注 retrieval/application，不是 write |
| 记忆保留/反事实 | ConMem / MemAlign（arXiv:2610.33432） | 1,079 个 memory misalignment case；反事实 multi-scenario probing | 没有 agent-induced preference 标签；代码未找到 |
| 安全/授权漂移 | ULSPB（arXiv:2605.06731） | routine chats 导致授权边界漂移 | 无 LICENSE；偏好不是安全状态；不可直接复用代码 |
| 记忆系统基础设施 | Mem0、Letta/MemGPT、A-MEM、Zep | 生产级 memory 接口与检索 | 写入策略默认“行为即偏好” |
| 可插拔评测 | MemGym（arXiv:2605.20833） | memory manager 接口、标准评测循环 | 缺少 influence 场景与反事实 |

### 5.2 AcCoRD：最合适的交互底座

AcCoRD 是目前最完整的公开交互式偏好动态 harness 之一：

- 100 个购物场景 + 100 个旅行场景；
- LLM user simulator；
- 四种偏好动态：hard/soft underspecification、unachievable、triggered；
- 有 satisfaction / task success 评测；
- 有 consistency checking 和 rollout 代码；
- MIT License，代码可改。

但它有三个关键缺口：

1. **单 session**：没有跨会话 memory；
2. **agent 不影响 latent preference**：推荐只会触发用户透露已存在的偏好，不会改变偏好；
3. **没有反事实 ground truth**：没有“同一用户有无 agent 影响”的配对世界。

因此 AcCoRD 适合做 **Stage 2 的交互真实性底座**，不能单独支撑我们的核心 claim。

### 5.3 MemoryCD：最合适的真实历史底座

MemoryCD 提供：

- 323 个真实用户；
- 167,870 个商品；
- 12 个域；
- 4 个任务：rating prediction、review summarization、review generation、item ranking；
- 真实跨年行为，比纯合成 persona 更有说服力；
- 仓库 MIT，数据在 Hugging Face。

它的缺口是：

- 没有交互式 agent；
- 没有推荐动作；
- 没有用户对推荐的即时反应；
- 没有 influence model；
- 没有隐藏的潜在偏好和反事实标签。

因此 MemoryCD 适合做 **Stage 1 的真实历史底座**：用它提供用户历史、商品库和跨域行为，再外挂一个受控的 influence simulator。

### 5.4 CALMRec：方法论最接近，但不能作为唯一依赖

CALMRec 的 identification + propensity weighting 与我们的方法最接近。它说明：

- 推荐系统的曝光不是随机的；
- 需要用 propensity 或干预数据做去偏；
- 反馈循环会改变未来观测。

差异在于：

- CALMRec 主要处理推荐系统中的评分/排序，不处理自然语言 memory write；
- 它没有 compliance vs. internalization 的概念；
- 它没有 LLM 的摘要、措辞、记忆检索放大机制；
- 论文中的代码链接在 arXiv HTML 中没有明确出现，不能假设一定可得。

因此我们应把 CALMRec 当作 **方法论近邻和 baseline 来源**，而不是唯一底座。若代码不可得，按论文重实现一个简化版 IPW baseline。

### 5.5 空白点

综合来看，仍然存在四个空白：

1. **没有跨会话、交互式、带反事实 ground truth 的 agent-induced preference drift benchmark。**
2. **没有把 compliance 与 internalization 明确区分，并落到 memory write 决策上的形式化。**
3. **没有把 exposure propensity、随机探索、negative controls 和 provenance 结合起来的 memory writer。**
4. **没有同时评估“偏好归因正确性”和“推荐质量/多样性”的协议。**

这四个空白共同构成我们的研究空间。单独做第 1 个容易变成“又一个 benchmark”；单独做第 3 个容易变成“prompt trick”；四者结合才有完整故事。

---

## 6. Benchmark 设计

### 6.1 设计原则

1. **同一个用户、同一个初始状态，构造配对世界。**  
   有 agent 影响 vs. 无 agent 影响，其他条件尽量相同。

2. **隐藏状态与可观测行为分离。**  
   agent 只能看到对话、推荐、接受/拒绝、评分；评测者能看到 `U_t`、冲击、compliance/internalization 标签。

3. **反事实必须可计算。**  
   不是让 LLM judge 猜“如果没有推荐会怎样”，而是模拟器直接生成两个世界。

4. **真实历史优先。**  
   用 MemoryCD 提供真实用户轨迹，减少纯合成 persona 的审稿风险。

5. **交互真实性可升级。**  
   先 text-only，再接 AcCoRD；不把 WebShop/Java 作为第一周阻塞项。

6. **可复现。**  
   固定 seed、数据 manifest、模型版本、prompt、memory budget；一条命令重建 pilot。

### 6.2 Stage 1：MemoryCD-only influence simulator

**目的**：低成本验证效应是否存在，先跑通指标和写入策略。

**数据**：
- 从 MemoryCD 采样 20 个 pilot 用户，主实验扩展到 100 个用户；
- 覆盖至少 2 个域（Electronics + Books 起步）；
- 使用真实商品标题、类别、价格、历史交互；
- 原始数据不提交，只提交下载脚本和 manifest。

**会话构造**：
- 每个用户 5–10 个 session；
- 每个 session 有一个购物任务；
- agent 推荐 3–5 个商品；
- 用户以接受/拒绝/评分/澄清回应；
- 每次 session 结束，writer 写 memory；
- 下一次 session 从 memory 中检索。

**用户模拟器**：
- 输入：隐藏 `U_t`、上下文、agent 推荐、exposure；
- 输出：接受/拒绝、评分、简短理由、是否主动澄清；
- 接受概率随 `U_t` 与推荐属性的匹配度、exposure 强度、agent 措辞变化；
- 以概率 `η` 发生 internalization；
- 以概率 `p` 发生外生冲击。

**优点**：真实历史、成本低、可控、容易做消融。  
**局限**：对话是模板化的，不能完全代表真实用户。

### 6.3 Stage 2：AcCoRD text-only harness

**目的**：用更真实的交互和偏好动态验证外部效度。

**接入方式**：
- 先读取 AcCoRD 的场景 JSON；
- 用 target product + attributes 构造 mock catalog；
- 不启动 WebShop/Java；
- 复用 AcCoRD 的 user simulator 提示词和一致性检查；
- 加入跨会话 memory wrapper、动态 preference state、influence 注入；
- 先跑 10 个场景 smoke，再扩到 50/100 个。

**为什么先 text-only**：
- AcCoRD 的完整 WebShop 环境依赖重，容易拖 1–2 周；
- 我们的核心变量是 memory write，不是网页操作；
- text-only 足以测试“推荐 → 接受 → 写入 → 再推荐”的闭环。

**Stage 2 的额外价值**：
- 四类偏好动态可以测试不同 failure mode；
- 真实对话能暴露模板 simulator 看不到的措辞效应；
- 可作为论文的第二个 domain。

### 6.4 潜在状态与影响模型

每个用户有 K 个属性：

```text
U_t = (color, size, price_sensitivity, brand, material, ...)
```

每个属性有一个 preferred value 或分布。会话之间：

- 以概率 `p_shock` 发生外生冲击；
- 以概率 `η` 将本次 exposure 内化；
- 以概率 `p_noise` 产生一次性行为噪声；
- 记忆可能过期、冲突、过度泛化。

推荐曝光模型：

```text
P(accept = 1) = σ(
    α · match(U_t, item)
  + γ · exposure_strength
  + δ · agent_framing
  + context_term
  - cost_term
)
```

internalization 模型：

```text
P(internalize = 1) = σ(
    β0
  + β1 · repeated_exposure
  + β2 · context_diversity
  + β3 · independent_rechoice
  + β4 · persistence
  - β5 · explicit_correction
)
```

这些参数不是“真实人类心理学定律”，而是可控的实验旋钮。论文必须报告参数敏感性，不能只挑一个好看的点。

### 6.5 配对反事实世界

对每个用户和每个关键 session，构造两个世界：

```text
W0：无 agent 影响
    - agent 不推荐目标属性，或推荐中性选项
    - 用户仍可自主选择
    - 记录 U_t 的演化

W1：有 agent 影响
    - agent 推荐目标属性 X
    - 记录曝光、接受、是否内化
    - 记录 U_t 的演化
```

两个世界共享：

- 同一个初始 `U_0`；
- 同一个外生冲击序列；
- 同一个随机种子（在模拟器中）；
- 同一套商品库和上下文。

然后可以标注：

| 世界 0 行为 | 世界 1 行为 | 潜在偏好变化 | 标签 |
|---|---|---|---|
| 不接受 X | 接受 X | 无 | compliance |
| 不接受 X | 接受 X | 有且持续 | internalization |
| 接受 X | 接受 X | 有，但与曝光无关 | exogenous / pre-existing |
| 不接受 X | 不接受 X | 无 | no effect |
| 接受 X | 接受 X | 无 | stable preference / noise（需进一步区分） |

这张表是 benchmark 的核心。没有配对世界，CMR 只能靠启发式标注；有了配对世界，才能给出可辩护的 ground truth。

### 6.6 三个核心 schema

**A. `UserState`（隐藏，评测用）**

```json
{
  "user_id": "u001",
  "session_id": "s003",
  "attributes": {"color": "black", "size": "M", "price_sensitivity": 0.7},
  "shock": {"occurred": false, "type": null},
  "counterfactual": {"color": "blue", "size": "M", "price_sensitivity": 0.7}
}
```

**B. `InteractionEvent`（agent 可见）**

```json
{
  "event_id": "e001",
  "user_id": "u001",
  "session_id": "s003",
  "turn": 4,
  "agent_action": {"type": "recommend", "item_id": "i123", "attributes": {"color": "blue"}},
  "user_response": {"type": "accept", "item_id": "i123", "utterance": "..."},
  "exposure": {"attribute": "color", "value": "blue", "propensity": 0.82},
  "timestamp": "2026-10-30T10:00:00Z"
}
```

**C. `MemoryRecord`（可审计）**

```json
{
  "memory_id": "m001",
  "user_id": "u001",
  "attribute": "color",
  "value": "blue",
  "evidence_type": "agent_suggested_accepted",
  "source_event_ids": ["e001"],
  "influence_prob": 0.72,
  "confidence": 0.35,
  "validity": {"start": "2026-10-30", "end": null},
  "text": "User accepted blue after assistant recommendation; prior preference black; may be compliance."
}
```

关键字段不是 `text`，而是：

- `evidence_type`：主动选择 / 推荐后接受 / 独立复购 / 明确纠正；
- `source_event_ids`：能回溯到哪次交互；
- `influence_prob`：这次行为受 agent 影响的估计概率；
- `confidence`：是否足够稳定；
- `validity`：在哪些上下文/时间段有效。

### 6.7 Benchmark 任务

1. **Next-session recommendation**：给定历史与 memory，预测下一次会话用户会接受什么。
2. **Preference query**：问 agent “用户喜欢什么颜色/品牌/价位”，评测其回答是否区分稳定偏好与情境性选择。
3. **Memory audit**：给定 memory record，判断它是否 overclaim / provenance loss / scope inflation。
4. **Counterfactual replay**：删除或替换一条 memory，重放同一请求，测量行为变化。
5. **Downstream utility**：任务成功率、满意度、推荐质量、多样性。

主实验不必五个任务全做；建议主表用 1 + 2 + 5，诊断表用 3 + 4。

### 6.8 数据划分与泄漏控制

- **用户级划分**：train/dev/test 用户不重叠；per-user memory 不跨用户共享。
- **时间划分**：用过去 session 建 memory，预测未来 session；不能用未来信息写过去 memory。
- **场景划分**：AcCoRD 场景按 ID 划分，避免同模板泄漏。
- **隐藏状态隔离**：`U_t`、shock、compliance 标签绝不进入 agent prompt。
- **Judge 隔离**：LLM judge 不接触隐藏标签；人工校验抽样。
- **探索日志**：记录 propensity，评测时可用，写入时只能使用 agent 可见字段或预先设计好的探索策略。

---
## 7. 方法：Causal Memory Writer

### 7.1 总体思路

传统 memory writer：

```text
事件 → LLM 摘要 → “User prefers X” → 存储
```

我们的 writer：

```text
事件
  → 记录 provenance（agent action、exposure、用户回应、上下文）
  → 估计 influence / internalization
  → 选择记忆类型（episodic / hedged / durable）
  → 决定写 / 不写 / 等更多证据
  → 存储带来源、置信度、有效期的 MemoryRecord
```

核心原则：

> **记忆不是“用户是什么”的判决书，而是“我们目前有哪些证据、这些证据有多强”的审计记录。**

### 7.2 组件一：Provenance schema

每条记忆至少包含：

```text
attribute        # 颜色、尺寸、价格敏感度、品牌...
value            # 具体值
evidence_type    # 主动选择 / 推荐后接受 / 独立复购 / 明确纠正 / 推断
source_event_ids # 来源事件
exposure         # 用户是否被 agent 暴露了该值
influence_prob   # 该行为受 agent 影响的概率
confidence       # 作为稳定偏好的置信度
validity         # 生效时间、上下文、过期条件
counterevidence  # 是否存在相反证据
```

`evidence_type` 是最重要的字段。不同证据的权重不同：

| evidence_type | 解释 | 初始信任 |
|---|---|---|
| `explicit_statement` | 用户主动说“我喜欢 X” | 高 |
| `independent_choice` | 用户在没有推荐的情况下选择 X | 中高 |
| `repeat_purchase` | 跨时间、跨上下文复购 X | 高 |
| `agent_suggested_accepted` | agent 推荐后接受 X | 低到中 |
| `inferred` | agent 从行为中推断 | 低 |
| `corrected` | 用户明确纠正旧记忆 | 高，且触发旧记忆降权 |

### 7.3 组件二：Exposure propensity

我们需要知道：

```text
e(A_t | X_t) = P(agent 选择 action A_t | 上下文 X_t)
```

如果 agent 推荐蓝色耳机的概率是 0.9，而用户接受了蓝色，那么这条证据的“信息量”远低于用户在没有推荐时主动搜索蓝色。

实现方式：

- 如果 agent 是规则/排序系统，直接记录 propensity；
- 如果是 LLM agent，使用一个轻量的 propensity model，输入上下文、候选集合、历史，输出每个候选被展示/推荐的预测概率；
- 对 LLM 的随机性，记录 temperature、prompt 版本和候选集合；
- 不要求完美估计，但必须记录并做敏感性分析。

一个简化的 IPW 权重：

```text
w_t = 1 / e(A_t | X_t)
```

用于估计“在控制曝光概率后，行为变化与偏好的关系”。具体估计器可以是：

- IPW；
- self-normalized IPW；
- doubly robust；
- 在模拟器中使用已知 propensity 做 oracle 对照。

### 7.4 组件三：Randomized exploration

仅有观测 propensity 还不够：如果 agent 从不推荐某个候选，positivity 不成立。  
因此需要一定程度的随机探索：

- 以概率 `ε` 推荐非首选但合理的候选；
- 探索必须满足安全和质量约束；
- 记录探索成本和用户效用；
- 不让探索变成“为了实验故意推荐差东西”。

探索的作用不是“提升推荐效果”，而是 **制造外生 variation**，让 compliance 和 internalization 变得可识别。

需要报告：

- `ε` 从 0 到 0.3 的敏感性；
- 探索带来的短期效用损失；
- 探索是否改善了长期 CMR / SFB；
- 是否可以把探索限制在低风险属性上。

### 7.5 组件四：Negative controls

Negative control 的思想是：

> 如果只有被 agent 曝光的属性发生了变化，而未被曝光但同样合理的属性没有变化，那么变化更可能来自 agent 影响，而不是用户真实偏好漂移。

具体做法：

1. 选择一组与目标属性相关但未被曝光的属性；
2. 比较曝光属性和对照属性的变化；
3. 如果目标属性显著变化、对照属性不变，标记为高 influence；
4. 如果两者都变化，标记为可能的真实漂移或上下文变化；
5. 如果都不变化，标记为无效应。

还可以加入：

- **placebo outcome**：一个理论上不应受推荐影响的用户行为；
- **pre-trend check**：在推荐之前，目标属性是否已经在变化；
- **future persistence**：推荐结束后，变化是否持续。

Negative controls 不能单独证明因果，但能显著降低“把真实漂移误判为 compliance”的概率。

### 7.6 组件五：Persistence test

不要因为一次接受就写 durable preference。  
可以用一个简单的序贯规则：

```text
count = 0
for each new evidence:
    if evidence is agent-induced:
        count += 0.5
    if evidence is independent:
        count += 1.0
    if evidence is contradictory:
        count -= 1.0
    if count >= threshold and evidence spans >= k contexts:
        promote to durable preference
```

更好的做法是贝叶斯更新：

```text
P(durable | evidence_1:t) ∝ P(evidence_1:t | durable) P(durable)
```

并要求：

- 至少跨 `k` 个 session；
- 至少跨 `m` 个上下文；
- 至少有一次非推荐驱动的行为；
- 没有未解释的 explicit correction。

这些阈值要在 dev set 上选，不能直接在 test 上调。

### 7.7 组件六：Write / hedge / abstain 策略

不是所有事件都值得写。我们定义四种写入动作：

| 动作 | 适用情况 | 记忆形式 |
|---|---|---|
| `durable` | 多次独立证据、跨上下文、持久 | “用户偏好 X；证据：主动选择 + 复购” |
| `hedged` | 有证据但可能受 agent 影响 | “用户在推荐下接受了 X；可能是情境性偏好” |
| `episodic` | 一次性事件、任务性妥协 | “用户在 2026-10-30 的耳机任务中接受了 X” |
| `abstain` | 证据不足、冲突未解决、隐私/安全风险 | 不写入，或只写待验证假设 |

关键指标不是“写了多少”，而是：

- 写对的 durable 比例；
- 该 abstain 时是否 abstain；
- 该写时是否漏写；
- 后续检索是否能用上。

### 7.8 方法伪代码

```text
for each session t:
    observe interaction event e_t
    log provenance(e_t)
    estimate exposure propensity e_t.propensity
    estimate influence_prob(e_t) using:
        - exposure strength
        - agent framing
        - negative controls
        - prior history
    estimate internalization_prob(e_t) using:
        - repeated exposure
        - context diversity
        - independent rechoice
        - persistence
        - explicit correction
    choose write action:
        if internalization_prob high and persistence passed:
            write durable memory
        elif influence_prob high and evidence weak:
            write hedged memory
        elif event is task-specific:
            write episodic memory
        else:
            abstain or create hypothesis
    store MemoryRecord with provenance
```

### 7.9 方法的边界

- 如果 `η = 0`（agent 完全不影响偏好），proposed 不应比 naive 差太多；它应该主要表现为更谨慎的写入。
- 如果 `η` 很大但 `p_shock` 也很大，识别会变难；需要更多 exploration 或更强先验。
- 如果用户明确纠正，proposed 必须快速降权旧记忆；这是必要的安全属性。
- 如果没有 exploration，proposed 只能做“文本层面的 provenance 保留”，不能声称完全因果识别。

---

## 8. 评测指标

### 8.1 主指标

#### CMR：Compliance Misattribution Rate

**问题**：有多少 compliance 被写成了 durable preference？

**定义**：

```text
CMR = 被写成 durable preference 的 compliance 事件数
      / 所有 compliance 事件数
```

这个定义把“不写”计入分母，因此不会奖励完全沉默的 writer。  
同时报告一个条件版本：

```text
CMR_cond = 被写成 durable preference 的 compliance 事件数
           / 所有被写入的 compliance 事件数
```

**理想**：越低越好；但不能单独看，必须同时看覆盖率、质量和 IDR。

#### SFB：Self-Fulfilling Bias

**问题**：控制真实偏好后，记忆推断的偏好是否仍然朝 agent exposure 方向偏移？

**定义**：拟合

```text
\hat U_{i,t} = α + β · Exposure_{i,t} + γ · U_{i,t} + controls + ε
```

其中 `\hat U` 是 memory 推断出的偏好，`U` 是隐藏真实偏好。  
`β` 就是 SFB。理想值为 0；显著为正说明记忆把 agent 的曝光误当成了用户偏好。

也可以报告标准化系数和 bootstrap 置信区间。

#### IDR：Internalization Detection Rate

**问题**：真正内化的偏好，记忆有没有正确捕获？

```text
IDR = 被正确写成 durable preference 的 internalization 事件数
      / 所有 internalization 事件数
```

**理想**：越高越好。  
CMR 低但 IDR 也低，说明 writer 只是过度保守，不是真的更聪明。

#### Quality

**问题**：去偏之后推荐还有没有用？

包括：

- 任务成功率；
- 用户满意度；
- NDCG / ranking quality；
- 推荐多样性；
- 长期用户效用。

**约束**：proposed 相对 best baseline 的质量下降不超过 5%（预注册阈值）。

### 8.2 诊断指标

#### AL：Adaptation Lag

外生冲击后，记忆追上真实状态需要多少个 session：

```text
AL = min { k : |\hat U_{t+k} - U_{t+k}| < δ }
```

越小越好。用于区分“过度保守”与“稳健”。

#### OUR：Over-Update Rate

```text
OUR = 由噪声/agent 影响触发、但没有真实变化的更新数
      / 所有更新数
```

越低越好。

#### CR：Counterfactual Regret

在有 agent 影响的世界与无 agent 影响的世界之间，用户效用的差：

```text
CR = E[Utility(W0)] - E[Utility(W1)]
```

如果 memory 让 agent 过度推荐 X，CR 会上升。  
这是最接近“用户到底损失了什么”的指标。

#### Faithfulness

记忆文本是否忠实保留了：

- 来源事件；
- agent 是否推荐；
- 时间和上下文；
- 置信度；
- 反证。

可以用 LLM judge + 人工 100 条抽样校验。Judge 只做辅助，不作为唯一证据。

#### Diversity

推荐结果中不同属性/商品的分布。  
用于检测“记忆塌缩”：agent 越来越只推荐一个属性，即使质量指标没有下降。

### 8.3 指标关系

| 指标 | 测什么 | 太高 | 太低 |
|---|---|---|---|
| CMR | 误把 compliance 写成偏好 | 记忆污染 | 好 |
| IDR | 正确识别 internalization | 好 | 过度保守 |
| SFB | 记忆朝曝光方向漂移 | 自我实现 | 好 |
| AL | 冲击后适应速度 | 过时 | 可能过拟合噪声 |
| OUR | 错误更新 | 不稳定 | 好 |
| CR | 用户效用损失 | 伤害用户 | 好 |
| Quality | 推荐有用性 | 好 | 不可接受 |
| Faithfulness | 记忆可审计性 | 好 | 不可信 |
| Diversity | 选择空间 | 好 | 记忆塌缩 |

**主表**：CMR、SFB、IDR、Quality。  
**副表**：AL、OUR、CR、Faithfulness、Diversity。  
所有指标报告均值、95% CI、按 domain 拆分。

---

## 9. 实验设计

### 9.1 Baselines

| Baseline | 作用 |
|---|---|
| No memory | 下界；没有跨会话个性化 |
| Recency / last-write-wins | 最简单的时序策略 |
| Summarize-all | 直接把对话摘要写入 |
| Mem0 | 生产级记忆系统 |
| Letta / MemGPT | 分层记忆与上下文管理 |
| A-MEM | 结构化/关联记忆 |
| CAPTURE-style POMDP | belief tracking baseline（重实现） |
| CALMRec-style IPW | exposure debias baseline（重实现） |
| Oracle latent | 上界；直接使用真实 `U_t` |
| Proposed | provenance + propensity + exploration + controls + persistence |

**重要实验设计**：把“memory backend”和“writer policy”解耦。

- 固定 backend（如 Mem0），比较 naive / provenance / proposed writer；
- 固定 writer，比较 Mem0 / Letta / A-MEM 的检索行为；
- 这样才能回答：收益来自写入策略，还是来自后端。

### 9.2 主实验矩阵

| 阶段 | 数据 | 方法 | seeds | 目的 |
|---|---|---|---|---|
| Stage 1 pilot | MemoryCD 20 用户 × 5 sessions | naive / provenance / proposed | 3 | 验证效应和指标 |
| Stage 1 main | MemoryCD 100 用户 × 10 sessions | 全部 baseline | 3–5 | 主结果 |
| Stage 2 pilot | AcCoRD-Shop 10 场景 | naive / provenance / proposed | 3 | 验证交互接入 |
| Stage 2 main | AcCoRD-Shop 100 场景 | 全部 baseline | 3 | 外部效度 |
| Stage 2 optional | AcCoRD-Travel 子集 | 最佳 3 个方法 | 3 | 跨域稳健性 |

### 9.3 消融

1. 去掉 provenance 字段；
2. 去掉 propensity；
3. 去掉 randomized exploration；
4. 去掉 negative controls；
5. 去掉 persistence test；
6. 只用 prompt 让 LLM “注意 compliance”；
7. 只写 hedged memory，不写 durable；
8. 不同 memory budget；
9. 不同 `ε`；
10. 不同 `η` / `p_shock`；
11. 不同 LLM（frontier vs. small model）；
12. 不同 judge（LLM vs. human）。

### 9.4 敏感性分析

- `η` 从 0 到 1：影响强度；
- `p_shock` 从 0 到 0.3：真实漂移频率；
- `ε` 从 0 到 0.3：探索成本；
- memory budget：10 / 50 / 200 条；
- session 长度：5 / 10 / 20；
- 用户数：20 / 100；
- 商品属性维度：4 / 8 / 16。

敏感性分析的目的不是找“最容易显著”的设置，而是展示结论在什么条件下成立、在什么条件下失效。

---
### 9.5 统计方案

- **分析单位**：用户/场景，不以单条 memory 为独立样本，避免伪重复。
- **配对设计**：同一用户的有影响/无影响世界配对比较。
- **置信区间**：user-level paired bootstrap，至少 1,000 次重采样。
- **混合效应模型**：`metric ~ method + domain + (1 | user) + (1 | scenario)`。
- **主指标预注册**：CMR、SFB、IDR、Quality；其余为探索性分析。
- **多重比较**：主指标用 Holm-Bonferroni；副指标标注 exploratory。
- **效应量**：报告绝对差、相对差、95% CI，不只报 p 值。
- **可复现性**：3 seeds；主表用 mean ± std；保留每个 run 的原始输出。

### 9.6 里程碑与 Go/No-Go

| Gate | 时间 | 条件 | 不通过时 |
|---|---|---|---|
| **G1** | 第 2 周末 | naive CMR ≥ 20%；provenance 相对下降 ≥ 30% | 调 influence 强度/domain；若 CMR < 10%，考虑转向诊断工具 |
| **G2** | 第 4 周末 | AcCoRD text-only 端到端跑 10 场景；对话不崩；CMR/SFB 可测 | 退回 MemoryCD-only；不接 WebShop |
| **G3** | 第 6 周末 | proposed 显著优于 best baseline；quality 下降 < 5% | 缩小 claim，改为诊断/benchmark 论文 |
| **G4** | 第 8 周末 | 3 seeds、2 domains 方向一致 | 补实验或降级为 workshop |

### 9.7 杀手实验

> 在 20 轮跨会话交互中，naive memory 推断出的偏好会随 agent exposure 系统性偏移；控制真实偏好后，SFB 显著大于 0。proposed writer 显著降低 CMR/SFB，同时推荐质量和多样性不出现不可接受的下降。

这个实验同时需要：

1. 一条随 exposure 增强的 drift 曲线；
2. 一条 provenance/causal writer 的下降曲线；
3. 一条 quality/diversity 的代价曲线；
4. 一个反事实 replay 的具体 case study。

只有“CMR 下降”不够；必须证明不是通过“少写”或“推荐变差”换来的。

---

## 10. 结果预期与失败判据

### 10.1 预期结果

- naive memory 在受控 exposure 下产生可测的 CMR；
- SFB 随 exposure 强度上升；
- provenance writer 降低 overclaim，但对 internalization 的识别有限；
- 加入 exploration / negative controls 后，CMR 和 SFB 进一步下降；
- proposed 在 quality 上的损失可控，且 diversity 不塌缩；
- 在 MemoryCD 与 AcCoRD 上方向一致。

### 10.2 失败判据

以下任一情况出现，说明 idea 需要收缩或转向：

1. **CMR 在所有 domain 都低于 10%**：agent 诱导效应太弱，核心叙事不成立。
2. **provenance prompt 已经解决 80% 以上问题**：复杂因果机制不必要，应转向轻量诊断工具。
3. **proposed 的收益完全来自少写**：coverage/quality 大幅下降，说明方法没有真正识别。
4. **只在合成 simulator 中成立**：外部效度不足，需要真实数据或 human study。
5. **效应无法与普通 recency/冲突检测区分**：novelty 不足，需重新定位。
6. **用户的明确纠正无法快速修正记忆**：安全属性失败，方法不可接受。

### 10.3 如果失败，还能留下什么

即使主方法不成立，以下产出仍有价值：

- 一个 agent-induced drift 的诊断 benchmark；
- 一套 CMR/SFB 指标和可视化；
- 一份现有 memory 系统的审计报告；
- 一个 provenance schema 和 counterfactual replay 工具；
- 一篇“为什么 prompt-only 修复不够”的负面结果论文。

这也是为什么项目不应把全部赌注押在“proposed 必须赢”上。

---

## 11. 贡献与论文定位

### 11.1 目标贡献

1. **概念贡献**：提出 agent-induced drift，并把它与普通偏好漂移、记忆冲突、投毒、过度个性化区分开。
2. **形式化贡献**：把 memory write 形式化为因果归因问题，给出 compliance/internalization 的定义和识别边界。
3. **数据贡献**：构建带配对反事实世界的跨会话 benchmark，结合真实历史与交互场景。
4. **方法贡献**：提出 provenance-aware causal writer，并系统比较 prompt-only、IPW、POMDP、结构化记忆等 baseline。
5. **实证贡献**：量化现有系统把 compliance 写成 preference 的程度，以及修复的收益/代价。

### 11.2 论文标题候选

- *Compliance Is Not Preference: Agent-Induced Drift in Long-Term Memory*
- *The Self-Fulfilling Memory: Causal Attribution of Preference Drift in LLM Agents*
- *Memory Is Not Evidence: Debiasing Long-Term Memory Writes under Agent Influence*
- *Write What You Know: Provenance-Aware Memory for Agent-Induced Drift*

推荐第一个作为主标题：直接、可读、点明核心区分。

### 11.3 目标 venue

- **主**：ACL / EMNLP / NAACL（agents、memory、personalization）；
- **次**：NeurIPS / ICML（benchmark + causal method）；
- **应用**：RecSys（推荐与曝光偏差）；
- **保底**：NeurIPS MemAgents workshop、ACL workshop。

### 11.4 不能声称的内容

- 不能声称“真实用户一定如此”，除非做了真实用户研究；
- 不能声称“proposed 解决了所有记忆漂移”；
- 不能把 2026 年预印本说成已同行评审；
- 不能把模拟器中的因果效应直接外推到生产环境；
- 不能把“CMR 降低”说成“用户效用提升”，除非 Quality/CR 支持；
- 不能把“记忆写得更少”当作主要卖点。

---

## 12. 可行性与资源

### 12.1 已有底座

| 资产 | 用途 | 可用性 | 注意 |
|---|---|---|---|
| **AcCoRD**（arXiv:2608.27818） | 交互场景、user simulator、偏好动态 | MIT；代码公开 | WebShop 环境重，先 text-only |
| **MemoryCD**（arXiv:2603.25973） | 真实用户历史、商品库 | 仓库 MIT；HF 数据 | 数据源自 Amazon Reviews 2023，遵守上游条款 |
| **MemGym**（arXiv:2605.20833） | memory 接口、评测循环 | Apache 2.0 | 作为接口参考 |
| **CALMRec**（arXiv:2607.23647） | propensity / identification 思路 | 代码未确认 | 按论文重实现 baseline |
| **CAPTURE**（arXiv:2609.02265） | POMDP belief tracking | 代码未找到 | 只作为概念 baseline |
| **ULSPB**（arXiv:2605.06731） | 现象与任务设计参考 | 无 LICENSE | 不直接复用代码 |
| **ConMem / MemAlign**（arXiv:2610.33432） | 反事实 retention 设计 | 代码未找到 | 只读思路 |
| **Mem0 / Letta / A-MEM** | 真实 memory backend | 开源/文档可用 | 适配成本主要在接口 |

### 12.2 10 周实施节奏

| 周 | 目标 | 关键产出 |
|---|---|---|
| 1 | schema 冻结、最小闭环 | 20 用户子集、MemoryBackend、writer v0、metrics 骨架 |
| 2 | MemoryCD pilot | CMR/SFB pilot 报告、Gate 1 |
| 3 | AcCoRD text-only harness | 5–10 场景跑通、跨会话 memory |
| 4 | AcCoRD pilot + 识别假设 | 50 场景、compliance 标签、Gate 2 |
| 5 | method v1 + 主实验矩阵 | causal writer、baseline 对齐 |
| 6 | 主结果 | Gate 3、主表 |
| 7 | 消融与稳健性 | 参数敏感性、失败案例 |
| 8 | 多种子/多域 | Gate 4、human eval 小样本 |
| 9 | 论文初稿 | 全文 v1、复现包 |
| 10 | 投稿/开源 | arXiv、GitHub、leaderboard |

详细分工见 `2026-10-30_Agent-Induced-Drift_5人10周项目计划.md`。

### 12.3 五人角色

| 角色 | 职责 |
|---|---|
| **P1 Lead / 因果与评测** | 问题定义、DAG、指标、实验协议、论文叙事 |
| **P2 Sim / Data** | MemoryCD、catalog、AcCoRD harness、influence simulator |
| **P3 Memory** | memory 接口、Mem0/Letta/A-MEM 适配、日志、反事实回放 |
| **P4 Method** | causal writer、propensity、exploration、negative controls、prompt |
| **P5 Eval / Analysis** | metrics、统计、judge、图表、错误分析 |

### 12.4 预算

- LLM API：$2,000–5,000；
- Human annotation：$500–1,000；
- GPU：可选，1–2 张 A100 或 4 张 4090；
- 总计：约 $3,000–7,000。

预算的关键不是模型规模，而是 **探索实验和多种子重跑**。如果预算紧张，优先保证 Stage 1 + 3 seeds，而不是盲目扩 AcCoRD 场景数。

---
## 13. 风险与预案

| 风险 | 概率 | 影响 | 预案 |
|---|---:|---|---|
| AcCoRD WebShop 依赖太重 | 高 | 拖 1–2 周 | 先 text-only；不启动 Java/WebShop |
| CALMRec 代码不可得 | 高 | baseline 缺失 | 按论文重实现 IPW；不依赖作者 |
| 效应太小（CMR < 10%） | 中 | 论文不成立 | 加强 influence γ；换 gift/fashion domain；转向诊断工具 |
| 收益来自少写记忆 | 中 | 方法无价值 | 同时报告 coverage、quality、diversity |
| 合成用户被质疑 | 高 | 审稿风险 | MemoryCD 真实历史 + human eval 小样本 |
| LLM judge 偏差 | 中 | 指标不可信 | judge-free 指标 + 人工校验 |
| 真实数据隐私/条款 | 中 | 不能发布 | 只发派生/合成数据；提供下载脚本 |
| 被别人 scoop | 中 | novelty 下降 | 每月 arXiv 扫描；W4 前挂项目页/草稿 |
| 识别假设过强 | 高 | 审稿人质疑 | 模拟器做识别，真实数据只做外部效度 |
| prompt-only 已足够 | 中 | 方法贡献不足 | 把 prompt-only 作为 ablation；强调无外生 variation 的识别边界 |

### 13.1 最大的科学风险

不是工程做不出来，而是：

> **审稿人认为这只是推荐系统 feedback loop 的已知问题，加了一个 LLM memory 的包装。**

应对方式：

- 必须展示 LLM-specific 的放大机制：自然语言摘要丢失 provenance、措辞改变用户反应、记忆写成 trait、跨会话置信度复利；
- 必须给出因果形式化和识别边界，而不是只做相关性分析；
- 必须有一个“无外生 variation 就无法识别”的清晰论证；
- 必须报告 negative result 和失败案例，而不是只挑好结果。

### 13.2 最大的工程风险

AcCoRD 的完整环境可能拖慢进度。  
因此第 1–2 周只做 MemoryCD-only；第 3 周才接 text-only AcCoRD；WebShop 永远不是关键路径。

### 13.3 最大的伦理风险

“agent 影响用户偏好”本身可以是良性个性化，也可以是操纵。  
我们需要明确边界：

- 不设计欺骗性说服；
- 不针对脆弱人群；
- 不隐藏关键选项；
- 不把探索率用于真实用户而不告知；
- 研究阶段只在模拟器/受控环境进行；
- 真实部署需要 IRB/同意/退出机制。

---

## 14. 伦理、限制与边界

### 14.1 伦理

- 研究在模拟用户和公开数据上进行，不直接操纵真实用户。
- 如果后续做 human study，必须获得知情同意，并提供退出机制。
- 不把“提高用户接受率”作为优化目标；优化目标是“记忆归因正确 + 用户长期效用”。
- 记忆审计可能涉及隐私；真实部署应采用本地化/最小化存储。

### 14.2 限制

1. **模拟器限制**：用户行为由模型生成，可能与真实人类不同。
2. **数据限制**：MemoryCD 是 Amazon Reviews 派生数据，存在选择偏差。
3. **时间限制**：10 周只能做短期漂移，不能观察数月/数年。
4. **识别限制**：真实数据无法完全满足 sequential ignorability。
5. **Judge 限制**：LLM judge 可能偏向长文本、自信语气或特定模型。
6. **Domain 限制**：购物场景不能代表医疗、金融、法律等高风险领域。
7. **方法限制**：provenance 和 propensity 只能降低偏差，不能消除所有未观测混杂。

### 14.3 适用边界

本 idea 最适合：

- 有跨会话记忆的个性化 agent；
- 推荐/购物/内容选择等行为可观测的场景；
- 用户选择受曝光和措辞影响明显的场景；
- 有明确用户效用可以评估的场景。

不适合直接外推到：

- 高风险医疗/法律决策；
- 用户偏好本身不可观测的场景；
- 没有交互日志的纯批量推荐；
- 需要强因果保证但没有随机化的生产系统。

---

## 15. 交付物

### 15.1 研究交付

- 问题定义与因果 DAG；
- benchmark 设计与数据 schema；
- MemoryCD + AcCoRD 的 harness；
- CMR/SFB/IDR 等指标实现；
- 主实验、消融、敏感性分析；
- 论文初稿与附录；
- 失败案例与 negative results。

### 15.2 工程交付

```text
inflmem/
  data/          # loader, catalog, manifest
  sim/           # influence simulator, AcCoRD text harness
  memory/        # base, mock, mem0, letta, amem
  method/        # causal writer, propensity, exploration
  eval/          # metrics, judges, stats
  analysis/      # plots, tables
  scripts/       # run_pilot.py, make_tables.py
  docs/          # problem, dag, metrics, decisions
  tests/         # unit + golden tests
```

### 15.3 开源交付

- GitHub 仓库（Apache 2.0，代码）；
- 数据下载脚本与 manifest（不重新分发原始 Amazon 数据）；
- 可复现配置与 leaderboard；
- 一页 README quickstart；
- 反事实 replay demo；
- 记忆审计报告模板。

---

## 16. 参考文献与链接

> 2026 年论文多为预印本，引用时需注明“preprint / under review”，不要写成已同行评审。

### 核心底座

1. **AcCoRD**: Evaluating User-Agent Collaboration Under Realistic User Preference Dynamics. arXiv:2608.27818.  
   https://arxiv.org/abs/2608.27818  
   https://github.com/tejas1995/accord_benchmark

2. **MemoryCD**: Benchmarking Long-Context User Memory of LLM Agents for Lifelong Cross-Domain Personalization. arXiv:2603.25973.  
   https://arxiv.org/abs/2603.25973  
   https://github.com/AgentMemoryWorld/MemoryCD  
   https://huggingface.co/datasets/WZDavid/MemoryCD

3. **CALMRec**. arXiv:2607.23647.  
   https://arxiv.org/abs/2607.23647

4. **CAPTURE**: Disentangling Preference Drift from Memory Poisoning in Personalized LLM Agents. arXiv:2609.02265.  
   https://arxiv.org/abs/2609.02265

5. **ULSPB**. arXiv:2605.06731.  
   https://arxiv.org/abs/2605.06731  
   https://github.com/XiaoyuXU1/ULSPB

6. **ConMem / MemAlign**. arXiv:2610.33432.  
   https://arxiv.org/abs/2610.33432

7. **MemGym**. arXiv:2605.20833.  
   https://arxiv.org/abs/2605.20833  
   https://github.com/WujiangXu/MemGym

### 记忆系统与评测

8. **MemGPT**: Towards LLMs as Operating Systems. arXiv:2310.08560.  
   https://arxiv.org/abs/2310.08560

9. **Mem0**: Building Production-Ready AI Agents with Scalable Long-Term Memory. arXiv:2504.19413.  
   https://arxiv.org/abs/2504.19413

10. **A-MEM**: Agentic Memory for LLM Agents. arXiv:2502.12110.  
    https://arxiv.org/abs/2502.12110

11. **Zep**: A Temporal Knowledge Graph Architecture for Agent Memory. arXiv:2501.13956.  
    https://arxiv.org/abs/2501.13956

12. **LongMemEval**. arXiv:2410.10813.  
    https://arxiv.org/abs/2410.10813

13. **Evaluating Very Long-Term Conversational Memory of LLM Agents**. arXiv:2402.17753.  
    https://arxiv.org/abs/2402.17753

### 偏好漂移、冲突与个性化

14. **BeliefShift**. arXiv:2603.23848.  
    https://arxiv.org/abs/2603.23848

15. **MemConflict**. arXiv:2605.20926.  
    https://arxiv.org/abs/2605.20926

16. **OP-Bench**: Benchmarking Over-Personalization for Memory-Augmented Personalized Conversational Agents. arXiv:2601.13722.  
    https://arxiv.org/abs/2601.13722

17. **PRAGMA**. arXiv:2609.09664.  
    https://arxiv.org/abs/2609.09664

18. **Stale, Misattributed, or Late: Where Personal Memory Fails Before Generation**. arXiv:2610.10265.  
    https://arxiv.org/abs/2610.10265

19. **FinPerMA**. arXiv:2608.04095.  
    https://arxiv.org/abs/2608.04095

20. **Ground Truth First**. arXiv:2607.21962.  
    https://arxiv.org/abs/2607.21962

---

## 附录 A：完整运行示例

### Session 1

用户：

> “我想买一副通勤用的耳机，黑色比较百搭，预算 1000 以内。”

agent 发现黑色缺货，推荐蓝色：

> “黑色暂时没货，这款蓝色同配置，今天 899。”

用户：

> “行吧，蓝色也可以。”

**隐藏状态**：`U = {color: black}`，没有变化。  
**行为**：接受蓝色。  
**标签**：compliance。  
**naive memory**：`User prefers blue headphones.`  
**provenance memory**：`User accepted blue after agent recommended it because black was out of stock; prior preference black; possible compliance; confidence 0.3; context: commute headphones.`

### Session 2

agent 检索到 “prefers blue”，只展示蓝色：

> “根据你之前的偏好，这几款蓝色耳机更适合你。”

用户：

> “可以，就这个。”

**隐藏状态**：仍然 `color: black`。  
**标签**：compliance（重复暴露）。  
**naive memory**：`User strongly prefers blue; repeated acceptance confirms.`  
**provenance memory**：`Second acceptance occurred under agent-initiated blue-only recommendation; not independent evidence; confidence remains low.`

### Session 3

用户主动说：

> “其实我还是想要黑色，上次是没货才买的蓝色。”

**标签**：explicit correction。  
**proposed**：旧蓝色记忆降权，新增“用户明确纠正，黑色是首选”；不把纠正当成一次性噪声。

### Session 4（真正的 internalization）

几周后，用户在没有推荐的情况下主动搜索蓝色，并在不同场景（运动耳机）选择蓝色；跨两个上下文、两次独立选择。

**标签**：internalization。  
**proposed**：将蓝色从 hedged 升级为 durable，但保留“最初由推荐引入”的 provenance。

这个例子说明：

- 单次接受不能区分 compliance / internalization；
- 重复接受也可能是 agent 造成的；
- 真正的 internalization 需要独立、跨上下文、持续的证据；
- 记忆应该能表达“不确定”和“有条件”，而不是二值化。

---

## 附录 B：一页 Pitch

**问题**：长期记忆把“用户接受了 agent 推荐的 X”写成“用户偏好 X”，但接受可能是 compliance；错误记忆会通过后续推荐自我强化。

**现有空白**：AcCoRD 有交互但没有跨会话 memory 和 agent influence；MemoryCD 有真实历史但没有交互；CALMRec 有 exposure debias 但不是自然语言 memory write；CAPTURE 区分漂移/投毒但不把 agent action 当因。

**方案**：把 memory write 当成因果归因；用 provenance、exposure propensity、随机探索、negative controls、persistence test 决定写什么、怎么写、写多确信。

**Benchmark**：同一用户、同一冲击，构造有/无 agent 影响的配对世界，标注 compliance / internalization / exogenous / noise。

**指标**：CMR、SFB、IDR、Quality；辅以 AL、OUR、CR、Faithfulness、Diversity。

**杀手实验**：naive memory 的推断偏好随 exposure 系统性漂移；proposed 降低 CMR/SFB，且 quality 下降 < 5%。

**可行性**：MemoryCD + AcCoRD 双底座，MIT/Apache 资产可用；5 人 10 周可完成 pilot 和主实验。

**风险**：效应太小、prompt-only 已足够、合成用户外部效度不足。对应 Gate 和转向方案已写入计划。

---

## 附录 C：当前状态

截至本文档日期：

- 已完成：文献调研、底座论文筛选、问题定义、benchmark 设计、指标设计、10 周工程计划；
- 已下载/核对：AcCoRD 代码与场景、MemoryCD 代码与数据说明；
- 尚未完成：influence simulator、MemoryBackend 适配、pilot 实验、主实验、human eval、论文写作；
- 因此本文档中的效应大小、CMR 数值、质量代价均为待验证假设，不是实验结果。

---

*本文档用于团队内部讨论和项目立项，不构成对真实用户行为的因果结论。*

