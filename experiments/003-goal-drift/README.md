# Goal Drift PoC

> CUFE_KDD 实验编号：`003`
> 对应 Idea：[`ideas/003-goal-drift-idea/`](../../ideas/003-goal-drift-idea/)
> 负责人：[@dingyu668](https://github.com/dingyu668)
> 状态：`completed`（Phase 3 预注册门槛结论为停止或修订当前实现）

仓库仅保留源码、配置、汇总指标、审计文档和图表。可由脚本重建的合成数据、逐条预测和大型明细表未提交；请按 Phase 1、Phase 2、Phase 3 的顺序运行以重建完整产物。

这是一个不调用大模型 API 的、可复现的受控合成实验，用于研究跨会话长期目标漂移检测、漂移感知记忆更新及其对确定性下游任务的影响。

## 环境与运行

- 已验证环境：Windows、Python 3.14.0。
- 依赖：Pandas、Matplotlib（见 `requirements.txt`）。
- 固定随机种子：`20251025`。

```powershell
cd experiments/003-goal-drift
python -m pip install -r requirements.txt
python src/run_experiment.py
python src/run_experiment.py --check-determinism
```

本机已经安装依赖时可跳过安装。程序重新生成 `data/trajectories.json` 和全部 `results/` 产物。

## 设计与指标口径

数据含 48 条轨迹、每类 12 条：突变漂移、渐进漂移、仅话题切换、稳定。每条轨迹有 10 个会话。渐进漂移从 session 4 开始出现弱新目标证据，session 7 被定义为目标确认；突变在 session 5 发生并确认。

检测器均因果运行：

- Baseline A 只比较相邻会话话题，因此有意作为容易误报的弱基线。
- Baseline B 比较初始三会话目标和最近三会话目标，并要求连续两次不一致。
- Method C 使用长期参考目标、单次突变阈值和累积变化质量，分别捕捉突变与渐进变化。

Method C 还记录新目标在此前会话中的弱证据：发生强变化时，有持续先兆则分类为渐进，否则分类为突变。`drift_type_accuracy` 只在已正确检出的真实漂移轨迹上计算。

检测器由 `run_detectors` 创建只含 `session_id/text` 的输入，不接收场景或真实漂移位置。真实标签仅供 `evaluate.py` 计算指标。未来信息检查验证同一前缀在追加未来会话前后产生相同检测结果。

记忆策略：A 不更新；B 按 `exp(-0.18 * age)` 时间衰减；C 使用 Method C 的检测时点，把该时点以前且与检测目标冲突的目标记忆降权为 0.12，不删除历史，且不降权背景记忆。

下游规则任务要求选出当前成本偏好、执行偏好，并利用持续背景约束。每条轨迹从漂移确认时刻（非漂移轨迹从 session 7）起评估连续 3 个在线任务；每次只构建截至任务会话的记忆前缀，不能使用未来会话。决策只使用带权记忆及当前请求的固定权重证据；自动评分无模型调用。

## 公平性和边界

- 三种检测方法使用同一数据；三种记忆策略使用同一份 Method C 检测结果和同一任务。
- 标签不进入检测器，检测器逐会话顺序读取，不能看未来。
- 阈值是 PoC 内固定常数，没有在测试轨迹上搜索最优阈值。
- 零次更新不会被解释成完美识别：没有预测且存在过时记忆时，召回率和 F1 为 0。
- 记忆识别 Precision/Recall/F1、干扰率、保留率采用跨轨迹微平均；更新数量是每条轨迹平均值。
- “有效记忆”包括当前目标记忆和背景记忆；不能靠清空历史获得低干扰率。
- 这是规则基线与合成数据实验，不代表真实 LLM Agent 效果，也不宣称算法创新性。

详尽的实际结果、失败案例、局限和复现结论见 `results/experiment_summary.md`。
