# 项目文档结构约定

## 核心原则

本仓库包含多个独立的小项目，每个小项目以独立文件夹为单位组织。**文档结构以小项目文件夹为层次进行规范**，而非在仓库根目录统一管理。

即：每个小项目文件夹内部遵循 `doc-structure` skill 的标准目录结构，仓库根目录不设 `docs/`。

## 当前小项目清单

| 文件夹 | 项目名称 | 说明 |
|--------|---------|------|
| `options-learning-analysis/` | 期权分析工具箱 | 纯前端期权交互式分析工具套件 |

## 目录结构示意

```
finance/                              # 仓库根目录
├── .gitignore
├── .aone_copilot/                    # 仓库级 AI 协作配置
│   └── rules/
│       └── conventions.md            # 本文件
│
├── options-learning-analysis/        # 小项目 1
│   ├── README.md                     # 项目入口
│   ├── docs/                         # 该项目的文档目录
│   │   ├── README.md                 # 文档地图
│   │   └── progress/                 # 进度与路线图
│   │       └── progress-and-roadmap.md
│   ├── *.html                        # 功能页面
│   └── quotes_server.py              # 后端服务
│
└── <future-project>/                 # 未来新增的小项目
    ├── README.md
    └── docs/
        └── ...
```

## 新增小项目时的操作

1. 在仓库根目录下创建新的项目文件夹
2. 在该文件夹内按 `doc-structure` skill 规范初始化文档结构（按需裁剪）
3. 更新本文件的「当前小项目清单」表格
