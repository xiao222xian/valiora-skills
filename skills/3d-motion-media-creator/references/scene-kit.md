# 三维场景套件 `assets/starter-3d/`

`starter-3d` 是叠在 `lov-motion-media-creator` 起步模板（其 `assets/starter/`）之上的一层，只放三维特有的东西：
`src/three/` 套件、四章示例、`remotion.config.ts`、三维依赖、资料组件与调色脚本、取贴图、取字体与封面底图的脚本、测量与回归工具。时间轴、HUD、标题卡、字幕、配乐、
署名、分块渲染与交付都用底座的，写法见 `lov-motion-media-creator` 的 `references/starter-template.md` 与 `references/pipeline.md`。
套件来自《如何打造一款特斯拉》（2026-10-12）的 `work/remotion/src/three/`，去掉了该片的品牌与素材，2026-10-13 按复测改了接触阴影、地面与字体。

## 起步

```bash
python3 "$SKILL_DIR/scripts/bootstrap_3d.py" <project>/work/remotion   # 底座 + 三维层，只往空目录写；--dry-run 逐个列出
cd <project>/work/remotion
pnpm install                          # 合并进 package.json 的 three、@react-three/*、postprocessing、@remotion/three
python3 tools/fetch_textures.py       # CC0 贴图与 HDRI -> public/assets/，署名写进 src/credits.ts；--dry-run 只看计划
python3 tools/fetch_fonts.py          # 三款 SIL OFL 字体 -> fonts-ofl/（实例化 4 个字重，几分钟）；--from <目录> 用本机已有的
tools/bootstrap.sh                    # 底座：字体子集（OFL 字体）、纸纹与颗粒、占位 Logo、静音母带
export GL=angle                       # 底座 tools/stills.mjs（单章静帧、deliver.sh covers）从环境变量取后端
npx tsc --noEmit -p .
node tools/chapters.mjs --out ../manifest/chapters.txt
tools/preview.sh explode stills both 30 240
```

- 底座位置依次取 `--base`、`$MOTION_MEDIA_CREATOR_DIR`、`~/.agents/skills/lov-motion-media-creator`（Skill 根目录或其 `assets/starter`）。
- 不复制底座的示例片：`src/scenes/S*.tsx` 与 `src/lib/glyphs*.ts`（留着会把《字里中国》的字打进字体子集）；`node_modules`、`public/`、`fonts-src/`、
  `fonts-ofl/` 从不复制，目标里的文件一个不删。
- 三维依赖在 `deps-3d.json`，版本是 2026-10-12 一起验证过的组合：postprocessing 6.39.5 只支持 three < 0.187（6.38 只支持 < 0.182，
  会黑屏），R3F 9.8.1 要求 React < 19.4；`@remotion/three` 自动对齐工程的 `remotion` 版本。合并后 `pnpm-lock.yaml` 会在安装时更新。
- 复制时改底座的五个文件，哪条没对上就打 `warning` 并以 1 退出，按提示手改：`src/Cover.tsx`（`COVER` 的片名字体 `OFL-SerifHeavy`；退回色谱时
  不画示例片的「汉」字，`bandGlyph: ''`）、`tools/fonts.py` 与 `src/lib/fonts.ts`（OFL 字体表，见「字体」）、`src/components/HUD.tsx`（进度轴在第一章
  首帧整条出现，不淡入，见 pitfalls-3d）、`audio/chapters/briefs.json`（配乐简报的章节键换成示例片的四章，值是占位，按新片重写）。
- 已有工程的改版：先 `--dry-run`，它逐个列出新增、会覆盖与会保留的文件；`--force` 更新套件与工具，片子自己的文件（`src/timeline.ts`、`src/scenes/`、
  `src/credits.ts`、`src/narration.ts`、`src/Cover.tsx`、`src/cover3d.tsx`、`src/media.ts`、`src/three/textures.ts`、两份简报、`pnpm-lock.yaml`）内容不同就保留，
  `--keep <模式>` 再多保留几条，`--overwrite-film` 才把它们换回示例；`package.json` 在工程自己的那份上合并三维依赖。删过贴图组的片子，
  更新后 `kit.tsx` 可能又引用那些组，`tsc` 会指出来，照旧删掉。`src/credits.ts` 被换回示例时，重跑 `fetch_textures.py` 补回贴图署名。

## 覆盖层里有什么

| 路径 | 作用 | 新片要改什么 |
| --- | --- | --- |
| `remotion.config.ts` | `--gl=angle`、并发 4、`delayRender` 超时 120 s，对 `remotion render/still/studio` 生效 | 不改 |
| `src/timeline.ts` | 示例片《齿轮箱》：序、拆解、材料、取放、批量、片名，每章 ≥ 330 帧、起点在 15 帧拍网格上；导出与底座一致；载入时拒绝遮罩类转场 | 全部换成新片；`AXIS.format` 按轴改 |
| `src/scenes/index.ts`、`S00`–`S05` | 示例章节（见下表）；`  <id>: <Component>,` 一行一章，`tools/preview.sh` 靠它找文件 | 换成新片的章节 |
| `src/scenes/gearbox/` | 程序化齿轮箱：渐开线齿轮、剖分箱体、轴、轴承、螺栓，带爆炸参数 | 示例素材，换题材时删 |
| `src/scenes/CoverPicture.tsx`、`src/cover3d.tsx` | 封面底图用的三维定帧（无字），三个比例各一个机位 | 换成新片最能代表的一镜 |
| `src/scenes/common.tsx` | 分画幅机位 `useCams`、左下说明 `Caption`、引线标签的安全带 `useLabelBand`、叠化 `DissolveIn` | 一般不改 |
| `src/three/` | 套件，见下文 | 一般不改；缺什么在章节目录里写本地版本 |
| `src/components/Archival.tsx`、`src/media.ts` | 资料的满幅窗口 `Photo`、`Footage` 与 `mediaUrl`；素材目录（示例为空） | `media.ts` 由 `tools/conform.py` 生成 |
| `src/dev/ShadowAB.tsx` | 接触阴影回归：四格对照，不进成片 | 不改 |
| `tools/fetch_textures.py` | 下载 `textures.ts` 列的 CC0 贴图与 HDRI，写署名 | 不改；改 `textures.ts` |
| `tools/fetch_fonts.py` | 取三款 OFL 字体、实例化静态字重、记来源 | 不改 |
| `tools/conform.py` | 资料照片与影像统一调色、缩放、转 30 fps 去音轨，写 `src/media.ts` | 不改；改登记表 |
| `tools/frametime.sh`、`tools/determinism.sh` | 全尺寸稳态单帧耗时；并发 1 与 4 逐帧比对 | 不改 |
| `tools/cover_3d.py` | 把 `CoverPicture` 渲成封面底图 | 不改 |
| `tools/gltf_nodes.py` | 列出 glTF/GLB 的节点、材质、贴图、动画、版权字段与 Draco | 不改 |

## 示例章节

| 章 | 画面 | 用到的套件 |
| --- | --- | --- |
| 序 `S00Opening` | 暗场里一条灯带从齿轮箱背后扫过，片名落定；底部一条光线展开，切到 01 章时就是 HUD 进度轴 | `Stage`、`AreaLight` 移动、`GroundShadow`、底座 `rulerGeometry` |
| 01 拆解 `S01Explode` | 螺栓、箱盖、两根轴的总成、轴承依次拆开，镜头拉远并慢环绕，五条引线标注钉在零件上 | `explodeAt` 分段缓动、`lerpCam`、`orbit`、`project` + 底座 `Callout`、景深 |
| 02 材料 | 混凝土台面上十种表面，每种一块倒角样块加一个球；HDRI 给反射，一条灯带扫过 | `useMat` 全部纹理组、`hdri`、横竖两套布局 |
| 03 取放 | 从材料章叠化 15 帧进来；六轴机械臂把大齿轮从左台取下、装上右台的定位心轴；同一块画布里远景硬切近景，落座时 6 帧震动 | `DissolveIn`、`RobotArm`、`ikArm` 每帧求解、`openFor`、`shake`、`ConcreteFloor`、`fog={[9, 45]}`、`useLabelBand` |
| 04 批量 | 1,200 台逐排落位，镜头从第一台拉到整片；大数字计数 | `instancedMesh` 按帧写矩阵、`count` 只画已出现的、`fog={[28, 100]}`、`BigNumber`（思源黑体，数字等宽） |
| 片名 `S05Outro` | 近黑底片名卡；说明「均为示意」；署名块读 `src/credits.ts`（CC0 贴图合成一行） | 底座片尾的署名块原样 |

每章都挂 `ShotNote`（角落「示意」）；左下说明在有旁白时让位给字幕（底座 `NARRATED`）。

## `Stage` 与 `Cam`（`Stage.tsx`）

```tsx
<Stage hdri="studio_small_09_1k.hdr" envIntensity={0.4} exposure={1.05} post={{vignette: 0.35, dof: {target: [0, 0.3, 0]}}}>
  <Cam {...cam} />
  ...
</Stage>
```

- 一镜一块画布：`ThreeCanvas`、AgX 色调映射（three r186 自带）、反射环境、后期链（SMAA、可选景深、高阈值辉光、暗角）、DOM 颗粒。
- 画布 `antialias: false`，抗锯齿交给链里的 `SMAA`：多重采样的画布会破坏后期链输出，后期链又让画布的 antialias 失效（2026-10-12）。
- 后期链之后挂 `PostWarmup`：每个新标签页（单张静帧、每个渲染分块）的头一两帧后期链还没建好，出黑帧。它在 effect 里扣住首帧，
  隔两个 animation frame 各 `advance` 一次再放行；扣住不能放在 render 里，挂起的兄弟组件（贴图、模型、HDRI）会丢掉没提交的 render。
- 不给 `hdri` 时用 `StudioEnv`（几块发光面板拍成的环境），不需要任何文件；`hdri` 只给反射，背景默认关。
- 景深：`target` 和 `bokehScale` 可以逐帧变；`focalLength` 是效果的构造参数，一变就整个重建，别做动画。
- 雾：默认 `fog` = [6, 40] m（`FOG`），颜色就是 `bg`，地面在远边之前融进背景，6 m 内的主体不受影响；远处还有主体的镜头把起点放到最远主体之后
  （03 章 [9, 45]、04 章 [28, 100]），`fog={null}` 关掉；`envBackground` 时默认不加。不加雾时 20–60 m 的地面在 9:16 远景与 3:4 封面里露出一条硬地平线（2026-10-13）。
- 同一时刻一章只挂一块 `Stage`：章间转场已经叠两块，每块是一个 WebGL 上下文。镜头切换优先在同一块画布里换 `Cam`（03 章），
  要换布景时才用 `<Sequence layout="none">` 换一块 `Stage`。
- 后期链让渲染器的 `autoClear` 常关。画进自己渲染目标的东西要自己清空：`GroundShadow`、drei `MeshReflectorMaterial` 都会；drei `ContactShadows` 不会。
- `Cam`：焦距按 36 mm 长边换算视场（16:9 按宽、9:16 按高），所以同一焦距在两种画幅里沿长边取景一致；每次 render 从场景算好的
  `CamSpec` 设置，画布里没有任何东西驱动相机。

## 相机数学（`camera.ts`）

```tsx
const cam = lerpCam(a, b, prog(frame, 0, 125, E.inOutSine));      // a、b 是本画幅的机位，见 useCams
const [x, y] = project(cam, W, H, [0.07, 0.36, 0.012]);            // 三维点 -> 屏幕像素，和画布同一套投影
const s = shake(frame, [SEAT], 0.0035);                             // 冲击后 6 帧衰减，按帧号播种
<Cam {...cam} pos={addV(cam.pos, s)} target={addV(cam.target, s)} />
```

- 引线标注用 `project()` 把三维锚点换成屏幕坐标，再交给底座 `Callout`；`project` 与 three 的 `lookAt` 同一基向量，包括正俯视时的微扰，
  所以镜头移动时引线不漂。
- 每个镜头横竖各给一套机位（`scenes/common.tsx` 的 `useCams({h, v})`），竖版不裁横版画面；主体放在舞台带 y 330–1540。
- `orbit(target, r, azimuth, elevation)` 给环绕位置；环绕不超过每秒 10 度（30 fps 每帧 0.0058 rad）。
- `shake` 用底座 `rng` 按冲击帧和帧号播种：每个标签页、每次重渲都一样。drei `CameraShake` 读时钟，不能用。

## 材质（`kit.tsx`、`textures.ts`）

```tsx
const cast = useMat('castAlu', {repeat: 16});        // 挤出体 UV 是米：16 = 每 6 cm 一块贴图
const ball = useMat('steel', {repeat: [2, 1]});      // 盒、球、圆柱 UV 每面 0-1
<Bevel size={[0.32, 0.8, 0.32]} position={[0, 0.4, 0]} material={ped} r={0.01} />
```

- `MatKind`：`brushedAlu circularAlu steel galvanized bareSteel darkSteel chrome castAlu moltenAlu copper rubber machinePaint
  safetyYellow graphitePaint anodized leather concrete glass`。每种都有粗糙度贴图和微法线；只有铝液和玻璃不带贴图（美术规范允许的例外）。
- `roughness` 是乘在粗糙度贴图上的系数，不是最终值。ambientCG Metal050A 的粗糙度贴图均值约 0.05（2026-10-13 下载实测 0.05，特斯拉片
  记为 0.06），拉丝金属不管 `roughness` 填多少都成了镜面；`fetch_textures.py` 取图时把它的 1–99 百分位重映射到 0.24–0.40（实测均值 0.31），
  保留拉丝纹理。新加一组贴图时先看它的粗糙度均值。
- 拉丝铝与不锈钢带各向异性（`anisotropy` 0.7 / 0.4）：高光沿拉丝方向拉长，十种材料里才分得出拉丝、旋纹与镀铬（2026-10-13 对比渲染）。
- 铸铝用 Rubber004 的细颗粒：特斯拉片用的混凝土组在大面积铸件上显出成排重复的掉漆斑（2026-10-13）。
- `repeat` 取决于几何体的 UV：`Bevel`、球、圆柱每面 0–1；`ExtrudeGeometry`、`ShapeGeometry` 与按米建的平面 UV 就是米。
- 每次调用返回独立实例；选项要逐帧稳定（变了就重建材质）。
- `Bevel`：带倒角的盒子，半径默认 4 mm，自动压到最薄边的一半以下。不许出现不倒角的方块。
- 地面：`StudioFloor`（暗色模糊反射）、`ConcreteFloor`（CC0 水泥，`tile` 米一块）；两者默认 400 m 宽，远边总在雾里，放在 `FLOOR_Y`（见 `GroundShadow`）。

### 贴图表与取图

`textures.ts` 是唯一的表：`TEX_SETS`（键 -> `{source: 'ambientcg' | 'polyhaven', id, roughness?}`）、`HDRIS`、路径约定
`assets/tex3d/<set>/{color,roughness,normal}.jpg` 与 `assets/hdri/<id>_<res>.hdr`。它不 import 别的文件，`fetch_textures.py` 用 node 读它。

```bash
python3 tools/fetch_textures.py --dry-run        # 计划：下载地址、重映射、要加的署名；不联网、不写文件
python3 tools/fetch_textures.py                  # 缺什么取什么；已有的跳过，只核对署名
python3 tools/fetch_textures.py --only metal050a --force
python3 tools/fetch_textures.py --offline        # 不联网：缺的都写成纯灰占位，不署名；下次联网运行自动替换
```

- ambientCG 下整组 zip（1K 约 2.6 MB），Poly Haven 走 files API 并校验 MD5；走 `HTTPS_PROXY`。每组旁边写 `source.json`
  （来源、页面、作者、许可、SHA-256、日期、是否占位、重映射前后均值）。
- 署名按来源链接去重，追加进 `src/credits.ts` 的 `CREDITS`（CC0，片尾合成「其余资料：ambientCG、Rob Tuytel、Sergej Majboroda（CC0）」）。
  表里每一组都会被下载并署名：片子没用到的组连同 `kit.tsx` 里用它的材质一起删，再删 `credits.ts` 里那一行。
- 2026-10-13 实测：七项（六组贴图、一个 HDRI）13 MB，一分半以内；离线占位能渲染，但只是平面，交付前必须联网重跑。

## 地面接触阴影（`GroundShadow.tsx`）

```tsx
<StudioFloor size={40} />                          {/* 默认 y = FLOOR_Y = -0.003 */}
<GroundShadow size={1.4} far={0.6} blur={0.02} />  {/* 物体底面站在 y = 0 */}
<GroundShadow y={PLINTH_Y} size={[1.13, 0.58]} far={0.12} blur={0.012} />  {/* 台面放在 PLINTH_Y + FLOOR_Y */}
```

- 为什么不用 drei `ContactShadows`：后期链关掉 `autoClear`，它的渲染目标不清空，连续渲染里影子一帧帧叠成拖影。特斯拉片的修法 `ClearBeforeComposer`
  （`autoClear` 在 -1 优先级打开、0.5 关回）有效，但每帧翻一次渲染器的全局状态；`GroundShadow` 每个目标自己 `clear`，不碰 `autoClear`，模糊以米计。
  回归：`MODULE=../dev/ShadowAB tools/preview.sh explode sheet 16x9 30 60 330`，同一个滑动方块四格对照（2026-10-13 全尺寸第 300 帧，地面 160–165/255）：
  `GroundShadow` 脚下约 131、无拖影；`ContactShadows` 拖影 118–156；加 `ClearBeforeComposer` 约 127、无拖影；无后期链约 97。同一天早些时候一次复测记成
  `ClearBeforeComposer` 让影子整个消失，那次没留下可复跑的测试，这次复现不了，作废；`ContactShadows` 放在地面上方时站着的物体本来就没有影子（下一条），
  容易误读成同一件事。
  `GroundShadow` 连续渲染的帧与单开标签页的静帧逐像素差 0.8/255（编码误差）。
- 它从接触面下方 1 mm 朝上拍深度图：物体底面必须在这台相机之上。物体站在接触面（默认 y = 0），接收面低 3 mm（`FLOOR_Y`）；
  接收面若和物体底面齐平，会被拍成整片遮挡物，影子全黑或全无。drei `ContactShadows` 放在地面上方 2 mm 时，站在地上的物体一点影子都没有，也是这个原因。
- 显示平面带 `polygonOffset`：远景里 2 mm 的高差低于深度精度（15 m 处约 1.3 mm）。
- `blur` 以米计：站在地上的物体，影子就是它脚下往外晕开的这一圈。`far` 以内越近越黑。

## 灯（`lights.tsx`）

```tsx
<AreaLight pos={[-0.7, 1.1, 0.9]} to={[0, 0.15, 0]} w={0.9} h={0.35} intensity={22} />   // 柔光箱、灯条
<ShadowSpot pos={[0, 4, 1]} to={[0, 0, 0]} intensity={60} />                               // 需要投影的灯
<StudioEnv intensity={0.6} />                                                              // Stage 没给 hdri 时自带
```

- 面光源要先 `RectAreaLightUniformsLib.init()` 才会照亮东西，R3F 不做；文件加载时做一次。面光源沿本地 -Z 发光，
  `AreaLight` 用 `Matrix4.lookAt(原点, 方向)` 把 -Z 对准 `to`，手写旋转很容易反。面光源不投影。
- `ShadowSpot`：2048 阴影图、小偏移、柔边。three r186 去掉了 `PCFSoftShadowMap`，`Stage` 用 VSM；大块地面接收 VSM 会起带，
  地面关 `receiveShadow`，交给 `GroundShadow`。
- `StudioEnv` 在每个标签页只拍一次（`Environment` 的 `frames=1`），只因为面板不动才安全；它被 `memo` 住，因为 `Environment` 的子元素一变就重拍，
  而场景每帧都重渲子元素。灯要动时用 `AreaLight`，别动环境。

## 机械臂（`RobotArm.tsx`）

```tsx
const tool = lerpV(up(A), A, E.inOutCubic(t));                 // 工具点走直线：每帧插值目标再求解
<RobotArm joints={ikArm(tool, BASE, 0.275)} tool="gripper" toolOpen={openFor(gearRadius)} />
```

- 程序化通用六轴臂（无品牌，不用署名），底座在原点，臂展约 2.3 m；`tool`：`gripper | spotWeld | suction | none`。
- `ikArm(target, base, toolLen)` 解出 j1–j3 与 j5，让工具竖直朝下指向目标；`toolLen` 是法兰到工具点：夹爪手指中段约 0.22，指尖 0.3。
  03 章取 0.275，指尖停在零件底面上方 3 mm，不扎进台面。
- 竖直取放每帧插值目标再求解（工具走直线）；工位之间按绕底座的圆弧插值（角度、半径、高度分开插），看起来像关节运动。`lerpJoints` 在两组解之间插值时工具走曲线。
- 手指沿臂所在竖直面的径向开合：近景机位要从侧面看手指，不要顺着开合方向（03 章第一版近景被一根手指挡满画面）。
- `gripGap(open)`、`openFor(halfWidth)`：手指中心与内侧面的换算，合到零件上就用 `openFor(零件半宽)`。
- 肩部转鼓比转台箱体长 1 cm（0.52 对 0.5）：等长时两端面同在 z = ±0.25，z-fighting（2026-10-12）。

## 外部模型（`Model.tsx`、`gltf_nodes.py`）

```bash
python3 tools/gltf_nodes.py public/assets/models/car.glb        # 节点树、材质与贴图、动画、asset.copyright、是否 Draco
```

```tsx
const REMOVE = ['License Plate', /Emblem/];                        // 放在组件外：选项按引用比较
const SWAP = {Tireside: plainRubber};                               // 胎侧贴图带标志：换成素面
<Model src="assets/models/car.glb" remove={REMOVE} replace={SWAP} fit={{size: 4.7, axis: 'max'}} rotationY={Math.PI / 2} />
```

- 任意 glTF/GLB：去掉标志（`remove`，按节点名或材质名，真删不是隐藏，所以不投影、不算进尺寸）、换材质（`replace`）、只留部分顶层节点（`only`）、
  缩放到实际尺寸（`fit`）、居中落地（`ground`，默认开）。每个实例各自克隆（`SkeletonUtils.clone`，蒙皮网格不会和别的实例共用骨骼）。
- 渲染时上不了网：drei 默认从 gstatic 拉 Draco 解码器，渲染会卡住或超时。压缩模型写 `draco`，并把
  `node_modules/three/examples/jsm/libs/draco/gltf/` 复制到 `public/draco/`；不写时压缩模型直接报错，不会卡住。
- 动画模型用 `clip={{name, t: frame / fps}}`，内部是 `mixer.setTime`；`mixer.update(delta)` 用时钟差，每个标签页都不一样。
- 取用模型当下记进 `src/credits.ts`（CC BY 要作者、标题、许可、来源链接；删过标志写 `changed: '移除标志'`）。起步模板不带任何模型。
- `gltf_nodes.py` 按名字标出疑似标志（logo、emblem、badge、plate、decal…）；贴图上的标志名字看不出来，要渲一张看。
  2026-10-13 用 CarConcept（CC BY 4.0，未随模板分发）复测：标出了 `License Plate`、`InteriorSteeringEmblem`，与特斯拉片手工隐藏的一致；
  `replace` 换掉胎侧后侧面标志消失；Poly Haven 的分离式 glTF（外部 .bin 与贴图）照常加载。

## 大量重复件

```tsx
useLayoutEffect(() => {                       // 在 Remotion 这一帧的 advance() 之前写好矩阵
  for (let i = 0; i < started; i++) mesh.setMatrixAt(i, matrixOf(i, frame));
  mesh.count = started;                       // 还没出现的不画
  mesh.instanceMatrix.needsUpdate = true;
}, [frame, started]);
<instancedMesh ref={ref} args={[geometry, material, N]} frustumCulled={false} castShadow />
```

- 矩阵只由帧号算出；`frustumCulled={false}`：实例的包围球只按几何体算一次，散开后会被错剔。多个零件合成一次绘制用 `mergeGeometries`。

## 资料（`Archival.tsx`、`conform.py`、`media.ts`）

```bash
python3 tools/conform.py --dry-run     # 读 ../licenses/assets.json：查许可、角标署名、源文件，列出要转的
python3 tools/conform.py               # -> public/media/{photo,video}/<键>，写 src/media.ts
```

```tsx
<Sequence durationInFrames={90} layout="none">
  <Photo media="factory-1956" dur={90} push={[1, 1.03]} />            {/* Footage 同样的参数，加 from（秒） */}
  <ShotNote kind="archival" media="factory-1956" />                    {/* 资料 · 摄影 某某 · CC BY 2.0 */}
</Sequence>
const tex = useTexture(mediaUrl('patent-sheet'));                       // 场景里的实体相纸
```

- 登记表每条（`kind` 为 `photo` 或 `video`）要有 `files[0].path`、`license_id`（`CC0`、`PD`、`CC BY 2.0/3.0/4.0`、`Pexels`、`Copernicus` 之一，其余拒收）
  与 `onscreen`（角标上「资料 · 」之后的那段，作者与许可）；`key` 默认取源文件所在目录名，`use: false` 跳过，`wide` 的影像留到 3840 宽，
  `bw` 把存成彩色的黑白片按灰度处理。字段写法见 assets-and-licensing「登记」。
- 照片长边 ≤ 3840、JPEG q90；影像 H.264 CRF 18、30 fps、去音轨、长边 ≤ 1920；彩色的统一对比 ×1.04、饱和 ×0.88，灰度的不调。
- `src/media.ts` 是生成的，不手改；角标 `ShotNote kind="archival"` 与 `"stock"` 从这里取署名，CC BY 的条目另写进 `src/credits.ts` 给片尾。
- 2026-10-13 复测：生成的照片、灰度图与测试影像在 `Photo`、`Footage`（9:16 `box` 与 `fill`）和场景里的实体相纸三种用法下都正常；许可不在名单、
  缺 `onscreen`、缺源文件时 `--dry-run` 就列出并以 1 退出。

## 字体

- `tools/fetch_fonts.py` 取 Noto Serif SC、Noto Sans SC 的可变字体（google/fonts 仓库，25.1 MB、17.8 MB）与 IBM Plex Mono Regular、Medium，
  记 URL、SHA-256、大小与日期（`fonts-ofl/sources.json`），实例化出 `fonts-ofl/static/` 下的六个字重：`OFL-Serif`（宋 600）、`OFL-SerifHeavy`（宋 900）、
  `OFL-Sans`（黑 400）、`OFL-SansMedium`（黑 500）、`OFL-Mono`、`OFL-MonoMedium`。和 2026-10-12 校验过的 SHA-256 不同时保留文件、警告并以 1 退出。
- 之后基座的 `tools/bootstrap.sh` 照常抽取、按 `src/` 用到的字做子集并过 OTS（2026-10-13：六款子集 31–155 KB，全部通过）。
- `fetch_fonts.py --force` 重做之后，`fonts-src/` 里的旧字重不会自动更新：`python3 tools/fonts.py extract && python3 tools/fonts.py subset`。
- 2026-10-13 用 `--from` 从本机已有的同名文件复测（实例化与特斯拉片的 `F2-*` 字节数一致，每个约 20 秒 CPU）；下载这条路只核对了四个地址可达、大小一致。

## 标注、转场与测量

- `ShotNote`：每个镜头角落一行，16:9 右上与 HUD 章名同一行，9:16 在舞台带底部，14 px（用户长期偏好）。`kind` 为 `model`（默认，`note || '示意'`，
  不用 `??`：特斯拉片的空 `note` 让角落空了一整段，2026-10-12）、`archival`、`stock`（从 `media` 键取署名）或 `ai`（「生成画面 · 示意」）。
- `useLabelBand().y(y)`：把引线标签的 y 夹在舞台带内、字幕带之上；`project()` 钉住的标签跟着镜头走，回拉时会滑进字幕（01 章 `pin()`、03 章的写法）。
- `DissolveIn`：叠化进章。`timeline.ts` 写 `transition: 'none'` 加 `transitionFrames`，章组件的根包一层；整片入口里两块画布叠 15 帧（示例 03 章，
  2026-10-13 整片第 1046–1068 帧看过）。
- `tools/frametime.sh <id> <章内帧> [帧数] [画幅]`：全尺寸稳态单帧，同一帧起渲 N 帧与 1 帧相减再除以 N−1。
- `tools/determinism.sh <id> <起> <止> [画幅]`：并发 1 与 4 两个浏览器逐帧比，阈值见 render.md。
- 封面底图：`python3 tools/cover_3d.py` 把 `CoverPicture` 渲成底座封面读的 `public/assets/cover/ai-<比例>.png`（这个槽位名是底座定的），
  旁边的 `.json` 写 `source: 3d-still`、`ai: false`，交付报告不能把它算成 AI 生成内容；已有的付费 AI 底图默认保留，`--force` 才替换。
  然后 `tools/stills.sh covers` 看三张。画面与片中同源，不花钱；构图要给片名留出左 40%（横）或上 40%（竖）。

## 确定性与渲染

- 所有运动由 `useCurrentFrame()` 推出：不用 `useFrame` 做动画（渲染时 `frameloop` 为 never，clock 是真实时间），不用 `Math.random`、
  `Date`、`performance.now`，不用 drei `Float`、`Sparkles`、`CameraShake`、`Cloud`、`AccumulativeShadows` 与 TAA 一类时间累积效果；随机用底座 `rng(seed)`。
  `useFrame` 只用于渲染目标的收拾（`GroundShadow`）。
- `Environment` 的 `frames={1}` 只在每个标签页第一帧烘焙：画面里有东西在动就会在分块接缝处跳。
- `--gl=angle`：不写时无头 Chrome 静默退到 SwiftShader，约 5.7 秒一帧（特斯拉片基准，2026-10-12）。`remotion.config.ts` 管 CLI，
  底座 `tools/stills.mjs` 只认 `GL` 环境变量（单章静帧与 `deliver.sh covers` 走它）。`deliver.sh` 自带并发 6，三维片传 4：`tools/deliver.sh 16x9 v0.1 4`。
- 实测（2026-10-13，本机，示例片，机器负载 50–140）：全尺寸单张静帧连同开标签页 1.3–2.9 秒（每次打包后的第一张最慢），这个数不能拿来对照
  0.6 秒的预算；`tools/frametime.sh` 量的稳态单帧 01 章 0.12、03 章 0.18、04 章 0.13 秒；`deliver.sh` 整片 2100 帧 445 秒（3 块）。
  特斯拉片两种画幅各 5,211 帧、按章分 5 块渲染后无损拼接，横版 969 秒、竖版 940 秒（v0.2 交付报告）。
- 每章自检至少一次连续渲染（`tools/preview.sh <id> sheet` 或 `clip`）：拖影、对焦跑到原点这类问题单张静帧看不出来。
- 确定性用 `tools/determinism.sh`（2026-10-13 示例 03 章 26 帧最大差 0/255）。早先的复核法是片段里抽一帧与同一帧的单开静帧比：要两边缩放一致
  （`clip` 固定半尺寸、h264 CRF 24），01 章差 1.2–1.4/255、03 章 1.5–1.8/255，是编码误差。

## 已知缺口

- `Model` 的 `clip` 没有用带动画的模型实测过。
- 影像贴进三维（`@remotion/media` 的 `Video` 加 `onVideoFrame`）没有写进套件，也没有实测；`useOffthreadVideoTexture` 在 4.0.534 已标弃用。
- 没有镜头表：每个镜头手挂 `ShotNote`，覆盖整章靠联系表看；特斯拉片的 `src/shots.ts`（镜头表 + 覆盖检查）没有搬。
- HUD 墨色每章只能按 `hudAlt` 切一次；按镜头切要改基座 HUD。
- 片头接 01 章的进度轴、字体表都靠 `bootstrap_3d.py` 改基座文件；基座改了这几处的写法，补丁会对不上（脚本报 `warning` 并以 1 退出），见 skill-composition「基座待修项」。
- `fetch_fonts.py` 的下载路径只核对了地址与大小，没有整包下载复测。
