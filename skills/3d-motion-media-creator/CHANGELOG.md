# Changelog

## [0.1.1] - 2026-10-14

### Changed

- 商业说明改为包含在 Lovstudio.AI VIP Membership 全套权益中：本 Skill 与依赖均包含，不单独定价、不兑换 Credits；会员金额以实际会员方案为准。
- 保留私有源码；GPU、渲染时间与第三方服务费用不包含在会员权益中。本次官网登记状态待发布流程回读验证。
- 同步入口元数据、运行 Manifest、可信度卡、定价卡与 README 版本；运行代码、起步工程、案例与引用资料保持不变。

## [0.1.0] - 2026-10-13

首个版本：`lov-film` 片型套件的第二个成员「三维图志 · 3D Motion Atlas」（ID 由用户 2026-10-13 确认）。从《如何打造一款特斯拉》
（2026-10-12，Remotion 4.0.534 + three 0.186.1）提炼，叠在 `lov-motion-media-creator` 0.9.0 上：共享流水线在顶层 `depends_on`
声明依赖、按 Skill ID 引用，不复制。

### Added

- `scripts/bootstrap_3d.py`：按 `--base`、`$MOTION_MEDIA_CREATOR_DIR`、共享安装目录的顺序找基座，复制它的起步模板（不带示例片与生成目录），
  叠上 `assets/starter-3d/`，把三维依赖并进 `package.json`（`@remotion/three` 对齐工程的 `remotion`）。复制时给底座五个文件打补丁：`src/Cover.tsx`
  的片名字体与 `bandGlyph`、`tools/fonts.py` 与 `src/lib/fonts.ts` 的字体表（三款 OFL 字体）、`src/components/HUD.tsx` 的进度轴出现时机、
  `audio/chapters/briefs.json` 的章节键；补丁对不上时报 `warning` 并以 1 退出。`--dry-run` 逐个列出新增、覆盖与保留的文件；`--force` 更新套件与工具、
  保留片子自己的文件（时间线、场景、署名、旁白、封面、素材目录、贴图表、简报、锁文件），`package.json` 在工程自己的那份上合并；
  `--overwrite-film`、`--keep` 调整保留范围；目标里的文件一个不删。
- `assets/starter-3d/`：
  - 场景套件 `src/three/`：`Stage` 与 `Cam`（AgX、SMAA、景深、辉光、暗角、`PostWarmup`、无 HDRI 时的 `StudioEnv`）、`camera.ts`（`project`、`lerpCam`、
    `orbit`、确定性 `shake`）、`useMat` 的 18 种 PBR 材质与 `textures.ts` 贴图表、`StudioFloor` / `ConcreteFloor` / `Bevel`、`GroundShadow`、
    `AreaLight` / `ShadowSpot`、`RobotArm` 与 `ikArm`、通用 glTF 加载 `Model`（`remove`、`replace`、`only`、`draco`、`fit`、`ground`、`clip`）、
    `ShotNote`（`model` / `archival` / `stock` / `ai`，资料署名取自素材目录）；`Stage` 默认加雾，地面默认 400 m。
  - 资料：`src/components/Archival.tsx`（`Photo`、`Footage`、`mediaUrl`）、`src/media.ts`（空的素材目录）、`tools/conform.py`（从登记表统一调色、
    缩放、转 30 fps 去音轨，写素材目录，许可不在名单即拒收）。
  - 字体：`tools/fetch_fonts.py`（Noto Serif SC、Noto Sans SC、IBM Plex Mono，记 SHA-256，实例化六个静态字重，`--from` 用本机已有文件）。
  - `scenes/common.tsx` 的 `useLabelBand`（引线标签夹在字幕带之上）与 `DissolveIn`（叠化进章）；`timeline.ts` 载入时拒绝遮罩类转场。
  - `tools/frametime.sh`（全尺寸稳态单帧）、`tools/determinism.sh`（并发 1 与 4 逐帧比）、`src/dev/ShadowAB.tsx`（接触阴影四格回归）。
  - 示例片《齿轮箱》（70 秒、6 章，每章横竖各一套机位，03 章叠化进来）与三维定帧封面 `CoverPicture`。
  - `remotion.config.ts`（`angle`、并发 4、120 秒超时）与 `deps-3d.json`（整组锁定的三维依赖）。
  - `tools/fetch_textures.py`（ambientCG、Poly Haven 的 CC0 贴图与 HDRI，写来源旁注与署名，`--dry-run`、`--offline`、`--only`、`--force`、`--res`）、
    `tools/gltf_nodes.py`（节点、材质、贴图、动画、版权字段、Draco 与疑似标志）、`tools/cover_3d.py`（三维定帧进基座的封面底图槽位，旁注标 `ai: false`）。
- references：`style-grammar-3d.md`、`scene-kit.md`、`render.md`、`assets-and-licensing.md`、`pitfalls-3d.md`、`skill-composition.md`、`user-profile.md`。
- Profile：只存三维记录 `render_backend`、`render_concurrency`、`texture_library`、`brand_marks`；片子级记录读写基座的命名空间。
- 可信度卡、真实案例（《如何打造一款特斯拉》v0.1–v0.5）与定价卡（免费或付费待用户决定）。

### Changed（相对特斯拉片的三维套件）

- 地面接触阴影改用 `GroundShadow`：drei `ContactShadows` 在后期链下连续渲染会拖影；特斯拉片的 `ClearBeforeComposer` 修法复测有效（影子在、无拖影），
  但每帧翻渲染器的全局状态；该片的 `ContactShadows` 多放在地面上方 2 mm，那里站着的物体没有影子（2026-10-13 `src/dev/ShadowAB.tsx`）。
  物体站在 y = 0，地面放在 `FLOOR_Y`。早先记的「`ClearBeforeComposer` 让影子整个消失」没有可复跑的测试，复现不了，已改正。
- 字体从系统字体换成三款 SIL OFL 字体；计数中的大数字用思源黑体（思源宋体的数字不等宽）。
- `useMat` 去掉 `envMapIntensity`：three 0.186 在 `scene.environment` 下不用它。
- 地面加大到 400 m 并默认加雾：20–60 m 的地面在竖版远景与 3:4 封面里露出硬地平线。
- 基座 HUD 的进度轴在 01 章首帧整条出现（复制时补丁），不再有两帧半透明的轴与「工序 00」。
- 铸铝改用 Rubber004 的细颗粒（混凝土组在大面积铸件上成排重复）；拉丝铝与不锈钢加各向异性；Metal050A 的粗糙度贴图在取图时重映射到 0.24–0.40。
- 车模加载器换成通用 `Model`；起步层去掉全部品牌、文字与素材文件，示例改为程序化齿轮箱。

### 基座待修项（2026-10-13 记，修好后删补丁）

- 基座 `references/pitfalls.md` 第 35 行补上 `ContactShadows` 放置高度的坑；HUD 的 `show` 改为 `frame < RULER_START ? 0 : …`；`Reveal` 加叠化；
  字体表留替换入口；`references/suite.md` 的现有成员加入本 Skill。明细见 `references/skill-composition.md`「基座待修项」。
