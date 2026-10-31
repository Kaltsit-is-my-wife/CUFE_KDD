# Phase 2 Goal Drift PoC 实验总结

本实验是规则方法和合成数据的受控验证，不是真实 LLM Agent 实测。生成种子 `20261025`，轨迹级 Bootstrap 种子 `20261026`。

## 数据与盲测边界

- 共 168 条轨迹；开发集 56，测试集 112。按完整轨迹划分，无会话跨组。
- 测试集每场景 16 条；检测器只读 `data/interactions.json`，预测完成后评估器才读取 `data/labels.json`。
- 检测、记忆阈值只通过开发集选择；测试集只运行一次最终配置。选定参数见 manifest。

## 测试集检测

| method | precision | recall | f1 | false_positive_rate | localization_hit_rate_tolerance_2 | mean_abs_localization_error | mean_detection_delay | tp | fp | fn | tn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_a_topic | 0.564 | 0.969 | 0.713 | 1.000 | 0.323 | 3.661 | -4.129 | 62.000 | 48.000 | 2.000 | 0.000 |
| baseline_b_persistence | 0.865 | 1.000 | 0.928 | 0.208 | 0.594 | 2.531 | 1.531 | 64.000 | 10.000 | 0.000 | 38.000 |
| method_c_original | 0.829 | 0.984 | 0.900 | 0.271 | 0.952 | 0.746 | -0.238 | 63.000 | 13.000 | 1.000 | 35.000 |
| method_d_evidence | 0.914 | 1.000 | 0.955 | 0.125 | 0.984 | 0.406 | 1.609 | 64.000 | 6.000 | 0.000 | 42.000 |

无漂移轨迹的 Detection Delay 保持 NA，只单独计误报。分场景结果见 `phase2_detection_metrics.csv`。

## 测试集记忆（在线任务时点 overall）

| strategy | obsolete_precision | obsolete_recall | obsolete_f1 | obsolete_interference_rate | valid_memory_retention_rate | incorrect_downweight_rate | mean_update_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| no_update | 0.000 | 0.000 | 0.000 | 0.404 | 1.000 | 0.000 | 0.000 |
| time_decay | 0.460 | 0.600 | 0.521 | 0.371 | 0.578 | 0.476 | 12.648 |
| drift_aware_original | 0.984 | 0.480 | 0.646 | 0.282 | 0.995 | 0.005 | 4.735 |
| drift_aware_improved | 0.994 | 0.793 | 0.882 | 0.192 | 0.993 | 0.003 | 7.873 |

分类别与轨迹末端结果也在同一 CSV 中，以 `evaluation_scope` 区分。低干扰不能脱离有效记忆保留率解读。

## 配对任务与轨迹级 95% Bootstrap CI

| strategy | estimate | ci_low | ci_high | n_trajectories |
| --- | --- | --- | --- | --- |
| drift_aware_improved | 0.804 | 0.763 | 0.845 | 112.000 |
| drift_aware_original | 0.894 | 0.856 | 0.932 | 112.000 |
| no_update | 0.542 | 0.461 | 0.625 | 112.000 |
| time_decay | 0.537 | 0.469 | 0.609 | 112.000 |

旧目标冲突率：

| strategy | estimate | ci_low | ci_high | n_trajectories |
| --- | --- | --- | --- | --- |
| drift_aware_improved | 0.189 | 0.146 | 0.231 | 112.000 |
| drift_aware_original | 0.098 | 0.064 | 0.135 | 112.000 |
| no_update | 0.458 | 0.372 | 0.542 | 112.000 |
| time_decay | 0.281 | 0.219 | 0.345 | 112.000 |

所有策略共享同一批轨迹、任务、当前要求。CI 以完整测试轨迹重采样，而非把同轨迹的多个任务当独立样本。配对差异见 `phase2_task_pairwise.csv`；CI 覆盖 0 时不宣称可靠优势。

## 失败与解释

- Method D 相对 Method C：F1 从 0.900 提升到 0.955，FPR 从 0.271 降到 0.125；代价是平均延迟从 -0.238 增至 1.609。
- 稳定场景四个方法的 FPR 分别为：A=1.000、B=0.000、C=0.000、D=0.000。Method D 的误报全部来自更难的短暂变化场景（该场景 FPR=0.375）。
- 改进记忆的在线过时召回从原始策略 0.480 提升至 0.793，但任务成功率从 0.894 降至 0.804。原始减改进的配对差为 0.091，95% CI [0.049, 0.131]；主要机制是 Method D 更晚报警，确认点附近任务尚未完成旧目标降权。
- 时间衰减任务成功率为 0.537，不再是 1.0；与不更新的差为 -0.004，其区间覆盖 0，且背景会随年龄丢失。
- 代表性案例：Method D 在 `p2-temporary_shift-09`（短暂变化）于 session 10.0 误报；Method C 漏掉 `p2-gradual_drift-22`；改进记忆在 `p2-abrupt_drift-08` 的 session 7 因 `cost_goal_conflict;pace_goal_conflict` 任务失败。
- 全部误报、漏报、提前/延迟报警及任务失败保存在 `phase2_failure_cases.csv`，没有删除不利样本。

## 限制

- 仍是合成英文表达和人工词典；生成器与抽取器虽分离潜变量/标签，但仍共享有限语义域。
- 当前测试轨迹足以给出轨迹级不确定区间，但不足以证明跨领域或真实 Agent 泛化。
- Bootstrap CI 是描述性非参数区间，没有进行多重比较校正；不应过度解释边界结果。
- 实施中发现并修复了临时区间抽样和在线记忆指标口径错误，因此测试流程在修复后重跑。检测与记忆阈值始终由开发集自动选择、没有按测试指标手工调节，但本测试仍不等同于从未暴露的一次性外部盲测。

本次重复性检查：`PASS`（16 个产物两次运行 SHA-256 一致）。
