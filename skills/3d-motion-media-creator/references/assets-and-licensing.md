# 素材与授权（三维）

署名表 `src/credits.ts`、片尾署名卡、简介署名块与 AI 生成内容清单的写法都在基座 `lov-motion-media-creator`：`references/fact-and-disclosure.md`
「片尾署名」「AI 生成内容清单」与 `references/publish-handoff.md`「署名块」。本文件只写三维片多出来的部分：贴图、HDRI 和模型从哪里来、什么许可能用、
怎么登记、改了什么要怎么写，以及品牌标识怎么挡在画面外。实例来自《如何打造一款特斯拉》（2026-10-12），「特斯拉工程」路径相对 `projects/how-to-build-a-tesla/`。

## 许可允许名单

特斯拉片 2026-10-12 用户拍板的口径，作为默认：

| 许可 | 能否用 | 署名 |
| --- | --- | --- |
| CC0、公有领域 | 能 | 不要求；可在片尾「其余资料」一行致谢 |
| Pexels 许可（照片、影像）、Pixabay 内容许可（音效） | 能，逐条读许可页的禁止项 | 不要求 |
| CC BY 2.0 / 3.0 / 4.0 | 能 | 必须：片尾署名卡逐条写，改过的写改动说明；照片、影像另在逐镜标注行写作者与许可 |
| SIL OFL 1.1（字体） | 能 | 不上屏；交付报告里写字体与许可（`tools/fetch_fonts.py` 记在 `fonts-ofl/sources.json`） |
| CC BY-SA（任何版本） | 不用 | 调色、裁切、贴进三维都可能构成改编，ShareAlike 可能要求整片以 BY-SA 发布；特斯拉片 12 项一项没用 |
| NC、ND，或许可写不清的 | 不用 | 默认如此，没有在本片评估过 |
| 新闻机构素材 | 不用 | 特斯拉片剔除了作者字段为「中国新闻网」的开工视频（2026-10-12 用 Commons API 复核） |

## 登记

取材当下逐条登记，一份素材一条（特斯拉工程 `work/licenses/assets.json`，131 条）：

- 标题、页面 URL、文件 URL、许可（照抄页面上的写法，并写明在哪里核实的，例：「CC BY 4.0（README Legal 段）」）；
- 许可要求的署名原文（`credit`），改动了什么；
- 取用日期、文件路径、字节数、SHA-256；
- 是否含被讲品牌的标识（起步层用 `is_brand`，特斯拉工程用 `is_tesla`），方便审计品牌在哪些画面出现。
- 资料照片与影像另写 `tools/conform.py` 要的几项：`kind`（`photo` 或 `video`）、`license_id`（`CC0`、`PD`、`CC BY 2.0`、`CC BY 3.0`、`CC BY 4.0`、
  `Pexels`、`Copernicus` 之一，`license` 照旧照抄原文）、`onscreen`（角标上「资料 · 」之后的那段，只写作者与许可，例「摄影 Steve Jurvetson · CC BY 2.0」），
  可选 `key`（片中用的键名，默认源文件所在目录名）、`use: false`（登记了但不用）、`wide`、`bw`。

登记表放在 `work/licenses/assets.json`（`conform.py` 默认读这里，文件路径相对 `work/`）。上屏的署名再从这张表抄进 `src/credits.ts`（基座的署名表，
片尾署名卡与简介共用）；资料镜头的角标由 `ShotNote kind="archival"` 从 `conform.py` 生成的素材目录 `src/media.ts` 取，和登记表同源
（[style-grammar-3d.md](style-grammar-3d.md)「资料」「标注与 HUD」）。

## CC0 贴图与 HDRI：ambientCG、Poly Haven

- ambientCG：全部素材为 CC0 1.0，不要求署名，作者欢迎注明，建议写法「Created using <asset name> from ambientCG.com, licensed under the
  Creative Commons CC0 1.0 Universal License」（docs.ambientcg.com/license，2026-10-13 读）。取文件：
  `https://ambientcg.com/api/v2/full_json?id=<ID>&include=downloadData` 列出各分辨率的下载链接，形如 `https://ambientcg.com/get?file=<ID>_1K-JPG.zip`
  （`Metal050A` 的 1K-JPG 2.6 MB、2K-JPG 6.8 MB，2026-10-13）。包里用 `_Color`、`_Roughness`、`_NormalGL`，不用 `_NormalDX`。
- Poly Haven：全部 HDRI、贴图、模型为 CC0，不要求署名，欢迎注明（polyhaven.com/license，2026-10-13 读）。取文件：`https://api.polyhaven.com/files/<id>`
  按分辨率列出文件；贴图用 `*_diff`、`*_rough`、`*_nor_gl`，HDRI 用 `*_2k.hdr`，模型是 `*_2k.gltf` + `.bin` + `textures/`。
- 特斯拉片用过的：ambientCG `Metal050A`、`Metal051A`、`Metal047A`、`Rubber004`；Poly Haven 的水泥、皮革贴图，6 张 2K HDRI（studio_small_09、
  cyclorama_hard_light、aircraft_workshop_01、autoshop_01、modern_buildings_night、shanghai_bund），以及 covered_car、overhead_crane、mounted_fluorescent_lights、
  modular_industrial_pipes_01、modular_factory_facade、circuit_board、industrial_storage_cart、portable_welding_cart 等模型；Khronos `ClearCoatCarPaint`（CC0）
  只取它的车漆金属片法线。
- 自托管：贴图放 `public/assets/tex3d/`（特斯拉片把 ambientCG 的金属、橡胶从 2K 包缩到 1K，`sips -Z 1024`；铺大面积地面的水泥贴图留 2K），
  HDRI 放 `public/assets/hdri/`，模型放 `public/assets/models/<名>/`。起步层不带这些文件，由脚本按清单去取，不进 git。
- 用前检查：Poly Haven 模型的 `textures/` 是否下齐（2026-10-12 连到 `dl.polyhaven.org` 多次 `SSL_ERROR_SYSCALL`，6 个模型的贴图要重试几轮才补齐，缺图时 `useGLTF` 会报错）；粗糙度贴图的均值
  （`Metal050A` 只有 0.055，见 [pitfalls-3d.md](pitfalls-3d.md)）。改过的贴图另存原图（`*-original.jpg`），在登记表写一句改了什么；CC0 不要求说明，留档是为了能复原。
- 署名：CC0 不进逐镜标注，片尾按基座的 `otherLine()` 合成一行致谢（`CREDITS` 里 `license: 'CC0'`，作者可写 `ambientCG`、`Poly Haven`）。

## CC BY 的 glTF 模型：以 CarConcept 为例

CarConcept 是特斯拉片的主角车，也是全片唯一一份需要署名的三维模型（2026-10-12）。

- 来历（README Legal 段，2026-10-13 读）：Khronos glTF Sample Assets，© 2024 Darmstadt Graphics Group GmbH，模型与贴图作者 Eric Chadwick，CC BY 4.0；
  源自 Unity Fan 的公有领域模型「FREE Concept Car 004」。车上的 Khronos 标志与 3D Commerce 标志 © Khronos Group，按 Khronos 商标条款授权，
  不在 CC BY 之内。GLB 11.8 MB。
- 标志在哪里（特斯拉工程 `work/remotion/src/three/Car.tsx:6-10,44,50-52`）：节点 `License Plate`（车牌）、节点 `InteriorSteeringEmblem`（方向盘徽标）、
  材质 `Tireside`（胎侧贴图带标志）。前两个隐藏，胎侧换成素面橡胶。换别的模型时按名字搜一遍节点和材质（`logo|emblem|badge|plate|<品牌名>`），
  再从四周和近处各渲几张静帧确认。
- 署名：片尾一条「Eric Chadwick, © 2024 Darmstadt Graphics Group · CarConcept · CC BY 4.0」，后接改动说明「以上素材均经修改」；CC BY 4.0 要求注明是否修改。
  写进基座的署名表：

  ```ts
  {author: 'Eric Chadwick, © 2024 Darmstadt Graphics Group', title: 'CarConcept', license: 'CC BY 4.0',
   url: 'https://github.com/KhronosGroup/glTF-Sample-Assets/tree/main/Models/CarConcept',
   changed: '去掉 Khronos 与 3D Commerce 标志，换车漆与胎侧材质'}
  ```

- 起步层不带 CarConcept（CC BY、11.8 MB）。加载任意 glTF，用套件的 `Model`（用法见 [scene-kit.md](scene-kit.md)「外部模型」）：
  1. 放进 `public/assets/models/`（GLB，或 glTF 连同 `.bin` 与 `textures/`），取材当下登记（上文「登记」）。
  2. `python3 tools/gltf_nodes.py <文件>`：节点树、材质与贴图、动画、`asset.copyright`、是否 Draco，按名字标出疑似标志；贴图上的标志名字看不出来，渲一张看。
  3. `<Model src remove replace fit draco>`：`remove` 按节点名或材质名真删（不投影、不算进尺寸），`replace` 换材质（例如带标志的胎侧换素面橡胶），
     `fit` 缩放到实际尺寸，`ground` 默认把它落到 y = 0；压缩模型写 `draco` 并自托管解码器（[render.md](render.md)「GPU 与无头环境」）。每个实例用
     `SkeletonUtils.clone` 各自克隆，蒙皮网格不会共用骨骼（手写 `gltf.scene.clone(true)` 会共用）。
  4. 写进 `CREDITS`，改过的写 `changed`（例「去掉示例标志，换胎侧材质」）。
  5. 只要车身壳、侧围这类部件时用 `only` 留下要的顶层节点；远处的大量车辆用公告板替身，近处用从同一模型取的简化版。
  特斯拉工程的 `work/remotion/src/three/Car.tsx`（`useGLTF` + `clone(true)` + 按名字隐藏）只作证据，2026-10-13 用 CarConcept 在 `Model` 上复测过同样的去标志。
- Sketchfab 上的 CC BY 模型：许可看 Sketchfab API 的许可标签（「CC Attribution」），署名写「"标题" by 作者 (主页), CC BY 4.0 — modified (…)」。
  名字里带品牌的（例如名为「kuka」的机械臂）要去掉品牌后再用，并在改动里写明。特斯拉片从 Sketchfab 登记了 7 个 CC BY 模型（含下一条的扫描车），最后一个没用：
  机械臂改用程序化的通用六轴臂（`work/remotion/src/three/RobotArm.tsx`，没有品牌、不用署名），电机、电芯、输送带都程序化。能程序化的通用设备就程序化，省掉署名，也没有标志。
- 真实品牌产品的扫描模型（例：一辆特斯拉车型的摄影测量扫描，CC BY 4.0）：CC BY 只管扫描本身的版权，不管外观与商标；反光车漆通常扫得很差。
  特斯拉片没用，主角车用通用概念车（2026-10-12 用户决定）。

## 真实照片与影像

资料怎么上屏、怎么调色见 [style-grammar-3d.md](style-grammar-3d.md)「资料」；标注与署名格式见基座 `references/fact-and-disclosure.md`。取材时：

- 维基共享资源：读文件页的许可模板与 FlickreviewR / LicenseReview 结果；批量下载用单线程、每次间隔 8 秒，否则 429（特斯拉工程 `HANDOFF-v0.2.md:40`）。
- Flickr 来的照片逐张读原描述核作者：特斯拉片发现某摄影师 2012 年 5 月有一组照片是公司制造团队拍的；另一张「摄影」署名的照片，举着板子的人就是署名者本人，
  「摄影」不成立，剔除（2026-10-12）。
- NASA 影像是公有领域，照页面要求的写法署名（例「NASA's Goddard Space Flight Center」）；含 Sentinel 数据的写「Contains modified Copernicus Sentinel data」。
- Pexels：免署名、可修改；不许让可识别的人显得负面、暗示人物或品牌背书、当商标用（许可页，2026-10-12 读）。画面里有被讲品牌的车机界面或标志的不用。
- 资料内容要和画面说的一致：钢水素材发橙白光，不能拿来当铝液；洗车机不是淋雨测试；别人做的科普动画不用。
- 下载脚本的请求头（User-Agent 等）只写工具名，不写个人邮箱或任何个人信息：2026-10-12 有两个核查 Agent 把用户邮箱写进了 User-Agent，
  发往 commons.wikimedia.org 最多 11 次（v0.2 交付报告「过程记录」）。

## 品牌与商标

讲真实公司、真实产品时（2026-10-12 特斯拉片用户决定，作为默认）：

- 三维、自制界面、AI 画面、封面里一律不出现被讲品牌的标志；标志只允许出现在纪录性质的资料照片里。
- 三维里的产品用通用、无标识的设计，整片标「车型为示意」一类的说明；「这就是那个产品」的部分交给资料照片。
- 自制界面（车机屏幕、仪表）用通用设计，不模仿品牌界面的布局和字体（特斯拉片 11 章的「软件更新」用思源黑体和一条进度条）。
- 强调色不用接近品牌标准色的颜色（特斯拉片用琥珀 `#E3B04B`，避开品牌红）。
- 资料照片里别家公司的标识裁出画面（引语背景照片裁到左侧约 75%，避开卡车商标）。
- 片尾说明写独立声明：「本片为独立科普，与 <公司> 无隶属关系」；用了其他公司、其他工厂的画面时写「标『资料 · 同类工序』的画面取自其他车企或其他工厂」。

## 生成式图像与视频

- 不让生成模型画标志：提示词固定写明不要标志、文字、人物（特斯拉片为可选 AI 镜头准备的英文提示词：
  「unbranded generic car body, no logos, no text, no people, single continuous shot」），出图后逐张、逐帧检查有没有标志、字母、徽章与畸形结构，
  有就弃用重出，不在成品上修补。封面底图的禁止项见基座 `references/covers.md`「提示词」。
- AI 写实镜头默认不用；要用只作替换层：以本片的三维帧作首帧（必要时也给尾帧），画面里整段标「生成画面 · 示意」；真人、历史、真实地点与事件不生成；
  不去除模型自带的水印（如 SynthID）。每个镜头的模型、提示词、种子与费用写进交付报告，画面上不写模型名（基座硬门禁）；AI 生成内容清单按基座逐类列出。
- 三维渲染、程序化几何、程序化动画不是生成模型做的，不进 AI 生成内容清单。
