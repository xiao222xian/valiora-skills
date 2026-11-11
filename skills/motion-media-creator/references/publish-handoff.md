# 发布交接

交付之后、发布之前，写一份交接单交给 `lov-media-publisher`：哪个文件进哪个槽，每个平台用哪段文案、量过多长，
哪些块可以原样追加到任何文本末尾，哪些事要用户拍板。发布 Skill 只读交接单和 `publish-copy/`，不回头翻交付报告。

## 目录

```
output/reports/vX.Y/
├── publish-handoff.md             交接单（模板见下）
└── publish-copy/
    ├── chapters.txt               章节时间轴：node tools/chapters.mjs 生成，不手写
    ├── credits-full.txt           署名完整版：逐条带许可链接与来源链接（node tools/credits.mjs 生成）
    ├── credits-compact.txt        署名压缩版：许可链接合成一行（同上）
    ├── wechat-channels.txt        各平台正文，不含任何追加块
    ├── bilibili.txt
    ├── youtube.txt
    ├── bilibili+chapters.txt      拼好的变体：文件名按拼接顺序写组成部分
    ├── …
    └── <平台>-published.txt       用户在平台上手改并发布的原文（金标准，发布后回写）
```

章节时间轴在 Remotion 工程根目录生成：`node tools/chapters.mjs --out ../../output/reports/vX.Y/publish-copy/chapters.txt`。
它从 `src/timeline.ts` 取起点，时间码向下取整到秒，第一条是 `00:00`；少于 3 章或任一章显示时长不足 10 秒时非零退出、不写文件，
不足 11 秒时警告。`--names short` 换用短章名。章节时长在结构方案阶段就按 ≥ 11 秒设计：《如何打造一款特斯拉》有三章
显示时长正好 10 秒（2026-10-12），刚够 YouTube 的下限。

拼接和测长用同一段脚本，块与块之间空一行；长度是 Python 字符数（含换行），与 `lov-media-publisher` 的 `check_copy.py` 口径一致：

```bash
python3 - output/reports/vX.Y/publish-copy bilibili chapters credits-compact <<'EOF'
import sys
from pathlib import Path
d, parts = Path(sys.argv[1]), sys.argv[2:]
text = "\n\n".join((d / f"{p}.txt").read_text(encoding="utf-8").strip("\n") for p in parts)
(d / ("+".join(parts) + ".txt")).write_text(text + "\n", encoding="utf-8")
print(len(text), "+".join(parts) + ".txt", "has <>" if any(c in text for c in "<>") else "")
EOF
```

视频号、B 站、小红书的字段再跑一遍 `check_copy.py`（用法见 `lov-media-publisher`）；它不覆盖 YouTube，YouTube 按上面的长度和
「不含 `<` `>`」自查。

## 平台限制

| 平台 | 字段 | 限制 | 依据与日期 |
| --- | --- | --- | --- |
| 视频号 | 短标题 | 6–16 字，不能有逗号（可用空格代替） | 平台报错原文；6 字下限 2026-10-12 实测（`lov-media-publisher`） |
| 视频号 | 描述 | 1–3 行钩子 + 5–10 个精准话题 | 发布 Skill 的写法约定，不是平台上限（2026-08-26） |
| 视频号 | 封面 | 3:4 个人主页卡片、4:3 分享卡片两个槽 | 2026-10-12 本片发布时页面所见；槽位数以页面为准 |
| B 站 | 标题 | ≤ 80 | 页面计数器 `n/80` |
| B 站 | 简介 | ≤ 2000 | 页面计数器 `n/2000` 实测 |
| B 站 | 标签 | ≤ 10；部分名字是话题专用，提交即被拒；「原创」可能被平台自动带上并占一个名额；平台按内容或账号自动猜的标签要先删 | 2026-10-12：「新能源汽车」被拒（「当前tag为话题专用，不允许自定义添加」），「原创」自动带上，自动带的「创意」已删 |
| B 站 | 章节 | 每行 `MM:SS 章节名`，可点击；成片有已核验章节时简介必须带全 | `lov-media-publisher` 门禁 |
| YouTube | 标题 | ≤ 100 字符，不含 `<` `>` | 平台规则，2026-10-12 记录，未撞线 |
| YouTube | 简介 | ≤ 5000 字符，不含 `<` `>` | 同上 |
| YouTube | 标签 | 合计 ≤ 500 字符 | 同上 |
| YouTube | 章节 | 第一条 `00:00`，至少 3 条，每条 ≥ 10 秒（按显示的时间码算） | 同上；`tools/chapters.mjs` 检查 |

页面上读到的限制与本表不同时，以页面为准，并把原文和日期补进本表。

## 金标准：第一个平台上用户改过的文本

- 第一个平台发布时，用户在页面上手改过的文案（`description_source=user-edited`）就是本期的金标准：原文存
  `publish-copy/<平台>-published.txt`，写进交接单「发布记录」。Agent 之前写的各平台正文从此只是草稿，不再恢复。
- 后续平台从金标准派生，只做两类改动：
  1. 平台机制要求的最小适配：视频号的 `#话题` 移到 B 站标签字段，简介里删掉话题段；YouTube 可以保留；标题按平台字数派生。
  2. 在末尾原样追加独立块：先章节时间轴，再署名（需要时）。块内不改字，也不改写钩子。
- 所以章节时间轴和署名必须是独立文件，不揉进任何一个平台的正文；派生后重新测长、重新跑 `check_copy.py`。
- 追加署名会改动用户文本，发布前要问用户。片尾署名卡本身完整（见 [fact-and-disclosure.md](fact-and-disclosure.md)「片尾署名」），
  简介的署名段只是补充，用户可以不加。

2026-10-12《如何打造一款特斯拉》：用户在视频号把描述改成四段 124 字的制作手记加 11 个话题（全文 194 字），Agent 原先的
「一辆车，大约由 3 万个零件组成」草稿弃用。

| 变体 | 组成 | 长度 / 上限 |
| --- | --- | --- |
| 视频号（用户发布） | 用户原文 + 11 个话题 | 194 |
| B 站简介 | 原文去话题段 + 时间轴 15 条 | 260 / 2000 |
| B 站简介（加署名） | 上一行 + 署名压缩版 | 1938 / 2000 |
| YouTube 简介 | 原文（含话题）+ 时间轴 | 330 / 5000 |
| YouTube 简介（加署名） | 上一行 + 署名完整版 | 2605 / 5000 |
| 弃用：Agent 的 B 站草稿 | 钩子、说明 + 时间轴 + 署名完整版 | 2646 / 2000，超限 |

## 署名块

- 完整版：逐条「作者，《标题》，许可（许可链接），来源链接」；不要求署名的素材（CC0、公有领域、Pexels）合成一行。
  本片 11 条 CC BY，2273 字。
- 压缩版：逐条「作者，《标题》，许可，来源链接」，不逐条写许可链接；许可链接合成一行
  （`许可协议：creativecommons.org/licenses/by/2.0 、/by/3.0 、/by/4.0`）；CC0、公有领域、Pexels 那一行换成
  「其余素材署名见片尾」一类指回片子的话（片尾或片中标注里确实有它们时才这样写）。本片 1676 字，放进 B 站后 1938 字。
- 两版都由 `node tools/credits.mjs --out-dir ../../output/reports/vX.Y/publish-copy`（在 Remotion 工程根目录跑）从 `src/credits.ts`
  生成，片尾署名卡读的是同一张表，条目、顺序自然一致；脚本打印两版长度（与上面的拼接脚本同一口径），缺来源链接、许可推不出链接或重复条目时
  非零退出、不写文件。改了素材表，两版重出、片尾静帧重看，不手改这两个文件。
- 这个脚本在《如何打造一款特斯拉》之后才有：把该片的 11 条 CC BY 填进素材表的草稿副本实测，压缩版 1668 字（2026-10-13；该片手写的
  压缩版 1676 字，标题行写法不同）。

## 交接单模板

````markdown
# <片名> · 发布交接 vX.Y

状态：platform-ready，尚未上传。发布交给 `lov-media-publisher`。

## 文件与槽位

| 槽位 | 文件 |
|---|---|
| 成片 16:9（B 站、YouTube；视频号横版） | `output/videos/<品牌>-<片名>-横版16x9-<日期>-vX.Y.mp4` |
| 成片 9:16（视频号竖版，做了才有） | `…-视频号9x16-…` |
| 封面 16:9（B 站 16:9 槽、YouTube 缩略图） | `output/images/<品牌>-<片名>-封面16x9-<日期>-vX.Y.jpg` |
| 封面 4:3（B 站首页槽、视频号分享卡片） | `…-封面4x3-…` |
| 封面 3:4（视频号个人主页卡片） | `…-封面3x4-…` |

## 文案（长度为实测）

| 平台 | 字段 | 内容或文件 | 长度 / 上限 | 预检 |
|---|---|---|---|---|
| 视频号 | 短标题 | <原文> | n / 6–16 | check_copy pass |
| 视频号 | 描述 | `publish-copy/wechat-channels.txt`（话题 n 个） | n | pass |
| B 站 | 标题 | <原文> | n / 80 | pass |
| B 站 | 简介 | `publish-copy/bilibili+chapters.txt` | n / 2000 | pass |
| B 站 | 简介（加署名备选） | `publish-copy/bilibili+chapters+credits-compact.txt` | n / 2000 | pass |
| B 站 | 标签 | <逐个列出> | n / 10 | pass |
| YouTube | 标题 | <原文> | n / 100 | 无 `<` `>` |
| YouTube | 简介 | `publish-copy/youtube+chapters.txt` | n / 5000 | 无 `<` `>` |
| YouTube | 简介（加署名备选） | `publish-copy/youtube+chapters+credits-full.txt` | n / 5000 | 无 `<` `>` |
| YouTube | 标签 | <逐个列出> | 合计 n / 500 | — |

## 可追加的块

- 章节时间轴：`publish-copy/chapters.txt`，n 条，最短显示 n 秒（`tools/chapters.mjs` 通过；低于 11 秒的章写出来）。
- 署名：完整版 `credits-full.txt`（n 字）、压缩版 `credits-compact.txt`（n 字），`tools/credits.mjs` 从 `src/credits.ts` 生成。片尾署名卡已列全部条目与许可链接。

## AI 生成内容清单

<按 fact-and-disclosure.md「AI 生成内容清单」逐项列表；没有的类别写「无」>

平台事实：<YouTube 对 AI 音乐的声明要求；《人工智能生成合成内容标识办法》第十条；作者偏好及其范围。照抄 fact-and-disclosure.md，
写明核实日期>

## 发布时需要你决定

- 各平台的 AI 标注：视频号「视频标注」、B 站「创作声明」（投稿后不能改）、YouTube 的 altered or synthetic content 声明。
  默认值按 Profile 偏好；Skill 不替你选，也不下合规结论。发布 Skill 登记为 `auto` 的平台（<逐个列出>）提交前不再问、
  按偏好不标注；要标注，请在这次发布请求里说明。
- 是否在简介末尾追加署名段（片尾已有完整署名）。
- 原创声明、合集、话题与标签。

## 发布记录

### <平台>

- 状态：<`lov-media-publisher` 的状态字段>；回读时间与证据（内容列表条目、状态原文）。
- 描述来源：`description_source=<…>`；用户手改时原文存 `publish-copy/<平台>-published.txt`，此后它是金标准。
- 平台改写或拒绝的字段：expected / actual / reason。
````

交接单里的每个数字都来自实测（文件字符数、`check_copy.py`、`chapters.mjs`、`credits.mjs` 的输出），不估算。用户在平台上改过文字后，
重写「文案」表并把旧变体标为弃用，不删除。

交给用户时，回复里直接贴出「AI 生成内容清单」与「发布时需要你决定」两节，不只给交接单路径。`lov-media-publisher` 的
`confirm-final` 平台会在终稿确认时再问一次 AI 标注；`auto` 平台按偏好不标注、直接提交，发布后才报告，B 站创作声明又不能改，
这次回复是用户唯一一次在提交前看到清单的机会（见 [fact-and-disclosure.md](fact-and-disclosure.md)「AI 生成内容清单」）。
