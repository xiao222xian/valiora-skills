# 渲染：版本、后端、速度与分块

三维片的渲染与基座 `lov-motion-media-creator` 共用同一套交付链（基座 `assets/starter/tools/deliver.sh`、`tools/chunks.mjs`、`tools/bundle.sh`、
`tools/preview.sh`、`tools/stills.mjs`，交付契约见基座 `references/pipeline.md` 第 7 节）。本文件只写三维多出来的部分：版本锁、GL 后端、速度、
分块与单章检查在三维里多出的要求，以及 GPU 与无头环境的限制。数字来自《如何打造一款特斯拉》（2026-10-12，Apple M3 Pro、11 核 CPU、36 GB 内存，
chrome-headless-shell 157.0.8080.0）；「特斯拉工程」路径相对 `projects/how-to-build-a-tesla/`。

## 版本锁

2026-10-12 从 npm registry 实读，2026-10-13 在特斯拉工程 `node_modules` 回读确认。全部写死版本号，不用 `^`。

| 包 | 版本 | 发布日期 | 约束 |
| --- | --- | --- | --- |
| `remotion`、`@remotion/cli`、`@remotion/three`、`@remotion/media` | 4.0.534 | 2026-10-07 | `@remotion/three` 要求 three ≥ 0.137、`@react-three/fiber` ≥ 8 |
| `three` | 0.186.1 | 2026-09-24 | `@types/three` 0.186.0 |
| `@react-three/fiber` | 9.8.1 | 2026-09-24 | react ≥ 19 < 19.4（用 19.1.0） |
| `@react-three/drei` | 10.7.9 | 2026-09-25 | fiber ^9、three ≥ 0.159 |
| `@react-three/postprocessing` | 3.2.0 | 2026-10-10 | fiber ≥ 9.7.0、postprocessing ^6.36.0；3.1.3（2026-09-27）的约束相同 |
| `postprocessing` | 6.39.5 | 2026-09-09 | three ≥ 0.168.0 < 0.187.0 |
| `react`、`react-dom` | 19.1.0 | | `typescript` 5.8.3，Node 24 |

- 升级上限：postprocessing 6.39.5 卡住 three < 0.187，fiber 9.8.1 卡住 React < 19.4。要升就整组一起升，升完在示例工程里重跑：GL 后端检查（见下文）；
  `tools/determinism.sh`；接触阴影对照 `MODULE=../dev/ShadowAB tools/preview.sh explode sheet 16x9 30 60 330`（四格结果见 `src/dev/ShadowAB.tsx` 的注释）；
  控制台里没有 `GroundShadow: three changed the depth shader`（`GroundShadow` 改 three 的深度着色器，改不上时只打这一句警告、影子变成平的剪影）；
  每章静帧与每个渲染分块的第一帧不黑（`PostWarmup`）。
- postprocessing 6.38.0 只支持 three < 0.182，配 three 0.186 时后期链输出黑屏（2026-10-12 特斯拉工程一度装错，见 [pitfalls-3d.md](pitfalls-3d.md)）。

## 渲染配置

- `remotion.config.ts`（特斯拉工程 `work/remotion/remotion.config.ts`）：

  ```ts
  Config.setChromiumOpenGlRenderer('angle');      // 不设就静默退回软件渲染
  Config.setConcurrency(4);                       // 多于 4 个标签页共用一个 GPU 进程，没有收益
  Config.setDelayRenderTimeoutInMilliseconds(120000); // 大号 HDRI、glTF 加载
  ```

- 这个文件只有 CLI 读（`npx remotion render|still|studio`，从当前目录找）。基座 `deliver.sh` 在工程根调用 `npx remotion render`，不传 `--gl`、
  `--timeout`，所以 `angle` 与 120 秒超时自动生效；它只把第三个参数当并发（默认 6），三维片传 4：`tools/deliver.sh 16x9 vX.Y 4`。
  特斯拉工程是在自己的 `deliver.sh:52-54` 里写死 `--gl=angle`。走 Node API 的脚本不读这个文件：基座 `tools/stills.mjs`（单章静帧、`deliver.sh covers`）
  只认环境变量 `GL`，基座 `tools/preview.sh` 也用 `GL` 把 `--gl` 传给 `sheet`、`clip`；起步层的 `frametime.sh`、`determinism.sh` 默认 `angle`。
- 交付后核对后端：`deliver.sh` 打印「render 16x9: N s in k chunks (video D s)」，N ÷ (D × 30) 就是每帧墙钟。GPU 约 0.08–0.25 秒一帧（特斯拉片 v0.3、
  v0.4 约 0.08；示例片 2026-10-13 机器满载时 0.21），SwiftShader 约 5.7 秒，差两个数量级，一眼分得出；交付报告写实际后端与每帧用时。
- 画布与后期链（`Stage`）：`gl={{antialias: false, preserveDrawingBuffer: true, toneMapping: THREE.AgXToneMapping}}`，`shadows="variance"`；
  `EffectComposer multisampling={0}` 加 `SMAA`；后期链后挂 `PostWarmup`。后期链让 `autoClear` 常关，画进自己渲染目标的组件自己清空：
  `GroundShadow`、drei `MeshReflectorMaterial`（这几处各对应一个坑，见 pitfalls-3d）。

## GL 后端实测

2026-10-12，macOS、Apple M3 Pro，同一个轻量三维场景（`work/research/tech-report.md:29-38`）：

| `--gl` | 结果 |
| --- | --- |
| `angle` | 可用，经 ANGLE 走 Metal，GPU 加速 |
| 不设（默认） | 退回软件渲染 SwiftShader，日志只有一句 「Automatic fallback to software WebGL has been deprecated」；4 个标签页 200 秒只出 35/120 帧，约 5.7 秒一帧 |
| `swangle` | 同上，200 秒 34/120 帧 |
| `vulkan`、`egl`、`angle-egl` | 失败：`THREE.WebGLRenderer: A WebGL context could not be created` |

Remotion 4.0 的默认值是 `null`（由 Chrome 决定），5.0 起默认 `angle`（Remotion 文档 gl-options，2026-10-13 读）。新机器或新版本先做一次检查：
全尺寸出一张轻场景静帧并计时；要好几秒的，先看是不是走了 SwiftShader。其他平台没有验证过：文档说 Linux 上用 GPU 选 `angle-egl`，
GitHub Actions 上 `angle` 会失败，Lambda 与 Cloud Run 默认 `swangle`；按上表逐个后端出一帧再定，不要沿用本表。

## 速度

### 基准

2026-10-12，独立基准工程，测试时机器上还有两个渲染在跑（负载 22–25），数字偏保守。场景：`MeshPhysicalMaterial`（带清漆）、2048 阴影贴图、
PMREM 环境光、mipmap Bloom、SMAA、暗角；heavy 是 4,416 节电芯实例化，约 110 万三角形（`work/research/tech-report.md:40-54`）。

| 测试 | 120 帧 | 600 帧 |
| --- | --- | --- |
| heavy，并发 1 | 20.9 秒 | |
| heavy，并发 4 | 16.3 秒 | 39.4 秒，约 66 ms/帧 |
| heavy，并发 8 | 15.2 秒 | 41.5 秒 |
| 再加 1024 反射地面、MSAA×4、4096 阴影，并发 4 | | 45.3 秒，约 75 ms/帧 |
| 同上，并发 8 | | 43.4 秒 |
| 竖版 1080×1920，并发 4 | 14.0 秒 | |

- 并发超过 4 没有收益：所有标签页共用一个 GPU 进程。
- 每个标签页的头几帧要 0.4–2.4 秒编译着色器；一张全尺寸静帧冷启动 1.7–5 秒（含字体与图片加载）。单张静帧的耗时因此量不出单帧成本，
  性能预算看下面的稳态单帧。

### 各章实测

2026-10-12 章节 Agent 报告：全尺寸、并发 1、扣除启动开销的稳态单帧耗时（秒），做法是同一帧起渲 30 帧与 1 帧、用时相减再除以 29
（例：片头 16:9 30 帧 7.0 秒、1 帧 5.4 秒，约 0.06 秒一帧）。当时各章在同一台机器上并行渲染，竖版数字多是上限。

| 章 | 16:9 | 9:16 | 画面 |
| --- | --- | --- | --- |
| 片头 | 0.06 | ≤ 0.37 | 整车、爆炸图、实例化紧固件 |
| 计划 | 0.20–0.24 | 0.20–0.26 | 桌面微距、实体相纸、景深 |
| 电池包 | 0.25 | 0.14 | 4,416 节电芯实例化 |
| 冲压 | 0.11 | 约 0.2 | 压机、模具、钢卷 |
| 压铸 | 0.20 | 0.26 | 压铸机、铝液、机械臂 |
| 焊装 | 0.10 | 0.23 | 白车身、6 台机械臂、火花 |
| 总装 | 0.13 | 0.13 | 吊具、AGV、glTF 厂房件 |
| 片尾 | 0.5–0.6 | 0.6–1.0（半尺寸，含启动） | 片名卡、署名卡；背景是压暗的压铸章定帧图片，首帧 1.7 秒（字体与图片加载） |

性能预算：全尺寸 16:9 稳态单帧不超过 0.6 秒，用起步层 `tools/frametime.sh <id> <章内帧> [帧数=30] [16x9|9x16]` 量（同上的做法，
从章的预览 bundle 渲，`REBUNDLE=0` 复用上次的）。2026-10-13 示例片，机器负载 50–140：01 章 0.12、03 章 0.18、04 章 0.13 秒一帧，同一批单张静帧
1.3–2.9 秒。超了就降几何细分、反射地面分辨率（`MeshReflectorMaterial` 1024）或阴影贴图（2048）。

### 整片

`deliver.sh` 打印的用时，包括打包、分块渲染、无损拼接与混入母带。片长 173.7 秒（5211 帧，30 fps），每版 5 块。

| 版本 | 画幅 | 用时 | 备注 |
| --- | --- | --- | --- |
| v0.2 | 16:9 | 969 秒 | 与 9:16 同时跑 |
| v0.2 | 9:16 | 940 秒 | 与 16:9 同时跑 |
| v0.3 | 16:9 | 426 秒 | 单独跑 |
| v0.4 | 16:9 | 431 秒 | 单独跑 |
| v0.5 | 16:9 | 只换音轨 | v0.4 母版的视频流复制、混入新母带，再 `SKIP_RENDER=1` 跑交付与质检 |

### 按成片分钟估算

| 情形 | 每分钟成片 | 依据 |
| --- | --- | --- |
| 单画幅单独跑（并发 4） | 约 2.5 分钟 | v0.3、v0.4：426–431 秒 ÷ 2.9 分钟；平均约 82 ms/帧 |
| 两个画幅同时跑 | 两版一起约 5.6 分钟（墙钟） | v0.2：969、940 秒，同时开跑 |
| SwiftShader（忘了 `--gl=angle`） | 约 2.9 小时 | 5.7 秒/帧 × 1800 帧 |
| Blender EEVEE 1080p（估算，未实测） | 约 0.5–1.5 小时 | 1–3 秒/帧 |
| Blender Cycles 128–256 spp（估算，未实测） | 约 7.5–30 小时 | 15–60 秒/帧，只适合少数英雄镜头 |

时间大头不在渲染，在搭章与返修：v0.2 的 15 段场景由多个 Agent 并行搭了几个小时（用户 2026-10-12：「大概还要多久……都做了一天了……」），
两版整片渲染合计约 16 分钟。16:9 整片重渲约 7 分钟，先用单章预览把问题修完，再跑交付。

## 分块渲染

分块、每块新起浏览器、无损拼接与母带只编码一次都是基座 `deliver.sh` 的事（基座 `references/pitfalls.md`「整片一次渲染…崩溃」）。三维片多出来的：

- Remotion 文档写明 `angle` 有已知的内存泄漏，建议长片分段渲染（gl-options，2026-10-13 读）：三维片分块是必须的，不是优化。
- 块的第一帧就是新标签页的第一帧：后期链要 `PostWarmup` 才不黑；`Environment` 的 `frames={1}`、`AccumulativeShadows` 与 TAA 一类时间累积效果
  按标签页各算一次，块与块之间对不上，有物体在动的镜头不能用。
- 所有分块出自同一个 bundle。2026-10-12 特斯拉片在第 2 块渲染途中修了共享代码（空 `note` 的标注），已渲完和正在渲的块都还是旧 bundle，
  只能停下全部重来（[pitfalls-3d.md](pitfalls-3d.md)）。
- 同时挂载的 `ThreeCanvas` 不超过 2 块（章间转场重叠时正好两块，叠化也一样）：每块画布一个 WebGL 上下文，Chrome 约 16 个就开始丢上下文；三维章节不用 premount。

## 单章预览与检查

单章预览、空 public 打包与 `cp -Rc` 的做法和原因在基座（`tools/preview.sh`、`tools/bundle.sh`，基座 `references/pitfalls.md` 第 38、39、41 行）。三维片的用法：

```bash
export GL=angle
tools/preview.sh <id> stills both 30 120 250     # 章内帧，横竖各一张（每张新开一个标签页）
tools/preview.sh <id> sheet 16x9 10              # 整章每 10 帧一格：连续渲染，拖影和对焦问题只在这里出现
tools/frametime.sh <id> 150                      # 全尺寸稳态单帧（预算 0.6 秒）
tools/determinism.sh <id> 120 150                # 并发 1 与 4 逐帧比：隐藏的时间依赖
REBUNDLE=0 tools/preview.sh <id> stills 9x16 200 # 源码没改时复用上次的 bundle
```

- 拖影、景深对焦跑到原点这类问题，静帧看起来全对，只有连续渲染才露出来：每章至少看一张 `sheet`。
- 确定性：`tools/determinism.sh` 把同一段帧分两个浏览器以并发 1 和并发 4 各渲一遍、逐帧比，最大差值不超过 24/255、差值超过 8 的像素不超过 0.1%
  （特斯拉工程 `work/remotion/tools/determinism.sh` 的阈值，起步层通用化：用 `tools/preview.sh <id> bundle` 的产物，PNG、半尺寸，需要 numpy 与 Pillow）。
  2026-10-13 示例 03 章第 190–215 帧最大差 0/255。不一致就说明有隐藏的时间依赖（`useFrame`、`Math.random`、drei 的动画组件、按标签页烘焙的效果）。
- 以黑场或叠化进入的章，单章入口里前几帧是黑的（上一章没挂载），不是故障；转场本身在整片入口里看。

## GPU 与无头环境

- 渲染时不能联网：Remotion 启动 Chrome 时带 `--no-proxy-server`，本机直连 HTTPS 会失败（2026-10-12 用 curl 不走代理复现）。drei 的默认外链在渲染时
  会卡住或超时：Draco 解码器（`https://www.gstatic.com/draco/versioned/decoders/1.5.5/`）、`Environment` 的 `preset`（`raw.githack.com`）。
  HDRI 放 `public/assets/hdri/` 用 `files` 指定，不用 `preset`；模型带 Draco 压缩时把 `three/examples/jsm/libs/draco/gltf/` 复制到 `public/draco/`，
  用 `useGLTF(url, staticFile('draco/'))` 指过去（drei 10.7.9 `core/Gltf.js` 的第二个参数为字符串时就是解码器路径）。
- 加载：`useGLTF`、`useTexture`、`Environment files` 走 Suspense，会自动 `delayRender`；手写的 `TextureLoader`、`fetch` 要自己 `delayRender`。
  大号 HDRI、glTF 靠 120 秒超时兜住。
- 时钟：`ThreeCanvas` 渲染时把 `frameloop` 设为 `never`，每帧调一次 `advance(performance.now())`，所以 `useFrame` 拿到的 clock 和 delta 是真实时间
  （`@remotion/three` 源码核实，2026-10-12）。动画只从 `useCurrentFrame()` 推（[style-grammar-3d.md](style-grammar-3d.md)「运动」）。
- `<ThreeCanvas>` 里面的 `<Sequence>` 要写 `layout="none"`。
- 阴影：three 0.186 去掉了 `PCFSoftShadowMap`，R3F 的 `shadows` 默认值退回 PCF（日志有警告）；`Stage` 用 `shadows="variance"`，地面接触阴影用套件
  `GroundShadow`，不用 drei `ContactShadows`（见 pitfalls-3d）。
- 机器共用：所有标签页共用一个 GPU 进程，别的渲染会拖慢它（2026-10-12 各章并行时，一次 2 帧的渲染用了 19 秒）。重渲染错开时间，预览的 `CONC` 用 2。
- Blender 不在默认链路里（特斯拉片没用）。只在两种情况考虑：素材整理（FBX/.blend 清理、减面、烘焙后导出 glTF），或实时光栅化做不像的 2–3 个英雄镜头
  （EEVEE 渲染 → ProRes 422 HQ → `<OffthreadVideo>`）。2026-10-12 Homebrew 的 `blender` 是 5.2.2（DMG 346 MB）；5.0 起引擎 ID 改为 `BLENDER_EEVEE`，
  `ImageFormatSettings` 要先设 `media_type` 再设 `file_format`；无头模式下能否用上 Metal 没有验证，装好先渲 1 帧测。
