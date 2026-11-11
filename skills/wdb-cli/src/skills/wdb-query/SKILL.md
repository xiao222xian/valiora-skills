---
name: lov-wdb-query
description: >
  万能微信秘钥：使用已有密钥或已解密数据库，自由查看、检索并精准读取本地微信数据，覆盖聊天、联系人、朋友圈、封面、统计、结构浏览与只读 SQL。Use when the user mentions“万能微信秘钥”“查微信记录”“读取朋友圈”，或需要按稳定记录身份定位微信数据。
license: MIT
compatibility: "macOS, Python 3.9+, SQLCipher CLI for encrypted databases."
depends_on:
  - lov-branding-consistency
allowed-tools:
  - Bash
  - Read
metadata:
  author: contributors
  version: "0.6.4"
  tags:
    - wechat
    - sqlcipher
    - database
    - cli
    - agent-context
  dependencies: []
---

# 万能微信秘钥 · Universal WeChat Key

一把面向本地微信数据的通用钥匙：使用已有密钥清单或已解密数据库，自由查看、
检索并精准读取聊天、联系人、朋友圈、封面、统计及其他数据。既提供常见内容的
语义化快捷查询，也允许 Agent 浏览数据库结构并执行受限只读 SQL，从而适应不同
微信版本和未预先列举的数据。

## Triggers

### Activate when

- “查一下 2026-08-01 和张三的聊天记录”“精准读取这条消息”。
- “获取某个好友的基本信息、朋友圈封面、某条朋友圈的点赞和评论”。
- “把我 2021 年 8 月的朋友圈原图下载下来”“取这条朋友圈的高清图”。
- “统计某一天的微信消息、联系人和朋友圈活动”。
- “看看这个微信数据库里有什么”“读取收藏、群成员或新版本新增的数据表”。
- “用万能微信秘钥查一下这条记录”“帮我读取本地微信数据”。
- “Find a WeChat record by date” or “inspect and query WeChat database data”.

### Do not activate when

- 用户要从正在运行的微信进程提取新密钥；这属于密钥提取流程，本 Skill 只消费已有密钥清单。
- 用户要修复、构建或操作某个数据库查看器应用；应在对应产品仓库中处理。
- 用户只提供聊天截图并要求 OCR；应使用图片理解或 OCR 能力。

## Workflow (MANDATORY)

**You MUST follow these steps in order.**

### Step 0: Resolve the Skill and runtime

1. 使用环境变量 `SKILL_DIR`；若未设置，从当前 Skill 上下文解析安装目录。
2. 确认 `$SKILL_DIR/scripts/wdb_cli.py` 和
   `$SKILL_DIR/references/data-contract.md` 存在。
3. 加密数据库需要 `sqlcipher`；优先使用 `WDB_SQLCIPHER`，否则从 `PATH`
   查找。
4. 不把密钥、完整聊天正文或私人路径写入日志或回答，除非用户明确要求输出对应正文。
   查询所需的临时数据库副本仅存于私有目录，保持源库加密状态，命令结束即清理。
5. 所有命令（包括 `doctor`、兼容策略探测和已解密库）必须通过 CLI 的隔离副本读取。
   不直接用 SQLite/SQLCipher 打开微信原库；`-readonly`、`mode=ro` 和
   `query_only` 仍可能参与原库的 `-shm` 操作，不能代替隔离。
   不复制、修改或删除原库 `-shm`，不执行原库 checkpoint，不附加或停止微信进程。
   快照失败只报告 `snapshot` 阶段错误，不回退到直连原库。

手工运行时：

```bash
export SKILL_DIR="/path/to/lov-wdb-cli"
python3 "$SKILL_DIR/scripts/wdb_cli.py" --help
```

### Step 1: Resolve the data source

按以下优先级定位密钥源：

1. 当前请求里的 `--keys PATH`。
2. `WDB_KEYS_FILE`。
3. WDB Pro 当前 app id 的管理副本：
   `~/Library/Application Support/ai.lovstudio.wdb-pro/database-keys/wdb-pro-managed-keys.json`。
4. WDB Pro 旧 app id `me.lovpen.wdb-pro` 的同名管理副本（仅作迁移兼容）。
5. `~/.wechat-cli/all_keys.json` 及同目录 `config.json`。
6. 当前目录的 `keys.toml`、`wdb.keys` 或单个 `*.keys`。

支持 WDB Pro `wdb-pro-managed-keys.json`、`keys.toml`、DTrace `.keys`、
wechat-cli `all_keys.json`，以及通过 `--database PATH` 直接读取已解密 SQLite。
多账号时用 `--account` 限定数据库路径；不要凭昵称猜账号。

先执行：

```bash
python3 "$SKILL_DIR/scripts/wdb_cli.py" --keys KEYS doctor
```

若失败，保留 CLI 返回的 `debug` 对象供复制排查；不得在 debug 中加入 key。

### Step 2: Select the narrowest command

- 某天或区间聊天：`chats --date YYYY-MM-DD`，可加 `--contact`、`--query`。
- 好友资料：`contacts --match NAME_OR_WXID`。
- 朋友圈帖子和互动：`moments --date YYYY-MM-DD`，可加 `--contact`、
  `--feed-id`（可重复）。
- 朋友圈原图：`moments-media --feed-id FEED_ID --output DIR`，也可用 `--contact`
  加 `--date` 或 `--from/--to` 选帖。`x-Enc` 加密图自动解密，视频只标记 `skipped`；
  `--output` 不能位于微信数据目录内。相邻请求间隔 0.4 秒，几十条帖子以上放后台运行。
- 朋友圈封面：`cover --contact NAME_OR_WXID`，需要落盘时再加 `--output`。
- 媒体图片：先用 `record` 取 `packed_info_data` 里的 mediaId，再用
  `scripts/decode_wechat_v4_dat.py` 解码 `.dat`；输出默认落在当前目录，不写回微信数据目录。
- 汇总统计：`stats --date YYYY-MM-DD` 或 `--from/--to`。
- 精确行读取：`record --database PATH --table TABLE --rowid ROWID`。
- 未知数据或新版本结构：先用 `schema` 浏览数据库、表和字段，再用 `sql`
  执行单条只读查询。
- 读库范围：用密钥文件（含 `--account`）时，`contacts`、`cover`、`moments`、`moments-media`
  不打开消息库和头像库；`chats`、`stats`、`doctor`、`schema` 仍复制全部库，一个账号的消息库
  可达数 GB，先确认磁盘空间。`--database` 指定的库总会全部读取。

示例：

```bash
python3 "$SKILL_DIR/scripts/wdb_cli.py" --keys KEYS chats \
  --date 2026-08-01 --contact "张三" --format jsonl

python3 "$SKILL_DIR/scripts/wdb_cli.py" --keys KEYS moments \
  --contact wxid_example --feed-id FEED_ID --format json

python3 "$SKILL_DIR/scripts/wdb_cli.py" --keys KEYS moments-media \
  --contact wxid_example --from 2021-07-25 --to 2021-10-10 --limit 200 --output ./moments-originals

python3 "$SKILL_DIR/scripts/wdb_cli.py" --keys KEYS record \
  --database DATABASE_PATH --table Msg_HASH --rowid 42

python3 "$SKILL_DIR/scripts/wdb_cli.py" --keys KEYS schema \
  --table favorites

python3 "$SKILL_DIR/scripts/wdb_cli.py" --keys KEYS sql \
  --database DATABASE_PATH --query 'SELECT rowid, * FROM Favorites LIMIT 20'
```

### Step 3: Preserve stable identity

聊天和朋友圈结果必须保留 `source.databasePath`、`source.tableName`、
`source.rowid`。跨表结果按归一化时间排序。需要再次精确读取时使用 `record`，
不得回退成联系人、时间、正文片段的模糊匹配。

联系人名称匹配可能产生多个结果。此时先返回候选的 `displayName`、`username`
与稳定 source，再缩窄条件；不要把同名联系人合并成一个人。

`--contact` 在联系人表里按账号、昵称、备注、别名做子串匹配，原值本身也总会当作账号精确匹配：
已删除的好友、旧账号不在联系人表里，`chats`、`moments`、`moments-media`、`stats` 传完整 wxid
也能查到。

### Step 4: Interpret product semantics

读取 `$SKILL_DIR/references/data-contract.md` 后再解释结果，尤其注意：

- `displayName` 优先级为备注、昵称、别名、稳定账号。
- 朋友圈封面来自 packed `WCContactData` 的字段路径 `27.2`。
- `SnsMessage_tmp3` 代表本地可观测到的互动；点赞数与评论数应标注为
  `observedLikeCount` / `observedCommentCount`，不要宣称是服务器完整总数。
- 聊天按时间截取 `--limit`：保留最新的 limit 条，输出仍按时间正序。`--query` 不在 SQL 里截断，
  先列出全部候选行，再按时间倒序逐块解压正文匹配，凑够 limit + 1 条命中即停；`truncated: true`
  表示还有命中没返回，或有库、表、正文因错误没读完。关键词匹配不区分大小写。无时间窗、无联系人
  的关键词检索要解压整库候选正文，约 1 GB 的分库约 1 分钟，能先限定联系人或时间窗就先限定。
- 朋友圈按时间截取 `--limit`：先扫全部行的作者和 XML `createTime`，再读正文。
  `meta.matchedCount` 是命中总数，`truncated: true` 表示还有命中没返回，或有库、表因错误
  没扫完。`mediaUrls` 是缩略图优先的地址列表，要原图用 `moments-media`。
- 自然日按本机时区的 00:00:00 到次日 00:00:00 处理；秒和毫秒时间戳均兼容。
- 压缩正文优先解 Zstandard，再尝试 LZ4；缺少可选解码器时保留编码信息和
  稳定 source，不生成猜测正文。
- 群聊消息在库里带 `发送者:\n` 前缀：`text` 已剥离该前缀、`rawContent` 保留
  原始字节，`senderUsername` 优先取 `Name2Id`、取不到时回退到前缀。
- appmsg 类型以正文里的 `<appmsg><type>` 为准并输出 `appType`；`local_type`
  对复合类型（如 `244813135921`）不可直接映射。只命名验证过的编号：`57` 是
  引用回复（`text` 只是回复者写的字，被引用原话在 `quoted.content`），`62`
  是拍一拍，其余编号一律记 `app`。
- 判断“扣1 / 报名 / 到场”这类立场时必须同时看 `quoted`。`text=➕1` 可能是在
  附议被引用的原话（例如“为什么不是上海”），不表示报名参加。

### Step 5: Validate and report

1. 检查命中数、`truncated`、`errors` 和每条 source。
2. 默认使用 `--format json`；长列表或交给下游 Agent 时使用 JSONL。
3. 回答中先给目标结果，再给读取范围与未覆盖的数据源。
4. 不显示 key；涉及私密正文时只返回用户要求的范围。
5. 数据来自本次调用内各数据库的隔离副本，包含复制时稳定的 WAL；不宣称跨库原子一致
   或持续实时。磁盘空间不足、持续写入或回滚日志阻止复制时，报告未覆盖来源。
6. 品牌依赖仅约束摘要和说明文案；聊天原文、源数据与稳定记录身份保持原样。

## Dependencies

- Python 3.9+
- Homebrew `sqlcipher`（读取加密库）；已解密 SQLite 不需要它
- 可选 Python 包 `zstandard` 与 `lz4`，用于微信 4.x/旧版压缩正文
- 可选 `ffmpeg`（含 `ffprobe`），用于把 wxgf（HEVC）图片转成 JPG/PNG
- `moments-media` 需要能访问微信 CDN（`qpic.cn` 等），只用 Python 标准库

## Validation

```bash
python3 "$SKILL_DIR/scripts/test_wdb_cli.py"
python3 "$SKILL_DIR/scripts/wdb_cli.py" --database FIXTURE.db doctor
```

## Runtime context (shared)

运行前读取本 Skill 包的 `skill.yaml`，由宿主提供 `skill-runtime/v1` 上下文。字段解析顺序为：当前请求、项目上下文、个人 Preferences、品牌 Profile、通用默认值。

- 只使用 Manifest 声明的字段；Profile 保存公开品牌事实，Preferences 保存个人工作偏好。
- `required: true` 字段缺失时，按 Manifest 的问题配置向用户提出一个聚焦问题；用户明确同意后再保存回答。
- 报错提供可复制的 `context_id`、字段路径与来源，诊断内容避开秘密、完整私人路径和原始配置。

## 维护备注

- `_cipher_query` 在 SQL 结果为空时，`parsed_values[-1]` 会被 `PRAGMA key/query_only` 的 JSON 状态行（`[{"ok":"ok"}]`）污染，导致 `message_rows` 误把状态行当消息行而抛 `KeyError('__rowid')`；已用 `.output /dev/null` 包裹两个 PRAGMA 修复，重构时勿移除该重定向（2026-08-21, 3feb3e2）
- 微信消息按 `message_0/1/2.db` 分库，同一群的 `Msg_MD5(username)` 表可能分布于多个分库；某个分库在某时间范围内无消息时该库查询返回空，属正常（2026-08-21, 3feb3e2）
- 从聊天里拿到的公众号分享卡片，正文不在 `id="js_content"` 的 DOM 里（该 div 渲染为空）；正文在 HTML 内联脚本的 `content_noencode: '...'` 变量中，需截取该字符串并把 `\xNN` 转义还原，图片 URL 取 `data-src`（2026-09-03, 8a8a0e8）
- 报名/入口二维码往海报图里放两个（如观众/选手）时，`cv2.QRCodeDetector.detectAndDecodeMulti` 只返回其中一个；必须按坐标裁剪出每个码再各自 `detectAndDecode`，否则会把两个入口当成一个（2026-09-03, 8a8a0e8）
- 群消息在库里带 `发送者username:\n` 前缀，直接 `content.startswith("<")` 会判失败，导致 `type=57` 的引用回复降级为 `unknown`，把“引用别人的话再回 +1”当成报名；已改为先拆前缀再判类型，并从 `<refermsg>` 输出 `quoted`，判断立场必须同时看 `quoted`（2026-09-10）
- `chats --query` 曾在 SQL 里对每个 400 表批次按时间取 `limit + 1` 行，再在 Python 里做子串匹配：BLOB 正文无条件通过 SQL 预筛，较新的图片、表情占满窗口后命中被挤掉，同一条查询在 `--limit 5` 下返回 0 条、在 `--limit 100` 下返回 15 条，`truncated` 仍为 false（2026-09-11, 4468fb3）。现改为关键词检索不在 SQL 里截断：先列出全部候选行的 rowid 与时间，再按时间倒序每 2000 行解压正文匹配，凑够 `limit + 1` 条即停；合并各批次、各库后保留最新的 limit 条（旧代码按正序截取，会丢掉最新一条、返回中间一段）。无时间窗、无联系人的稀有关键词要解压整库候选正文：约 1 GB 的分库实测 46 万条压缩正文，全库检索约 1 分钟；只有 `zstd` 命令时逐条起进程要 66 分钟，现每个正文块合并为一个进程，按帧头声明的解压长度切回各行（约 65 秒）。纯文本行的 `instr` 预筛当时仍区分大小写，英文关键词会漏掉大小写不同的纯文本消息（2026-10-29）；现预筛两边先转小写，关键词含 É、Ж 这类 ASCII 以外的大小写字母时纯文本行不做预筛（2026-10-30）
- 微信 4.x 收到的图片是加密 `.dat`（magic `07 08 56 32 08 07`）：15 字节头 + AES-128-ECB 段 + 明文段 + 尾部单字节 XOR。`aes_key = md5(f"{code}{wxid}").hexdigest()[:16]` 的 **ASCII 前 16 字符**（不是 hex 解码），`xor_key = code & 0xff`，`code` 取自 `xwechat_files/<wxid>/.../app_data/net/kvcomm/key_<code>_*`；密文跨度是 `(aes_size // 16 + 1) * 16`，把已对齐的 `aes_size` 当明文长度会破坏图片中段（PNG 的 IDAT CRC 失败，但图片仍能打开，肉眼容易放过）。用 `scripts/decode_wechat_v4_dat.py` 解码并核对 `png_crc_ok`（2026-09-11, 4468fb3）
- 中间图和高清图解密后常常不是 JPEG/PNG，而是 `wxgf`（微信封装的 Annex-B HEVC）：一个账号一个月的非缩略图里约六成是它。带透明通道的 wxgf 含两条流，**灰度 alpha 流在前、彩色流在后**，只取第一个起始码会得到一张灰度蒙版；解码器按 ffprobe 的 `pix_fmt` 区分两条流，彩色流转 JPG，带 alpha 时 `alphamerge` 成 PNG。输出里 `container: wxgf`、`streams`、`alpha` 标明走了这条路径（2026-09-23）
- 图片消息的本地文件路径由 `packed_info_data` 里的 32 位 mediaId 决定：`msg/attach/<Msg 表名 hash>/<YYYY-MM>/Img/<mediaId>[_h|_t].dat`；`_h` 高清、无后缀为中间图、`_t` 为缩略图。消息 XML 里的 `md5` 与 CDN 地址不能当本地路径用（2026-09-11, 4468fb3）
- 群成员名单用 `chatroom_member(room_id, member_id)` 关联 `name2id.rowid` 取 username，`room_id` 来自 `chat_room.id`（`chat_room.username = '<xxx>@chatroom'`）；`chat_room.ext_buffer` 内嵌成员 username，可用 `LIKE '%wxid%'` 快速定位某人所在的群。按人统计前先按 username 去重，不要把同名备注合并成一个人（2026-09-11, 4468fb3）
- 由本 Skill 数据生成的一切**对外可见产物**（卡片、文章、报告、海报）不得出现本机数据库路径、库文件名、表名、`wxid_` 账号或本机工具名；来源行统一写成「来源：群聊记录」这类可披露文案。内部留痕放在工作目录，不进交付物（2026-09-11）
- `moments` 曾先 `ORDER BY rowid DESC LIMIT limit+1` 再在 Python 里按作者和日期过滤。微信 4.x 的 `SnsTimeLine` 只有 `tid/user_name/content/pack_info_buf`，时间只在 XML 里，且 rowid 顺序不是时间顺序（回翻朋友圈时旧帖会以新 rowid 写入：本机 2021 年的帖子全落在最新约 8000 个 rowid 里），于是 2021 年区间查询返回 0 条还报 `truncated: false`。现改为先轻量扫描全部行的作者和 `<createTime>` 片段、按时间截断后再取正文；真实库 96,499 行的轻量扫描约 1 秒。任何“先按行序取 N 行、再在 Python 里过滤”的查询都有同类漏检（2026-10-29）
- 朋友圈 `x-Enc` 原图的 ISAAC-64 必须走 rand_isaac `from_seed`（seed 放第一个 u64 槽，两轮初始化），不能用 `seed_from_u64`（一轮）：自造数据的往返测试两种都能过，只有前者能解真实 CDN 数据，所以测试用 rand_isaac 官方向量校验。解出的 JPEG 在 `FFD9` 后固定多 24 字节、下载大小与 XML `totalSize` 不同，都属正常，不要据此改算法（2026-10-29）
- `moments --contact X` 曾在 X 不在任何联系人表里时（已删除的好友、旧账号）静默返回 0 条：作者白名单取自联系人匹配结果，匹配为空就成了空集合，帖子全被滤掉；本机 2021 年朋友圈约三成作者已不在任何联系人表里，并不罕见。`chats` 原先只在一个都匹配不到时才回退到原值，0.6.2 让朋友圈照做，但联系人匹配是子串匹配，X 只要是别的联系人账号、昵称、备注或别名的一部分就不会回退（本机这类作者都没撞上，自定义的短微信号更容易撞）。现在两边都把原值并入匹配，原值只按账号精确比较，不会多带进别人（2026-10-30）
- 用密钥文件（含 `--account`）查询时，找表要先列出每个库的表，列表前又要为整个库建隔离快照，所以 `moments` 曾复制账号下全部数据库：本机 23 个库约 7 GB、约 17 秒，磁盘将满时复制失败。现在每类查找只跳过不可能含目标表的库类型：联系人查询跳过 Message、HeadImage、Sns，`SnsTimeLine` 跳过 Message、HeadImage（`keys.toml` 的标注是自由文本，sns.db 不一定标成 Sns）；过滤后一个不剩时回退到全部库，`--database` 指定的库一律读取。同一条 `moments` 查询降到 13 个库、约 1 GB、约 5 秒，命中数不变。联系人类表不只在 `contact.db`：`session.db` 的 `SessionNoContactInfoTable` 与 `general.db` 的 `wacontact` 也有，只取 Contact 类型会漏掉它们。`chats`、`stats` 仍要复制全部消息库（2026-10-29）

## 通用反馈闭环

用户在 Skill 驱动任务中提出修改意见时，继续当前产物前必须执行：

1. 先判断意见是 `task-specific`（仅本次）还是 `reusable`（可跨任务复用）。
2. `task-specific` 只修改当前任务，不改 Skill。
3. `reusable` 先确定作用域：领域规则先更新对应 canonical Skill；适用于所有 Skill 的规则先更新共享规范。
4. 完成规则更新、版本、lint 与分发核验后，再把修改应用到当前任务。
5. `reusable` 修改会使此前的“确认”“继续”“发吧”失效；完成当前产物修改和回读后必须停下，等待用户下一步指示，不自动进入发布、提交或其他外部写入。
