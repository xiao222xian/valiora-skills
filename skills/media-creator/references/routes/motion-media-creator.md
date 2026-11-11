# 路由：动态图志 → `lov-motion-media-creator`

无实拍、屏幕文字与旁白一起叙事的动态设计片（三维或二维），风格判断归片型 Skill `lov-motion-media-creator`（2026-10-12 由 `lov-film-atlas` 更名，展示名「动态图志 · Motion Atlas」不变）；本 Skill 只承担共享的音频母带、双画幅、媒体质检与交付契约。

- 触发：沿一条轴分章、每章一种视觉——编年、地图巡游、图鉴、工序、尺度。
- 输入：主题与资料来源；Profile 里的官方 Logo 与印章文字；可选配乐候选；旁白用 TTS 或用户逐句录音。
- 输出：16:9 平台成片（用户点名时加 9:16）、16:9 / 4:3 / 3:4 三比例封面、事实台账与交付报告；状态按 [`delivery-contract.md`](../delivery-contract.md)。不带旁白时记 `subtitle_status=not-applicable`；带旁白时字幕由批准的旁白稿生成并烧进画面，按片型 Skill 的门禁验收。
- 必问：轴与章节表先给作者看再开工；缺官方 Logo 时问一次；付费配乐、TTS 与 AI 封面生成先说明单价。
- 默认：2–4 分钟、8–15 章、30fps；只出 16:9 1920×1080，用户点名时同源加出 9:16 1080×1920。
- 不适用：有实拍、录屏或口播要剪（留在本 Skill）；只讲一个算法（`lov-algo-viz-creator`）；单个动效或 Logo 演绎（`hyperframes` / `motion-graphics`）。
