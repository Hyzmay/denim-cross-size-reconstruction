# Phase 0 Environment Capabilities

更新时间：2026-09-05

## 已具备的项目相关 Skills / Plugins

| 能力 | 当前状态 | 在本项目中的用途 |
|---|---|---|
| `denim-resize-research` | 可用 | 约束技术路线为 DXF 研发监督、局部几何变形、原像素保留和真实牛仔纹理补全；用于架构、实验与评估设计 |
| `pdf` | 可用 | 下载后校验 PDF、抽取全文、逐页渲染、检查公式/图表/附录，并按完整论文而非 Abstract 阅读 |
| `jupyter-notebook` | 可用 | Phase 0/后续几何与视觉实验的可复现实验记录；当前尚未创建实验 notebook |
| Browser Plugin | 可用 | 访问 arXiv、CVF、IEEE、论文项目页和澳门理工大学图书馆授权资源；ViTon-GUN 正式全文已验证可访问 |
| Git / Git LFS | CLI 可用 | 克隆与固定论文代码版本、检查提交和依赖、管理大文件；当前项目尚未配置 remote |
| Python scientific computing | 项目 `.venv` 可用 | 图像、几何、DXF、统计和 PDF 处理；版本与导入验证见下文 |

## 当前不可用或未暴露的能力

| 名称 | 实际状态 | 当前替代方案 |
|---|---|---|
| Deep Research / Research Skill | 当前 Skills 和官方 curated 列表均无此名称 | Browser + 全文 PDF + DOI/参考文献链 + 项目内结构化阅读记录 |
| Consensus | 当前会话无对应 Skill、Plugin 或 MCP 工具 | 通过论文原文、数据库页面及可公开访问的 Crossref/OpenAlex/Semantic Scholar 页面或 API 核验；不冒充 Consensus 输出 |
| Undermind | 当前会话无对应 Skill、Plugin 或 MCP 工具 | 使用数据库检索、引用表与 related-work 追踪构建候选论文集 |
| alphaXiv | 当前会话无对应 Skill、Plugin 或 MCP 工具 | arXiv 正文、版本记录、论文参考文献与作者项目页 |
| GitHub CLI (`gh`) | 未安装 | Git HTTPS/SSH、Git LFS 与 Browser；需要 PR/API 自动化时再单独评估安装 `gh` |
| Stable Diffusion / Diffusion / LLM fine-tuning | 按第一阶段约束不安装、不引入 | 几何预测、局部 deformation、source-pixel preservation 与 exemplar/patch texture completion |
| PyTorch | 未安装 | Phase 0 先做论文、数据、几何表示和可证伪基线设计；确定模型基线后再按最小需要评估 |

## 实测环境

- Python: `3.12.14`（项目 `.venv`）
- NumPy: `2.5.2`
- SciPy: `1.18.1`
- OpenCV: `5.0.0`
- scikit-image: `0.26.0`
- 另已验证：Matplotlib、pandas、ezdxf、pypdf、PyMuPDF、pdfplumber、JupyterLab
- `pip check`: `No broken requirements found`
- Git: `2.53.0.windows.3`
- Git LFS: `3.7.1`

## 全文阅读规则

每篇论文必须覆盖 Abstract、Introduction、Related Work、problem definition、Method/Architecture、关键公式、Loss、训练策略、Dataset、Experiments、Ablation、Limitations/failure cases、Supplementary 和官方实现。输出必须明确分开：

1. 论文原本解决的问题、输入输出、监督和实验条件。
2. 可迁移到“单张牛仔裤图片 + 目标尺码”的模块、迁移条件，以及不能直接迁移的部分。

仅有摘要、网页片段或二手介绍时，不得标记为“完整阅读”。
