# Changelog

## [0.6.0] - 2026-10-30

来自「对话易七猫」v0.3（2026-10-30）。被访者看完 v0.2 在微信里提了三处：人名条头衔、自我介绍处加生活照（「在你要我介绍自己的时候可以加点图」）、
美颜要更明显（「要修！」，作者要自动化）。相册与加强美颜当时只写在工程本地（`work/remotion/src/Film.tsx` 的 `AlbumInsert`、`work/tools/fx_strong.py`），
本版并进 Skill；前两版漏用生活照的原因（盘点时子文件夹被过滤掉）写进盘点规则。

### Added

- 起步工程的相册插入 `inserts[].album`（`Film.tsx` 的 `AlbumInsert`，`types.ts` 的 `album`）：被访者本人的竖版生活照按顺序均分插入时长、一张张落下，
  叠成各带倾角与偏移的白边卡片堆，背后是当前那张的虚化底，字幕在上层；卡片按照片自身宽高比（`ar`）定大小，下沿停在字幕带之上，顶边在章节进度条之下
  （工程版顶边在 y=230，开着进度条时会压到它；本版放到 `TAG_TOP`，卡片小约 3%）。起止与 0.5.1 的其他插入一样用 `span()` 按帧取。
  原来的照片卡固定 16:9，竖图放进去会被裁成一条横带。
- `scripts/decorate.py`：相册插入不用写顶层 `img`，取第一张，时间线里每个插入都有图名。
- `scripts/check_timeline.py`：相册每一张都要在 `--public` 下存在，缺 `ar`（或不是正数）报错；人名条或地点条与相册同时出现时给 WARN
  （按 `Math.round` 取帧比较，人名条在相册第一帧收掉不算重叠）。
- `scripts/glitch_scan.py`：`--timeline` 下命中落在相册里时，写出当时最上面那张和它是第几张（如 `img/life-3.jpg (album 3/5)`）。相册没有自己的标签：
  卡片落下与虚化底淡入都跨好几帧。
- `scripts/fx_pieces.py --level strong`：强档美颜，移植自工程的 `fx_strong.py`。皮肤区在半分辨率上做双边滤波（sigmaColor 40，半分辨率下
  sigmaSpace = 脸宽 / 32）再放大回去，提亮 ×1.06 + 4，整帧 gamma 0.91，强度默认 1.0，不改脸型；`--photo` 同样认 `--level`。档位写进
  `<片段>.fx.json` 缓存键；不给 `--strength` 时取档位的默认值（自然档仍是 0.7）。脚本说明记下速度陷阱：全分辨率下强档的滤波核约为脸宽的五分之一，
  近景一张脸 0.5–1 秒，工程里 4 个进程每秒只有 2.6 帧。
- 文档：SKILL.md Step 1、5、6、10；`references/pipeline.md` 第 1 节（素材清单连子文件夹，作者说加了照片先找新增目录）、第 5 节（强档）、第 6 节
  （相册写法与 `check_timeline` 的新检查）、第 9–10 节（相册标签）；`references/style-grammar.md` 第 5 节（有相册时人名条与地点条先收）、第 6 节
  （相册规则；强档美颜，改脸型仍要被访者明确同意）；`references/pitfalls.md` 新增「盘点」一节（子文件夹里的生活照两版都没用上）与强档速度一条；
  `references/context-sources.md` 两条（lov-wdb-cli 0.6.4 及更早读微信 4.x 时 `isOwn` 恒为空，发送人看 `senderUsername`；聊天另存的图片名
  `Weixin Image_<时间>_<序号>_…` 里的序号就是消息的 local_id，即 lov-wdb-cli 输出的 `source.rowid`）；skill-card 的任务、风险与伦理说明。

### Changed

- `<片段>.fx.json` 多了 `level` 键：0.5.x 缓存的片段升级后第一次运行会重算一次（自然档结果与原来逐帧相同）。

### 复现核验

- 美颜（对话易七猫两段近景，项目只读，产物写临时目录）：新强档与工程 `fx_strong.apply` 逐帧比，62/62、154/154 帧的数组与人脸框完全相同；走完整的
  `one()` 编码路径，强档片段与工程 v0.3 的 `v-f3be9dfcc0fe.fx.mp4` 字节相同（md5 一致），`.faces.json` 相同，同参数再跑命中缓存、换档重算。
  自然档与 0.5.1 逐帧相同（62/62、154/154），`--photo` 输出 md5 相同；`--photo --level strong` 与 `fx_strong.py --photo --strength 1.0` 的 md5 相同，
  工程里的 `fx_strong.py` 在新脚本下照常运行。速度：强档每帧 112–125 毫秒，自然档（全分辨率）280–406 毫秒；脸宽 519、595 px 时全分辨率强档
  滤波一张脸 456、979 毫秒，半分辨率 56、93 毫秒，两者平均差 0.64、0.39 个灰阶。
- 相册：临时目录用 `setup_starter.py` 装新起步工程，套上对话易七猫 v0.3 的数据、中间轨与 5 张生活照（APFS 克隆），`tsc --noEmit` 通过；渲染第 474、
  500、540、580、617 帧，与 v0.3 成片同帧并排看：叠卡顺序、倾角、虚化底、字幕层次与卡片下沿位置一致，只有顶边按设计下移。另给时间线加 5 个零长章节、
  让进度条显示，渲染第 540、580 帧：卡片在进度条之下，进度条完整可读。
- `decorate.py`：去掉 v0.3 package 里相册的顶层 `img` 后重跑，`timeline.json` 与 `subs.json` 和工程 v0.3 的完全相同。
- `check_timeline.py`：v0.3 数据 PASS、0 WARN（人名条与地点条在相册第一帧收掉）；一张相册照片改成不存在的文件名、删掉一张的 `ar`，各报 1 个 ERROR；
  人名条按默认 4.6 秒、地点条伸进相册一帧，各报 1 个 WARN。
- `glitch_scan.py`：重扫 v0.3 渲染件，3 处命中（第 420、3324 帧 `motion`，第 4610 帧 `flat outro`）与 v0.3 的封装记录一致，相册所在的第 473–618 帧
  没有命中；在相册前后取 10 个帧号测标签，第 500、540、580、617 帧分别是 `life-1`、`life-3`、`life-4`、`life-5`，与成片画面最上面那张一致，
  第 472、619 帧不在相册里。

### 已知缺口

- 相册照片的 `ar` 要手写（v0.3 是 0.75 与 0.6667），`check_timeline` 只查有没有，不核对图片实际尺寸；写错时照片按 cover 裁切，不会变形。
- 强档的提亮量（gamma 0.91）量自易七猫自己修的那一版，只有这一个样本；换了被访者或光线差别大时，先给作者看前后对比。

## [0.5.1] - 2026-10-30

补上 0.5.0「已知缺口」里的起步工程照片插入晚一帧。

### Fixed

- 起步工程 `Film.tsx`：照片插入与参考卡改为像视频 B-roll 一样按帧取起止（从第 `Math.round(start × fps)` 帧起，到第
  `Math.round(end × fps)` 帧前止；三种插入共用 `span()`），不再拿 `frame / fps` 与秒数比较。`decorate` 把时间写成三位小数，30 fps 下
  落在帧边界上的起点有三分之一被进位到帧后，照片晚一帧出现、也晚一帧结束；压在片尾上，晚的那一帧露出底下的黑场（对话易七猫 v0.1
  第 4538 帧、对话王燚 v0.1 第 2825 帧）。快门闪白、推近与参考卡淡入的局部帧号随之是从 0 起的整数。
- `scripts/glitch_scan.py`：`--timeline` 判断插图在不在屏上时用同一取帧规则（原来对照片按 `frame / fps >= start` 建模）。0.5.1 之前装的
  工程里晚的那一帧仍在 `insert-flash` 的窗口里，现在会列出那张插图，本帧却是黑场。

### Changed

- `references/pitfalls.md`「照片插入的起点取整晚了一帧」改写规则：起步工程已修；0.5.1 之前装的工程改本片 `Film.tsx` 的同样两处，或给片尾
  照片起点加 `"delay": -0.001`。`references/pipeline.md` 第 9–10 节 `insert-flash` 的读法同步。

### 复现核验

- 临时目录装两份起步工程，只有 `Film.tsx` 不同（0.5.0 与本版），`media.video` 留空（黑底），时间线照对话易七猫 v0.1 的片尾：4742 帧、
  第 4538 帧进片尾，带闪白的照片起点 151.267 秒；另放一张参考卡（第 1001 帧）、一张不闪白的照片（第 2000 帧）和一段视频 B-roll
  （第 3002 帧），起点都是会进位的帧边界。逐帧渲染各处起止前后共 22 帧：
  - 第 4538 帧 0.5.0 全黑（均值 0.0），本版是插入第 0 帧的压暗虚化底（70.1）；第 4598 帧反过来，是 0.5.0 多出的最后一帧照片。不闪白的照片
    在第 2000、2120 帧同样。闪白第 1、2 帧两版均值差 0.9、1.5（0.5.0 的局部帧号带着 0.99 的小数）。
  - 参考卡各帧两版均值差不超过 0.4（第 0 帧本来全透明，淡入只是提前了不到一帧）；B-roll 各帧两版逐像素相同。两版 `tsc --noEmit` 都通过。
- 24 / 25 / 30 / 50 / 60 fps 各取 2 万个帧边界起点、按三位小数取整：0.5.0 的写法在 24、30、60 fps 下各有三分之一晚一帧，本版全部落在原帧上；
  加了 `"delay": -0.001` 的起点在本版下也落在原帧上，用过这个绕法的工程改成新写法后不会提前。
- `glitch_scan.py` 重扫对话易七猫 v0.1 / v0.2、对话符尧 v0.2、对话王燚 v0.1：命中帧、分数与标签和 0.5.0 逐条相同；易七猫第 4538 帧、王燚
  第 2825 帧的 `on_screen` 多出 `img/group.jpg`。

### 已知缺口

- 字幕与讲解图形仍按秒比较，同样可能晚一帧出现、晚一帧消失；它们叠在画面上，不会露出底下的黑场，本版不改。
- 已装好的工程不会跟着更新：对话王燚已交付的 `platform-wechat-channels-v0.1.mp4` 仍带着第 2825 帧黑场。

## [0.5.0] - 2026-10-30

来自「对话易七猫」（2026-10-30，v0.1 审片版分 4 段 Remotion 渲染）。v0.1 混进两帧渲染坏帧：第 1593 帧（0:53.1）画面顶部一条花屏色块，
第 1881 帧（1:02.7）手掌 B-roll 错位成两块，各只有一帧；5 fps 分页联系表没抽到，拿重渲的 v0.2 逐帧比对才发现，v0.2 同一位置干净。
本版把该项目里的临时扫描（`work/tools/glitch_scan.py`）做成封装质检的正式一步。

### Added

- `scripts/glitch_scan.py`：单帧坏帧扫描。逐帧流式解码（只留前后 3 帧，不把全片读进内存），270×480 灰度（横版 480×270）分 6×8 块，
  某块「本帧与前后两帧都不同、前后两帧彼此相近」（块均值差 min(d1, d2) − 3·d0 > 20，`--ratio` / `--floor` 可调）记一次命中。每处命中输出
  帧号、时间码、峰值块与命中块的源像素框，写「前一帧 / 本帧 / 后一帧」三联图（上排整帧、下排放大峰值块及其邻块）到 `qc/glitch-<stem>/`，
  结果写 `qc/glitch-<stem>.json`。
- 已知的相似情形打标签、不放行：`--timeline` 读这一版的 `timeline.json`（帧数与视频对不上时不用），片尾标 `outro`（lov-logo-sting 在 bar 拍上的
  整帧闪白），带 `flash` 的照片插入前一帧到第 9 帧标 `insert-flash`，并写出命中落在哪一段、哪张插图；按画面标 `flat`（本帧那块没有纹理：闪白、
  黑帧）、`cut`（前后两帧之间整幅画面都换了：挨着剪切点，周围的变化不算运动）与 `motion`（镜头内周围在动、本帧不比前后锐，或本帧明显比前后糊：
  手快速挥动的运动模糊）。
- `scripts/finalize_platform.py`：在二维码扫描那一遍逐帧解码里同时跑坏帧扫描，结果写进 `finalize-<stem>.json` 的 `glitch_scan`，命中逐条打印；
  新增 `--timeline`；`--no-scan` 只跳过二维码，坏帧扫描照跑。
- 门禁与文档：SKILL.md 硬门禁 7 与 Step 9；`references/pipeline.md` 第 9–10 节（判据、标签读法、重渲坏帧所在那一段的做法）、表格第 10 与 13 行、
  第 13 节横版质检；`references/pitfalls.md` 四条（单帧坏帧漏过 5 fps 联系表；整帧平均漏掉顶部花屏；片尾闪白、照片快门闪白与挥手也会命中；
  照片插入起点取整晚一帧，片尾露出一帧黑场）；skill-card 的任务、风险与验收项；SKILL.md Validation 的 `--help` 循环加入 `glitch_scan`。

### 复现核验

- 本片两个渲染件（只读，产物写在临时目录）：`review-v0.1-video.mp4` 4742 帧、6 处命中：1593（顶行 5 块，无标签）、1881（21 块，无标签，
  落在 3e 与 `media/broll-palm.mp4`）、420 与 3324（`motion`）、4538（`flat cut outro insert-flash`，合影插入前一帧黑场）、4670（`flat outro`，
  sting 闪白）。v0.1 的时间线在项目里已被 v0.2 覆盖，按两版 EDL 与 package 的差异（片尾 6.8 秒、两张合影插图）重建后使用。
  `review-v0.2-video.mp4` 4682 帧、3 处命中：420、3324（`motion`）与 4610（`flat outro`，片尾第 72 帧），没有别的命中。扫一个渲染件约 10 秒。
- 参考脚本（整片读进内存、同一判据）在两版上命中的帧与分数和本版相同（阈值 20 以上 v0.1 六处、v0.2 三处）。整帧平均判据（不分块）对第
  1593 帧得 −19.3（d1 12.8、d2 14.0、d0 10.7），漏掉；分块后顶行块 56.6。
- `finalize_platform.py` 端到端：v0.1 渲染件加 v0.1 最终混音封装到临时目录，`--timeline` 用重建的 v0.1 时间线：158.07 秒、7.46 Mbps、
  bt709 回读正确，二维码 4742/4742 帧 0 命中（与本片当时的封装记录一致）；编码后的文件上坏帧扫描得到同样 6 处，分数相差不超过 0.6，结果写进
  `finalize-review-v0.1.json` 的 `glitch_scan`，`scripts/` 下没有留下 `__pycache__`。另截含第 1593 帧的 6.7 秒片段跑一遍，时间线帧数不符时打印 WARN、
  照常给出画面标签。
- 另外 7 部片子的 12 个渲染件（对话刘凯宁、王燚、赵哲两份、亢焜两版、符尧两版、Kanna、Ricky 三版）共 43 处命中，逐张看过三联图（两版同帧、
  分数差在 0.1 以内的只看其中一版），没有渲染坏帧：用了 sting 的 5 版片尾各一处 `flat outro`；照片插入两处 `flat cut outro insert-flash`（符尧 v0.2 第 6816 帧
  是快门闪白前的第 0 帧，王燚第 2825 帧是取整黑场）；剪切点前一帧两处 `cut`（亢焜 v0.2 第 2570 帧、王燚第 1124 帧）；其余 `motion` 是手、
  手臂或身体的快速动作；10 处无标签是符尧两版里同样的 5 处手指小幅往返。王燚已交付的 `platform-wechat-channels-v0.1.mp4` 同样带着
  第 2825 帧黑场，重新编码后各处分数相差不到 0.3。

### 已知缺口

- 只抓一帧的坏帧：连着两帧坏，两帧彼此相同，扫不出来，仍靠联系表与金丝雀。
- 起步工程的照片插入与参考卡按秒判断出现（`frame / fps >= start`），`decorate` 把时间写成三位小数，30 fps 下落在帧边界上的起点约三分之一会晚
  一帧；压在片尾上就是一帧黑场（对话易七猫 v0.1 第 4538 帧、对话王燚 v0.1 第 2825 帧）。本版只在扫描里标出，并在 pitfalls 写了绕法（起点加
  `"delay": -0.001`）；把 `PhotoInsert` / `RefCard` 改成像 `BrollInsert` 一样按 `Math.round(start × fps)` 取帧，待单独修。
- `motion`、`cut`、`flat` 的阈值来自 8 部片子 14 个渲染件的 52 处命中；手指小幅往返（对话符尧 5 处）仍不打标签，要人看图。

## [0.4.1] - 2026-10-30

来自「易七猫对话手工川」（2026-10-29，飞书会议说话人视图录像 1920×1080、37 分钟素材 → 3 分 42 秒视频号竖版 v0.1 审片版）。本片在项目里绕开了
两处脚本问题（按模型批量的试切脚本、改剪辑表文字），本版修进 Skill，并记下会议录像的画面做法。

### Fixed

- `scripts/probe_cuts.py`（`in` / `out`）与 `scripts/seam_check.py` 改为按模型批量转写：先切好全部窗口（`seam_check` 直接用 `audio/lines/` 里的逐句 WAV），
  每个模型只加载一次、转完全部窗口再换下一个，最后按原格式打印。原写法对每个窗口 / 每句依次调用 large-v3 与 turbo，mlx-whisper 只缓存最后加载的
  一个模型，每条都要把两个模型各重新加载一次（large-v3 约 3 GB）。命令行参数、stdout 格式、窗口、淡入淡出与提示词都不变；表格在两个模型都跑完后
  一起打印，进度写到 stderr。
- `scripts/subs_from_lines.py` 闪行合并：判断句末语气词前先去掉结尾的 `？！?!，,。.`。断行保留句末「？」，「对吧？」原来不算语气词、被并进下一行，
  写出「对吧？我觉得创业确实不是人创的」这类超过每行 13 字的字幕（画面里折成两行）。

### Added

- `references/pitfalls.md` 两条：两个模型逐条交替转写、每条都重载权重；「对吧？」带问号被并进下一行。
- 飞书 / 腾讯会议说话人视图录像的做法：`references/style-grammar.md` 第 6 节写规则（会议界面不进画面；采访者不出镜时，采访者在主画面的帧换成被访者
  小窗的放大虚焦画面；被访者坐得偏低时用顶部 3:4 画框叠同画面的虚化底，人名条与讲解图形放到头顶），`references/pipeline.md` 第 5 节写做法（「只有被访者」
  的中间源、EDL `target` 1080×1440、ffmpeg 预先虚化的 `media.backdrop`、本片对 `layout.ts` / `Film.tsx` 的改法），SKILL.md Step 5 加一行指向。
- `references/pipeline.md` 第 4 节：一轮的候选点写进同一条命令（每条命令都要把两个模型各加载一次）；第 6 节闪行规则同步。

### 复现核验

- 在临时目录跑 0.4.0 与本版脚本，输入相同（本片 `audio/source-48k.wav` 只读；逐句 WAV、剪辑表与字幕数据都是副本），外面包一层计数
  `mlx_whisper.transcribe.load_model`：`probe_cuts in` 5 个窗口加载 10 次、65.2 秒 → 2 次、22.1 秒；`out` 5 个窗口 10 次、60.8 秒 → 2 次、17.4 秒；
  `seam_check` 6 句 12 次、51.1 秒 → 2 次、21.0 秒。三者 stdout 与 `seam_check` 的 JSON 都和 0.4.0 逐字节相同（`seam_check` 末行只差 `--out` 路径）。
- 字幕：剪辑表副本里 6 段「对吧」前被删掉的逗号按本片 `qc/seam-v0.1.json` 恢复成绕开前的原文，两版都用本片当时的 `--nouns` 跑。0.4.0 有 6 处「对吧？」
  向后并（H2、4c「对吧？我觉得创业确实不是人创的」，3b 两处，最宽「对吧？我得有一套理论让我能够自洽」15 个字，1f、5e 各一处）；本版 6 处
  都并回上一行（「我说你别创业，对吧？」「沮丧时刻给打垮呀，对吧？」等），超过 13 字的字幕从 3 行变为 0 行；其余 30 段的字幕文字与时间
  和 0.4.0 相同，两版都是 148 条。

### 已知缺口

- 会议录像的中间源脚本与 3:4 画框版式仍在本片项目里（`work/tools/cam_source.py`、`work/remotion/src/layout.ts` / `Film.tsx`）：取色位置、缩略窗坐标
  与认出被访者小窗的办法随会议软件和布局而变，没有做成通用脚本；起步工程没有 `WIN` 画框与 `media.backdrop`。
- `probe_cuts.py` 仍要自己列候选点；本片 `probe_plan.py` 从粗剪计划按包络自动找候选点、一次试切全片的做法没有并进来（命令行接口保持不变）。

## [0.4.0] - 2026-10-28

来自「对话符尧」（2026-10-28，iPhone 1920×1080 横拍、画面里只有被访者坐在左边的露台采访，40 分钟素材 → 3 分 54 秒视频号竖版 v0.1 审片版）。
当时为免与 0.3.0 冲突，跟脸平移、参考卡长标题与算式高亮只做在该项目的 `work/tools/` 与 `work/remotion/src/`，本版并回 Skill。

### Added

- `scripts/crop_centers.py`：横拍素材裁竖版时给每段写固定取景 `crop`（采样帧上人脸中心的中位数）。选脸统一为「宽于 `--min-width`（默认画宽 0.11）的
  最大人脸」，不再按最左 / 最右；两人同框时 `--guest-side left|right` 只在那个人的半边里取（G 为被访者一侧，Q 为另一侧）；`crop_on: "none"` 去掉
  `crop`；重算的段丢掉旧 `crop_track`。此前横拍的两期（采访 Ricky、对话符尧）都在项目里另写取景脚本，Ricky 那份按最左 / 最右取脸。
- `scripts/reframe.py`：固定 `crop` 会切脸的段写 `crop_track: [[source_t, centre], ...]`，裁切框跟脸平移。逐 piece 每秒 4 帧解码、YuNet 取最大人脸，
  每个采样点求出能把脸留在框内的中心范围，前后双向「懒跟随」取平均、约 1 秒平滑、夹回可行走廊、RDP 简化；`--margin` 默认 0.07、`--score` 默认 0.5。
  段级 `"reframe": {"margin", "score", "why"}` 覆盖命令行参数，用来记录联系表里抓到的例外；结果确定，复跑得到同一条轨迹、片段缓存不失效。
- `build_timeline.py` 原生支持 `crop_track`：每个 piece 按自己那一段轨迹生成分段线性的裁切 x 表达式（裁切在变速之前，`t` 是源秒数），缓存键随之变化。
- `scripts/subs_en.py`：把 `work/subs-en.json`（每段一行英文对一行中文）对回 `subs.json` 的 `en` 字段，SRT 改为每条中英两行；行数对不上就退出并列出那几段。
- 起步工程（`assets/starter/src`）：字幕与提问卡显示 `en` 英文行（回答 38 px 描边、提问卡 32 px）；`inserts` 支持 `"video": true` / `"from"` 整屏视频 B-roll
  （Sequence 内播放、首尾 4 帧溶接、缓推）；算式条步骤 `"hl": true` 在没有「=」时高亮最后一步；参考卡名称加副名过长时上下排、名称不折行；
  片尾 `LogoCard` 处注明换成 lov-logo-sting `<LogoSting>` 的接法。0.3.0「已知缺口」里的双语字幕行与 `Insert.video` 就此补上。
- `references/style-grammar.md`：横拍裁竖的取景规则（固定取景 + 跟脸平移；被访者靠在画面最边上时提问段用 `crop_on: "none"` 横幅全景加虚化底，回答段仍框脸）；
  无「=」算式条用 `hl` 收尾；视频 B-roll 的写法；双语字幕改用 `subs_en.py`。
- `references/pitfalls.md` 四条：单人横拍固定裁切切脸；选脸按最大不按最左；侧身时 YuNet 框比头窄、边距 0.03 不够（3a、3b、3c、4d 四段在联系表里仍切到鼻尖，
  0.07 才留出朝向空间；Remotion 推近 1.07–1.14× 每侧再吃掉裁切宽的 3–6%）；被访者靠最边时提问段只框到半张脸。
- `references/pipeline.md` 第 5、6 节、`references/skill-composition.md`、SKILL.md Step 5/6 与 Validation 段同步新脚本与顺序。

### 复现核验

- 在临时目录用对话符尧 `work/edl-v0.1.json`（`src/` 只读链接）复跑：`reframe.py --margin 0.03 --score 0.7` 一条命令得到的 EDL 与本片 35 段逐段相同
  （20 段的段级 `reframe` 记录生效，其中 3a、3b、3c、4d 为 0.07 / 0.5）；`crop_centers.py` 复算的 35 个 `crop` 与本片相同；Skill 版 `build_timeline.py`
  生成的时间线、字幕、SRT 与 voice 清单和本片工具逐字节相同，57 个 piece 的缓存文件名与本片 `render/seg` 一致。
- 本片是先全片 0.03 / 0.7 跑一轮，再对联系表里贴边的四段改 0.07 / 0.5 重跑；按本版默认参数（0.07 / 0.5）不带覆盖重跑本片，另有 9 个原本固定取景的段会加上轨迹。

### 已知缺口

- 横版组件 `FilmWide.tsx` / `layout-wide.ts` 仍在采访 Ricky 项目里，未并进起步工程。
- 人名条与讲解图形的整体缩放（采访 Ricky 横拍双人时缩到约 0.8）仍按 pitfalls 在本片 `layout.ts` / `Film.tsx` 里改，起步工程没有缩放参数。
- lov-logo-sting 组件归它自己的 Skill 维护，起步工程不内置副本，按 Step 6 交接接入。

## [0.3.0] - 2026-10-28

来自「对话 Ricky」（2026-10-26/27，iPhone 17 Pro 横拍双人同框、67 分钟素材 → 3 分 42 秒视频号竖版，再派生 B 站 16:9 横版并发布）。

### Changed

- B 站横版不再默认先问：SKILL.md Step 11、`references/publish-handoff.md` 原写「作者要 B 站横版时先问」，改为看 lov-media-publisher Profile
  `records.auto_publish.bilibili`。`auto` 时视频号发完直接派生、质检、交发布方；没有记录、`confirm-final` 或作者当次说「做好先给我看」时先问。
  来源：作者 2026-10-27「以后不用询问我，只需把控第一个发布平台即可」。新建 B 站合集仍要作者同意。
- `references/skill-composition.md`：横版成片一条指向 pipeline 第 13 节。

### Added

- `references/pipeline.md` 第 13 节「横版派生（B 站 16:9）」与阶段表一行：独立 EDL 版本与数据目录、横版独立组件、双人全景与说话人中景交替、
  竖版静帧回归、音轨原样复制；B 站版式观测值（字幕下沿 96 px、两侧 240 px、中文 58 / 英文 32 px）、参考卡与插入素材的横版改法、质检清单、
  APFS 克隆交付与封面槽对应；中景推近时被访者前倾、脸贴画面边缘的问题和渲染前用 `faces.json` 查边距的做法。
- `references/publish-handoff.md`「B 站跟发」：从视频号已发布文案最小适配（钩子问句当标题与简介、话题转标签、无章节不加时间轴）、
  两个封面槽各用哪张、沿用首发时确认过的事项、同名合集不存在时不建、「开放浏览」后才记 `published`、横版报告不写「待你确认」。
- `build_timeline.py`：EDL 片段可选字段 `crop`（0–1，画面水平中心），对横拍双人镜头按目标比例整高裁切到说话人，放大超过 1.3 倍时
  加轻度锐化；不写 `crop` 时仍是「居中 + 模糊填充」。缓存键含滤镜，改 `crop` 只重渲对应片段。来源：采访 Ricky（2026-10-26，
  iPhone 17 Pro 横拍、旋转 180°、双人同框、67 分钟素材）。
- `build_timeline.py`：相邻片段的源区间重叠时打 WARN（问答交界各自吸附会把重叠部分播两遍，采访 Ricky v0.1 的「介绍一下」里「绍」重复）。
- `references/style-grammar.md`：被访者讲自己的产品时要有产品镜头（原片没有就用他发来的产品视频做 B-roll）；片尾默认用 lov-logo-sting 那一版
  （作者 2026-10-27 反馈）。`references/pitfalls.md` 加问答交界重叠一条。
- `references/style-grammar.md`：章节黑卡与进度条改为可选包装，章名要独立可读；写明去掉章节的 EDL 与配乐改法（作者 2026-10-27 判一条
  3 分 48 秒采访短片的章节卡没必要）。
- `references/style-grammar.md`：加中英双语字幕的版式与译文做法（作者 2026-10-27 要求）；起步工程的字幕组件尚未内置英文行，本片实现在
  `work/remotion/src/Film.tsx`。
- 起步工程：提问卡去掉「提问」标签，改为左侧发光竖条区分说话人；新增概念参考卡（`Insert.ref`：名称、副名、释义、署名、宽高比），
  `PhotoInsert` 遇到 `ref` 时渲染整屏参考卡。`references/style-grammar.md` 同步两条规则（作者 2026-10-27 反馈）。
- `references/pitfalls.md` 另加四条：横拍双人镜头默认只会居中加模糊填充（要写 `crop`）、横拍裁竖后胸口区图形与人名条压下巴、
  顿号隔开的两个数字让断行计数报 `IndexError`、系统代理是 SOCKS 时转写退出。

### 已知缺口

- 横版组件 `FilmWide.tsx` / `layout-wide.ts`、中英双语字幕行、整屏视频 B-roll 插入（`Insert.video`）还在源项目 `work/remotion/src/`，
  没有并进起步工程；下一个要横版或双语的采访片仍需从该项目移植。

## [0.2.2] - 2026-10-22

### Added

- 可选依赖 `lov-logo-sting`（品牌片尾 / Logo Sting）：frontmatter `dependencies:` 加一项（带 check 与安装命令，不写进 `depends_on`，
  不强制安装）；不装或作者不要时照常用起步工程的静态 `LogoCard` 收尾。
- SKILL.md Step 6 加片尾交接：做可发布版本定片尾时提一次（审片初版只在作者要求时做），交官方 Logo SVG、本片 fps 与收尾曲拍点网格，
  取回 `<LogoSting>` Sequence 替换 `LogoCard`；`sting.wav` 并进母带前的最终混音（`finalize_platform.py` 只封装这条混音），加入后整条母带
  连同编码成片重测，混音与真峰门禁仍归本 Skill（参考成片需 −2.5 dBTP、限制器 0.70）。`references/skill-composition.md` 加同一交接，
  Dependencies 段同步。

### Fixed

- `skill-card.md` 的 Skill Version 自 0.1.0 起未同步，本版对齐为 0.2.2。

## [0.2.1] - 2026-10-21

### Changed

- 顶层 `depends_on` 加入 `lov-media-creator`（天才剪辑师）：作者决定让混音与质检运行时随本 Skill 一并安装。0.2.0 的目录条目只带上
  `lov-branding-consistency`，新用户要另装 `lov-media-creator`。frontmatter `dependencies:` 的运行时检查保留。
- README 安装段、`references/skill-composition.md` 依赖写法、`pricing-card.yaml` 证据缺口同步；版本号同步为 0.2.1。

## [0.2.0] - 2026-10-21

首次发布：Lovstudio.AI 官网会员分发，源码仓库私有。0.1.0 未单独发布，内容并入本版。

### 发布

- 商业模式确定为包含在 Lovstudio.AI VIP Membership 全套权益中，不单独定价、不兑换 Credits（作者 2026-10-21 确认）；同步 `pricing-card.yaml`、
  `skill-card` 的定价与分发字段、README 安装段。
- `cases/cases.json`：首个案例提示词里的微信联系人名改为「某某」，案例页公开展示时不露出被访者的联系人备注。


来自「对话亢焜」（2026-10-20，iPhone 17 Pro 杜比视界竖拍、27 分钟素材 → 3 分 19 秒审片版）的两处可复用问题。

### Added

- `scripts/sdr_source.py`：检测视频流的 `DOVI configuration record`，有杜比视界时用 macOS `avconvert`（PresetHighestQuality）转出整条
  SDR bt709 源，核对帧数、起点、时长与源一致、色彩标记为 bt709，报告写 `<输出>.json`，打印 EDL `source.video`；`--check` 只检测。
- `subs_from_lines.py` 新参数：`--models`（默认 `large-v3,turbo`，也接受 Hugging Face 仓库名与本地模型目录）、`--max-rate`、`--snap`、
  `--flash`、`--flash-units`、`--report`（默认 `qc/subs-timing-vX.json`）；`--model` 保留为单模型写法。
- `probe_cuts.py`、`seam_check.py` 新增 `--models`；`transcribe.py` 的 `--model` 接受别名 `large-v3`、`turbo` 与本地目录。

### Changed

- 字幕取时并入本期临时脚本 `subs_merge.py` 的逻辑并去掉逐句硬编码：两模型逐句择优（先排除会让某行显示快于每秒 12 字的模型，再按
  全片对白 95 分位 − 16 dB 的语音起点比较行首），缺字的边缘行跨模型补位，每句首行从句首开始，行首吸附到片段起点，「OK」「对」「对吧」
  这类不到 0.5 秒的闪行并入邻行；首行规则与时间合法性不满足时不写出。复跑本期 EDL 得到与手修版相同的 119 行。
- `build_timeline.py`：源是杜比视界时打印 WARN，提示先跑 `sdr_source.py`；docstring 写明 ffmpeg 色调映射不读杜比视界元数据。
- SKILL.md：Step 0 写明 Whisper 模型别名与缓存被清理后的重建办法（curl 断点续传、SHA-256 校验、按 HF 缓存结构放置或链接本地权重）；
  Step 1 盘点检测杜比视界并默认转 SDR 源；Step 5、Step 6、依赖与校验命令同步。
- `references/pipeline.md` 第 1、2、5、6 阶段的产物、门禁与命令同步；`references/skill-composition.md` 素材交接写明 SDR 视频源。
- `references/pitfalls.md` 新增杜比视界偏色、单模型取字幕时间、起声阈值跟着录音电平、模型缓存与代理四条；「mobius 最接近 iPhone 原生观感」
  收窄为只在 ffmpeg 曲线之间成立，只用于无杜比视界的 HLG/PQ。
- `skill-card`、`pricing-card`：脚本数改为 14，补 avconvert 运行依赖与两条风险。

## [0.1.0] - 2026-10-19（未单独发布，并入 0.2.0）

### Added

- 采访短片片型 Skill（`lov-film` 套件成员）：从「对话刘凯宁」真实交付沉淀。范围只有一种：一场采访 → 一条约 4 分钟以内的视频号竖版短片。
- 片型语法（原话钩子、约 5 章重排、提问卡与回答字幕、人名条、讲解图形、跳切推近、封面 A/B 与 4:3 分享卡），并把 lov-media-creator
  narrative-vlog 访谈规则里适用于竖版短片的部分改写进来；横版深度访谈、访谈长片与访谈纪录片留在 narrative-vlog「访谈长片」。
- 流水线与门禁、上下文来源（微信聊天、自述、公众号、现场照片）、发布交接（一次确认收齐）、踩坑记录。
- 脚本：`build_timeline.py`、`transcribe.py`、`probe_cuts.py`、`seam_check.py`、`subs_from_lines.py`、`fx_pieces.py`、`decorate.py`、
  `check_timeline.py`、`music_plan.py`、`gen_bgm.py`、`bgm_check.py`、`finalize_platform.py`、`setup_starter.py`。
- Remotion 起步工程 `assets/starter`（竖版成片，3:4 / 4:3 / 16:9 封面）与模板 `assets/templates`。

### Changed（发布前审查后的修正，版本仍为 0.1.0）

- 路由：导演视角触发只限采访短片；Do-not 增加横版深度访谈 / 访谈长片 / 访谈纪录片 → lov-media-creator narrative-vlog「访谈长片」，
  多人实录按交付形态分流（剪映草稿、选题卡、无人值守批量 → `lov-roundtable-clip`；逐条精包装可发布 → lov-media-creator independent-clips）。
- 片型语法补回迁移时丢掉的规则：产物演示合格标准（含地图动画、按实景照片建模、材质光影细节、镜头跟原话走、60 fps 逐帧确定性录制再降到
  30 fps、方块楼层与平涂录屏不合格）、三维与动效两轮评审上限及南头古城观测、产物服务于人物且位置交作者批、片头与片尾尾声两头都不对。
- 流水线顺序：EDL 定稿后先 `setup_starter`，再 `build_timeline` → `fx_pieces --copy-to` → `subs_from_lines` → `decorate`（从
  `timeline.base.json` 起）→ `check_timeline --public --mezz`；Remotion 命令改用子 shell；最终混音转 `public/audio/mix-vX.m4a`；
  `music_plan --media-creator` 打印带绝对路径的门禁命令。
- 脚本与起步工程：`fx_pieces` 中间轨按 BT.709 编解码并写标记，`.fx.json` 记参数、参数变了重算，核对帧数后才落缓存；`check_timeline`
  新增 `--public`（引用文件齐全）、人名条 / 地点条与讲解图形撞时间的 WARN、`--mezz` 断言 bt709；`setup_starter` 无封面规格时写中性骨架与
  深色占位底图；`finalize_platform` 逐帧二维码扫描、5 fps 分页联系表加 3 秒总览、手机预览按片长定码率；ASR 脚本不再强制离线；
  起步工程在 `media.video` 为空时显示黑底，新增 4:3 / 16:9 封面合成。
- EDL 新增顶层 `nouns`（锚点与高亮词都写进去，字幕断行不拆）；删去从未生效的 `title_card_seconds`，片名卡时长 = title 段 piece 长度。
- 封面：视频号封面槽数以发布页现场读到为准；选定的 3:4 与同一视觉的 4:3 分享卡一起交，`cover_status` 覆盖两张。
- 依赖：frontmatter 检查按 `MEDIA_CREATOR_DIR` 查找 lov-media-creator；写明首次转写下载两个 Whisper 模型（约 3.1 GB + 1.6 GB）、
  YuNet 模型的 OpenCV model zoo 下载地址；Profile 示例改为本 Skill 的完整命令。
- 模板去身份化（示例嘉宾 / Guest / 某大学 / 示例账号 / 某创业园区 / interview.MOV），加 `_example_of` 说明来源。
- 案例与卡片：状态改为「已提交、平台审核中」（`publish_status=platform_pending`）；输出不再列事实台账（事实核对写在交付报告里）；
  证据路径标明属于源项目、不随 Skill 分发；记入已知局限：案例成片的中间轨按 BT.601 编码、未加标记，渲染端按 BT.709 解码，肤色轻微偏移，
  已在 `fx_pieces.py` 修复。
- 定价：去掉「与套件其他成员一致」的说法；商业模式（一次性购买或 VIP Membership）待作者决定，99 元一次性只作草案，置信度低。
- 运行环境：`build_timeline` 找不到 jieba 时直接退出（原来静默按字数断行，`nouns` 失效）；流水线命令统一用虚拟环境的 `$PY`；
  `subs_from_lines` 加载 build_timeline 时不再在 Skill 目录写 `__pycache__`。
- 第二个真实案例（Kanna 本地草稿）中的修正：`fx_pieces` 皮肤遮罩改为按每张脸自身色度自适应（彩色灯光下原固定范围只盖住 5–18% 的脸），
  `.fx.json` 记 `skin` 算法版本；`finalize_platform` 总览页标签取整修正（原来偏早约 1.5 秒）。
- 踩坑记录新增：中间轨色彩矩阵错配、短句幻听时字幕回退临时时间、分词拆锚点、换了 Python 就换了断行、美颜缓存不看参数、起步工程装得太晚、
  联系表只覆盖前 3 分钟。
