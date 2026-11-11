# 三维踩过的坑

《如何打造一款特斯拉》v0.2–v0.5 制作中实际踩到的三维问题（2026-10-12），以及 2026-10-13 搭起步层时复测、新踩到的。「证据」一栏指向修好它的文件与行号，
特斯拉片的路径相对它的工程根目录 `projects/how-to-build-a-tesla/`，其中 Remotion 工程 `work/remotion/` 在表里简写为 `remotion/`；「章节 Agent 报告」
指当天各章制作 Agent 交回的问题清单；「起步层」指本 Skill 的 `assets/starter-3d/`。
不分片型的坑（字体、整片一次渲染崩溃、元数据里的工具名、空 public 打包、软链接、单章入口、`??` 与 `||`、配乐、封面、署名卡）在基座
`lov-motion-media-creator` 的 `references/pitfalls.md`，这里只留指针和三维片里的现象。标「亦见基座」的行两边都有，规则以基座为准；
例外是 `ContactShadows` 拖影一行：基座 `pitfalls.md` 第 35 行的修法复测有效，但没写放置高度这个坑，三维片也不用 `ContactShadows`，以本文件为准。

## 环境与版本

| 现象 | 根因 | 做法 | 日期 | 证据 |
| --- | --- | --- | --- | --- |
| 三维场景渲染极慢，约 5.7 秒一帧；日志里只有一句「Automatic fallback to software WebGL has been deprecated」 | 不指定 GL 后端时 headless Chrome 静默退回软件渲染 SwiftShader | `remotion.config.ts` 设 `Config.setChromiumOpenGlRenderer('angle')`；走 Node API 的脚本另传 `gl: 'angle'`（基座 `tools/stills.mjs` 用 `GL=angle`）。基座 `deliver.sh` 走 CLI、在工程根运行，读得到这个配置，不用另传（特斯拉工程是在自己的 `deliver.sh` 里写死 `--gl=angle`）；交付后按每帧用时核对（[render.md](render.md)「渲染配置」） | 2026-10-12；2026-10-13 起步层复测 | `remotion/remotion.config.ts:3-7`；`remotion/tools/stills.mjs:9`；`remotion/tools/deliver.sh:52`；`work/research/tech-report.md:29-38`；起步层示例片 `deliver.sh` 整片 2100 帧 445 秒（3 块），约 0.21 秒一帧（2026-10-13，机器满载） |
| `--gl=vulkan`、`egl`、`angle-egl` 报 `THREE.WebGLRenderer: A WebGL context could not be created` | macOS 上的 chrome-headless-shell 157 不支持这几个后端 | macOS 只用 `angle`；别的平台逐个后端出一帧再定（[render.md](render.md)「GL 后端实测」） | 2026-10-12 | `work/research/tech-report.md:29-36` |
| 后期链输出黑屏 | 一度装的 postprocessing 6.38.0 只支持 three < 0.182，工程是 three 0.186.1 | 整组锁版本：postprocessing 6.39.5（three ≥ 0.168 < 0.187）、`@react-three/postprocessing` 3.2.0；升级时整组一起升 | 2026-10-12 | `remotion/package.json:10-22`；`work/research/tech-report.md:21-27`；`HANDOFF-v0.2.md:58-59` |

## 后期链与渲染状态

| 现象 | 根因 | 做法 | 日期 | 证据 |
| --- | --- | --- | --- | --- |
| 每个新标签页的头一两帧是黑的：`remotion still` 单帧导出、单章预览静帧、每个渲染分块的第一帧 | `EffectComposer` 在 Remotion 每帧唯一一次 `advance` 之后才建好各个 pass | 后期链之后挂 `PostWarmup`：标签页第一帧扣住截图，隔两个 animation frame 各 `advance` 一次再放行，之后每帧再 `advance` 一次；扣住要在 `useEffect` 里拿，不在 render 里拿（同级的模型、HDRI 一挂起，没提交的 render 会被丢掉） | 2026-10-12 | `remotion/src/three/PostWarmup.tsx:5-35`；`remotion/src/three/Stage.tsx:96`；`HANDOFF-v0.2.md:60` |
| 画布开抗锯齿时后期链输出出错；关掉后边缘锯齿 | 多重采样的画布会破坏后期链的输出，而后期链本身让画布的 antialias 失效 | 画布 `antialias: false`，`EffectComposer multisampling={0}`，抗锯齿交给链里的 `SMAA` | 2026-10-12 | `remotion/src/three/Stage.tsx:73-74,90-91`；`work/research/tech-report.md:104` |
| `ContactShadows` 在连续渲染（联系表、片段、成片）里留下拖影：运动物体的影子一帧帧叠在一起；单开标签页出的静帧却正常，所以很容易漏 | drei `ContactShadows` 画进自己的渲染目标且不清空，后期链又把渲染器的 `autoClear` 关掉 | 现行做法：套件 `GroundShadow`，每个渲染目标自己清空，不碰全局 `autoClear`，模糊以米计。特斯拉片的修法是 `ClearBeforeComposer`（`useFrame` 优先级 -1 把 `gl.autoClear` 设为 true，0.5 设回 false）：2026-10-13 复测有效，影子在、没有拖影，但每帧翻一次渲染器的全局状态，套件不用它。同一天早些时候一次复测记成「这个修法让影子整个消失」，那次没留下可复跑的测试，这次复现不了，作废；下一行的放置高度问题也会让影子消失，容易误读成同一件事。每章至少看一张连续渲染的联系表（`tools/preview.sh <id> sheet`），不能只看静帧；升级三维依赖后重跑 `src/dev/ShadowAB.tsx` | 2026-10-12；2026-10-13 复测 | `remotion/src/three/Stage.tsx:38-50,88`、`remotion/src/scenes/plan/Shadows.tsx:5-18`（特斯拉片）；起步层 `src/three/GroundShadow.tsx`、`src/dev/ShadowAB.tsx`（滑动方块四格对照：`GroundShadow` 脚下压暗到约 131/255、无拖影；`ContactShadows` 在后期链下拖影 118–156；加 `ClearBeforeComposer` 约 127、无拖影；无后期链约 97；地面 160–165） |
| 站在地上的物体没有接触阴影，有没有后期链都一样 | `ContactShadows` 的相机放在 `position` 的高度、朝上拍；特斯拉片多数写成 `position={[0, 0.002, 0]}`，物体底面（y = 0）在相机下方，拍不到 | 用 `GroundShadow`：物体站在接触面 y = 0，相机在接触面下 1 mm，地面再低 2 mm（`FLOOR_Y`）。还用 `ContactShadows` 时把它放在接触面以下 | 2026-10-13 | 起步层 `src/dev/ShadowAB.tsx` 的 `ContactShadows` 改到 +2 mm：四种接法里方块脚下都不压暗（159/255，与空地面相同）；特斯拉片 `remotion/src/scenes/test/shots.tsx:166,297,377` 等处为 0.002，v0.5 成片 4432 帧车驶出时车底看不出接触阴影（逆光过曝，只能作旁证） |
| 有物体在动的镜头，在不同标签页、不同分块之间接触阴影或反射对不上，接缝处闪一下 | `ContactShadows`、`Environment` 用 `frames={1}` 时只在每个标签页的第一帧烘焙一次（原型 `Proto3D` 里电芯在上升，阴影却 `frames={1}`） | 有东西在动就不用 `frames={1}`；反射要扫动时转 `envRotation`，灯本身要动时每次提交从发光面板重新拍一次环境立方体 | 2026-10-12 | `work/research/tech-report.md:99-102`；`remotion/src/scenes/opening/env.tsx:23-35` |
| 改了 `post.dof.focalLength` 的镜头，在连续渲染里整段焦点不对（对在世界原点），静帧却对；让 `focalLength` 随帧变化时每帧都重建景深效果 | `focalLength` 变了就重建 `DepthOfField`，新效果在 `target` 的值再变化之前一直对焦在原点 | 对焦范围要变就换一块 `Stage`（一镜一块），不在一块 `Stage` 里动 `focalLength`。共享的 `Stage` 还没修，仍把 `focalLength` 直接传给效果 | 2026-10-12 | 01、05 章 Agent 报告；未修处：`remotion/src/three/Stage.tsx:92` |

## 材质与光

| 现象 | 根因 | 做法 | 日期 | 证据 |
| --- | --- | --- | --- | --- |
| 拉丝铝、钢、镀锌板一类金属全部渲染成镜面，`roughness` 填多少都没用 | ambientCG `Metal050A` 的粗糙度贴图几乎全黑：均值 0.055，范围 0.03–0.09；three 的 `roughness` 只是乘在贴图上的系数 | 把贴图本身重映射到 0.24–0.40（保留拉丝纹理），原图另存 `*-original.jpg`，重映射后复测（均值约 0.30）；新贴图用前先量均值（同批实测：`Metal051A` 0.18、`Metal047A` 0.26、`Rubber004` 0.59、水泥 0.75、皮革 0.62）。修完抽看已调好的章节静帧，它们原先是按镜面调的光。亦见基座 | 2026-10-12 | `remotion/public/assets/tex3d/metal050a_roughness.jpg`（重映射后）与 `work/assets/models/ambientcg-metal050a-metal009---aluminum-brushed-steel/metal050a_roughness-1k-original.jpg`（原图）；材质表 `remotion/src/three/kit.tsx:16,48-53`；08 章修复前的本地绕法 `remotion/src/scenes/weld/mats.ts:7-34`（换用水泥粗糙度贴图，`roughness` = 目标均值 ÷ 0.81） |
| 逐材质设的 `envMapIntensity` 不起作用：地面和小件要比车漆少一些反射，调不下来 | three 0.186 只在材质自己带 `envMap` 时用 `material.envMapIntensity`；用 `scene.environment`（`Stage` 的 HDRI 或 `StudioEnv`）时一律用 `scene.environmentIntensity` | 全局反射强度用 `Stage` 的 `envIntensity`；要逐材质控制，自己持有环境立方体目标，显式给材质 `envMap`。起步层的 `useMat` 已去掉 `envMapIntensity` 选项（2026-10-13），免得再踩 | 2026-10-12（片头章发现）；2026-10-13 在 three 源码核实 | `remotion/src/scenes/opening/env.tsx:5-35`；three 0.186.1 的 `src/renderers/webgl/WebGLMaterials.js:403-409`、`src/renderers/WebGLRenderer.js:2736-2740` |
| 地面上出现成块、成带的阴影伪影 | three 0.186 去掉了 `PCFSoftShadowMap`，`Stage` 改用 VSM（`shadows="variance"`）；大块地面在投影聚光灯下用 VSM 会起带 | 接触阴影用套件 `GroundShadow`；有投影聚光灯时 `StudioFloor receiveShadow={false}` | 2026-10-12 | `remotion/src/three/kit.tsx:174-175`（加了 `receiveShadow` 开关）；`remotion/src/three/Stage.tsx:72`；05 章 Agent 报告；`work/research/v02-builder-brief.md:123` |
| 面光源打反了方向，照不到要照的东西；面光源下没有阴影 | `rectAreaLight` 沿本地 −Z 发光，而 `Object3D.lookAt` 把 +Z 转向目标；面光源本身不投阴影 | 用套件 `AreaLight`（`Matrix4.lookAt` 求朝向，加载时 `RectAreaLightUniformsLib.init()`）；阴影交给同位置一盏投影聚光灯（套件 `ShadowSpot`） | 2026-10-12 | 起步层 `src/three/lights.tsx`；特斯拉片 `remotion/src/scenes/stamp/rig.tsx:44-50`、`remotion/src/scenes/assembly/light.tsx:3-19,22` |
| 远景与竖版镜头里，地面的远边成了一条硬地平线，上面是一片黑；3:4 封面的地平线横穿片名下沿 | 地面只有 20–60 m 宽，竖版视场高、低机位时远边落在画面里；近黑背景下，掠射角反射照亮的远处地面和背景之间是一条直线 | 地面做大（套件 `StudioFloor`、`ConcreteFloor` 默认 400 m），`Stage` 默认加雾（`fog` = [6, 40] m，颜色就是 `bg`），地面在远边之前融进背景；远处还有主体的镜头把雾起点放到最远主体之后（示例 03 章 [9, 45]、04 章 [28, 100]）。竖版和封面机位都要看一张 | 2026-10-13 | 起步层复测：04 章 16:9 第 250、355 帧、03 章 9:16 第 60 帧、01 章 9:16 第 150 帧、3:4 封面，改前都有地平线，改后没有；`src/three/Stage.tsx` 的 `FOG` |

## 几何与模型

| 现象 | 根因 | 做法 | 日期 | 证据 |
| --- | --- | --- | --- | --- |
| 机械臂肩部闪烁的条纹（z-fighting） | 肩部转鼓的端面与转台壳体的侧面都在 z = ±0.25，两面共面 | 转鼓加长到 0.52（壳体 0.5），端面错开 1 cm；相邻件的面一律错开，不共面。07 章先在本地遮住过 | 2026-10-12 | `remotion/src/three/RobotArm.tsx:129-132`；07 章 Agent 报告 |
| 主角车上出现示例资产的标志：车牌、方向盘徽标、胎侧文字 | Khronos CarConcept 示例模型自带 Khronos 与 3D Commerce 标志（不在 CC BY 授权内） | 隐藏节点 `License Plate`、`InteriorSteeringEmblem`，`Tireside` 材质换素面橡胶；署名的改动说明写上（[assets-and-licensing.md](assets-and-licensing.md)） | 2026-10-12 | `remotion/src/three/Car.tsx:6-10,44,50-52` |
| 部分 Poly Haven 模型 `useGLTF` 报错 | 下载时连 `dl.polyhaven.org` 多次 `SSL_ERROR_SYSCALL`（TLS 握手失败），6 个模型的 `textures/` 不全 | 下载脚本可重复运行、只补缺；用前检查 `textures/` 是否齐全，不齐就换程序化做法 | 2026-10-12 | `HANDOFF-v0.2.md:39-42`；`work/licenses/fetch3.log`；`work/research/v02-builder-brief.md:62-63` |
| 一次预览日志报 `ERR_CONTENT_LENGTH_MISMATCH`（`overhead_crane.bin`），画面却渲染正常 | 原因没查明，没有复现（当时多章在并行预览）；文件完好，3,022,220 字节，与 glTF 的 `byteLength` 一致 | 重跑一次；核对文件大小与 glTF 里 buffer 的 `byteLength`，一致就不用处理 | 2026-10-12 | 10 章 Agent 报告；`remotion/public/assets/ch-assembly/overhead_crane/overhead_crane.bin` |

## 叠加层与标注

| 现象 | 根因 | 做法 | 日期 | 证据 |
| --- | --- | --- | --- | --- |
| 片头接 01 章时，底部进度轴有 2 帧半透明（50%、75%），还露出片头的读数「工序 00 / 04」 | 片头的光线在 01 章首帧落成进度轴底线（片头没有尾巴），基座 HUD 却从首帧前 2 帧起线性淡入 4 帧，那两帧当前章还是片头 | HUD 从第一章起点帧直接全不透明显示：`show = frame < RULER_START ? 0 : …`。`bootstrap_3d.py` 复制基座 `HUD.tsx` 时改这一行；它报这条补丁没对上时手改 | 2026-10-12；2026-10-13 起步层复现并修 | 特斯拉片 `remotion/src/components/HUD.tsx:70-72`、片头章 Agent 报告；起步层改前成片第 328–329 帧可见，改后 326–329 帧只有片头的光线、330 帧整条进度轴 |
| 06 章三维镜头右上角的「示意」没有出现，标注行空白 | 镜头表的 `note` 填了 `''`，`??` 不回退 | 规则见基座 `pitfalls.md`「备注字段填了 `''`」；套件 `ShotNote` 写的是 `note \|\| '示意'`。三维片的代价更大：发现时成片第 2 块正在用旧 bundle 渲染，只能停下、改源码、重新打包、整片重渲。亦见基座 | 2026-10-12 | `remotion/src/shots.ts:56` |
| 涂装章漆层特写回拉的 0.5 秒里，引线标签滑进字幕带，和字幕交叠 | 用 `project()` 钉在三维点上的标签跟着镜头走，回拉时一起往下掉；二维片的标注是静止的，基座不管这一条 | 标签 y 夹在舞台带内、字幕带（16:9 约 y 845–952）之上：起步层 `scenes/common.tsx` 的 `useLabelBand().y()`，引线照样连到三维点。镜头移动的整段用 `sheet` 看，不只看静帧 | 2026-10-12 | v0.3 交付报告「需要你留意」；特斯拉片修法是夹住标签 y（会话记录：「Paint callouts collided with subtitles → clamped label y」）；起步层 `src/scenes/S01Explode.tsx` 的 `pin()` |
| 计数中的大数字左右抖 | 思源宋体（Noto Serif SC）的数字不等宽，也没有 `tnum`：「1」宽 473、其余约 540（字体单位），`tabular-nums` 对它无效 | 计数中的大数字用思源黑体（Noto Sans SC 的数字等宽 521）或 IBM Plex Mono；落定不动的大数字可以用宋体 | 2026-10-13 | fontTools 读 Noto Serif SC 2.003、Noto Sans SC 2.004 的 hmtx 与 GSUB；特斯拉片 `remotion/src/components/Overlay.tsx:172` 用的是宋体加 `tabular-nums`；起步层 04 章 `BigNumber font="OFL-SansMedium"` |

## 打包与预览

| 现象 | 根因 | 做法 | 日期 | 证据 |
| --- | --- | --- | --- | --- |
| 每章单独预览各打一次包，磁盘很快被占满；`public` 换成软链接后字体 404；一章出错所有人的预览都失败 | 规则见基座 `pitfalls.md` 的空 public 打包、软链接、单章入口三行（第 38、39、41 行）（`tools/bundle.sh`、`tools/preview.sh` 已封装）。三维片的量级：特斯拉片 `public/` 1.1 GB（资料影像 786 MB、三维资产 205 MB、音频 143 MB），15 章并行时机器只剩约 24 GiB | 照基座。亦见基座 | 2026-10-12 | `remotion/tools/preview.sh:2-4,19-32`；`remotion/tools/deliver.sh:42-46`；`du`（2026-10-13） |
| 单章入口里，以黑场或叠化进入的章前几帧全黑 | 上一章没有挂载，转场的前几帧本来就只有黑底 | 不是故障；从转场结束后几帧开始看（特斯拉片 07 章以 6 帧黑场进入，约第 4 帧起可见；示例 03 章叠化 15 帧）；转场本身在整片入口里看 | 2026-10-12 | 07 章 Agent 报告；`remotion/src/timeline.ts:105` |

## 没踩到、但已核实的预防规则

下面这些没有在成片里出过事，是开工前从源码、文档或实测确认的，规则写在 [render.md](render.md) 与 [style-grammar-3d.md](style-grammar-3d.md)：

- `useFrame`、drei 的 `Float`、`Sparkles`、`CameraShake`、`Wobble`/`Distort`、glTF 的 `mixer.update(delta)`、postprocessing 的 `Noise`/`Glitch` 读真实时间，
  渲染结果不确定（`@remotion/three` 与 drei 源码核实，`work/research/tech-report.md:89-92`）。时间累积类效果（drei `AccumulativeShadows`、TAA）
  按标签页各算一次，和 `frames={1}` 一样会在分块接缝处跳（`work/research/tech-report.md:102`）。确定性比对：起步层 `tools/determinism.sh`
  （2026-10-13 示例 03 章 26 帧最大差 0/255）。
- 影像贴进三维要按帧取：drei `useVideoTexture` 和 `<video>` 元素纹理是实时播放；`@remotion/three` 的 `useOffthreadVideoTexture` 在 4.0.534 的类型声明里已标弃用，
  指向 Remotion 文档 videos/as-threejs-texture（`@remotion/media` 的 `Video` 加 `onVideoFrame` 画进画布纹理）。本片没有用过，用前先过 `tools/determinism.sh`。
- 渲染时不能联网，drei 默认外链的 Draco 解码器与 `Environment preset` 会卡住或超时（`work/research/tech-report.md:95-98`）。
- `<ThreeCanvas>` 里的 `<Sequence>` 要 `layout="none"`；同时挂载的 `ThreeCanvas` 不超过 2 块，三维章节不 premount（`work/research/tech-report.md:94,106`）。
- 并发超过 4 没有收益（实测，`work/research/tech-report.md:44-53`）；`angle` 有已知内存泄漏，长片分块渲染（Remotion 文档 gl-options）。
