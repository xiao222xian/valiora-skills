# 章节技法索引

每章选一种，让章与章的差异成为看点。技法名只用于方案与内部沟通，不上屏。路径指向起步模板里的示例实现。

| 技法 | 适合的画面 | 示例 |
| --- | --- | --- |
| 柱面投影 + 纹样展开图 | 器物表面纹饰（陶罐、瓷瓶） | `src/scenes/S01Neolithic.tsx` |
| 裂纹生长 + 回纹密铺 | 甲骨卜兆、青铜纹饰 | `src/scenes/S02Shang.tsx` |
| 动态排版 + 弹簧动力学 | 多家观点并置（竹简、引文墙） | `src/scenes/S03Warring.tsx` |
| 融球合并 + 线描生长 | 多方合一、长城一类的连续线 | `src/scenes/S04Qin.tsx` |
| 路径动画 + 跟随镜头 + 粒子沉积 | 路线（丝路）、材料的形成（纸） | `src/scenes/S05Han.tsx` |
| 碎片分屏与重组 | 分裂与统一 | `src/scenes/S06Split.tsx` |
| 等距生长 + 计数粒子 | 城市格局、数量（诗作数） | `src/scenes/S07Tang.tsx` |
| 视差长卷 + 三维翻转 | 长卷画、活字排版 | `src/scenes/S08Song.tsx` |
| 程序生长纹样 | 缠枝花卉、青花盘 | `src/scenes/S09Yuan.tsx` |
| 程序海浪 + 航迹 + 纵深穿越 | 航海路线、宫城中轴 | `src/scenes/S10Ming.tsx` |
| 比例数据 + 断裂 | 朝代长度比例、历史转折 | `src/scenes/S11Qing.tsx` |
| 快切排版 + 铅字 | 密集大事年表 | `src/scenes/S12Modern.tsx` |
| 像素聚合 + 缩放总览 | 数字时代、全片字形光谱 | `src/scenes/S13Today.tsx` |

片头（墨滴晕开 → 一笔成轴）见 `src/scenes/S00Opening.tsx`；片尾（只有片名卡：印章 + 出品 + 官方 Logo + 说明，不做章节回顾）见 `src/scenes/S14Outro.tsx`。
转场种类见 `src/components/Reveal.tsx`。
