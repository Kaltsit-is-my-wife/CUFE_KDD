# Goal Drift PoC — 实验结果摘要

生成时间由本次程序运行决定；随机种子固定为 `20251025`。本实验是**规则基线与合成数据上的受控模拟**，没有调用大模型或外部模型服务，结果不代表真实 LLM Agent 的实测效果。

## 数据

- 轨迹总数：48；每条 10 个会话，共 480 个会话。
- 场景分布：abrupt_drift=12, gradual_drift=12, stable=12, topic_switch=12。
- 漂移真实标签只在指标评估中使用。检测器接口仅接收 `session_id` 与截至当前的 `text`，并通过前缀不变性断言检查未来信息泄漏。

## 漂移检测

| method | precision | recall | f1 | false_positive_rate | mean_detection_delay | mean_localization_error | drift_type_accuracy | topic_switch_false_positives |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_a_topic | 0.000 | 0.000 | 0.000 | 0.500 | nan | nan | 0.000 | 12.000 |
| baseline_b_persistence | 1.000 | 1.000 | 1.000 | 0.000 | 1.333 | 2.833 | 0.000 | 0.000 |
| method_c_sustained | 1.000 | 1.000 | 1.000 | 0.000 | -0.500 | 1.000 | 1.000 | 0.000 |

`mean_detection_delay = detected_at - confirmation_session`，负值表示在人工设定的确认点之前预警；`mean_localization_error = |detected_at - drift_start|`。普通话题切换误报数量单独列出。

## 记忆更新

| strategy | obsolete_interference_rate | valid_memory_retention_rate | obsolete_precision | obsolete_recall | obsolete_f1 | incorrect_downweight_rate | memory_update_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| no_update | 0.275 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| time_decay | 0.169 | 0.551 | 0.306 | 1.000 | 0.468 | 0.510 | 18.000 |
| drift_aware | 0.172 | 1.000 | 1.000 | 0.515 | 0.680 | 0.000 | 2.833 |

干扰率按目标记忆的加权占比计算；保留率是仍有效记忆相对原始权重的平均值。更新数量不是删除数量，Strategy C 只把不兼容的旧目标记忆降至 0.12，背景记忆保留。

## 端到端任务

| strategy | task_success_rate | old_goal_conflict_rate | constraint_satisfaction_rate | background_utilization_rate |
| --- | --- | --- | --- | --- |
| no_update | 0.667 | 0.333 | 0.667 | 1.000 |
| time_decay | 1.000 | 0.000 | 1.000 | 1.000 |
| drift_aware | 0.722 | 0.278 | 0.833 | 1.000 |

任务是确定性选择当前成本偏好、执行偏好和背景约束；成功要求两个当前目标约束与背景约束全部满足。每条轨迹从确认会话（无漂移轨迹从 session 7）开始连续评估 3 个在线任务，每次只能读取当时及以前的记忆和检测输出，共 144 个任务实例、432 条策略评分记录。

## 真实失败案例

- 轨迹 `topic_switch-00`，场景 `topic_switch`，方法 `baseline_a_topic`：真实确认位置 `nan`，预测位置 `1.0`。这是本次输出中实际筛选出的误报或漏报，而非手工编造。

## 三条主要发现

1. 相邻话题变化基线产生 12 个普通话题切换误报；持续性基线和 Method C 在本数据上的 F1 均为 1.000，但 Method C 平均比人工确认点提前 0.500 个会话，并正确区分两种漂移类型。
2. 漂移感知策略把过时干扰率从 0.275 降到 0.172，有效记忆保留率仍为 1.000；但其过时记忆召回仅 0.515，是明确失败点。
3. 时间衰减的任务成功率最高（1.000），漂移感知为 0.722，不更新为 0.667；代价是时间衰减的有效记忆保留率仅 0.551。因此当前结果不支持“漂移感知策略全面优于简单衰减”。

## 局限与下一步

- 合成文本的词表、漂移时间和规则检测器同源，外部有效性有限；轨迹规模仅 48。
- 规则抽取没有处理真实语言中的否定、隐喻、目标层级、相互矛盾证据和工具反馈。
- 下一阶段应在获得同意的真实 Agent 多会话日志上盲标漂移，用真实模型的任务输出做人工与自动双重评分，并测试检测阈值跨域泛化。
- 当前任务决策器是规则系统；不能把本结果表述为 LLM Agent 性能提升。

## 复现

从项目根目录运行：

```powershell
python src/run_experiment.py
python src/run_experiment.py --check-determinism
```

第二条命令在同一进程中连续运行两次，并比较核心 JSON/CSV/PNG/Markdown 的 SHA-256；全部一致才返回成功。

本次一致性检查状态：`PASS`（两次运行的 11 个核心产物 SHA-256 全部一致）。

## 文件路径

- 项目根目录：`D:\数据挖掘KDD\验证实验\goal-drift-poc`
- 合成轨迹：`D:\数据挖掘KDD\验证实验\goal-drift-poc\data\trajectories.json`
- 汇总结果目录：`D:\数据挖掘KDD\验证实验\goal-drift-poc\results`
- 必需结果：`trajectory_data.csv`、`detection_metrics.csv`、`memory_metrics.csv`、`task_metrics.csv`、`predictions.csv`、`detection_comparison.png`、`memory_comparison.png`、`task_success_comparison.png`、`experiment_summary.md`。
