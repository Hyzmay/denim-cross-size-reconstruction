# Phase 0 / Phase 1 多尺码验收报告

更新时间：2026-09-06

## 本轮完成范围

当前代码已把以下步骤串成一个可直接运行的、非生成式的 Python 管线：

`单张商品图 -> 自动分割 -> 结构点估计 -> canonical 表示 -> 尺码比例预测 -> 分区局部变形 -> 细节保护 -> 新区域检测 -> 真实源图 patch 补全候选 -> 边缘修复 -> 多尺码成图`

实现边界遵守项目约束：没有使用 Stable Diffusion、Diffusion、GAN、图生图模型或 LLM fine-tuning；纹理候选只来自输入牛仔裤自身的有效像素。

## 已生成结果

四个干净商品样品都按“假定源尺码 34”一次生成了 `32 / 33 / 34 / 36 / 38`，共 20 张成品：

| 样品 | 多尺码目录 | 全部通过 |
|---|---|---:|
| Medium blue | `runs/sample_002_gugr-multisize-final/` | 是 |
| Black | `runs/sample_006_gugr_black-multisize-final/` | 是 |
| Raw indigo | `runs/sample_007_gugr_raw_indigo-multisize-final/` | 是 |
| Off white | `runs/sample_008_gugr_offwhite-multisize-final/` | 是 |

集中总览：`docs/phase0/all_samples_multisize_summary.png`；便于界面直接查看的 50% 版本为 `docs/phase0/all_samples_multisize_preview.png`。

## 数值验收

- 20/20 尺码运行的总 acceptance 为 `true`。
- canonical garment representation 对源裤装 mask 的覆盖率均为 `1.0`，每张包含 10 个语义区域。
- 边缘修复的轮廓面积变化为 `0%` 到 `0.00442%`，远低于预注册的 `1.5%` 上限。
- 20/20 结果的轮廓粗糙度未增加；黑色样品 `34 -> 38` 的 roughness 从 `6.71827` 降至 `6.70409`。
- 尺码 38 的新增区域约占目标 mask 的 `10.11%` 到 `10.25%`；尺码 36 约为 `6.50%`。
- 细节保护 mask 覆盖约 `18.55%` 到 `19.69%` 的裤装区域，用于保护轮廓、缝线、门襟、口袋边和裤脚。
- 纹理 acceptance 要求可处理区域覆盖率至少 `95%`，且 texture-gradient gap 不得恶化。20/20 均通过。
- 只有 raw-indigo 和 off-white 的 `34 -> 38` 候选在量化指标上优于基线并被实际应用；其余扩码结果保留几何变形基线，避免为了“看起来做了补纹理”而引入伪影。

## 边缘磨损修复

旧结果的白边主要来自几何插值时把白色背景卷入前景边缘。当前实现先把 garment 内侧颜色连续延拓到 mask 外，再进行小范围形态学与高斯轮廓平滑，最后用亚像素 alpha 合成到白底。

黑色样品 `34 -> 38` 的专项验证结果：

- 二值轮廓仅改变 13 个像素。
- 面积变化 `0.00442%`。
- 生成 14,220 个亚像素过渡像素。
- 轮廓粗糙度下降 `0.01418`。
- acceptance 通过。

对应诊断：`runs/sample_006_gugr_black-edgefix-34-to-38/edge_refinement_comparison.png`。

## 可复现性

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q denim_resize tests scripts
.\.venv\Scripts\python.exe -m pip check
```

2026-09-06 最终核验：19 项测试全部通过，`compileall` 无错误，`pip check` 返回 `No broken requirements found`。

## 不能过度声明的部分

当前结果证明的是：在四张干净、单裤装、白底商品图上，经典视觉管线能够稳定产生多尺码视觉重构并通过现有代理指标。它还不是已完成的生产级“任意淘宝图片真实换码”系统：

- GUGR 商品没有可核验的厘米尺码表。本轮借用了已核验淘宝商品 `612962220220` 的尺码比例，因此只能称为视觉实验，不是 GUGR 的真实尺码结果。
- 没有对应样品的 DXF、实物平铺尺寸和人工 landmark ground truth，不能报告物理厘米误差、DXF 边界误差或 seam/notch 对齐误差。
- 人体穿着图、遮挡、复杂背景、多视图拼图和极端尺码差仍需单独评估。
- canonical 区域目前是图像结构代理，不是服装工业纸样拓扑。
- 真实新增布料的织纹方向、色落连续性和缝线拓扑延伸，仍需在带 DXF/实测标注的数据上验证。

## 下一阶段数据门槛

进入物理几何验证至少需要：同一款裤子的源尺码与目标尺码厘米表、正面平铺图、人工确认 mask/结构点，以及研发用 DXF 或等价轮廓真值。最终用户仍只需提供单张图片与目标尺码；这些额外数据只用于训练、监督和评估。
