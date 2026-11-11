# 三维图志 · 3D Motion Atlas

![Version](https://img.shields.io/badge/version-0.1.1-CC785C)

无实拍，用实时三维渲染把一道工序、一件产品的构造或一个尺度做成产品片质感的分章短片：实物 PBR 材质、有光源的低调布光、物理镜头、重物的重量；三维重建的画面标「示意」，人物、历史与现场交给真实照片和影像（标「资料」）。沿轴分章、章节标题卡与进度轴 HUD、旁白与大字幕、分章配乐卡点、事实核查、三比例封面、交付报告与发布交接单都由依赖 `lov-motion-media-creator`（动态图志）完成，本 Skill 只加三维这一层。`lov-film` 片型套件的第二个成员，做法来自《如何打造一款特斯拉》（2026-10-12）。

## 安装

本 Skill 与依赖的 `lov-motion-media-creator`、`lov-branding-consistency` 均包含在 Lovstudio.AI VIP Membership 全套权益中，不单独定价、不兑换 Credits。会员权益不包含 GPU、渲染时间或 TTS、AI 配乐、AI 封面等第三方服务费用；源码仓库保持私有。

```bash
npx skills add lov-3d-motion-media-creator -g -y
```

还要装基座 `lov-motion-media-creator`（`npx skills add lov-motion-media-creator -g -y`）：每个工程都从它的起步模板复制，共享流水线的工具也是它的。

## 你会得到

- 成片、16:9 / 4:3 / 3:4 三张封面、交付报告与发布交接单：形态同基座，默认只出 16:9，用户点名时加出 9:16。
- 一个带三维层的 Remotion 工程：场景套件（`Stage` 与物理机位、三维点到屏幕的投影、按帧可复现的震动、18 种 PBR 材质、融进背景的地面与倒角块、地面接触阴影、面光源与投影灯、带逆运动学的六轴机械臂、通用 glTF 加载与去标志），资料的满幅窗口与统一调色脚本，三款 SIL OFL 字体，`--gl=angle` 与并发 4 的渲染设置，稳态单帧测量与确定性比对脚本。
- 示例片《齿轮箱》（70 秒、6 章）：程序化齿轮箱拆解与引线标注、十种材料、机械臂取放、1,200 台批量、片名卡；不含品牌、模型与贴图文件。
- 贴图与 HDRI 由脚本从 ambientCG、Poly Haven 取（CC0），每份写来源旁注并登记进署名表；glTF 节点检查脚本标出疑似标志。
- 每章静帧、联系表与片段，按三维伪影清单逐张检查。

## 用法示例

- 「用三维讲一遍一台电动工具从零件到整机的装配」
- 「这条动态图志太幼稚了，改成三维，必要时配真实的照片和影像」
- 「做一条三维科普片：一颗芯片从晶圆到封装」
- 「齿轮箱的爆炸图动画，零件逐个拆开，每个都要标注」
- 「这章的阴影有拖影，金属看着像镜子，修完重渲」
- 「补出 9:16 竖版，每个镜头单独给机位」
- 「封面用片里的三维定帧，不花钱」
- "Make a 3D motion atlas of how a bicycle is built"

## 依赖

- 必需：`lov-motion-media-creator`（按 0.9.0 编写）及它的全部依赖：Node 24+、pnpm、Remotion 4、Python 3.9+、ffmpeg / ffprobe；旁白、配乐与 AI 封面底图的可选密钥照基座，只从环境变量读。
- 必需：`lov-branding-consistency`（上屏文字、标注、署名与封面文字的品牌门禁）。
- 三维包，整组锁定：`three` 0.186.1、`@react-three/fiber` 9.8.1、`@react-three/drei` 10.7.9、`@react-three/postprocessing` 3.2.0、`postprocessing` 6.39.5、`@types/three` 0.186.0；`@remotion/three` 跟底座的 `remotion` 同版本（4.0.534）。postprocessing 6.39.5 要求 three < 0.187，fiber 9.8.1 要求 React < 19.4，不单独升级。
- 能跑 WebGL 的 GPU：macOS 用 `--gl=angle`（2026-10-12 实测；不设后端会静默退到软件渲染，约 5.7 秒一帧）。其他平台先实测出可用的后端。
- 第一次取贴图要联网；渲染时不联网，HDRI、模型与 Draco 解码器都放在 `public/`。

## 质量门禁

- 基座的门禁全部照旧：画面不展示制作技术、字号下限、事实台账、节拍相位、章节时间轴、片尾署名卡、三比例封面、从编码文件回读的交付质检。
- 一切运动由帧号推出，同一帧在连续渲染与单开静帧里一致。
- 没有三维伪影：黑帧、未打光、缺失或占位贴图、z-fighting、阴影拖影、对焦跳到原点；每章至少看过一张连续渲染的联系表。
- 三维画面标「示意」，资料标「资料 · 作者 · 许可」；真实品牌的标志只出现在纪录性质的资料照片里。
- 贴图、HDRI、模型取用当下登记来源与许可，只用 CC0、公有领域、Pexels 与 CC BY；转场只用剪辑手法。

```bash
python3 scripts/validate_skill.py .
```

## Profile

读取共享 `user-profile/v1`。品牌、Logo、印章、默认画幅、旁白等片子级记录读基座的 `skills.lov-motion-media-creator.records`，在这里说出时也写回那里；本 Skill 只存四条三维记录：`render_backend`、`render_concurrency`、`texture_library`、`brand_marks`。用户明确说出的长期偏好用 `scripts/profile_store.py record ... --confirm` 保存。详见 [`references/user-profile.md`](references/user-profile.md)。

## 本地开发

源目录 `3d-motion-media-creator-skill`，安装入口 `lov-3d-motion-media-creator`。在本仓库根目录把源目录链接到本机的 Skills 目录：

```bash
export SKILL_SOURCE_DIR="$(pwd)"
ln -s "$SKILL_SOURCE_DIR" "${SKILL_SKILLS_INSTALL_DIR:?请设置本地 Skills 目录}/lov-3d-motion-media-creator"
```

- 同时改基座时，用 `MOTION_MEDIA_CREATOR_DIR=<基座源目录>` 或 `scripts/bootstrap_3d.py --base` 指向它的源目录。
- 改了 `assets/starter-3d/` 或 `scripts/bootstrap_3d.py` 后，在临时目录从头复测：`bootstrap_3d.py` → `pnpm install` → `tools/fetch_textures.py` → `tools/fetch_fonts.py` → `tools/bootstrap.sh` → `npx tsc --noEmit -p .` → `node tools/chapters.mjs` → 每章 `tools/preview.sh <id> stills both …` 与一张 `sheet`、`tools/determinism.sh`，逐张看图；动了阴影或三维依赖时加跑 `src/dev/ShadowAB.tsx`。
- 贴图、HDRI、模型与渲染产物不进仓库：起步层只带取用脚本与清单。

## License

MIT
