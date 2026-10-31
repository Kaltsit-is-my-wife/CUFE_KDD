# Phase 3 实验总结

这是规则与合成数据实验，不是真实 LLM Agent 评测。数据种子 `20270417`；开发/测试轨迹 112/224；测试任务记录 17724。

## 检测（独立测试 overall）

| method | precision | recall | f1 | false_positive_rate | localization_hit_rate_tolerance_2 | mean_abs_localization_error | mean_detection_delay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| method_c | 0.896 | 0.469 | 0.615 | 0.073 | 0.567 | 2.500 | 1.317 |
| method_d | 0.793 | 0.719 | 0.754 | 0.250 | 0.804 | 1.446 | 0.098 |
| method_e_confirmation | 0.907 | 0.609 | 0.729 | 0.083 | 0.769 | 1.603 | 1.808 |

Method E 是 Early Reversible 的确认事件；临时候选不是正式报警。无漂移延迟为 NA。

## 机制消融与任务成功

| strategy | estimate | ci_low | ci_high | n_trajectories |
| --- | --- | --- | --- | --- |
| A_C_original | 0.744 | 0.713 | 0.773 | 224.000 |
| B_C_improved | 0.786 | 0.758 | 0.814 | 224.000 |
| C_D_original | 0.747 | 0.717 | 0.778 | 224.000 |
| D_D_improved | 0.800 | 0.773 | 0.826 | 224.000 |
| early_reversible | 0.821 | 0.795 | 0.847 | 224.000 |
| no_update | 0.707 | 0.674 | 0.740 | 224.000 |
| oracle_timing | 0.940 | 0.925 | 0.953 | 224.000 |

Oracle Timing 是不可部署上界，不能与正常方法作公平排名。完整旧目标冲突、背景保留、首次正确执行时间和分场景结果见 CSV。

## 在线记忆（overall）

| strategy | obsolete_precision | obsolete_recall | obsolete_f1 | obsolete_interference_rate | valid_memory_retention_rate | incorrect_downweight_rate | temporary_recovery_success_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A_C_original | 0.895 | 0.087 | 0.158 | 0.356 | 0.995 | 0.006 | 0.125 |
| B_C_improved | 0.989 | 0.674 | 0.802 | 0.220 | 0.995 | 0.004 | 0.125 |
| C_D_original | 0.868 | 0.107 | 0.190 | 0.352 | 0.991 | 0.010 | 0.125 |
| D_D_improved | 0.980 | 0.711 | 0.824 | 0.207 | 0.989 | 0.009 | 0.188 |
| early_reversible | 0.944 | 0.798 | 0.865 | 0.190 | 0.980 | 0.028 | 0.125 |
| no_update | 0.000 | 0.000 | 0.000 | 0.373 | 1.000 | 0.000 | 0.125 |
| oracle_timing | 1.000 | 0.950 | 0.974 | 0.121 | 1.000 | 0.000 | 0.125 |

## 预注册主要比较与决策

- Early Reversible − D：任务成功率差 `0.020`，95% CI `[0.009, 0.032]`，原始配对随机化 p=`0.00065`，Holm p=`0.00195`。
- Early 背景保留率 `1.000`；稳定场景相对 D 的成功率下降 `0.000`。
- 门槛：`{"gain_at_least_0.05": false, "ci_lower_above_zero": true, "background_at_least_0.98": true, "stable_drop_within_0.02": true}`。
- 决策：**STOP_OR_REVISE_CURRENT_IMPLEMENTATION**。

## 失败归因与假设

- **H1 不支持。** 新测试上 D 的平均延迟为 0.098，反而早于 C 的 1.317；同为原始记忆时 C→D 的任务率从 0.744 到 0.747，同为改进记忆时从 0.786 到 0.800。第二阶段的延迟解释未在独立数据复现。
- **H2 不支持当前实现。** Early 在短暂变化场景成功率 0.824，D 为 0.834；严格恢复成功率仅 0.125，仍有恢复失败。
- **H3 支持。** Early 的过时记忆 F1=0.865，高于 D 的 0.824，但任务增益只有 0.020，未达到预注册 0.05 门槛。
- Oracle Timing 任务成功率 0.940，说明仍有时机/证据覆盖上界，但它读取真实起点，不可部署。
- 代表性保留失败：`{'record_type': 'detection', 'trajectory_id': 'p3-abrupt_drift-16', 'scenario': 'abrupt_drift', 'strategy_or_method': 'method_c', 'session': 12.0, 'reason': 'late'}`。所有失败均在 `phase3_failure_cases.csv`，未删除不利结果。

## 限制

- 仍使用有限人工词典；约 40% 表达是冻结抽取器不认识的分布迁移同义改写，仍不能代表真实语言。
- 第二阶段仅用于探索消融；正式确认使用新锁定测试集。开发参数固定后才连接测试标签。
- 配对检验进行了 Holm 校正，但合成分布、机制模型和任务效用仍限制外部有效性。
- 首次正式测试后只修正了 Oracle/不更新的失败归因名称和空状态日志写出，并补充报告解释；检测参数、早期策略参数、任务评分、预测和预注册门槛均未改变。修复后重新执行了完整双运行确定性检查。

重复性检查：`PASS`（17 个产物 SHA-256 一致）。原阶段完整性变化数：`0`。
