# CUFE_KDD

数据挖掘团队多人协作知识库与实验原型仓库。

本仓库用于保存团队思考、头脑风暴、文献笔记、实验方案、讨论记录和原型实验代码。它不是生产代码仓库，也不以部署、稳定性或线上服务为目标。

## 使用原则

1. 先写想法，再写实验：每个想法使用一个三位编号，正式实验与想法使用相同编号。
2. 想法文档和可运行代码分离：`ideas/` 记录为什么做、假设是什么；`experiments/` 记录怎么做、结果如何。
3. 草稿先放个人沙盒：`sandbox/` 用于临时试验和不保证复现的代码，成熟后再迁移到正式实验目录。
4. 废弃内容不删除：将想法或实验标记为 `archived`，保留原文、结论和迁移记录。
5. Git 只保存轻量资产：原始数据、模型权重、大日志和私密凭据禁止提交。
6. 所有变更通过 Pull Request 合并，至少一名团队成员 review，禁止直接 push `main`。

## 目录结构

```text
.
├── README.md                       # 仓库总览与使用边界
├── CONTRIBUTING.md                 # 分支、提交、PR 与新增 idea 规范
├── PROGRESS.md                     # 全部 idea/实验的统一进度表
├── CLAUDE.md                       # 项目长期记忆与协作约定
├── .gitignore                      # Python/Jupyter/数据挖掘忽略规则
├── sandbox/                        # 个人临时沙盒，不要求复现
│   ├── README.md
│   ├── member-01/README.md
│   ├── member-02/README.md
│   ├── member-03/README.md
│   ├── member-04/README.md
│   └── member-05/README.md
├── ideas/                          # 想法、方案、文献与讨论记录
│   └── 000-template/
│       ├── README.md
│       ├── notes.md
│       └── experiment.md
└── experiments/                    # 与 ideas 同编号的可运行实验原型
	└── 000-template/
		└── README.md
```

### `sandbox/`、`ideas/`、`experiments/` 的边界

| 目录 | 用途 | 复现要求 | 进入条件 |
|---|---|---|---|
| `sandbox/` | 个人草稿、快速验证、临时代码 | 不要求 | 有想法即可使用；不直接依赖其他成员沙盒 |
| `ideas/` | 假设、背景、文献、讨论、实验设计 | 文档应可理解 | 任何准备进入团队讨论的想法 |
| `experiments/` | 可运行的实验原型、配置、指标摘要、结果图片 | 应记录运行方式与环境 | 核心假设明确，且对应一个 `ideas/` 编号 |

成熟流程是：`sandbox/` 草稿 -> `ideas/001-xxx-idea/` 方案 -> `experiments/001-xxx/` 原型。编号一旦分配不复用，废弃内容移动或标记归档，不删除历史。

## 命名规则

- 正式目录使用小写字母、数字和短横线。
- idea 目录格式：`ideas/001-short-name-idea/`。
- 实验目录格式：`experiments/001-short-name/`。
- 编号固定三位、从 `001` 递增；`000-template` 仅用于复制，不作为真实项目。
- 文件名优先使用小写短横线；Markdown 文档可保留约定名称 `README.md`、`PROGRESS.md` 等。

## 数据、模型与结果

禁止提交原始数据集、受限数据、模型权重、大日志、密钥和个人隐私信息。仓库中只保留：

- 数据下载、校验、预处理和特征构造脚本；
- 数据字典、数据来源、版本、许可和获取说明；
- 指标摘要、配置摘要、错误分析和小型脱敏样例；
- 可审阅的图片、图表和 Markdown 结论。

大文件请使用团队约定的外部存储，并在文档中记录获取方式和校验信息。

## 从哪里开始

1. 阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。
2. 从 `ideas/000-template/` 复制模板，先填写核心假设和验收指标。
3. 在 `PROGRESS.md` 登记编号和负责人。
4. 实验设计稳定后，从 `experiments/000-template/` 创建同编号实验目录。
5. 使用 Pull Request 提交，邀请至少一名成员 review。

## 当前进度

所有 idea 和实验的状态以 [PROGRESS.md](PROGRESS.md) 为准。状态建议使用：`idea`、`planned`、`in-progress`、`blocked`、`completed`、`archived`。
