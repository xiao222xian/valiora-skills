---
name: lov-3d-motion-media-creator
description: >
  三维图志：无实拍，用实时三维渲染把一道工序、一件产品的构造或一个尺度做成产品片质感的分章短片，三维画面标示意、与真实资料并置；分章、旁白、配乐、封面与交付沿用 lov-motion-media-creator。
  Use when the user asks for 三维图志、三维科普片、3D 工序/产品动画 or a 3D motion atlas.
license: MIT
compatibility: "Portable Agent Skills format. Requires lov-motion-media-creator (written against 0.9.0) installed, with everything it needs (Node 24+, pnpm, Remotion 4, Python 3.9+, ffmpeg/ffprobe): its assets/starter is the base of every project and its tools run the shared pipeline. 3D packages, pinned as one set: three 0.186.1, @react-three/fiber 9.8.1, @react-three/drei 10.7.9, @react-three/postprocessing 3.2.0, postprocessing 6.39.5, @types/three 0.186.0, and @remotion/three equal to the base's remotion version (4.0.534); React below 19.4. A WebGL-capable GPU through --gl=angle (verified on macOS with Apple Silicon, 2026-10-12; measure a backend first elsewhere). Network once to fetch CC0 textures and HDRIs from ambientCG and Poly Haven; renders run offline."
depends_on:
  - lov-branding-consistency
  - lov-motion-media-creator
metadata:
  author: lovstudio
  version: "0.1.1"
  card_standard: lovstudio/skill-card/v1
  content_class: microcopy
  suite: lov-film
  tags:
    - video
    - 3d
    - motion-design
    - remotion
    - react-three-fiber
    - film-style
---

# 三维图志 · 3D Motion Atlas

把一道工序、一件产品的构造或一个尺度，用实时三维渲染做成产品片质感的分章短片：实物 PBR 材质、有光源的低调布光、物理镜头、重物的重量。
三维重建的画面标「示意」，人物、历史与现场交给真实照片和影像（标「资料」），观众分得清哪一格是重建、哪一格是证据。
片子仍是一部动态图志：沿轴分章、章节标题卡与进度轴 HUD、旁白与大字幕、分章配乐卡点、事实核查、三比例封面、交付报告与发布交接单，
这些都由依赖 `lov-motion-media-creator`（下称基座）完成，交付形态与基座相同（默认只出 16:9）。

本 Skill 是 `lov-film` 片型套件的第二个成员，只管三维这一层：起步叠加层与场景套件、三维风格语法、渲染设置、贴图与模型授权、三维坑表。
起步叠加层带一部 70 秒的示例片《齿轮箱》（程序化齿轮箱拆解、十种材料、机械臂取放、1,200 台批量），不含任何品牌、模型或贴图文件。
做法来自《如何打造一款特斯拉》（2026-10-12，二维首版被评「过于幼稚」后的三维重制）。

## Triggers

### Activate when

- 「用三维讲一遍 XX 是怎么造出来的」「做一条三维科普片 / 三维图志」「产品拆解、爆炸图、装配工序的三维动画」「从零件到整机、从一台到一万台」。
- 二维动态图志被嫌「幼稚」「像 PPT」，要升级成三维、产品片质感，必要时配真实照片与影像（《如何打造一款特斯拉》v0.1 → v0.2）。
- "Make a 3D motion atlas of how a battery pack is built", "a 3D process or product animation with real archival photos".
- 已有三维图志的改版：换模型或章节、修三维伪影（黑帧、拖影、镜面金属、z-fighting）、重渲、补竖版、换封面底图。

### Do not activate when

- 二维纸面风格的动态图志（编年、地图巡游、图鉴，每章一种二维技法）：交给 `lov-motion-media-creator`。
- 有实拍、录屏或口播素材要剪：交给 `lov-media-creator`。
- 单个 Logo 演绎、片头字或单个动效：交给 `motion-graphics`（用户点名 HyperFrames 时交给 `hyperframes` 系列）。
- 只讲一个算法或数据结构：`lov-algo-viz-creator`；只要封面：`lov-channels-cover`；只要发布：`lov-media-publisher`。

## 与基座的分工

| 归本 Skill | 归基座 `lov-motion-media-creator` |
| --- | --- |
| 三维叠加层 `assets/starter-3d/` 与 `scripts/bootstrap_3d.py` | 起步底座 `assets/starter/` 与它的全部工具 |
| 三维风格语法：光、材质、镜头、运动、资料并置、标注行、转场 | 选轴分章、节拍网格、字号下限、HUD 与章节标题卡、上屏文字去 AI 味 |
| 场景套件 `src/three/`、贴图取用、三维封面定帧 | 事实台账与对抗核查、旁白与字幕、分章配乐、母带 |
| 渲染设置（GL 后端、并发、超时）与三维的分块要求 | 封面（AI 无字底图与合成排字）、片尾署名、章节时间轴、费用账本 |
| 贴图、HDRI、模型与资料的授权，真实品牌的处理 | 交付质检、交付报告、发布交接单 |
| 三维坑表 | 不分二维三维的坑 |

- 基座的规则一律照旧，这里不复述；引用写作「基座 `references/<文件>.md`「节名」」，到基座目录下读（找法见 Step 0）。
- 两边冲突时，三维片以 [references/style-grammar-3d.md](references/style-grammar-3d.md)「与基座的差异」为准：全片一套字体，
  每章一个场与一套布光（不按基座 `references/techniques.md` 选二维技法），转场只用剪辑手法，右上角留给标注行。
- 相邻 Skill 的交接，以及为什么声明依赖、不复制流水线，见 [references/skill-composition.md](references/skill-composition.md)。

## User Profile (cross-session)

每次运行读两份 Profile：

```bash
python3 "$SKILL_DIR/scripts/profile_store.py" read --skill-id lov-3d-motion-media-creator --pretty
python3 "$SKILL_DIR/scripts/profile_store.py" read --skill-id lov-motion-media-creator --pretty
```

- 片子级记录（品牌名、官方 Logo、印章、默认画幅、旁白、标注、片尾）归基座命名空间 `skills.lov-motion-media-creator.records`，这里只读；
  用户在三维片的会话里说出这类长期偏好时，用 `--skill-id lov-motion-media-creator` 写回基座命名空间，不复制到本 Skill。
- 本 Skill 只存四条三维记录（`skills.lov-3d-motion-media-creator.records`）：`render_backend`（macOS 默认 `angle`）、`render_concurrency`（默认 4）、
  `texture_library`（本机贴图库）、`brand_marks`（默认：真实品牌的标志只出现在纪录性质的资料照片里）。
- 只保存用户直接说出的值：`profile_store.py record --skill-id … --path records.<字段> --value … --confirm`，报告保存路径；
  机器相关的三条只描述这台机器，换机器先实测再改。细则见 [references/user-profile.md](references/user-profile.md)。

## Workflow (MANDATORY)

按顺序执行。每一步先做基座同名步骤（基座 `SKILL.md` 的 Workflow 与 `references/pipeline.md`），再做这里写的三维部分。

### Step 0: 底座、Profile 与起步工程

- 找基座：`$MOTION_MEDIA_CREATOR_DIR`，否则用户主目录下的 `.agents/skills/lov-motion-media-creator`。找不到就停下，请用户安装
  `lov-motion-media-creator`，不要自己拼一份底座。完整读一遍基座 `SKILL.md`。本 Skill 按基座 0.9.0 写成；基座版本更高时，
  起步后先过类型检查与示例静帧再开工。
- 读 Profile（见上）。
- 起步，替代基座 Step 0 的「复制起步模板」：

  ```bash
  python3 "$SKILL_DIR/scripts/bootstrap_3d.py" <project>/work/remotion --dry-run  # 逐个列出新增、会覆盖与会保留的文件；不写
  python3 "$SKILL_DIR/scripts/bootstrap_3d.py" <project>/work/remotion            # 底座 + 三维层，只往空目录写
  cd <project>/work/remotion
  pnpm install                                  # 第一次不加 --frozen-lockfile：底座的锁文件没有三维依赖
  python3 tools/fetch_textures.py --dry-run     # 不联网：下载地址、粗糙度重映射、要加的署名
  python3 tools/fetch_textures.py               # CC0 贴图与 HDRI -> public/assets/，署名写进 src/credits.ts
  python3 tools/fetch_fonts.py                  # 三款 SIL OFL 字体 -> fonts-ofl/，实例化静态字重（几分钟）
  FILM_LOGO=… FILM_SEAL_DIR=… tools/bootstrap.sh   # 基座：字体子集、纸纹与颗粒、Logo、印章、静音母带
  export GL=angle                               # 基座 tools/stills.mjs（单章静帧、封面）只认这个环境变量
  npx tsc --noEmit -p .
  tools/preview.sh explode stills 16x9 150      # 示例章出一张图，确认这台机器能渲三维
  ```

  底座位置也可用 `--base <dir>` 指定。脚本不复制底座的示例片（`src/scenes/S*.tsx`、`src/lib/glyphs*.ts`），也不复制 `public/`、`node_modules`、字体目录；
  复制时改底座五个文件：`src/Cover.tsx`（片名字体、`bandGlyph`）、`tools/fonts.py` 与 `src/lib/fonts.ts`（换成三款 OFL 字体）、`src/components/HUD.tsx`
  （进度轴在 01 章首帧整条出现）、`audio/chapters/briefs.json`（章节键换成示例片的）。哪条没对上就报 `warning` 并以 1 退出，按提示手改。
- 已有三维图志的改版：先 `--dry-run` 看清单，再 `--force`：套件与工具更新，片子自己的文件（时间线、场景、署名、旁白、封面、素材目录、贴图表、
  两份简报、锁文件）内容不同就保留，`package.json` 在工程自己的那份上合并；`--overwrite-film` 才把它们换回示例（[references/scene-kit.md](references/scene-kit.md)「起步」）。
- 渲染后端：不是 macOS、又没有 `records.render_backend` 时，按 [references/render.md](references/render.md)「GL 后端实测」逐个后端出一帧再定。
  静帧明显偏慢先查是不是退到了软件渲染：单张全尺寸静帧连同开标签页 1.3–2.9 秒算正常（2026-10-13 本机），SwiftShader 要好几秒一帧还不算启动。
- 贴图库：`records.texture_library` 指向一个按 `public/assets/` 布局存放的目录（`tex3d/<组>/` 带 `source.json`，`hdri/` 带同名 `.json`）。
  先 `cp -Rc` 进工程的 `public/assets/`，再跑 `fetch_textures.py`：已有的跳过并按旁注补署名，只下缺的。
- 离线时 `fetch_textures.py --offline` 写纯灰占位，能渲染、不能交付；联网后重跑即替换。费用账本照基座，取贴图不花钱。

### Step 1: 结构方案（先给用户看，再开工）

- 先做基座 Step 1：选轴、8–15 章加片头片尾、节拍网格上的章长、每章配乐情绪、交付形态、署名登记、品牌元素。三维最合适的轴是工序、构造与尺度。
- 每章另写四样：主体（程序化几何，或 glTF 及其许可）、一套布光（色温与看得见的光源）、主镜头的焦距与机位（横竖各一套）、
  哪些镜头是三维示意、哪些交给资料照片与影像。章与章靠光区分，不靠换字体与配色（style-grammar-3d「光与色调」）。
- 以真实公司或产品为题：按 `records.brand_marks`，三维里用通用、无标志的造型，整片标「车型为示意」一类说明，品牌标志只出现在纪录性质的资料照片里；
  强调色避开品牌标准色；片尾写无隶属声明（[references/assets-and-licensing.md](references/assets-and-licensing.md)「品牌与商标」）。
- 模型与素材先过许可：CC0、公有领域、Pexels、CC BY 可用，CC BY-SA、NC、ND 不用。能程序化的通用设备就程序化：不用署名，也没有标志。
- AI 写实镜头默认不用，只在方案里列成可选项（style-grammar-3d「AI 写实镜头」）。排期吃紧时，后面的章降级成影棚台面加单件产品，不退回二维。
- 方案、片名与品牌元素一次问完（宿主有 AskUserQuestion 时用它），推荐项放第一个。

### Step 2: 事实台账

- 照基座 Step 2。三维多一类条目：画面判断。写实画面会被当成事实，铝液的颜色、铸件出模时发不发光、焊花持续几帧这类「画成什么样」
  也进台账做对抗核查（style-grammar-3d「写实会放大事实暗示」）。

### Step 3: 配乐、旁白与卡点

- 照基座 Step 3。配乐简报 `audio/chapters/briefs.json` 是 bootstrap 按示例片的章节键写的占位：键换成新片 `src/timeline.ts` 的章节 id、按新片重写，
  再跑基座的 `audio/gen_chapter_music.py`（付费，先 `--dry-run` 报价）。片头片尾按它的 `_readme`：有整片配乐时不写。
- 三维里的冲击（落件、合模、落座）写进 `src/timeline.ts` 的 `CUES`、落在拍上，冲击帧硬切，加 `shake` 的 6 帧衰减震动。

### Step 4: 搭建三维场景

- HUD、章节标题卡、字幕、字号下限、片尾署名卡、字体子集照基座 Step 4。示例片的 `src/timeline.ts`、`src/scenes/`（含 `gearbox/`）换成新片；
  `src/three/textures.ts` 里用不到的贴图组，连同 `kit.tsx` 里用它的材质与 `src/credits.ts` 里那一行一起删。
- 字体只用三款 OFL：章名 `font: 'OFL-Serif'`、片名 `OFL-SerifHeavy`，正文、字幕、标注走 `BODY`、`SUBTITLE_FONT`、`MONO`；计数中的大数字用 `OFL-SansMedium`
  （思源宋体的数字不等宽）。不往字体表里加系统字体（style-grammar-3d「字体」）。
- 套件用法见 [references/scene-kit.md](references/scene-kit.md)，要点：
  - 一镜一块 `Stage`（AgX、反射环境、后期链、`PostWarmup`）加 `Cam`；同一时刻一章只挂一块，`<ThreeCanvas>` 里的 `<Sequence>` 写 `layout="none"`。
  - 机位横竖各一套（`useCams`），竖版不裁横版，主体放在舞台带内；引线标注用 `project()` 钉在三维点上，再交给基座 `Callout`。
  - 材质只用 `useMat`（每种都有粗糙度与法线贴图），硬边用 `Bevel`，1 单位 = 1 米；新加贴图组先量粗糙度均值。
  - 物体底面站在 y = 0，地面放在 `FLOOR_Y`，接触阴影用 `GroundShadow`；灯用 `AreaLight`、要投影时加 `ShadowSpot`，HDRI 或 `StudioEnv` 只给反射。
  - 地面用套件的 400 m `StudioFloor` / `ConcreteFloor`，靠 `Stage` 的雾融进背景（默认 6–40 m）；远处还有主体的镜头把 `fog` 起点放到最远主体之后。
  - 引线标签的 y 用 `useLabelBand().y()` 夹在字幕带之上；章间叠化用 `DissolveIn`（基座没有叠化）。
  - 外部模型先跑 `python3 tools/gltf_nodes.py <file>`（节点、材质、贴图、版权字段、Draco、疑似标志），再用 `Model` 的 `remove` / `replace`
    去掉标志、`fit` 到实际尺寸，取用当下写进 `src/credits.ts`（改过就写 `changed`）。机械臂用 `RobotArm` + `ikArm`；大量重复件用 `instancedMesh`，矩阵按帧号算。
- 一切运动是 `useCurrentFrame()` 的纯函数：不用 `useFrame` 做动画，不用 `Math.random`、`Date`、`performance.now`，不用 drei `Float`、`Sparkles`、
  `CameraShake`、`Cloud`、`AccumulativeShadows`，不用 TAA 一类时间累积后期；随机用基座 `rng(seed)`，glTF 动画用 `Model` 的 `clip`（`mixer.setTime`）。
  渲染时这些读到的是真实时钟，或按标签页各算一次（render.md「GPU 与无头环境」「分块渲染」）。
- 每个镜头挂 `ShotNote`：三维镜头默认「示意」（`note || '示意'`）；资料镜头写 `kind="archival"`（同类工序 `"stock"`）和 `media` 键，标注从素材目录取
  「资料 · 说明 · 作者 · 许可」。资料先登记，再 `python3 tools/conform.py` 统一调色并生成 `src/media.ts`；只用满幅窗口（`Photo`、`Footage`）与场景里的
  实体相纸（`useTexture(mediaUrl(key))`）两种呈现（style-grammar-3d「资料」「标注与 HUD」）。
- 性能预算：全尺寸 16:9 稳态单帧不超过 0.6 秒，用 `tools/frametime.sh <id> <章内帧>` 量（同一帧起渲 30 帧与 1 帧、相减再除，扣掉开标签页）；
  单张静帧的耗时含开标签页与编译着色器，不能拿来比。超了先降反射地面分辨率、阴影贴图或几何细分。

### Step 5: 单章预览与三维检查

- 每章从只挂本章的入口预览（基座 `tools/preview.sh`，帧号是章内帧，`GL=angle` 已导出）：

  ```bash
  tools/preview.sh <id> stills 16x9 30 120 250   # 每个镜头至少一张；做竖版时 16x9 换成 both
  tools/preview.sh <id> sheet 16x9 10             # 整章每 10 帧一格，连续渲染
  tools/preview.sh <id> clip 16x9 <from> <to>     # 运动、震动、对焦
  ```

  静帧每张开一个新标签页，`sheet` 与 `clip` 是连续渲染。拖影、对焦跳到原点只在连续渲染里出现：每章至少看一张 `sheet`。
- 逐张打开看，按下面挑毛病；每章至少三轮「改 → 出图 → 看」（style-grammar-3d「自检」）：
  - 黑帧：每个标签页的头一两帧黑，是后期链后没挂 `PostWarmup`。以黑场或叠化进入的章，单章入口里前几帧本来就黑，从转场后几帧看起，转场在整片入口里看。
  - HUD 交接：片头接 01 章那一刻，进度轴应在 01 章首帧整条出现；前两帧露出半透明的轴和「工序 00」，是 bootstrap 改基座 HUD 的补丁没打上，不是三维伪影。
  - 未打光：面光源不亮或朝向打反（套件的 `AreaLight` 已处理，手写 `rectAreaLight` 最容易出错）；暗部死黑、亮部死白。
  - 贴图：缺图；纯灰占位（`source.json` 的 `placeholder` 为 true）；金属一片镜面（粗糙度贴图太黑）；大面积上贴图成排重复。
  - z-fighting：共面的面在联系表里闪条纹，相邻件的面一律错开。
  - 阴影拖影：运动物体的影子在连续渲染里一帧帧叠起来，静帧看不出。
  - 地平线：远景与竖版里地面的远边或一条硬地平线；雾起点要在最远主体之后。
  - 标注：镜头移动时引线标签滑进字幕带（看 `sheet`，不只看静帧）。
  - 品牌标志、线框、调试辅助线、坐标轴、工具名；穿模、回弹、匀速的机械感。
- 确定性：`tools/determinism.sh <id> <起> <止>` 把同一段帧以并发 1 与 4 各渲一遍逐帧比，最大差不超过 24/255、差值超过 8 的像素不超过 0.1%
  （2026-10-13 示例 03 章 0/255）；超了就有隐藏的时间依赖。
- 然后做基座 Step 5：联系表、转场窗口、`node tools/chapters.mjs`、片尾署名卡、画面不展示制作技术、上屏文字去 AI 味。
  已知坑见 [references/pitfalls-3d.md](references/pitfalls-3d.md)，不分片型的坑见基座 `references/pitfalls.md`。

### Step 6: 封面

- 照基座 Step 6：三比例、AI 无字底图、`src/Cover.tsx` 排字、`tools/stills.sh covers` 检查。
- 三维定帧是不花钱的底图备选：`python3 tools/cover_3d.py --dry-run`，再去掉 `--dry-run` 真跑，把 `src/scenes/CoverPicture.tsx` 渲进基座读的
  `public/assets/cover/ai-<比例>.png`，旁注 `.json` 写 `source: 3d-still`、`ai: false`；已有的 AI 底图默认保留，`--force` 才替换。
  构图给片名留出左 40%（横）或上 40%（竖），再 `tools/stills.sh covers` 看三张。
- 2026-10-12《如何打造一款特斯拉》的三维定帧封面被用户评为不够吸引人，换成了 AI 底图：两种都给用户看，由用户挑。

### Step 7: 渲染、交付与发布交接

- 照基座 Step 7，渲染设置按 [references/render.md](references/render.md)：

  ```bash
  export GL=angle
  tools/deliver.sh 16x9 vX.Y 4    # 并发 4：所有标签页共用一个 GPU 进程，基座默认的 6 没有收益
  ```

  `deliver.sh` 在工程根调用 CLI，`remotion.config.ts` 的 `angle` 与 120 秒超时自动生效，不用另传；它只把第三个参数当并发（默认 6），三维片传 4。
  它按章节分块、每块新开浏览器、无损拼接；`angle` 有已知的内存泄漏，三维片分块是必须的。交付后用它打印的用时核对后端：GPU 约 0.08–0.25 秒一帧，
  SwiftShader 约 5.7 秒（render.md「渲染配置」）。
- 所有分块出自同一个 bundle：渲染途中改了源码，就停下、重新打包、整片重渲。先用单章预览把问题修完再交付；
  16:9 单画幅约每分钟成片 2.5 分钟（2026-10-12，Apple M3 Pro，并发 4）。
- 交付报告（基座格式）另写三维资产清单（贴图、HDRI、模型的来源、许可与改动，取自各 `source.json` 与 `src/credits.ts`）和渲染后端与用时。
  AI 生成内容清单里，三维渲染、程序化几何与动画不算生成内容；封面底图按 `ai-<比例>.json` 的 `source` 判，`3d-still` 不算 AI 生成。
- 发布交接与发布照基座（交给 `lov-media-publisher`），本 Skill 不另写交接单。

## Hard gates

基座的 Hard gates 全部照旧。三维另有：

- 一切运动由帧号推出：`tools/determinism.sh` 在每章有运动的段落上通过（并发 1 与 4 逐帧比，最大差 ≤ 24/255，差值超过 8 的像素 ≤ 0.1%）。
- 成片里没有三维伪影：意外的黑帧、未打光的场景、缺失或占位的贴图（交付时没有 `placeholder: true` 的 `source.json`）、z-fighting、阴影拖影、
  对焦跳到原点；每章至少看过一张连续渲染的联系表。
- 地面接触阴影用套件 `GroundShadow`，不用 drei `ContactShadows`：后期链关掉 `autoClear` 后它在连续渲染里拖影，放在地面上方时站着的物体没有影子；
  特斯拉片的修法 `ClearBeforeComposer` 复测有效但每帧翻渲染器的全局状态，套件不用。升级三维依赖后重跑 `src/dev/ShadowAB.tsx`（2026-10-13 四格对照）。
- 远景与竖版里没有地面远边或硬地平线（套件 400 m 地面加 `Stage` 的雾）。
- 每个三维镜头都有「示意」类标注，每个资料镜头都有「资料 · 作者 · 许可」；观众分得清重建与证据。
- 真实品牌的标志不出现在三维画面、自制界面、AI 图与封面里，只在纪录性质的资料照片里（Profile `records.brand_marks`）；片尾有无隶属声明。
- 每份贴图、HDRI、模型与资料都在取用当下登记来源与许可；只用 CC0、公有领域、Pexels 与 CC BY；需要署名的进 `src/credits.ts` 并写明改动；
  起步层不带任何模型与贴图文件。
- 材质都是带粗糙度与法线贴图的 PBR（只有自发光、液体、玻璃例外），硬边都有倒角；画面上没有线框与建模网格。
- 上屏字体只用 `tools/fetch_fonts.py` 取的三款 SIL OFL 字体（思源宋体、思源黑体、IBM Plex Mono），不加系统字体；交付报告写字体名与许可。
- 章间转场只用剪辑手法（硬切、匹配剪辑、叠化、黑场、白场、闪白），不用基座 `Reveal` 的百叶、圆孔、碎片、波浪一类转场（`timeline.ts` 载入时拒绝）。
- 交付渲染走 GPU 后端（macOS `--gl=angle`），按章节分块，全部分块出自同一个 bundle。
- AI 写实镜头只在用户选用时出现，整段标「生成画面 · 示意」并进 AI 生成内容清单；三维渲染与三维定帧封面不算 AI 生成内容。

## References

| 文件 | 内容 |
| --- | --- |
| [references/style-grammar-3d.md](references/style-grammar-3d.md) | 三维片「对」的标准：与基座的差异、光与色调、材质、镜头、运动、资料并置、标注与 HUD、转场、字体、自检 |
| [references/scene-kit.md](references/scene-kit.md) | `assets/starter-3d/`：起步与改版、示例章节、`Stage`（雾）与 `Cam`、相机数学、材质与贴图、`GroundShadow` 与回归、灯、机械臂、外部模型、资料、字体、标注与转场、测量、确定性、已知缺口 |
| [references/render.md](references/render.md) | 版本锁与升级回归、渲染配置与后端核对、GL 后端实测、速度与稳态单帧、分块、单章检查、GPU 与无头环境 |
| [references/assets-and-licensing.md](references/assets-and-licensing.md) | 许可名单、登记、ambientCG 与 Poly Haven、CC BY 模型（以 CarConcept 为例）、资料照片、品牌与商标、生成式图像 |
| [references/pitfalls-3d.md](references/pitfalls-3d.md) | 三维踩过的坑：现象、根因、做法、证据 |
| [references/skill-composition.md](references/skill-composition.md) | 相邻 Skill、交接物，为什么依赖基座而不复制，与基座 suite.md 的对照，基座待修项 |
| [references/user-profile.md](references/user-profile.md) | 两个 Profile 命名空间与写回规则 |

基座 `lov-motion-media-creator` 里常用的：`SKILL.md`、`references/pipeline.md`、`style-grammar.md`、`fact-and-disclosure.md`、`covers.md`、
`publish-handoff.md`、`starter-template.md`、`pitfalls.md`、`suite.md`。
