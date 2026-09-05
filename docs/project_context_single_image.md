# 牛仔服装跨尺码重构项目 — Codex 新版工作上下文
## 版本：单张牛仔裤图片输入版

> **这是对上一版 Codex 文档的重大修改。**
>
> 原方案假设用户输入 `source image + source DXF + target DXF`。
> 现在项目的目标改为：
>
> **用户最终只需要提供一张牛仔裤图片，系统自动完成跨尺码重构。**
>
> DXF 不再是最终用户输入，而应作为研发阶段的几何真值、训练/验证数据或内部先验使用。

---

# 0. 给 Codex 的最高优先级说明

你现在接手的是一个“牛仔服装跨尺码重构项目”。

最终目标不是：

> 给一张图片 + 两个 DXF，然后做 DXF warp。

而是：

> **给系统一张牛仔裤图片，系统自动理解这条裤子的结构和几何，再根据目标尺码完成局部几何变形、纹理保持和新增区域纹理补全。**

因此项目最终输入应尽量接近：

```text
source_image
target_size
```

输出：

```text
target_size_reconstructed_image
```

研发阶段可以额外使用：

```text
source_DXF
target_DXF
```

作为 ground truth / geometric supervision / evaluation reference。

---

# 1. 项目真正要解决的问题

不要把问题理解为：

```text
图片放大
图片缩小
整体 resize
```

真正的问题是：

```text
Single Image
    ↓
Garment Understanding
    ↓
Garment Canonical Representation
    ↓
Target Size Geometry
    ↓
Region-aware Deformation
    ↓
Original Detail Preservation
    ↓
New Region Detection
    ↓
Real Denim Texture Completion
    ↓
Final Reconstruction
```

核心问题可以写成：

> **如何从一张牛仔裤图像中恢复足够的服装结构表示，使系统能够在改变尺码后尽可能保留原始真实像素、印花、细线和洗水效果，并仅对真正新增区域进行真实牛仔纹理补全？**

---

# 2. 当前项目的特殊要求

服装是一条牛仔裤。

已知：

- 大量细节来自真实牛仔面料和印花。
- 有较细的纹理/线条。
- 印花和细线的几何变形必须受到控制。
- 牛仔斜纹方向必须连续。
- 洗水形成的明暗渐变不能被破坏。
- 新增区域不能出现明显重复纹理。
- 不能因为追求“看起来像”而重新生成整条裤子。
- **原始真实像素的价值高于生成式模型的视觉幻觉。**

最高原则：

> **能不动的像素不动；必须变形的区域局部变形；真正新增出来的区域才补纹理。**

---

# 3. 重新定义最终系统

## 3.1 最终用户输入

理想情况：

```text
一张牛仔裤图片
+
目标尺码
```

例如：

```text
jeans.jpg
target_size = L
```

或者：

```text
jeans.jpg
source_size = M
target_size = XL
```

---

## 3.2 系统内部自动完成

### Stage A：服装检测

从整张图片中找到：

```text
pants mask
```

并去除：

- 背景
- 人体
- 其他衣物
- 阴影干扰

---

### Stage B：牛仔裤结构理解

至少需要识别：

```text
waistband
left leg
right leg
hip
crotch
thigh
knee
hem
side seam
inseam
pocket
fly
sewing lines
prints
fine lines
```

不是只做一个 binary mask。

需要建立：

```text
garment semantic map
```

---

### Stage C：canonical garment representation

参考 ViTon-GUN 的核心思想：

```text
source garment
      ↓
unwrapping
      ↓
canonical representation
      ↓
target deformation
      ↓
target garment
```

这里不要直接照搬 VTON。

本项目真正需要的是：

> **把不同照片中的牛仔裤转换成一个稳定的 canonical garment coordinate system。**

例如：

```text
canonical pants coordinates

y=0       waistband
          |
          |
y=0.25    hip
          |
y=0.45    crotch
          |
y=0.65    knee
          |
y=1.00    hem
```

左右裤腿也应有独立坐标。

---

# 4. 为什么不能只做一个 TPS

这是本项目非常重要的一点。

GP-VTON 的核心启发不是“直接使用它的网络”，而是：

> **不同 garment parts 不应该被一个 global deformation field 强行解释。**

GP-VTON 明确指出 global warp 对不同服装区域需要不同变形时容易导致语义错误和纹理 distortion；它采用 local flows 分别处理不同 garment parts，再通过 global parsing 组合结果。

因此本项目应该采用：

```text
whole pants
    ↓
semantic regions
    ↓
local deformation
```

对于牛仔裤可以考虑：

```text
R1 waistband
R2 left hip
R3 right hip
R4 crotch
R5 left thigh
R6 right thigh
R7 left knee
R8 right knee
R9 left hem
R10 right hem
```

不一定必须固定成 10 区。

最终应该让区域划分由：

- garment structure
- DXF geometry（研发阶段）
- image segmentation
- learned keypoints

共同决定。

---

# 5. 论文重点一：GP-VTON

论文：

**GP-VTON: Towards General Purpose Virtual Try-On via Collaborative Local-Flow Global-Parsing Learning**

CVPR 2023。

## 5.1 必须真正理解的核心

GP-VTON 不是本项目的直接解决方案。

真正值得借鉴的是：

### Local deformation

不同服装区域分别估计 deformation。

论文中使用：

```text
left part
right part
middle part
```

分别进行 local flow。

对于 pants，论文进一步将 lower garment 视为：

```text
left pant leg
right pant leg
middle region
```

这一点与我们的牛仔裤非常接近。

---

## 5.2 第二个关键点：Global Parsing

不能简单：

```text
local warp 1
+
local warp 2
+
local warp 3
```

然后直接拼起来。

因为不同局部变形结果会产生：

```text
overlap
boundary conflict
artifact
```

GP-VTON 使用 global garment parsing 来决定最终每个像素来自哪个局部区域。

本项目应该借鉴成：

```text
local deformation fields
        ↓
overlap handling
        ↓
semantic/geometry-aware blending
        ↓
final garment
```

---

## 5.3 第三个关键点：不要强迫 warp 去满足不合理边界

GP-VTON 提出 Dynamic Gradient Truncation。

它解决的是：

如果强迫 warped garment 完全贴合某个 boundary：

```text
boundary constraint
        ↓
texture squeezing
        ↓
texture distortion
```

我们的项目虽然不是 VTON，但问题高度相似。

例如：

```text
原始裤腿纹理
      ↓
目标裤腿变宽
      ↓
强行拉伸全部纹理
      ↓
斜纹被拉长
印花变形
细线变形
```

因此我们需要：

> **几何边界必须满足，但不是所有纹理像素都必须承担全部几何变化。**

这会成为本项目很重要的设计原则。

---

# 6. 论文重点二：GaPT-DAR

论文：

**GaPT-DAR: Category-level Garments Pose Tracking via Integrated 2D Deformation and 3D Reconstruction**

CVPR 2025。

## 6.1 最值得借鉴的东西

不是：

- 3D point cloud
- depth reconstruction
- garment pose tracking

真正值得借鉴：

> **把复杂 garment deformation 转换到 2D warping space 中处理。**

论文通过：

```text
3D observation
    ↓
optimal 3D→2D projection
    ↓
2D garment deformation
    ↓
TPS transformation
    ↓
3D reconstruction
```

完成 garment deformation。

---

## 6.2 对我们项目的启发

我们的项目其实可以进一步简化：

```text
Image
  ↓
2D garment representation
  ↓
2D local deformation
  ↓
texture remapping
```

因此不应该因为 GaPT-DAR 使用 3D 就把项目做成 3D。

我们真正需要的是：

> **2D deformation representation + garment shape prior。**

---

## 6.3 TPS 应该放在哪里

TPS 可以作为 deformation baseline。

但正式版本不能：

```text
整条裤子
   ↓
一个 TPS
```

更合理：

```text
waist TPS
hip TPS
crotch TPS
left-leg TPS
right-leg TPS
hem TPS
```

甚至后续可以升级：

```text
TPS baseline
      ↓
dense flow
      ↓
geometry-conditioned flow
```

---

# 7. 论文重点三：ViTon-GUN

论文：

**ViTon-GUN: Person-to-Person Virtual Try-on via Garment Unwrapping**

IEEE Transactions on Visualization and Computer Graphics, 2025。

## 7.1 最值得借鉴的思想

它把问题拆成：

```text
Person-to-Garment
        ↓
canonical garment
        ↓
Garment-to-Person
```

其中最重要的是：

> **Garment Unwrapping**

即：

```text
garment in arbitrary pose
        ↓
canonical A-Pose representation
```

---

## 7.2 对本项目的重要意义

我们的 source image 可能不是标准平铺图。

可能：

- 有轻微褶皱
- 有透视
- 左右腿角度不同
- 裤腰有旋转
- 裤脚不完全水平

如果直接在原始 image coordinate 上做 deformation：

```text
image coordinate
     ↓
target size
```

很容易混入：

- camera perspective
- pose
- wrinkle
- local distortion

所以应该考虑：

```text
source image
      ↓
garment parsing
      ↓
canonical garment space
      ↓
size transformation
      ↓
target image
```

这可能成为本项目最重要的结构之一。

---

# 8. 论文重点四：DualFit

论文：

**DualFit: A Two-Stage Virtual Try-On via Warping and Synthesis**

ICCV Workshops 2025。

## 8.1 核心启发

DualFit 采用：

```text
Stage 1:
warp garment
      ↓
preserve high-frequency details

Stage 2:
synthesis / blending
      ↓
only regenerate where necessary
```

尤其强调：

- logos
- printed text
- fine-grained garment details
- seams

这与本项目非常接近。

---

## 8.2 本项目应该进一步“去生成化”

不要直接照搬：

```text
warp
+
diffusion synthesis
```

而应该做：

```text
warp
+
real-patch synthesis
```

即：

```text
original valid region
        ↓
keep original

new region
        ↓
real denim exemplar
        ↓
patch synthesis
```

所以本项目可以形成：

> **Warp-first, Preserve-first, Real-texture-completion**

---

# 9. 四篇论文合起来之后，本项目的结构

四篇论文不要分别照搬。

应该形成：

```text
ViTon-GUN
    ↓
Canonical Garment Representation
    │
    ├───────────────┐
    ↓               ↓
GaPT-DAR         GP-VTON
2D deformation   Local deformation
    │               │
    └───────┬───────┘
            ↓
    Region-aware deformation
            ↓
        DualFit
            ↓
 Preserve original details
            ↓
 New-region completion
            ↓
 Real denim texture
```

这才是本项目的论文逻辑。

---

# 10. 从 DXF 输入转向“DXF 作为研发真值”

这一点必须明确。

## 过去

```text
Image
+
Source DXF
+
Target DXF
      ↓
Reconstruction
```

## 现在

```text
Image
+
Target Size
      ↓
AI/vision system
      ↓
Reconstruction
```

但是研发阶段：

```text
Source DXF
+
Target DXF
```

仍然非常重要。

它们可以用于：

### 训练 supervision

学习：

```text
image geometry
        ↕
DXF geometry
```

### deformation ground truth

得到：

```text
source geometry
      ↓
target geometry
      ↓
ground-truth deformation
```

### evaluation

比较：

```text
predicted garment boundary
        VS
target DXF boundary
```

因此：

> **DXF 从“用户输入”变成“研发阶段的几何老师”。**

这是整个项目从工程算法走向科研算法的重要变化。

---

# 11. 最终算法框架

推荐正式架构：

```text
                  ┌─────────────────┐
                  │ Single Jeans    │
                  │ Image           │
                  └────────┬────────┘
                           ↓
                 Garment Segmentation
                           ↓
                 Structure Recognition
                           ↓
              Semantic Keypoint Detection
                           ↓
             Canonical Garment Representation
                           ↓
                 Size Transformation Model
                           ↓
              ┌────────────┴────────────┐
              ↓                         ↓
       Geometry-preserving        Detail-preserving
       local deformation          constraints
              │                         │
              └────────────┬────────────┘
                           ↓
                    Warped Garment
                           ↓
                 Valid / New Region Mask
                      ┌────┴────┐
                      ↓         ↓
                  Valid area   New area
                      ↓         ↓
                 Keep/Warp     Real Denim
                 original      Patch Synthesis
                      │         │
                      └────┬────┘
                           ↓
                 Boundary / Seam Blending
                           ↓
                 Texture Direction Check
                           ↓
                 Print / Fine-line Check
                           ↓
                     Final Image
```

---

# 12. 关键模块

## Module A：Garment Segmentation

输入：

```text
single jeans image
```

输出：

```text
pants mask
```

研发初期可以使用现有 segmentation model。

不要一开始自己训练。

---

## Module B：Garment Keypoints

至少：

```text
waist-left
waist-right
hip-left
hip-right
crotch
left-knee
right-knee
left-hem
right-hem
```

后续增加：

```text
pocket corners
fly
seam intersections
print landmarks
```

---

## Module C：Canonical Garment

建立：

```text
image coordinates
        ↓
canonical coordinates
```

这个模块是未来论文潜在创新点之一。

---

## Module D：Size Transformation

输入：

```text
canonical garment
source size
target size
```

输出：

```text
target canonical geometry
```

这里研发阶段可以利用 DXF 学习：

```text
DXF source
    ↓
DXF target
    ↓
ground truth deformation
```

---

# 13. Size Transformation 不应该简单理解成“放大”

例如 M → L：

不是：

```text
x × 1.08
y × 1.08
```

而是：

```text
waist      + Δ1
hip        + Δ2
crotch     + Δ3
thigh      + Δ4
knee       + Δ5
hem        + Δ6
length     + Δ7
```

即：

```text
Δgeometry = f(region, size_difference, garment_style)
```

未来甚至可以建立：

```text
deformation field
=
f(
  garment category,
  source size,
  target size,
  garment structure
)
```

---

# 14. 纹理处理的核心原则

## 14.1 原始区域

优先：

```text
original pixels
```

而不是：

```text
generated pixels
```

---

## 14.2 变形区域

使用：

```text
local warp
```

但加入：

```text
print mask
line mask
edge mask
```

---

## 14.3 新增区域

使用：

```text
real denim texture
```

而不是直接：

```text
Stable Diffusion
Flux
其他生成模型
```

---

# 15. 牛仔纹理必须考虑的因素

新增区域至少保持：

### Twill direction

牛仔斜纹方向。

---

### Texture phase

纹理周期/相位连续。

---

### Local frequency

不能一块区域明显比周围更模糊或更锐。

---

### Brightness

新增区域不能突然变亮/变暗。

---

### Wash gradient

洗水区域的明暗渐变必须延续。

---

### Seam continuity

缝线、边缘和结构线必须连续。

---

# 16. 印花/细线保护

这是本项目和普通 VTON 很重要的区别。

需要自动建立：

```text
print mask
fine-line mask
seam mask
edge mask
```

然后定义：

```text
deformation cost
```

例如：

```text
普通 denim texture:
    deformation freedom = high

fine line:
    deformation freedom = low

printed logo:
    deformation freedom = very low

seam:
    geometry constrained
```

最终可以形成：

```text
geometry loss
+
texture loss
+
edge loss
+
print preservation loss
```

---

# 17. 研发阶段必须保留 DXF

虽然最终用户不提供 DXF，但研究阶段不要删除 DXF。

数据可以组织成：

```text
sample_001/
    source.jpg
    source.dxf
    target_M.dxf
    target_L.dxf
    target_XL.dxf

sample_002/
    source.jpg
    source.dxf
    target_M.dxf
    target_L.dxf
    target_XL.dxf
```

这样可以得到：

```text
image
+
known geometry transformation
```

这是训练和 evaluation 的关键。

---

# 18. 最重要的研究问题

项目真正值得写论文的不是：

> “我做了一个牛仔裤图片变大算法。”

而是：

> **How can a single garment image be transformed across sizes while preserving authentic high-frequency garment appearance and minimizing synthetic content?**

可以进一步形成：

### Research Question 1

如何从单张服装图像建立稳定的 canonical representation？

### Research Question 2

如何利用服装结构先验预测跨尺码 deformation field？

### Research Question 3

如何让局部几何变化与印花/细线保持约束？

### Research Question 4

如何仅对新增区域进行真实面料 texture completion？

### Research Question 5

如何评价跨尺码重构的几何正确性与视觉真实性？

---

# 19. 推荐实验路线

## Baseline 1

```text
Global Resize
```

作为最简单 baseline。

---

## Baseline 2

```text
Global Affine
```

---

## Baseline 3

```text
Global TPS
```

---

## Baseline 4

```text
Local TPS
```

---

## Baseline 5

```text
Local TPS
+
texture patch synthesis
```

---

## Proposed

```text
Canonical garment
+
size-conditioned deformation
+
local deformation
+
detail-preserving constraints
+
real-denim texture completion
```

这样论文实验会非常清楚。

---

# 20. Evaluation

不能只看 IoU / MAE。

## Geometry

```text
Boundary Error
Keypoint Error
Seam Alignment Error
Region Area Error
```

---

## Texture

```text
Texture Continuity
Twill Orientation Error
Local Frequency Difference
Color/Wash Consistency
```

---

## Detail

```text
Print Preservation
Fine-line Displacement
Edge Preservation
Seam Preservation
```

---

## Perceptual

可以参考 GP-VTON 使用的：

```text
SSIM
LPIPS
FID
mIoU
Human Evaluation
```

但本项目需要加入自己的：

```text
Print Preservation Score
Twill Direction Consistency
Boundary Continuity Score
```

---

# 21. 不能做的事情

暂时不要：

1. 训练一个大型 diffusion 模型直接生成整条裤子。
2. 用 Stable Diffusion / Flux 替代几何算法。
3. 整图 resize。
4. 整条裤子只使用一个 affine。
5. 整条裤子只使用一个 TPS。
6. 只使用 IoU。
7. 只使用 MAE。
8. 新区域简单复制矩形纹理。
9. 忽略牛仔斜纹。
10. 为了视觉好看重新生成原始印花。
11. 一开始就训练 LLM。
12. 在没有建立 baseline 前堆复杂模型。

---

# 22. Codex 当前开发顺序

## Phase 0：重新定义输入

先实现：

```text
input:
    jeans.jpg
```

并完成：

```text
automatic pants segmentation
```

---

## Phase 1：结构理解

实现：

```text
pants mask
+
semantic regions
+
keypoints
```

先不做纹理生成。

---

## Phase 2：Canonical representation

实现：

```text
image
 ↓
canonical garment
```

并把结果可视化。

---

## Phase 3：DXF supervision

研发阶段：

```text
source DXF
target DXF
```

用于验证：

```text
predicted geometry
VS
ground truth geometry
```

---

## Phase 4：Size deformation

先实现：

```text
Global Resize
Global TPS
Local TPS
```

建立 baseline。

---

## Phase 5：Local deformation

参考 GP-VTON 的思想：

```text
waist
hip
crotch
left leg
right leg
hem
```

分别变形。

---

## Phase 6：Detail preservation

加入：

```text
print mask
line mask
seam mask
edge mask
```

---

## Phase 7：Real Denim Texture Completion

先：

```text
SSD patch matching
```

然后：

```text
PatchMatch
```

再考虑：

```text
direction-aware
multi-scale
phase-aware
```

---

## Phase 8：完整 evaluation

建立：

```text
geometry metrics
texture metrics
detail metrics
human evaluation
```

---

# 23. 当前最重要的工程原则

**不要先写复杂模型。**

第一步必须先证明：

```text
一张真实牛仔裤图片
        ↓
自动识别裤子
        ↓
自动找到关键结构
        ↓
建立 canonical representation
        ↓
能够做一个可控的 M→L / M→XL 变形
```

如果这一步做不稳：

```text
texture synthesis
LLM
diffusion
fine-tuning
```

全部暂时没有意义。

---

# 24. 关于论文阅读：必须严格执行

本项目目前重点参考四篇论文：

1. GP-VTON — CVPR 2023
2. GaPT-DAR — CVPR 2025
3. ViTon-GUN — IEEE TVCG 2025
4. DualFit — ICCV Workshop 2025

**要求：不要只看 abstract。**

以后如果 Codex / ChatGPT 要基于论文提出算法，必须先完成：

```text
Abstract
Introduction
Related Work
Method
Loss
Experiments
Ablation
Limitations
Supplementary（如果有）
```

然后才能说“论文启发了什么”。

特别注意：

> **论文中的任务、数据、输入输出、监督方式、实验条件必须和本项目区分。**

不能因为论文用了 garment deformation，就说论文“解决了跨尺码重构”。

---

# 25. 四篇论文在本项目中的角色

| Paper | 真正借鉴内容 | 不要照搬 |
|---|---|---|
| GP-VTON | Local deformation + global parsing + avoid texture squeezing | VTON generator |
| GaPT-DAR | 2D deformation space + TPS + garment shape prior | 3D tracking / depth reconstruction |
| ViTon-GUN | Garment unwrapping + canonical representation | Person-to-person VTON |
| DualFit | Warp first + preserve fine details + regenerate only necessary regions | 完整生成式 VTON |

---

# 26. 最终希望形成的核心算法

可以暂时命名为：

**Single-Image Size-Aware Garment Reconstruction**

或者：

**Single-Image Garment Cross-Size Reconstruction with Geometry-Aware Local Deformation and Texture Preservation**

核心：

```text
Single Image
      ↓
Garment Understanding
      ↓
Canonical Representation
      ↓
Size-conditioned Geometry
      ↓
Local Non-rigid Deformation
      ↓
Detail-aware Warping
      ↓
New-region Detection
      ↓
Real Denim Exemplar Synthesis
      ↓
Boundary / Texture / Print Preservation
      ↓
Final Cross-size Garment
```

---

# 27. 未来论文可能的创新点

不要现在就决定最终创新点。

目前候选方向：

### Innovation A
Single-image garment canonicalization for cross-size reconstruction.

### Innovation B
Size-conditioned region-aware deformation field.

### Innovation C
Print/fine-line constrained garment deformation.

### Innovation D
Real-texture-only completion of geometrically newly created regions.

### Innovation E
Garment-specific evaluation metrics for cross-size reconstruction.

最终最好形成：

```text
一个核心方法
+
一个纹理保持模块
+
一个新的评价体系
```

而不是堆很多小模块。

---

# 28. Codex 第一阶段任务

拿到真实牛仔裤图片后：

### Task 1

读取图片：

```text
jeans.jpg
```

### Task 2

自动分割：

```text
pants mask
```

### Task 3

输出：

```text
pants_mask.png
```

### Task 4

检测：

```text
waist
hip
crotch
left leg
right leg
knee
hem
```

### Task 5

输出：

```text
keypoints_visualization.png
```

### Task 6

建立：

```text
canonical_garment.png
```

### Task 7

如果存在 DXF：

将 DXF 作为 ground truth 叠加检查。

### Task 8

暂时不要做：

```text
texture generation
diffusion
LLM
fine-tuning
```

---

# 29. 一句话总目标

本项目最终不是：

> AI 生成一条不同尺码的牛仔裤。

而是：

> **从一张真实牛仔裤图片中恢复可控的服装结构表示，根据目标尺码建立局部几何变形，并最大程度保留原始真实像素、印花、细线和洗水纹理，只对真正新增区域进行真实牛仔面料纹理补全。**

---

# 30. 论文依据备注

本版本的核心方法框架依据以下公开论文资料重新整理：

- GP-VTON, CVPR 2023
- GaPT-DAR, CVPR 2025
- ViTon-GUN, IEEE TVCG 2025
- DualFit, ICCV Workshop 2025

**重要：本文件中的论文总结只允许作为研究设计依据，不等于这些论文直接解决了本项目。**

后续若要写论文 related work / method，必须重新逐篇核对原文全文、公式、实验和 supplementary，不能根据摘要或二手总结直接下结论。
