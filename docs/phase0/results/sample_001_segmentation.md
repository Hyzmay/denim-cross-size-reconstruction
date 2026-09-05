# Sample 001 Segmentation Result

运行日期：2026-09-05

输入与预注册标准见 `docs/phase0/samples/sample_001_front_back.md`。

## Baseline: Largest Component Only

- Run：`runs/sample_001-baseline-largest/`
- Foreground area ratio：`0.3150017146776406`
- Component count：`1`
- Bounding box：`[61, 53, 429, 1005]`
- 结果：失败。正面裤型被保留，但背面裤型被最大连通域过滤删除；同时未达到双视图前景面积下限 `0.35`。

## Changed Variable: Major Multi-Component Retention

只改变连通域选择：由“只保留最大连通域”改为“最多保留两个面积不小于最大连通域 `25%` 的主连通域”。背景建模、形态学参数与 GrabCut 参数保持不变。

- Run：`runs/sample_001-multiview-protocol/`
- Method：`border_grabcut`
- Foreground area ratio：`0.6204938271604938`
- Component count：`2`
- Foreground border pixel count：`0`
- Component areas：`367394`、`356350`
- Component bounding boxes：`[61, 53, 429, 1005]`、`[593, 57, 427, 1000]`
- Mask SHA-256：`F14333C6F9E9CC6BF85B1CA11337CA7ABA8E7813614F3088686A5B183DE47F46`
- 重复运行：mask 完全一致。

## Visual Inspection

- 正面和背面两个主体均保留。
- 两个视图的 waistband、crotch、左右裤腿和卷边 hem 均可见且轮廓连续。
- 白色背景主体被排除，没有前景接触图像外边界。
- 右下角水印没有成为第三个主要连通域，但与背面右裤脚相连的水印像素进入了 mask，造成局部边界污染。
- 正面内腿边界存在少量阶梯状误差，需要人工 mask 才能量化。

## Conclusion

多视图主体保持标准通过；像素级分割质量仍为 inconclusive。没有人工 ground-truth mask，因此不报告 IoU、Dice 或 boundary F1，也不把合成测试指标用于该真实样本。

下一个最小实验是为该图建立人工校验 mask，或比较一个预训练 garment/person parsing 模型，重点评估水印、浅色卷边和内腿边界。几何结构阶段应先使用左侧正面视图，避免右侧水印污染传播到 canonical representation。

