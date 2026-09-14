# 团队协作与提交规范

## 1. 适用范围

本仓库是数据挖掘团队的知识库和实验原型仓库，不是生产代码仓库。提交应优先提升思考过程、实验记录和团队复用能力，而不是追求工程化部署。

## 2. 分支策略

- `main`：稳定、可阅读的团队主线，禁止直接 push。
- 每项工作从最新 `main` 创建独立分支，完成后通过 Pull Request 合并。
- 分支命名使用小写短横线，并包含工作类型和三位编号：
  - `idea/001-short-name`
  - `experiment/001-short-name`
  - `docs/update-contributing`
  - `sandbox/member-01-short-name`
  - `fix/001-metadata`
- 一个分支尽量只服务一个 idea、实验或文档主题。
- 合并前同步最新 `main`，解决冲突后再请求最终 review。

## 3. Pull Request 规则

1. PR 标题说明动作和编号，例如 `add idea 001: graph-based features`。
2. PR 描述至少包含：背景、核心假设、变更内容、验证方式、数据集/基线、已知限制和后续工作。
3. 所有 PR 至少由一名团队成员 review；作者不得自行批准自己的 PR。
4. reviewer 重点检查：假设是否明确、实验是否能回答假设、指标是否合适、数据是否合规、编号是否对应、是否误提交大文件。
5. review 意见处理完毕后再合并；保留有价值的讨论记录。
6. 合并方式优先使用 squash merge，提交信息保持主题清晰。
7. 发现实验结论被后续证据推翻时，补充记录或新建后续 idea，不删除原始历史。

## 4. 提交信息

推荐格式：`<type>: <short description>`，例如：

- `idea: add 001 ranking hypothesis`
- `experiment: record 001 baseline result`
- `docs: update progress table`
- `sandbox: add temporary feature probe`
- `archive: close 002 negative result`

提交信息使用英文短句或团队已约定的统一语言，动词开头，避免 `update`、`test` 这类无法说明内容的单独描述。

## 5. 新增 idea 流程

1. 在 issue、讨论或会议记录中提出问题，并确认没有重复编号。
2. 从 `ideas/000-template/` 复制目录，分配下一个未使用的三位编号。
3. 目录命名为 `ideas/001-short-name-idea/`，在 `README.md` 填写负责人、成员、状态、背景和【核心假设】。
4. 在 `notes.md` 记录文献、数据集、讨论和决策；在 `experiment.md` 设计基线、指标、消融、资源和停止条件。
5. 在 `PROGRESS.md` 新增一行，填写 idea 状态；尚未开始实验时，实验状态写 `not-started`。
6. 发起 PR，由至少一名成员确认：核心假设可证伪、数据使用合规、指标可观测、实验范围可控。
7. 方案通过后，从 `experiments/000-template/` 创建同编号实验目录，例如 `experiments/001-short-name/`。
8. 实验代码和结果只提交轻量、可审阅内容；运行日志、数据集、权重放在外部存储并在文档中记录位置、版本和校验信息。
9. 实验结束后更新 idea、实验 README 和 `PROGRESS.md`，写明结论、限制和下一步。

## 6. sandbox 使用规则

- 每位成员只在自己的 `sandbox/member-xx/` 下工作，避免共享临时文件产生冲突。
- 沙盒代码可以不完整、不可复现，也不要求长期维护；但不得提交密钥、受限数据或超大文件。
- 沙盒中的有效发现应迁移为正式 idea 或实验，迁移时说明来源和已知限制。
- 不要从其他成员的沙盒目录导入代码作为正式依赖。

## 7. 数据和产物检查

提交前确认：

- 没有原始数据、模型权重、数据库文件、大日志或凭据；
- Notebook 已清理敏感输出，必要时保留关键指标摘要；
- 图表不包含隐私信息，且文件大小合理；
- 运行命令、Python 版本、依赖、随机种子和数据版本已记录；
- idea 编号与实验编号一一对应。

## 8. 归档规则

废弃或暂缓的 idea 不删除。将状态改为 `archived`，补充归档日期、原因、已验证结论、未解决问题和是否被其他 idea 继承。实验代码保留最后可解释版本，并在 `PROGRESS.md` 中同步状态。
