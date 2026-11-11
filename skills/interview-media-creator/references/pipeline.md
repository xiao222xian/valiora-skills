# 流水线：产物与门禁

每一阶段都有一个可回读的产物；没有产物或门禁未过，不进入下一阶段。`$IMC` 指本 Skill 目录，`$MC` 指 lov-media-creator 目录
（`$MEDIA_CREATOR_DIR`，缺省 `~/.agents/skills/lov-media-creator`；`music_plan.py --media-creator` 也接受它），`$PY` 指持久虚拟环境的
Python（装好 numpy、opencv-python、mlx-whisper、opencc、jieba；系统 `python3` 往往缺 jieba，字幕断行会出错，`build_timeline` 会直接退出）。工程目录约定：素材留在项目根，
过程文件在 `work/`，交付在 `deliverables/`；所有脚本按 EDL 所在目录解析相对路径（EDL 放在 `work/`）。下文命令都从项目根运行；
要进 `work/remotion` 的命令写成子 shell `( cd … && … )`，跑完仍在项目根。

| 阶段 | 产物 | 门禁 |
| --- | --- | --- |
| 1 盘点 | `work/source-probe.json`；有杜比视界时 `work/src/<名>-sdr709.mov` 与同名 `.json` 核对记录；照片清单；`work/context/`（聊天记录、被访者自述、公众号文章摘录）；`work/facts.md` 事实台账 | 每个设备、每类素材（连子文件夹）都列出来；旋转元数据、HDR 曲线与杜比视界已读；SDR 源帧数、起点、时长、bt709 核对通过；台账每条有出处 |
| 2 转写 | `audio/source-48k.wav`、`audio/source-16k.wav`；两份逐字稿（large-v3 与 turbo）；`audio/words.json`；待确认专名清单 | 两个模型都跑完；分歧专名列出，不猜 |
| 3 阐述与剪辑表 | `work/director-statement.md`；`work/edl-vX.json`（`nouns`、冷开场、片名、5 章、收尾） | 钩子全是被访者原话；每章有命名依据；拒答与不方便公开的内容已删；时长 2–4 分钟 |
| 4 切点核验 | 每个句首句尾的试切记录；EDL 片段带 `a`/`b` 固定标记；`qc/seam-vX.json` | 逐句回转写没有残词或吃字（同音误识除外）；相邻同源句共用切点 |
| 5 画面 | `remotion/`（起步工程，`public/{data,media,audio,img,fonts}`）；`render/seg/*.mp4`（逐片段 SDR）、`*.fx.mp4`、`*.fx.json` 与 `*.faces.json`；`render/mezz-vX.mp4` 及其在 `remotion/public/media/` 的克隆；`remotion/public/data/timeline.base.json` | `fx_pieces` 核对中间轨帧数 = 时间线帧数（不符退出 1）；中间轨 bt709；美颜前后对比已给作者 |
| 6 字幕与包装 | `remotion/public/data/{timeline,subs}.json`（`subs_from_lines.py` + `decorate.py`）；`qc/subs-timing-vX.json`；`work/package.json` | 字幕断行不拆词；每句首行从句首开始；保留临时时间的行与短于 0.6 秒的字幕听过；重点词约三分之一；讲解图形不压脸；`check_timeline.py --public --mezz` 通过 |
| 7 配乐与混音 | 候选与 `ledger/costs.jsonl`；`music/tracks.json`；`music/cues-vX.json`、`film-vX.json`；`audio/voice-proc-vX.json`；`audio/mix-vX/final-mix.wav` 与 stems；`remotion/public/audio/mix-vX.m4a` | 候选做过人声分离检查；`validate_cues` 0 ERROR；`smr_check` 全过；母带 −16 LUFS-I / ≤ −3 dBTP；`intelligibility` 差值 ≤ 0.02；音乐 stem 无 2 秒以上断档 |
| 8 Studio 与金丝雀 | Studio 主预览；关键帧金丝雀（冷开场、片名、每种卡、每个讲解图形、照片、Logo） | 无控制台错误；Studio 只挂一个音频；`src` 快照对比无 Studio 写回 |
| 9 渲染与封装 | `render/review-vX-video.mp4`（分段渲染）；`deliverables/review-vX.mp4` 与手机预览 | 完整解码；≤ 10 Mbps；bt709 标记回读正确；`audio_qc` 通过（编码后 TP < −1）；手机预览 < 30 MB |
| 10 质检 | `qc/contact-<stem>-NN.jpg`（5 fps，每页 48 格）与 3 秒一格的总览页；逐帧二维码扫描；单帧坏帧扫描与每处命中的三联图 `qc/glitch-<stem>/f<帧号>.jpg`；`qc/finalize-*.json` | 联系表每页都看过；二维码命中逐条人工判；坏帧命中逐张看三联图，渲染坏帧重渲那一段再扫，直到只剩在图上核实过的已知模式（片尾闪白、照片快门闪白、运动模糊）；手机屏、聊天截图上的个人信息已处理 |
| 11 封面 | `deliverables/cover_3x4-{a,b}-vX.png`；选定后同一视觉的 `cover_4x3-<v>-vX.png`；要 B 站时 `cover_16x9-<v>-vX.png` | 270×360 可读；4:3 同样可读；系列条与官方 Logo 在安全区；眼睛与主体不被遮 |
| 12 交付与发布交接 | `deliverables/delivery-report-vX.md`；`publish-copy-vX.md`；批准后 `subs-approved-vX.srt`、`platform-wechat-channels-vX.mp4` | 状态字段按 lov-media-creator delivery-contract；`subtitle_status=approved` 必须有作者对 SRT SHA-256 的确认；`cover_status` 覆盖 3:4 与 4:3 |
| 13 横版派生（B 站，可选） | `work/edl-vX-h.json`；`remotion/public/data-h/`；`deliverables/review-bilibili-vX.mp4` 与手机预览、`platform-bilibili-vX.mp4`、`cover_16x9-<v>-vX.png`、`publish-copy-bilibili-vX.md`、`delivery-report-bilibili-vX.md` | 两版 `timeline.base.json` 逐项相同；竖版静帧逐像素零差异；音轨 md5 与已发布竖版相同；完整解码、逐帧二维码、单帧坏帧扫描、联系表全看；`check_video.py --platform bilibili --expected-orientation horizontal` 通过 |

## 1 盘点

```bash
find . -maxdepth 2 -not -path './work*' -not -path './deliverables*' | sort   # 素材清单：连子文件夹一起列
$PY $MC/scripts/media_probe.py --input SOURCE.MOV --output work/source-probe.json --pretty
$PY $IMC/scripts/sdr_source.py SOURCE.MOV          # 有杜比视界才转换：work/src/SOURCE-sdr709.mov，打印 EDL source.video
ffmpeg -i SOURCE.MOV -map 0:a:0 -ac 1 -ar 48000 -c:a pcm_s16le work/audio/source-48k.wav
ffmpeg -i SOURCE.MOV -map 0:a:0 -ac 1 -ar 16000 -c:a pcm_s16le work/audio/source-16k.wav
```

- 素材清单连子文件夹一起列：作者后加的照片常放在子文件夹里，只列根目录的文件会漏掉（对话易七猫的 `生活照/`，见 pitfalls「盘点」）。
  作者说「加了照片」时先找第一次盘点之后新增的目录：`find . -maxdepth 2 -newer work/source-probe.json -not -path './work*' -not -path './deliverables*'`，
  不要把根目录里早就在的图当成新照片。
- 多段素材（同一场采访分几段拍）先按拍摄时间排序，确认没有重叠；需要时用 ffmpeg concat 成一条源再转写，记下每段在拼接源里的起点。
- 上下文来源见 [context-sources.md](context-sources.md)。HEIC 照片用 `sips -s format jpeg` 转出预览，再看图。
- 杜比视界（iPhone HDR 录像，profile 8.4）：ffmpeg 的 zscale + tonemap 不读杜比视界元数据，整片过亮偏品红。`sdr_source.py` 默认用
  `avconvert -p PresetHighestQuality` 转出整条 SDR bt709 源（27 分钟约 2.2 GB，后台跑），核对帧数、起点、时长与源一致、色彩标记是 bt709，
  报告写在 `<输出>.json`；EDL `source.video` 指向它，`source.audio` 仍是从原片提取的 WAV。只有 `--check` 时只检测不转换。
- 联系表：每 15 秒一帧；有 SDR 源就从 SDR 源取帧，否则 HDR 先色调映射；快速知道哪里是近景、哪里是演示、哪里在找手机。

## 2 转写

```bash
$PY $IMC/scripts/transcribe.py work/audio/source-16k.wav --out work/audio/asr-large-v3.json \
  --words work/audio/words.json --nouns "被访者名,英文名,地点,产品词" --print
$PY $IMC/scripts/transcribe.py work/audio/source-16k.wav --out work/audio/asr-turbo.json \
  --model mlx-community/whisper-large-v3-turbo --nouns "..."
```

- 用作者机器上装好 mlx-whisper、numpy、opencv-python、opencc、jieba 的持久虚拟环境（`$PY`）运行，不要 `uv run --with` 的临时环境。
- 第一次运行会从 Hugging Face 下载模型（large-v3 约 3.1 GB、turbo 约 1.6 GB）；先告诉作者体积，两个都缓存后可以 `export HF_HUB_OFFLINE=1`。
  `--model` / `--models` 也接受别名（`large-v3`、`turbo`）与本地模型目录；缓存被清理、Python 下载器经代理卡住时，按 SKILL.md Step 0 用 curl 断点续传重建。
- 两个模型听不一致的专名（「茉莉营 / 魔力营」→ 查证为「模力营」；「关注穿着 / 关注川哥」）进待确认清单；地名和机构名用公开资料核实。
- 转写提示词只放风格句与专名，不放预期内容（静音窗口会把提示词当成「说的话」返回）。

## 3 阐述与剪辑表

- 先写 `work/director-statement.md`（模板 `assets/templates/director-statement.md`），再写 EDL（模板 `assets/templates/edl.example.json`）。
  EDL 片段的 `text` 是校正后的实际所说，片段 `pieces` 是源时间 `[入点, 出点(, "a"|"b"|"ab")]`。
- 去掉口水词时，一个片段可以有多个 piece；单个 piece 至少 1 帧。
- EDL 顶层 `nouns` 是字幕断行用的词表：人名、专名，加上 `package.json` 里每个 `anchor` 与 `highlights.keys`（例：「负一到零」不写进去，
  jieba 会切成「负一到 / 零」，锚点找不到、高亮也不亮）。`build_timeline.py` 与 `subs_from_lines.py` 会把 EDL `nouns`、每个章名和命令行
  `--nouns` 一起加进 jieba 词典。EDL `nouns` 只管断行；转写类脚本（`transcribe`、`seam_check`、`subs_from_lines`）的 `--nouns` 还会进
  Whisper 提示词，那里只放真实人名、地名这类专名，不放锚点短语。
- 片名卡时长 = title 段 piece 的长度；要改就改 piece，没有单独的时长字段。
- 模板来自真实案例、身份信息已替换（见各模板的 `_example_of`），只用来看结构，新片全部重写。

## 4 切点核验

```bash
$PY $IMC/scripts/probe_cuts.py work/audio/source-48k.wav intervals 476.0:478.8
$PY $IMC/scripts/probe_cuts.py work/audio/source-16k.wav in '[["5a",[477.8,478.1,478.33],2.2]]'
$PY $IMC/scripts/probe_cuts.py work/audio/source-16k.wav out '[["6d",543.3,[545.48,545.8]]]'
$PY $IMC/scripts/build_timeline.py work/edl-v0.1.json --audio
$PY $IMC/scripts/seam_check.py work/edl-v0.1.json --nouns "被访者名,英文名,地点"
```

- 先给每个句首、句尾跑 `intervals`，在有声区间的前后找候选点，再用 `in` / `out` 试切；选定后在 EDL 里标 `a` / `b` 固定。
- `in` / `out` 先切好全部窗口，每个模型只加载一次、批量转写，两个模型都跑完才打印表格（进度在 stderr）；所以一轮的候选点都写进同一条命令的
  JSON 列表，不要一句一条命令，每条命令都要把两个模型各加载一次。`seam_check` 也是按模型批量转写。
- `seam_check` 的读法写在脚本说明里：两个模型都多听到或都少听到的才是剪口问题。
- 包络缓存写在 `work/audio/<音频名>.env10ms.npy`；音频是指向素材目录的软链接时，也不会写进素材目录。

## 5 画面

切点定稿后先装起步工程，再出画面。顺序固定：`setup_starter` →（横拍素材：`crop_centers` → `reframe`）→ `build_timeline` → `fx_pieces --copy-to`
→ `subs_from_lines` →（双语：`subs_en`）→ `decorate` → `check_timeline`。

```bash
$PY $IMC/scripts/setup_starter.py work/remotion --sans-font FONT.ttf --title-font FONT.ttf --logo LOGO_WHITE.png \
  --series "系列名" [--cover-spec work/cover.json] [--node-modules PATH]
$PY $IMC/scripts/crop_centers.py work/edl-v0.1.json --write   # 横拍：每段固定取景（最大人脸）；两人同框加 --guest-side left|right
$PY $IMC/scripts/reframe.py work/edl-v0.1.json --write        # 横拍：固定框会切脸的片段写 crop_track（跟脸平移）
$PY $IMC/scripts/build_timeline.py work/edl-v0.1.json --video --audio
$PY $IMC/scripts/fx_pieces.py work/edl-v0.1.json -j 4 --copy-to work/remotion/public/media   # 美颜 + 人脸 + 拼中间轨 + 克隆
$PY $IMC/scripts/fx_pieces.py --photo IN.jpg OUT.jpg --strength 0.6                          # 照片、封面底图
# 被访者要求更明显的美颜：两条命令都加 --level strong（强度默认 1.0），成片、封面与照片同一档
```

- `setup_starter` 建好 `public/{data,media,audio,img,fonts}`，写占位 timeline / subs；不给 `--cover-spec` 时写中性封面骨架
  （系列名取 `--series`，A/B 两版只有「主标题第一行」「重音词」占位）和一张 1080×1920 深色占位底图 `public/img/cover-base.jpg`，
  所以数据就绪前打开 Studio 不会 404。`media.video` 为空时成片显示黑底占位。已存在 `src/` 时它拒绝覆盖。
- 横拍素材（比竖版宽）：`crop_centers` 按每段 `crop_on`（否则说话人）取画面里最大人脸的中位水平中心写 `crop`；`crop_on: "none"` 的段去掉 `crop`，
  横幅全景居中放在虚化底上（被访者靠在画面最边上时的提问段）。`reframe` 逐 piece 每秒 4 帧找脸，固定框留不出 `--margin`（默认画宽 0.07）的段
  写 `crop_track`，其余不动；某段要不同参数时写该段 `reframe` 字段（见脚本说明），本片的命令行参数记进交付报告。渲完看 5 fps 联系表，
  贴边的段调参数或改全景；不改的片段缓存不失效。
- 会议录像（飞书 / 腾讯会议的说话人视图，谁说话主画面给谁）：先做一条「只有被访者」的中间源，EDL `source.video` 指向它。逐帧判断主画面是谁，
  看画面里位置固定、两人颜色不同的一块（易七猫对话手工川取主画面左缘一条：采访者那边偏白，被访者身后是红墙；主画面是被访者的帧占 70.6%）；
  采访者在主画面的帧换成被访者自己小窗放大后的虚焦版，切换前后各约 6 帧渐变，采访者说话期间短于约 2 秒的切回也保持虚焦；会议录像不带色彩标记，
  解码、编码都显式按 BT.709。会议切主画面比说话晚约 2 秒，几句回答的开头因此仍是虚焦（本片 5 处、0.6–2 秒），交付报告里列出时间码。
  被访者坐得偏低时 EDL `target` 写 1080×1440，中间轨就是顶部的 3:4 画框；虚化底用 ffmpeg 从中间轨预先做好
  （`scale=1440:1920,crop=1080:1920,gblur=sigma=42,eq=brightness=-0.14:saturation=0.85`，按 bt709 编码），写进 `package.json` 的 `media.backdrop`
  （`decorate` 原样带进时间线），不在 Remotion 里逐帧 CSS 模糊。起步工程没有画框和虚化底，本片改的是 `layout.ts`（`WIN` 画框与下沿 240 px 渐隐，
  字幕中心 y≈1480，人名条与讲解图形挪到头顶的墙上）和 `Film.tsx` 的画面层（虚化底 + 带渐隐遮罩的画框，提问段约 8 帧内虚到 12 px、压暗 32%）。
  取色位置、缩略窗坐标和认出被访者小窗的办法随会议软件与布局而变；本片的 `work/tools/cam_source.py`、`work/remotion/src/layout.ts` 与 `Film.tsx`
  （属源项目，不随 Skill 分发）只作参考，换一场录像要重新量。
- `build_timeline` 同时写 `timeline.json` 和未装饰的 `timeline.base.json`；改 EDL 后只渲新片段（缓存键含源区间、速度与滤镜，`crop_track` 也在滤镜里）。
  源是 SDR 时只缩放；无杜比视界的 HLG/PQ 用 mobius 色调映射；`source.video` 仍指向杜比视界原片时打印 WARN，先跑 `sdr_source.py`。
- `fx_pieces` 的中间轨按 BT.709 编码并写 bt709 标记（解码端也显式按 BT.709）；`<片段>.fx.json` 记下档位、strength、是否美颜与模型，参数变了自动重算；
  编解码返回码或帧数不对时不写缓存。强档在半分辨率上做双边滤波再放大回去（全分辨率的滤波核太大，见脚本说明的速度陷阱），最后整帧 gamma 0.91 提亮；
  它比全分辨率的自然档还快。`--copy-to` 用 APFS 克隆（`cp -c`，失败退回普通复制）把中间轨放进 `remotion/public/media/`，不用软链接。
  有 `remotion/public/data/timeline.json` 时它比对中间轨与时间线帧数，不符退出 1。

## 6 字幕与包装

```bash
$PY $IMC/scripts/subs_from_lines.py work/edl-v0.1.json --nouns "被访者名,英文名,地点"
$PY $IMC/scripts/subs_en.py work/edl-v0.1.json      # 双语时：work/subs-en.json 按行对回 subs.json，SRT 每条两行
$PY $IMC/scripts/decorate.py work/edl-v0.1.json work/package.json
$PY $IMC/scripts/check_timeline.py work/remotion/public/data --public work/remotion/public \
  --mezz work/remotion/public/media/mezz-v0.1.mp4
```

- `subs_from_lines` 用剪好的每句对白重新取字幕时间，默认 `--models large-v3,turbo` 两个模型各转一遍（一个模型跑完再换下一个，各加载一次）：
  - 逐句择优：先排除会让某行显示快于 `--max-rate`（默认每秒 12 字）的模型，再按语音起点（全片对白 95 分位电平 − 16 dB，静音 ≥ 80 ms 后起声）
    比各模型行首的平均距离，近 0.02 秒以上才换掉第一个模型；
  - 选中模型缺字的边缘行用另一模型补，都缺才用 `build_timeline` 的临时时间；
  - 行首在 `--snap`（默认 0.5 秒）内的片段起点吸附过去（片段起点是试切过的字头）；
  - 每句首行从句首开始（入点已试切到第一个字）；不超过 `--flash-units`（默认 2）个字、对齐后显示不到 `--flash`（默认 0.5 秒）的
    闪行并入邻行：句末语气词（吧、吗、呢、啊；结尾的问号、叹号、逗号、句号不算，「对吧？」也是）或最后一行并入上一行，其余并入下一行；
  - 两个模型匹配率都低于 `--min-ratio` 的句子整句保留临时时间，打印 WARN；结尾列出留在临时时间的行与短于 0.6 秒的字幕，逐条听。
  - 每句的匹配率、选中模型、补位、吸附与合并写在 `qc/subs-timing-vX.json`。
- `decorate` 每次都从 `timeline.base.json` 开始，所以只改包装时只重跑 `decorate`，从 package 删掉的人名条、地点条、插图也会消失；改了 EDL 就从
  `build_timeline` 重跑。
- 包装规格见 `assets/templates/package.example.json`：所有出现时间都锚到原话（字幕里的一段文字），不写时间码；每个锚点与高亮词都要在 EDL `nouns` 里。
  模板之外起步工程还认：算式条步骤的 `"hl": true`（没有「=」时高亮最后一步）；`inserts` 的 `"video": true` 与 `"from"`（整屏视频 B-roll，
  `img` 指向 `public/media/` 里 1080×1920 的片段）；`inserts` 的 `"album"`（生活照相册，见下一条）；参考卡名称加副名过长时自动上下排。
- 相册（style-grammar 第 6 节）：`"album": [{"img": "img/life-1.jpg", "ar": 0.75, "focus": [0.5, 0.42]}, …]`，照片按顺序均分插入时长、一张张落下；
  `ar` 是宽 / 高（决定卡片大小，缺了 `check_timeline` 报错），`focus` 是缓推中心（缺省 [0.5, 0.4]），顶层 `img` 不用写（`decorate` 取第一张）。
  起点锚到被访者报身份的那句，终点放在自我介绍结束（易七猫 v0.3：`{"anchor": "AI硬件", "segment": "1a"}` 到 `{"segment_end": "1b"}`）。
  照片转成 JPEG 放进 `public/img/`（v0.3 用 1080×1440 与 960×1440），HEIC 先 `sips -s format jpeg`；被访者自己修过的照片不再过 `fx_pieces --photo`。
  人名条、地点条的 `seconds` 收到相册开始之前：两者也从自我介绍开始，默认 4.6 秒常会压进相册（v0.3 收到 2.34 秒）。
- `subs_en` 要在 `subs_from_lines` 之后跑（后者重写 `subs.json`、不带英文）；`decorate` 保留 `en`。改了断行就先改 `work/subs-en.json` 再跑，
  行数对不上它直接退出并列出那几段。
- `check_timeline`：`--public` 核对 `media.video`、`media.audio`、每张插图（含相册每一张）与 `cover.json` 的底图都在，相册照片缺 `ar` 报错；
  `--mezz` 核对帧数与 `color_space=bt709`；人名条与数字 / 印章 / 箭头讲解图形同时出现、地点条与算式条同时出现、人名条或地点条与相册同时出现时
  给 WARN，按 style-grammar 挪开。

## 7 配乐与混音

```bash
$PY $IMC/scripts/gen_bgm.py --name a --out work/music/gen/a --ledger work/ledger/costs.jsonl --prompt "..."
$PY $IMC/scripts/bgm_check.py candidates work/music/gen/a.mp3 work/music/gen/b.mp3 --lib work/music/lib
$PY $MC/scripts/bgm_tracks.py --track A=work/music/lib/gen-a.wav --instrumental A --output work/music/tracks.json --summary work/music/tracks.md
$PY $IMC/scripts/music_plan.py work/edl-v0.1.json work/music.json --media-creator "$MC"
# 照它打印的命令依次跑 validate_cues → smr_check → score_mix --stems → intelligibility（每行以 cd work && 开头，脚本路径已展开）
$PY $IMC/scripts/bgm_check.py stem work/audio/mix-v0.1/stem-music.wav
ffmpeg -i work/audio/mix-v0.1/final-mix.wav -c:a aac -b:a 256k work/remotion/public/audio/mix-v0.1.m4a
```

- 付费生成前向作者说明单价（Lyria 3 Pro 观测约 $0.08/首），每次调用记账本；候选做完人声检查再进曲库。
- `smr_check` 有句子不过时，优先给那句所在的曲子段加 `dips`，或把它前后的段一起压浅；不要整条曲子调低。
- 混音规则、门禁阈值与运行环境以 lov-media-creator `references/audio-mix.md` 为准；本 Skill 只按「叙事片多曲配乐」那一套流程调用它的脚本。
- `mix-vX.m4a` 只供 Studio 预览与包装数据引用；成片封装用 `final-mix.wav`。

## 8 Studio 与金丝雀

```bash
(cd work/remotion && npx remotion studio src/index.ts --no-open --port 3230)
(cd work/remotion && node render-stills.mjs InterviewVertical ../qc/canary-v0.1 20,272,343,...)
```

- 开 Studio 前给 `src` 存一份 shasum 快照；会话后对比，Studio 拖动或缩放会把 `from=` / `scale` 写回源码。
- 重建数据期间 Studio 热更新可能读到半成品 JSON 报错，数据写完后刷新页面再判断。

## 9–10 渲染、封装与质检

```bash
(cd work/remotion && zsh render-chunks.sh InterviewVertical ../render/review-v0.1-video.mp4 <lastFrame> 4)
$PY $IMC/scripts/finalize_platform.py --video work/render/review-v0.1-video.mp4 --audio work/audio/mix-v0.1/final-mix.wav \
  --out deliverables/review-v0.1.mp4 --title "片名" --artist "出品方" --qc-dir work/qc --phone \
  --timeline work/remotion/public/data/timeline.json
$PY $MC/scripts/audio_qc.py --input deliverables/review-v0.1.mp4 --output work/qc/audio-qc-v0.1.json --pretty
$PY $IMC/scripts/glitch_scan.py work/render/review-v0.1-video.mp4 --qc-dir work/qc \
  --timeline work/remotion/public/data/timeline.json   # 单独扫一个文件：重渲后的渲染件、横版、B-roll 素材
```

- `<lastFrame>` = `timeline.json` 的 `frames` − 1。开渲前看磁盘：至少预留成片体积的 3 倍；渲染期间挂一个监视（剩余低于约 8 GB 报警）。
- 二维码检测器逐帧跑；联系表按 `--contact-fps`（默认 5）分页写 `qc/contact-<stem>-NN.jpg`，每页 48 格，另有每 3 秒一格的总览页。
  每一页都看完才算「联系表全片看过」；报告里写页数与扫描帧数。
- 单帧坏帧扫描与二维码共用同一遍逐帧解码（`--no-scan` 只跳过二维码）：270×480 灰度分 6×8 块，某一块里「本帧与前后两帧都不同、
  前后两帧彼此相近」就记一次命中（块均值差 min(d1, d2) − 3·d0 > 20）。每处命中打印帧号、时间码、峰值块（行列从左上角数，从 0 开始）、
  命中块数与源像素框，写三联图 `qc/glitch-<stem>/f<帧号>.jpg`：上排前一帧 / 本帧 / 后一帧（红框是命中块，黄框是峰值块），
  下排放大峰值块及相邻块；结果在 `finalize-<stem>.json` 的 `glitch_scan`，报告里写命中数与每处的判断。它只抓一帧的坏帧：
  连着两帧坏，两帧彼此相同，扫不出来，仍靠联系表与金丝雀。
- `--timeline` 给这一版的 `timeline.json`：命中标出落在哪一段、哪张插图（相册里是当时最上面那张，如 `img/life-3.jpg (album 3/5)`），
  片尾与带 `flash` 的照片插入打标签；帧数与成片对不上（另一版的时间线）时不用，打印 WARN。标签只是提示，不自动放行，每处命中都看三联图：
  - 无标签：先看。对话易七猫 v0.1 的两处渲染坏帧（顶部花屏、B-roll 错位）都没有标签：周围几乎不动（`around` 1.2、18），
    本帧多出硬边（`edges` 1.7、2.5）。手指小幅往返也会无标签命中（对话符尧 5 处：单块、分数 20–26、`edges` 约 1），
    图上是画面里本来的动作就放行。
  - `outro`：片尾。lov-logo-sting 在 bar 拍上整帧闪白一帧（参考节拍在 sting 第 72 帧；sting 占片尾最后 `timing.dur` 帧，
    参考 144 帧时就是距片尾 72 帧），图上本帧应是完整的 Logo 闪白；起步工程的静态 `LogoCard` 不闪，片尾有命中要查。
  - `insert-flash`：带 `"flash": true` 的照片插入前一帧到第 9 帧。快门闪白从插入第 0 帧（只有压暗的虚化底）升到第 2 帧（九成白），
    第 0 帧比前后都暗，常会命中（对话符尧 v0.2 第 6816 帧）。第 0 帧是一整帧黑场、不是压暗的虚化底时，是 0.5.1 之前的起步工程
    把起点晚了一帧，见 pitfalls「画面与包装」。
  - `flat`：本帧那块几乎没有纹理（闪白、黑帧、虚化底）。不在片尾、也不在闪白插入里的 `flat` 就是一帧黑场或闪帧，按坏帧处理。
  - `cut`：前后两帧之间整幅画面都换了（`change` ≥ 30），本帧挨着剪切点或甩镜，`around` 不再说明局部在动，所以不给 `motion`
    （对话亢焜 v0.2 第 2570 帧：切到产品镜头前最后一帧，手臂在动）。图上看本帧属于前一个还是后一个镜头、有没有花屏。
  - `motion`：手或物体在动，多半带运动模糊。图上要看到那只手或那个物体处在前后两帧之间的中途位置，才放行。
- 真坏帧重渲它所在的那一段：`render-chunks.sh` 每段 ⌈总帧数 ÷ 段数⌉ 帧，坏帧在第 ⌊帧号 ÷ 每段帧数⌋ 段（从 0 数；对话易七猫 v0.1
  4742 帧分 4 段、每段 1186 帧，1593、1881 都在 part1）。把 `render/review-vX-video-chunks/partN.mp4` 移到别处，重跑同一条渲染命令，
  它只重渲缺的那段并重新拼接；再 finalize，命中只剩核实过的已知模式才算过。命中落在视频 B-roll 里时先单独扫那段素材，素材干净才是渲染问题。
- 手机预览的码率按片长反算，目标 28 MB 以内（远程传文件上限 30 MB），超过 30 MB 会报 WARN。

## 11 封面

```bash
(cd work/remotion && for v in a b; do node render-stills.mjs InterviewCover34-$v ../qc/cover 0; done)
(cd work/remotion && node render-stills.mjs InterviewCover43-a ../qc/cover 0)     # 作者选定 a 之后：4:3 分享卡
(cd work/remotion && node render-stills.mjs InterviewCover169-a ../qc/cover 0)    # 只在要 B 站等 16:9 时
```

- 封面规格写在 `work/remotion/public/data/cover.json`（结构见 `assets/templates/cover.example.json`）；底图先用
  `fx_pieces.py --photo FRAME.jpg work/remotion/public/img/cover-base.jpg` 美颜，`base.top` 决定从哪里开始裁 3:4。
- 4:3（1440×1080）与 16:9（1920×1080）用同一份 `cover.json`：有 `"wide": {"img": "img/cover-wide-base.jpg"}` 就用这张横向底图，
  没有就复用 `base.img`，按 cover 铺满、焦点偏右。
- 视频号封面槽数以发布页现场读到为准（观测：一个 3:4 槽，有时 3:4 + 4:3 两个槽），所以选定的 3:4 与 4:3 一起交。

## 12 交付与发布交接

- 交付报告按 lov-media-creator `references/delivery-contract.md` 的状态字段与「Report minimum」写；本片型另加：冷开场三句的原话与源时间、
  每章命名依据、讲解图形清单、事实核对（每条上屏事实的出处）、待确认事实、AI 生成内容清单（配乐）与费用账本汇总。
- 发布交接见 [publish-handoff.md](publish-handoff.md)。B 站 16:9 横版见下一节。

## 13 横版派生（B 站 16:9）

什么时候做：lov-media-publisher Profile 的 `records.auto_publish.bilibili` 为 `auto` 时，视频号发完就直接派生、质检，交给发布方，不再问作者
「要不要做横版」「横版先给你看吗」（作者 2026-10-27「以后不用询问我，只需把控第一个发布平台即可」）。没有这条记录、值是 `confirm-final`，
或作者当次说了「做好先给我看」，就先问，或先交审片再等批准。新建 B 站合集仍要作者同意，这一条不随 `auto` 放开。

起步工程没有横版成片合成，按 lov-media-creator `references/platform-variants.md` 从同一条时间线派生：剪辑、字幕、配乐、混音一处不动，
只换画面与版式。横拍素材的做法（采访 Ricky 2026-10-27 走通，横版组件在该项目的 `work/remotion/src/FilmWide.tsx`，未并进起步工程）：

- 复制 EDL，只改 `version`（如 `v0.4-h`）与 `target`（1920×1080）。16:9 目标下 `crop` 等于整幅，片段缓存键随滤镜变化，竖版缓存不动。
- `build_timeline.py --video --remotion-data remotion/public/data-h`，再 `fx_pieces.py --remotion-data remotion/public/data-h`，
  得 `mezz-<版本>-h.mp4`；核对两版 `timeline.base.json` 的每个条目起点、帧数与源区间逐项相同。字幕仍用竖版那份
  `subs.json`（含人工修正与英文行），`data-h/subs.json` 不用。
- 横版合成用独立的组件与版式常量（`FilmWide.tsx`、`layout-wide.ts`），时间线取竖版 `timeline.json`，只换 `media.video`，
  speech 条目带上 EDL 的 `crop`。每个跳切在「双人全景」与「说话人中景」（约 1.3 倍、以 `crop` 为水平锚点）之间交替；
  人名条做下三分之一时，它在屏期间保持双人全景，避免压到下巴。
- 版式（观测值）：字幕下沿距底边 96 px、两侧各留 240 px，避开 B 站悬停控制条；中文 58 px、英文 32 px。地点条在左上，讲解图形放在
  两人头顶之间的上方区域。参考卡改成左图右文；竖拍的插入视频居中放在自身模糊底上；本身是 16:9 的照片直接铺满，先确认铺满后没有
  露出竖版里裁掉的人或内容。lov-logo-sting 片尾按 16:9 自适应，音效已在共用混音里，帧位不变。
- 竖版已发布时，改 `Root.tsx` 前后给竖版拍静帧基线，逐像素比对；基线先拍两次同一帧，确认渲染是确定的。
- 画面直接用渲染原码率，音轨从已发布的视频号文件原样复制，两份音轨 md5 相同；不走 `finalize_platform.py` 的 9 Mbps 重压
  （B 站不限码率、会自行转码）。质检照第 10 节：完整解码、bt709 回读、时长与竖版一致、逐帧二维码、单帧坏帧扫描（不走 finalize，
  单独跑 `glitch_scan.py`，`--timeline` 用竖版那份）、5 fps 联系表全片看过、关键帧金丝雀在 Studio 看过。
- 中景推近会放大被访者的动作：采访 Ricky 横版里他身体前倾时，脸贴到画面左边缘（约 1:52–1:55、3:03–3:13，竖版同处取景中心一样）。
  渲染前用 `<片段>.faces.json` 查中景里脸框离画面边缘的距离，贴边的片段只用双人全景；来不及改就在交付报告「已知小问题」里写明时间码。
- 交付：`platform-bilibili-vX.mp4` 是审片版的 APFS 克隆，报告写明两者 SHA-256 相同；16:9 封面用作者已选那一版的同一视觉
  （`InterviewCover169-<v>`），4:3 槽沿用竖版的分享卡；文案见 [publish-handoff.md](publish-handoff.md)「B 站跟发」。
