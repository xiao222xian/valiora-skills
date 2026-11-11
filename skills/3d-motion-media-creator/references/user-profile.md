# User Profile 契约

本 Skill 在 `skill.yaml` 里声明 `user-profile/v1`：每次运行从同一份用户自有的 JSON Profile 读取用户、品牌、工作区与偏好，
源码里不写任何个人路径或品牌值。宿主通过 `SKILL_PROFILE_PATH`（或运行时配置的 Profile 路径）提供这份文件。

## 两个命名空间

三维图志是 `lov-motion-media-creator` 之上的一层，片子级的记录（署名品牌、Logo、印章、画幅、旁白、标注、片尾）在两类片子里含义相同，
只存一份，归基础 Skill 所有。本 Skill 只拥有三维特有的记录。

| 命名空间 | 归属 | 本 Skill 怎么用 |
| --- | --- | --- |
| `user`、`brand`、`workspace`、`preferences` | 共享 | 读 |
| `skills.lov-motion-media-creator.records` | 基础 Skill | 读；用户在本 Skill 的会话里直接说出这些值时，写回这里（见下文），不复制到本 Skill 的命名空间 |
| `skills.lov-3d-motion-media-creator.records` | 本 Skill | 读写；只放三维特有的记录 |

旧命名空间 `skills.lov-film-atlas` 不读：基础 Skill 0.9.0 已把它迁到 `skills.lov-motion-media-creator`（2026-10-13）。

### 从基础 Skill 复用的记录

| 记录 | 用途 |
| --- | --- |
| `brand_name`、`brand_logo`、`seal_asset` | 片尾署名卡、封面与片名卡的品牌资产；只引用官方源文件 |
| `default_aspect` | 默认交付画幅 |
| `narration` | 旁白用 TTS 还是真人原声 |
| `annotation`、`outro` | 标注小字的位置与大小、片尾只留片名卡 |

这些记录的含义与默认值以 `lov-motion-media-creator` 的 `SKILL.md`「User Profile」为准，本 Skill 不重新定义。

### 本 Skill 自己的记录

| 记录 | 含义 | 没有记录时 |
| --- | --- | --- |
| `render_backend` | 本机渲染三维用的 `--gl` 后端 | macOS 用 `angle`；其他系统先按 `references/render.md` 实测，不猜 |
| `render_concurrency` | 渲染并发的标签页数 | 4（2026-10-12 在 macOS 上实测超过 4 没有收益：所有标签页共用一个 GPU 进程） |
| `texture_library` | 本机已下载的 CC0 贴图库目录 | 按材质表从来源站下载到工程的 `public/assets/tex3d/` |
| `brand_marks` | 以真实品牌为题时，它的标志允许出现的位置 | 只在纪录性质的资料照片里；三维画面、AI 图与封面都不出现（《如何打造一款特斯拉》2026-10-12 的用户决定） |

机器相关的记录（`render_backend`、`render_concurrency`、`texture_library`）只描述这台机器，换机器后先实测再改。

## 每次运行先读

```bash
python3 scripts/profile_store.py read --skill-id lov-3d-motion-media-creator --pretty
python3 scripts/profile_store.py read --skill-id lov-motion-media-creator --pretty
```

第一条给出共享的 `user`、`brand`、`workspace`、`preferences` 与本 Skill 的 `records`；第二条只取它的 `records`。

取值顺序：

- 片子级的值：当前请求 → 工程上下文 → `skills.lov-motion-media-creator.records` → 共享偏好 → 共享 `user` / `brand` → 安全默认值。
  品牌先取基础 Skill 的 `records.brand_name` / `records.brand_logo` / `records.seal_asset`，再回退共享的 `brand.*`
  （共享品牌可能是伞形品牌，不一定是这类片子的署名）。
- 三维特有的值：当前请求 → 工程上下文 → `skills.lov-3d-motion-media-creator.records` → 上表的默认值。

本 Skill 的命名空间里出现片子级的键（例如 `brand_logo`）时，以基础 Skill 的为准，并在结果里报告这处重复。
最终结果保留 `profile_scope` 与每个值的来源。

## 只保存用户直接说出的值

用户明确说某个值以后都这样用时，在这句话之后立即保存，并报告保存路径。

三维特有的记录：

```bash
python3 scripts/profile_store.py record \
  --skill-id lov-3d-motion-media-creator \
  --path records.render_backend \
  --value '"angle"' \
  --confirm
```

片子级的记录写回基础 Skill 的命名空间，两类片子读到的是同一个值：

```bash
python3 scripts/profile_store.py record \
  --skill-id lov-motion-media-creator \
  --path records.default_aspect \
  --value '"默认只出 16:9 横版；用户点名时才出 9:16"' \
  --confirm
```

基础 Skill 的记录是给人读的一句话，不是枚举值；写回时沿用这种写法。

共享事实用 `--path brand.<字段>` 或 `--path user.<字段>`。脚本原子写入、保留 Profile 里无关的数据、
有数字 `revision` 时加一，并且不回显保存的值。

推断出来的信息、凭据、token、cookie 与形似密钥的字段不进长期记录；用户没说要长期保存的值只留在本次请求里。
贴图库、模型目录这类本机路径只写进 Profile，不写进源码、案例或交付报告。

## 兼容

`--user-config` 仍作为旧调用的兼容参数被 Skill Creator 接受；Profile 契约总是生成，用户不选初始化模式。
