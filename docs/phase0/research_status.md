# Phase 0 Research Status

更新时间：2026-09-05

## 当前项目约束

- 最终输入：`source_image + target_size`。
- DXF 只作为研发阶段的 geometry ground truth、supervision 和 evaluation reference，不作为最终用户必需输入。
- 优先级：原始像素保留 > 局部几何变形 > 新增区域检测 > 真实牛仔 exemplar/patch completion。
- 当前阶段禁止使用 Stable Diffusion、Flux、整图生成、LLM fine-tuning 或其他大型生成模型替代几何方法。
- 先完成 geometry 和 structure validation，再研究 texture completion。

## 论文全文队列

| Paper | 正式身份 | 全文状态 | 代码/项目入口 | 当前阅读状态 |
|---|---|---|---|---|
| GP-VTON | CVPR 2023, arXiv:2303.13756, DOI: 10.1109/CVPR52729.2023.02255 | 主论文已保存并完成文本抽取与 10 页渲染 | https://github.com/xiezhy6/GP-VTON | 2026-09-06 已逐节核对主论文；Supplementary/官方代码仍待核验 |
| GaPT-DAR | CVPR 2025, pp. 22638-22647 | CVF accepted version 已保存并完成文本抽取与 10 页渲染 | https://github.com/zanly20/GaPT-DAR ; https://sites.google.com/view/gapt-dar | 2026-09-06 已逐节核对主论文；官方代码仍待核验 |
| ViTon-GUN | IEEE TVCG 31(10), pp. 7740-7751, DOI: 10.1109/TVCG.2025.3550776 | 已通过澳门理工大学图书馆授权代理获取 IEEE 正式全文，并完成文本抽取与 12 页渲染 | IEEE document 10944549 | 2026-09-06 已逐节核对主论文；Supplementary/官方代码仍待核验 |
| DualFit | arXiv:2508.12131 | arXiv v1 已保存并完成文本抽取与 11 页渲染 | https://uark-aicv.github.io/DualFit | 2026-09-06 已逐节核对主论文；官方代码仍待核验 |

本地论文目录：`references/papers/`

临时全文与逐页渲染目录：`tmp/pdfs/`

### 本地文件完整性

| File | Pages | SHA-256 |
|---|---:|---|
| `GP-VTON_arXiv_2303.13756v1.pdf` | 10 | `1BF5847EBAD2C44643EB9712FF580D42E2CF7204562903C069DC68DF1BF0E5B8` |
| `GaPT-DAR_CVPR_2025.pdf` | 10 | `8399B4A2E4EC0333794ED6F587873F16E7E589376474242A3F91D85D092780EF` |
| `DualFit_arXiv_2508.12131v1.pdf` | 11 | `D48B7497B2CB44477DC0D5A440EEC90F4213D696D270870C15F769C901F4A391` |
| `ViTon-GUN_TVCG_2025.pdf` | 12 | `15B92150ECC3F9FE76907587F273A4D570E4465F0E4C1F26CB4E172CEFAB7E05` |

## 完整论文阅读检查项

每篇论文必须分别核对：

- Abstract
- Introduction
- Related Work
- Problem definition / inputs / outputs / supervision
- Method and architecture
- 关键公式及符号定义
- Losses and training strategy
- Dataset and preprocessing
- Experiments and baselines
- Ablations
- Limitations and failure cases
- Supplementary material（若存在）
- Official implementation / reproducibility constraints（若存在）

每篇论文的结论必须分成两栏：

1. 论文原本解决的问题与实验条件。
2. 可迁移到单张牛仔裤跨尺码重构的方法，以及不能迁移的部分。

## Phase 0 当前门槛

在收到真实牛仔裤图片前不开始 segmentation 实现。收到图片后的第一个可证伪问题为：

> 在不训练新模型的条件下，现有 segmentation 方法能否产生足以稳定定位 waistband、crotch、双裤腿与 hem 的 pants mask？

首个实验只允许比较少量现有 segmentation baseline，并使用人工校验 mask/landmarks 评估。最低记录项包括输入尺寸、颜色空间、背景/人体情况、mask 边界质量、关键结构可见性与失败区域。通过标准必须在检查样本后、编码前固定，不能根据结果事后修改。

### 已完成的工程准备

- 已实现无需训练的 OpenCV `border_grabcut` 自动分割基线。
- 已实现 mask、foreground、overlay、配置、指标、输入哈希与依赖版本的运行记录。
- 已实现 IoU、Dice、boundary F1 与 mask diagnostics。
- 6 个单元/合成测试通过；受控合成裤型 IoU 为 `0.998708774950234`。
- 该结果只证明代码管线在受控输入上成立，不代表真实牛仔裤图片的分割质量。

## 当前阻塞项

- 已收到并运行首张真实牛仔裤正背双视图商品图；多视图主体保持通过，但尚无人工 ground-truth mask，不能量化真实 IoU、Dice 或 boundary F1。
- 右下角水印与背面裤脚相连，当前 classical baseline 存在局部边界污染；结构阶段应先使用较干净的正面视图，或先比较预训练 garment parsing baseline。
- 四篇重点论文的主论文全文均已合法获取并完成逐节核对；本轮教学总结见 `docs/learning/02_四篇论文与项目迁移_教师提问版.md`。Supplementary 与官方代码仍需逐篇核验。
