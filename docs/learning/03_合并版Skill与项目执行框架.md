# 牛仔服装跨尺码重构：合并版 Skill 与项目执行框架

## 1. 合并结果

新版 `denim-resize-research` 将两份内容合并：

- 旧 Skill 的工程严谨性：坐标系、DXF 语义、mesh 有效性、失败条件、实验记录和可复现性。
- 新设计稿的项目完整性：单图部署接口、附件分离、结构曲线、canonical pants、尺寸条件目标几何、细节保护、真实纹理补全和 alpha 感知边缘。

没有直接照抄新稿。以下内容被修正：

- Alpha/matting 和 identity gate 从后处理提前到 P0。
- 不再把 `acceptance_passed=true` 解释为物理尺码正确。
- 不再静默补造尺码表缺失字段。
- 不再使用固定的细节优先级处理所有商品。
- `L_detail` 只在存在训练或优化目标时使用。
- `Ours` 改为待验证的 candidate system，不提前宣称创新。
- Codex 可以协助研究设计和论文分析，但研究结论必须由证据支持。

## 2. 项目真正解决的问题

```text
输入：单张牛仔裤商品图 + 已知源尺码 + 同款商品尺码表 + 目标尺码
输出：目标尺码图像 + 几何/纹理/边界评估记录
```

最终用户不需要 DXF。DXF、同款跨尺码图片、实际测量和人工标注只在研发阶段作为监督或 Ground Truth。

第一阶段不是“任意图片都能精确换码”。它限定为近似平铺、主体完整、背景可分离、透视有限、源尺码已知的商品图。

## 3. 必须先通过的 P0

### 老师提问

为什么还没做真正跨尺码之前，要先做 `source size = target size`？

### 标准回答

因为目标几何没有变化。如果身份运行仍改变裤子内部纹理、边缘、alpha、口袋或缝线，就证明管线本身在制造损失；此时继续扩大尺码只会把错误放大。

P0 顺序为：

```text
输入检查
-> segmentation
-> source alpha matting
-> 边缘颜色去污染
-> 裤身/结构/装饰/可移除附件分层
-> source=target identity run
-> identity metrics
```

Identity 至少检查 hard-mask IoU、boundary F1、alpha MAE、内部像素 MAE、关键点位移和 protected-detail change。

## 4. 正确的跨尺码 Pipeline

```text
Input Standardization
-> Segmentation + Source Matting
-> Garment / Accessory Layer Separation
-> Landmarks + Structure Curves
-> Canonical Pants Correspondence
-> Size-conditioned Target Geometry
-> Structure-aware Local Deformation
-> Detail Constraints
-> Source-validity / New-region Detection
-> Classical Real-denim Completion
-> Warped-alpha Final Composite
-> Geometry / Detail / Texture / Boundary Evaluation
```

关键变化不是多加一个“美化边缘”的函数，而是让 source alpha、前景颜色、mask、关键点、语义层和 validity map 使用同一几何变换。

## 5. 尺码信息怎样进入几何

每个商品使用独立 profile，保留字段名称、单位、量法、来源和容差。必须区分平铺宽度与围度。

尺码字段需要映射到明确几何对象：

- 腰宽/腰围 -> waistband curve 或横截面；
- 臀围 -> hip cross-section；
- 裤长 -> outseam 或规范化纵向距离；
- 前后浪 -> crotch/waist structure；
- 膝围和脚口 -> 对应横截面与 hem curve。

缺少膝围、前浪、后浪或脚口时，只能标记 `missing`、带不确定性的 `estimated`，或者将相应物理指标设为 `not_evaluated`，不能假装尺码表已经提供。

## 6. 结构和细节怎样分层

系统不能只输出一个 `protected_mask`。目标表示至少区分：

- Denim body：允许按结构变形；
- Structural details：腰头、门襟、裤缝、口袋、裤袢、固定纽扣和铆钉；
- Decorative details：Logo、印花、刺绣、破洞和洗水；
- Removable accessories：吊牌、夹子、衣架和外部商品图形。

结构细节约束位置和拓扑；装饰细节约束局部外观与锚点；牛仔纹理约束斜纹方向、频率、颜色和洗水连续性；附件单独移除或合成。

## 7. 新区域的严格定义

```text
new_region = target_geometry AND NOT warped_source_validity
```

`warped_source_validity` 必须由真实对应关系得到。它不是简单的“目标轮廓减去原宽度”，也不能把严重过拉伸的像素当作可靠纹理。

只有 new、occluded、invalid 或 over-stretched 区域进入纹理修复。其他像素保留源图通过几何映射得到的真实外观。

## 8. 三种评价状态

新版 Skill 要求分开报告：

```text
proxy_checks_passed: true | false
geometry_evaluated: true | false
physical_geometry_status: passed | failed | not_evaluated
```

没有 DXF、同款目标尺码图片或可验证实际测量时，`physical_geometry_status` 必须是 `not_evaluated`。轮廓变平滑、纹理梯度改善、程序测试通过，都不能替代物理几何验证。

## 9. 四篇论文分别用在哪里

| 论文 | 原问题 | 本项目主要迁移 | 不能声称的内容 |
|---|---|---|---|
| GP-VTON | 人物条件虚拟试穿 | 语义区域局部形变与全局组合 | 逐行缩放不能称为 local-flow 网络 |
| ViTon-GUN | 经 canonical garment 的人物到人物试穿 | source-canonical-target correspondence | 诊断 UV 不能称为 learned unwrapping |
| GaPT-DAR | 点云条件下的服装 2D/3D 跟踪 | 显式二维形变、canonical prior、TPS 思路 | 单张 RGB 不能声称复现 3D/NOCS 系统 |
| DualFit | warp 后再生成/修复的虚拟试穿 | 区分可靠像素和必须修复区域 | 当前非生成式项目不采用其生成网络 |

论文学习必须分别记录：原始输入输出、数据假设、架构公式、Loss、实验消融、局限、可迁移部分、不可迁移部分和当前代码真实实现程度。

## 10. 开发顺序

### P0：边界与身份

完成输入合同、分割、source alpha、附件处理和 identity gate。

### P1：几何

建立人工 mask/landmarks/curves、canonical correspondence、外部尺码 profile，并用一个小尺码差与 DXF 或同款图片验证。

### P2：形变与细节

实现结构约束 mesh/TPS、foldover 和 distortion 检查、结构层与装饰层约束。

### P3：补全与扩展

实现 validity-aware 新区域、经典真实纹理补全、批量评估、消融和更多商品。

真人穿着、复杂背景和严重遮挡属于后续扩展，不应成为第一阶段默认输入。

## 11. Skill 文件结构

```text
denim-resize-research/
|-- SKILL.md
|-- agents/openai.yaml
`-- references/
    |-- input-contract.md
    |-- cross-size-pipeline.md
    |-- evaluation.md
    `-- paper-transfer.md
```

`SKILL.md` 只保存必须始终遵守的原则和路由；具体输入、算法、评价和论文迁移按当前任务读取相应 reference，避免每次加载全部内容。

## 12. 使用示例

可以在 Codex 中这样调用：

```text
$denim-resize-research 检查当前 segmentation 和 alpha 是否满足 P0 identity gate。
```

```text
$denim-resize-research 根据同款尺码表设计一个 34 到 36 的小尺度几何实验，并明确哪些尺寸缺失。
```

```text
$denim-resize-research 对比当前 deformation 与 GP-VTON local flow，区分概念迁移和真实实现。
```

新版 Skill 是研究和工程执行规范，不代表项目已经实现其中所有阶段。每个阶段仍需通过代码、实验、Ground Truth 和可复现产物逐项证明。
