# ASS/SSA 全屏艺术字与场景卡片

## 为什么不能只用 SRT

SRT 主要只有序号、开始时间、结束时间和纯文本。播放器可能对 `<i>`、`<b>` 或换行提供有限支持，但位置、字体、颜色、描边、阴影和动画没有稳定的跨播放器契约。因此“角色第一次登场时全屏显示名字和解释”应使用 ASS/SSA，而不是把样式信息塞进 SRT。

## ASS 能表达什么

ASS 事件可以使用覆盖标签：

- `\pos(x,y)`：把事件放到指定位置。
- `\an1`–`\an9`：九宫格对齐；`\an5` 是中心。
- `\fs64`、`\fnFont Name`：字号和字体。
- `\c&H00D7F7&`、`\alpha&H80&`：颜色和透明度。
- `\bord3`、`\shad2`：描边和阴影。
- `\fad(400,600)`：淡入淡出。
- `\move(x1,y1,x2,y2)`：移动文字。
- `\t(0,800,\fs90)`：在时间区间内变换样式。

脚本会生成 `Default`、`ArtTitle`、`SceneCard` 和 `Watermark` 四种基础样式。默认 `elegant` 视觉配置使用暖白低对比度、小字号、细描边、轻淡入淡出和无装饰框；`classic` 才使用较大的金色标题。用户可在 art-cue JSON 中覆盖位置、对齐、字号、颜色、字距和描边；复杂动画仍可在 ASS 文件中手工调整。

艺术 ASS 还可生成一个低透明度的 `Watermark` 事件，默认使用 B / `cinematic_serif` 电影衬线方向：暖金色、轻微字距、共享 Profile 的品牌 Logo 和右下角安全边距，默认文字为“手工川工作室 Agent 字幕组”。Logo 默认从 `brand.logo` 读取，并与文字使用同一暖金色；带 Logo 时省略文字专用横线，保持 Logo 与品牌文字成为一个紧凑锁定组合。Logo 与文字合并在同一个 `Watermark` 事件中，所有 SVG 路径合并为一个无阴影矢量块，Logo 后加入透明排版占位来计入 Logo 宽度，并按播放器的矢量横向缩放校正 Logo 宽高比、对齐文字中线。也可用 `--watermark-logo "/path/to/logo.svg"` 指定一次性 SVG，生成器会将 SVG 路径转换成 ASS `\p1` 矢量并内嵌到输出中。可选方向包括 `minimal`、`cinematic_serif`、`soft_glow`、`glass`、`signature` 和 `gold_title`；用 `--watermark-style` 选择，用 `--watermark-text "你的品牌名"` 改名，用 `--no-watermark` 关闭。普通 SRT 不会包含水印。

图像叠加视频需要保留原图 Logo 时，可用 `--no-watermark-logo` 只输出文字事件，并用 `--watermark-end HH:MM:SS.mmm` 将文字水印延长到视频尾部。

### 水印横线的跨播放器版式不变量

部分播放器会把事件的 `Watermark` 样式对齐再次应用到 `\\p1` 矢量绘图。为了避免 B/E 横线在左、右之间漂移，生成器固定遵守以下规则：

- `Watermark` 样式自身使用底部居中对齐（`Alignment=2`）。
- 品牌文字和横线都使用 `\\an2`，并共享完全相同的 `\\pos` 横坐标。
- 横线路径从 `m 0 0` 开始，不能再按左端、右端或半个线宽做位置补偿。
- 自定义中英混排品牌名只影响文字安全边距的估算，不改变横线与文字的共享中心锚点。

修改水印布局后运行：

```bash
python3 scripts/test_watermark_layout.py
```

该测试覆盖共享 Profile 默认 Logo、显式 Logo、默认品牌名、短品牌名、长中英混排品牌名和 `--no-watermark`，验证样式对齐、Logo 矢量事件及文字/横线横坐标一致。

## Art-cue JSON

```json
[
  {
    "start": "00:00:12.000",
    "end": "00:00:17.000",
    "text": "ARAGORN\\nHeir of Isildur",
    "style": "ArtTitle",
    "position": [960, 430],
    "align": 5,
    "font_size": 54,
    "color": "#E8DDCA",
    "outline": 1,
    "shadow": 1,
    "fade_in": 650,
    "fade_out": 900
  }
]
```

`start`、`end` 可以是 `HH:MM:SS.mmm` 或 `HH:MM:SS,mmm`。文本中的换行会转成 ASS 的 `\\N`。位置以 `--resolution` 的 PlayRes 坐标为准，默认是 1920×1080。

## 工作边界

- 能做：开场角色名、地点卡片、章节标题、居中大字、上下三分之一位置的字幕、简单淡入淡出和移动。
- 需要视频证据：精确判断角色何时登场、画面留白在哪里、字幕是否会遮挡主体。只从文本无法可靠推断这些信息。
- 需要烧录时：使用 FFmpeg 的 `subtitles`/libass 滤镜，并确认字体已安装。ASS 文件本身不改变视频。
- 如果目标播放器不支持 ASS，提供同一份 SRT 作为可移植降级版本，但要明确说明它不会保留全屏艺术字布局。
