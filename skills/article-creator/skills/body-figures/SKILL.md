---
name: lov-body-figures
description: >
  判定一篇公众号文章的正文是否需要配图，交接给 `lov-illustrate` 产出，并验收图片是否真的承载了正文的证据。Use when the user says“正文要不要配图”“给正文补数据图”或“decide and add body figures”。
license: MIT
compatibility: "Embedded module of lov-article-creator; the decision gate is instruction-first, production is delegated to lov-illustrate."
depends_on:
  - lov-branding-consistency
  - lov-illustrate
metadata:
  author: LovStudio
  version: "0.4.0"
  tags: [wechat, body-figures, evidence]
  dependencies: []
---

# 正文图解 · Article Figures

分享封面负责让读者点开，`4:3` 首图负责开场，正文配图负责让读者**核对**。三个角色不能互相替代。

本模块拥有「这篇要不要配图、配什么类型」的判定权，不拥有画图能力；产出交给 `lov-illustrate`。

## Triggers

### Activate when

- “这篇正文要不要配图？”
- “给正文补上那几张数据图。”
- “Decide whether the body needs figures, then add them.”

### Do not activate when

- 只需要分享封面或 `4:3` 首图；交给 `lov-cover-package`。
- 正文尚未定稿；先交给 `lov-article-writing`。
- 处理 `repost` 包；来源正文是冻结区，不得插入发布方图片。

## Inputs and outputs

输入是文章包内已装配的 `article.md` 与 manifest。输出是写回 manifest 的 `body_figures` 判定，以及判定为需要时落在包内 `figures/` 的图片和回写后的正文。

## Workflow

1. 完整读取 Kit 根目录 `references/body-figures.md`。
2. 先判断任务性质：用户是否提供了一份完整的真实素材集合（整套 PPT、完整分镜等）并要求“完整存档 / 实录复刻”。是的话默认全量收录这份素材（含章节页、过渡页），不擅自精选；只有用户明确要求“挑重点”才转入下一步的精选判定。
3. 判定题材。数据调研、评测、对比、教程和机制解释类默认需要；招募、活动、探店、旅行和空间介绍类默认需要，并按 Kit 根目录 `references/body-figures.md` 的「地点、活动与招募类：富媒体与组图」执行；用真实故事串起履历的叙事与招募长文默认需要，并按同一文件的「叙事、履历与招募长文：图跟着故事走」执行；观点、随笔、短评和公告默认不需要。
4. 判定为不需要时，写出本篇专属理由并结束；不接受“篇幅短”“暂不需要”这类无信息理由。
5. 判定为需要且属于「编辑摘要」而非「完整存档」时，先列出正文里每一处**由数据或结构承担论证**的位置，这些位置才是配图的候选，不按篇幅平均分配。
6. 每张配图只在真正需要单独归属、来源链接或补充解释时才加图注；同一句样板说明（如图片来源、性质）不得在每张图下重复，写进 alt 文本一次即可。
7. 需要新产出图片时，把 `article.md` 交给 `lov-illustrate`，要求图片落在 `figures/`、按相对路径回写；「完整存档」场景下素材本身就是真实产物，直接放入 `figures/` 并引用，不必也不应该交给 `lov-illustrate` 重新生成。
8. 回写后重跑 Kit 根目录 `scripts/build_article_package.py`，带上 `--figures` 与 `--figures-reason`，让 manifest 与实际文件一致。

## Acceptance

- `body_figures.decision` 是 `required` 或 `not-required`，不是 `undecided`。
- 判定为 `required` 时，正文至少嵌入一张图，且核心数字由数据图表而非 AI 概念图承担。
- 图片数字与正文、manifest 和 `sources.md` 一致。
- 图片在手机宽度下可读；`4:3` 首图不计入正文配图。
- 「完整存档 / 实录复刻」任务已核对用户提供的真实素材集合是否被全量收录，没有未经用户同意的擅自精选或遗漏（含章节页、过渡页）。
- 没有同一句样板图注在多张图下重复出现。
- 招募、活动、探店类文章中，读者将要去的每个地点都有相邻实拍；同主题 3 张以上素材已做成手机可读的组图，并通过隐私门禁。
- 叙事、履历与招募长文中，每张图都紧跟点名它的段落；演讲、分享和活动的图里看得到作者本人；成就与数字由原始页面截图或汇总证据图承担，且与正文一致。

## Dependencies

`lov-illustrate` 是配图产出的唯一 owner，仅用于需要新产出图片的场景；「完整存档」场景下的真实素材直接交接，不经过它重新生成。本模块随 Kit 分发，只交接 Markdown 与判定结果。
