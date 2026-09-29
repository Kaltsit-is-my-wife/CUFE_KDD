# 全局进度

本文件是仓库内唯一的 idea/实验进度总表，不依赖外部项目管理工具。每次新增、状态变化、负责人变化或实验结论更新时同步修改。

## 状态定义

- `idea`：已登记，仍在讨论问题与假设。
- `planned`：方案和验收指标已明确，等待实现。
- `in-progress`：正在实现或运行实验。
- `blocked`：存在待解决的数据、资源或方法阻塞。
- `completed`：实验完成，结论和限制已记录。
- `archived`：废弃、暂停或被后续工作替代，但历史保留。

## Idea 与实验总表

| 编号 | Idea | 实验 | 主题 | 负责人 | 协作者 | Idea 状态 | 实验状态 | 核心假设摘要 | 基线 | 主要指标 | 数据集/版本 | 最近更新 | 下一步 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 000 | [模板](ideas/000-template/) | [模板](experiments/000-template/) | 示例模板，不是实际项目 | @team | @member-01, @member-02 | archived | archived | 待填写 | 待填写 | 待填写 | 待填写 | 2026-09-14 | 复制模板创建新编号 |
| 001 | [个人调研与想法总目录](ideas/001-my-research-idea/) | not-started | 个人调研累积容器（文献精读 + idea 候选） | @YuchenLiu | 待定 | idea | not-started | 调研容器，无单一核心假设；子课题成熟后须另开正式编号 | — | — | — | 2026-09-27 | 子课题成熟时另开编号并登记，已衍生出 002 |
| 002 | [Agent 交互间的语义漂移探测](ideas/002-agent-interaction-drift-idea/) | not-started | 多 agent 交互间的语义漂移检测 | @YuchenLiu | 待定 | idea | not-started | 若将 agent 交互轮编码为可稳定标注的语义原子（role/goal-atom/tool-action/commitment/constraint），则相对 post-hoc 行为指标，逐轮累积原子级转移矩阵能在漂移发生的那一步给出可定位信号，因行为指标是滞后聚合、无法对齐轮次 | post-hoc 行为指标（role adherence、ASI 类复合分）；相邻轮强基线 | 标注一致性 Cohen's κ；漂移率 vs 置换零分布；单步定位 F1 | 待定（候选：CAMEL/AutoGen/MetaGPT 日志 + 自建可控轨迹） | 2026-09-29 | 完成 P1 探针（语义原子标注一致性 κ ≥ 0.6）作为 go/no-go |

## 变更记录

| 日期 | 编号 | 变更 | 记录人 |
|---|---|---|---|
| 2026-09-14 | 000 | 初始化仓库模板 | @team |
| 2026-09-29 | 002 | 新增 idea「Agent 交互间的语义漂移探测」；贡献定位由"方法迁移"改为"语义本体 + 单步在线检测"；租服务器暂缓至探针定稿 | @YuchenLiu |
| 2026-09-29 | 001 | 补登记 001（个人调研容器）进总表，此前遗漏 | @YuchenLiu |
| 2026-09-29 | — | `.gitignore` 新增规则：`相关论文/`（版权 PDF）与 `sandbox/` 下个人草稿不入库，保留 `sandbox/` 目录结构说明文件 | @YuchenLiu |

## 使用约定

- 编号从 `001` 开始递增，编号一旦分配不复用。
- `Idea` 链接指向 `ideas/NNN-short-name-idea/`，`实验` 链接指向同编号的 `experiments/NNN-short-name/`。
- 表格中的状态必须和对应目录 README 的状态一致。
- 指标写简短结果摘要，详细曲线、误差分析和配置放在实验目录。
- 没有实验时，实验状态填写 `not-started`；归档时不要删除行。
