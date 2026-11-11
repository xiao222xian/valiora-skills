# 动态图志 · Motion Atlas

![Version](https://img.shields.io/badge/version-0.9.1-CC785C)

无实拍，把一个主题沿一条轴（时间、地图、图鉴、工序或尺度）分章，做成每章一种视觉的动态设计短片：章节标题卡与进度轴 HUD、旁白（TTS 或真人原声，逐句可换）与一眼能读的大字幕（默认中文，可中英双语）、每章一段 AI 配乐并卡在拍上、事实核查；默认交付 16:9 横版与 16:9、4:3、3:4 三张封面（AI 无字底图，片名、印章与 Logo 由合成排字），用户点名时加出 9:16 竖版；片尾署名卡自带许可链接，交付报告带 AI 生成内容清单、版本历史与费用账本汇总，另附各平台文案实测长度与章节时间轴的发布交接单。`lov-film` 片型套件的第一个成员。

## 安装

```bash
npx skills add lov-motion-media-creator -g -y
```

本地开发：源目录 `motion-media-creator-skill`，安装入口 `lov-motion-media-creator`。0.9.0 起由 `lov-film-atlas` 更名为 `lov-motion-media-creator`（展示名「动态图志 · Motion Atlas」不变）；0.2.0 起由 `lov-film-chronicle` 更名，编年只是其中一种轴。

## 用法示例

- 「做一条讲中国瓷器演进的动态图志，横竖两版」
- 「这期旁白用我的录音，字幕中英双语」
- 「文字再大一些，每章换一段音乐，节奏卡紧」
- 「丝路沿线 12 座城，做成地图巡游动画」
- 「13 种中国传统色的图鉴动画」
- 「像作品集一样，用动态设计讲一遍互联网的发展史」
- 「封面不够吸引人，用 AI 生图重做一版，视频号要 3:4 和 4:3」
- 「给 B 站和 YouTube 各出一版简介，带章节时间轴和署名，量一下长度」
- 「简单说说这片的版本迭代与消耗」
- "Make a motion atlas of the history of typography"

## Profile

读取共享 `user-profile/v1`：品牌名、官方 Logo 路径、印章文字、输出目录，以及默认画幅与旁白方式（`records.default_aspect`、`records.narration`）。用户明确说出的长期偏好用 `scripts/profile_store.py record ... --confirm` 保存。

## 依赖

- 必需：Node 24+、pnpm、Remotion 4；Python 3.9+（fontTools、Pillow、numpy、opentype-sanitizer 或 uv）；ffmpeg / ffprobe；uv（临时拉起 librosa 做分章配乐的节拍分析）。
- 旁白：豆包 Seed-TTS 2.0（环境变量 `VOICENGINE_API_KEY`），或逐句的真人录音。
- 配乐：OpenRouter 上的 Lyria 3 Clip（环境变量 `OPENROUTER_API_KEY`，0.04 美元一条 30 秒），或其他 AI 音乐模型。
- 可选：`lov-media-creator`（质检脚本）、`lov-channels-cover`、`lov-media-publisher`。

## 质量门禁

- 画面不展示制作技术；元数据只含片名与出品方，文件内不含工具名。
- 上屏事实有来源，示意画面有标注，年份计数与画面同步。
- 字幕、标注、数据与大数字不低于字号下限（1920×1080：字幕 46 / 27 px，标注 22 px，数据 26 px，大数字 120–160 px）；角落标注保持小字。
- 旁白只说事实台账里的事实，片名卡与片尾卡上没有旁白；母带 -16 LUFS、真峰值 ≤ -1 dBTP。
- 交付的每个画幅（默认只有 16:9）逐章联系表与转场窗口检查通过；成片从编码文件回读质检。

```bash
python3 scripts/validate_skill.py .
```
