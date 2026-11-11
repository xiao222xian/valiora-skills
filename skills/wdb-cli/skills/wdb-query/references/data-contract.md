# 数据契约

## 输入源

CLI 接受五类输入：

1. WDB Pro 管理副本：`wdb-pro-managed-keys.json` 顶层是数组，每项包含绝对
   `path`、64 位十六进制 `key` 与 camelCase `cipherCompatibility`。CLI 默认优先
   发现 `ai.lovstudio.wdb-pro` 的应用数据目录，并兼容旧 app id 的迁移路径。
2. `keys.toml`：每个数据库条目含 `path`、`key`、`cipher_compatibility`。
3. DTrace `.keys`：由 `sqlcipher db path:` 与后续 `PRAGMA key =` 配对。
4. wechat-cli：`all_keys.json` 中的相对路径和 `enc_key`，数据库根目录从同目录
   `config.json` 的 `db_dir` 读取。
5. 已解密 SQLite：通过 `--database` 直接提供，不需要 key。

同一路径只保留一个条目。CLI 的所有诊断对象都省略 key。

语义化命令覆盖高频微信数据，但不定义能力上限。对收藏、群信息、标签、会话、
媒体索引、搜索索引或新版本新增表，使用 `schema` 获取实时结构，再通过 `sql`
执行单条只读查询。这样不会因为固定字段清单而丢失可访问的数据类型。

## 稳定记录身份

### 读取隔离

所有后端只打开私有临时副本，源库只通过普通文件读取复制。复制主库与 `-wal`，
不接触源库 `-shm`；SQLite/SQLCipher 自行在副本目录创建 WAL 索引。不能省略 WAL，
否则会丢失尚未 checkpoint 的已提交记录；不能用 `immutable=1` 标记仍在变化的原库。
复制前后比较主库、WAL 和回滚日志的 inode、设备、大小、mtime 与 ctime。
最多三次尝试；检测到变化则丢弃副本，复制失败或非空回滚日志则明确报错，不直连降级。
这是经过稳定性检查的逐库文件副本，不是文件系统原子快照或跨库事务快照。
每次调用按需创建并复用副本，成功、查询失败或正常异常退出时清理。

副本按整库复制，同一次调用里打开过的库在退出前一直占用临时空间。因此使用密钥文件时，
每类查找跳过不可能含目标表的库类型：联系人查询（`contacts`、`cover` 与朋友圈命令的作者解析）
跳过 Message、HeadImage、Sns，`SnsTimeLine` 跳过 Message、HeadImage；过滤后一个都不剩时
回退到全部库。`--database` 显式给出的库总是全部读取；`chats`、`stats`、`doctor`、`schema`
仍打开全部库。库类型优先取 `keys.toml` 条目的标注，其余按路径推断（`contact`、`message`、
`sns`、`session`、`head_image` 等目录名），可用 `schema --database 文件名` 单独核对某个库的
`databaseType`。

`source.databasePath` 始终是原始路径，不能用临时路径替换记录身份。
禁止对原库执行 backup API、checkpoint、写 PRAGMA、清理 WAL/SHM，或对微信进程
提取密钥、发送信号、附加调试器。只读标志本身不阻止共享内存访问，参见
[SQLite WAL 文档](https://www.sqlite.org/wal.html)。

每条可回读记录包含：

```json
{
  "source": {
    "databasePath": "/path/to/database.db",
    "tableName": "Msg_HASH",
    "rowid": 42
  }
}
```

这是跨 Agent 传递定位信息的唯一精确契约。联系人名、正文、时间仅用于缩窄
结果，不替代稳定身份。

## 联系人

联系人优先读取 `WCContact`。字段名兼容微信版本差异：

- 稳定账号：`m_nsUsrName`、`username`、`user_name`、`wxid`
- 昵称：`nickname`、`m_nsNickName`
- 备注：`m_nsRemark`、`remark`、`conRemark`
- 别名/微信号：`m_nsAliasName`、`alias`
- packed 资料：`_packed_WCContactData`、`WCContactData`、`extra_buffer`

微信 4.x 的联系人类表分在三个库：`contact.db` 的 `contact`、`session.db` 的
`SessionNoContactInfoTable`、`general.db` 的 `wacontact`。各表的行分别返回、各带 `source`，
不跨表合并。`--contact` / `--match` 在账号、昵称、备注、别名里做子串匹配。

`displayName` 的优先级是备注 > 昵称 > 别名 > 稳定账号。朋友圈签名只读取
packed protobuf 顶层字段 4；封面 URL 只读取顶层字段 27 的嵌套字段 2，避免把
头像或其他链接误认成封面。

## 聊天

聊天表兼容 `Msg_*`、`Chat_*`、`Chat`、`Message_*` 等命名。联系人到表的
主要映射为 `MD5(username)`，并保留直接传入 32 位 hash 或完整表名的入口。
`--contact` 匹配到的每个联系人和原值本身都按此映射，所以已删除的好友、旧账号传完整 wxid
也能查到；这类会话不在联系人表里，`conversationId` 为 null。

常见字段：

- 正文：`message_content`、`msgcontent`、`strcontent`、`content`
- 时间：`create_time`、`msgCreateTime`、`createTime`、`timestamp`
- 类型：`local_type`、`messageType`、`type`
- 方向：`mesDes`、`direction`、`is_send`
- 群发送者：`real_sender_id` 通过同库 `Name2Id.rowid` 解析

时间筛选同时匹配 Unix 秒和毫秒。结果先按时间、再按数据库路径、表名、rowid
排序，不依赖单库局部顺序。

### 关键词检索与截断

微信 4.x 的聊天正文多为 zstd 压缩的 BLOB，SQL 无法在里面匹配关键词。因此 `--query`
不在 SQL 里截断，而是：

1. 每个数据库按 400 张表一批，按时间区间与联系人筛选，并用 `instr` 排除不含关键词的
   纯文本行；BLOB 行全部保留，只取 rowid 与时间；
2. 按时间、表名、rowid 倒序逐块（每块 2000 行）读取候选正文，解压后在原文、去掉群前缀的
   正文和提取出的 `text` 里做不区分大小写的子串匹配，凑够 `limit + 1` 条命中即停。

解压优先用 `zstandard` 模块。没有该模块、只有 `zstd` 命令时，一个正文块的 zstd 帧拼接后
交给同一个 `zstd` 进程，再按各帧头声明的解压长度切回各行；未声明长度的帧，以及进程失败或
输出总长对不上的整批，退回逐条解压。

不带 `--query` 时没有 Python 端过滤，每批直接在 SQL 里按时间倒序取 `limit + 1` 行。合并
所有批次与数据库后保留最新的 `--limit` 条，输出仍按时间正序。`truncated: true` 表示还有
命中没有返回，或某个数据库、表、正文块因错误没有读完（此时 `errors` 非空）。

纯文本行的 `instr` 预筛两边先转小写，与解压后不区分大小写的匹配一致。SQLite 的 `lower()`
只折叠 ASCII 字母，关键词含其他大小写字母（如 É、Ж）时纯文本行不做预筛，全部交给解压后的
匹配，候选行会多出一倍以上。

### 群聊前缀与 appmsg 类型

群聊消息在库里以 `发送者username:\n正文` 存储。CLI 会把前缀拆出来：`text`
返回去掉前缀的正文，`rawContent` 保留原始字节；`senderUsername` 优先取
`Name2Id` 解析结果，解析不到时回退到该前缀。因此 `text` 可以直接用于判断
表态，前缀不再混进正文。

`local_type` 对复合类型（例如引用回复实际存为 `244813135921`、拍一拍存为
`266287972401`）不可靠，不能直接映射。appmsg 类消息的真实类型在正文 XML 的
`<appmsg><type>` 中，CLI 以它为准并在 `appType` 输出原始数字。

`messageType` 只对已在真实微信载荷中验证过的类型做命名，其余一律记为 `app`，
避免把没验证过的编号猜成错误语义：

- `57` → `quote`，同时给出 `quoted`：`senderUsername`、`senderName`、
  `content`、`rawType`、`createTime`、`timestampUnix`、`serverId`。`timestampUnix` 为秒，
  被引用消息存成毫秒时读出时换算。
- `62` → `pat`（拍一拍，正文在 `<patinfo>`，CLI 只回 `<title>` 文本）。
- 其他编号 → `app`，需要语义时读 `appType` 与 `rawContent`。

引用回复的 `text` 只是回复者自己写的字，被引用的原话在 `quoted.content`。
判断“扣1 / 报名 / 到场”这类立场时必须同时看 `quoted`：`text=➕1` 可能是在
附议被引用的那句原话，而不是报名参加。

## 朋友圈

帖子来自 `SnsTimeLine`，内容一般为 XML 或压缩 XML。解析字段包括：

- `tid` / `feed_id`
- `username`
- `createTime`
- `contentDesc`
- 媒体 URL、文章标题、文章 URL 与封面 URL

互动来自 `SnsMessage_tmp3` 或同类表。空 `content` 视为点赞，非空视为评论。
这些记录代表本机数据库里可见的互动，所以使用 `observedLikeCount`、
`observedCommentCount` 和 `observedInteractions` 命名。

### 区间扫描与截断

微信 4.x 的 `SnsTimeLine` 只有 `tid`、`user_name`、`content`、`pack_info_buf` 四列，
发帖时间只在 XML 的 `<createTime>` 里；rowid 顺序也不是时间顺序，回翻朋友圈时旧帖
会以新的 rowid 写入。因此 `moments`、`stats` 与 `moments-media` 不在 SQL 里按
rowid 截断，而是：

1. 扫描全部行的 rowid、作者和 `<createTime>` 片段（表里有时间列时用时间列）；
2. 按作者与时间区间过滤，再按时间、数据库路径、rowid 倒序截取 `--limit`；
3. 只为保留下来的帖子按 rowid 读取正文与互动。

片段解析不出时间、或按联系人过滤时作者列为空的行，会直接读正文判定，不会漏掉。
`meta.scannedRows` 是扫描行数，`meta.matchedCount` 是命中总数；`truncated: true`
表示还有命中帖子没有返回，或某个数据库、表因错误没有扫描完（此时 `errors` 非空）。
`--feed-id` 可重复，用于一次精确读取多条帖子。

`--contact` 先在联系人表里匹配，按匹配到的 username 过滤作者，同名联系人各自保留
`authorId`；原值本身也总按作者账号精确匹配，已删除的好友、旧账号不在联系人表里也能查到，
与 `chats` 一致。

### 朋友圈原图（`moments-media`）

`mediaUrls` 只是 XML 里出现过的地址（缩略图优先，最多 9 个）。CDN 原图需要 token，
多数还经过 `x-Enc` 加密。`moments-media` 的契约：

- 只处理帖子自身 `<ContentObject>` 里带 `<type>` 子节点的 `<media>`：`2` 是图片，`6` 是
  视频，其余记为 `other`。视频号卡片的嵌套 `<media>` 只有 `<mediaType>`，忽略。视频与
  `other` 输出 `status: skipped`，不下载。
- 请求地址取 `<media><url>` 全文，`http` 改为 `https`；`<url>` 带 `token` 属性时补上
  `token` 和 `idx=1`（已有则不重复）。只请求 `qpic.cn`、`wechat.com`、`qq.com` 域名，
  UA 为 `MicroMessenger Client`。
- 响应体本身是图片（JPEG/PNG/GIF/WebP）时原样保存，`encrypted: false`。
- 响应头 `x-Enc: 1` 时，把 `<url>`（缺省时取 `<media>`）的 `key` 属性作为 seed 放进
  ISAAC-64 的第一个 u64 槽，按 rand_isaac `Isaac64Rng::from_seed` 做两轮初始化，按
  `next_u64` 顺序把每个字以大端字节序展开成密钥流，与响应体异或，`encrypted: true`。
  与 wdb-pro `decode_sns_remote_encrypted_image` 一致，主变体解不出图片签名时，再依次
  尝试字节翻转的 seed、小端字序与倒序密钥流。
- `x-errno` 为 `-106`/`-107`/`-108`、`x-info: illref`，或返回约 5 KB 的 120×120 PNG，
  都是防盗链占位（常见于 token 失效），记为 `failed`、`error.stage = placeholder`，不写文件。
- 文件名为 `<YYYYMMDD-HHMMSS>_<feedId>_<序号>.<ext>`，先写 `.part` 再改名；同名文件已
  存在时记为 `exists` 且不发请求，可以安全重跑。
- `--output` 不能位于微信数据目录（`xwechat_files`、`com.tencent.xinWeChat` 容器）内。
  结果与 stderr 进度日志只含 feedId、序号、状态、文件名和错误阶段，不含 URL、token、key。
- 至少需要 `--feed-id`、`--contact` 或日期范围之一；`--limit` 限制帖子数（默认 50），
  相邻请求间隔 0.4 秒。

每个结果项包含 `feedId`、`mediaIndex`、`mediaId`、`mediaType`、`timestamp`、
`timestampUnix`、`authorId`、`width`/`height`（来自 XML `<size>`）、`status`
（`downloaded`、`exists`、`skipped`、`failed`）、`path`、`kind`、`bytes`、`encrypted`、
`error` 和帖子的 `source`。`meta.postCount` 是处理的帖子数，`meta.statusCounts` 汇总各
状态数量，`meta.outputDir` 是实际保存目录；任一图片失败时 `meta.errors` 非空、退出码为 1。

解密得到的 JPEG 在 `FFD9` 之后固定多出 24 字节，图片可以完整解码，不代表解密失败；
下载字节数与 XML `totalSize` 也不相同，不能用来校验完整性。

## 媒体图片（微信 4.x 加密 `.dat`）

聊天里的图片消息在 `message_content` 里给出 `md5`、CDN 地址与 `aeskey`，但这些都不能直接
当成本地文件路径。真正的本地文件名是 `packed_info_data` 里的 32 位 mediaId：

```text
msg/attach/<Msg 表名 hash>/<YYYY-MM>/Img/<mediaId>_h.dat   # 高清
msg/attach/<Msg 表名 hash>/<YYYY-MM>/Img/<mediaId>.dat     # 中间图
msg/attach/<Msg 表名 hash>/<YYYY-MM>/Img/<mediaId>_t.dat   # 缩略图
```

`.dat` 是 V2 容器（magic `07 08 56 32 08 07`）：

```text
bytes[0:6]    07 08 56 32 08 07
bytes[6:10]   uint32le  aes_size             AES 段的明文长度
bytes[10:14]  uint32le  xor_size             尾部 XOR 段长度
bytes[14]     flags（0x01）
bytes[15 : 15 + aligned]                     AES-128-ECB 密文，PKCS#7 填充
bytes[15 + aligned : len - xor_size]         明文直通段
bytes[len - xor_size : len]                  尾部，逐字节 XOR xor_key

aligned = (aes_size // 16 + 1) * 16
```

密钥材料来自同账号的 kvcomm 表 `app_data/net/kvcomm/key_<code>_*`：

```text
aes_key = md5("{code}{wxid}").hexdigest()[:16]   # 取 ASCII 前 16 字符，不做 hex 解码
xor_key = code & 0xff
```

`scripts/decode_wechat_v4_dat.py` 实现了上述流程：自动发现 kvcomm code、
遍历 wxid 候选、校验图片签名与 PNG chunk CRC，并把结果写到当前目录（不写回微信数据目录）。
校验时不要只看“图片能打开”——AES 跨度算错时 PNG 仍能打开，但中段像素已损坏，只有
逐块 CRC 才能发现。

V1 容器（`07 08 56 31`）使用内置常量密钥，本 Skill 不提供。

### wxgf 明文（HEVC）

解密后的明文以 `wxgf` 开头时，它是微信封装的 Annex-B HEVC，而不是损坏的图片。中间图和
高清图常见这种格式。结构：

```text
bytes[0:4]   "wxgf"
bytes[4]     头长度（常见 0x12 / 0x13）
头之后        可能有 ICC profile 等元数据，随后是 1–2 条 HEVC 流
每条流        以 VPS NAL 起始：00 00 00 01 40 01
```

两条流时，第一条是灰度 alpha（`pix_fmt=gray`），第二条是彩色图；顺序不可当作判断依据，
按 `pix_fmt` 区分。解码器用 ffprobe 分流、ffmpeg 渲染：只有彩色流时输出 JPG，带 alpha
时合成 PNG，并在结果里报告 `container`、`streams`、`alpha`。缺少 `ffmpeg`/`ffprobe` 时
wxgf 文件报错，不输出猜测结果。

## 输出

JSON 顶层固定包含：

- `schemaVersion`: `lov-wdb-cli/v1`
- `command`
- `data`
- `meta`: 命中数、扫描范围、截断状态、可复制错误列表

JSONL 第一行为 `meta`，后续每行为一个 data item。文本格式只用于人工快速查看；
Agent 之间传递优先使用 JSON 或 JSONL。

`sql` 命令的 `data` 是原始行对象，`meta.databasePath` 与 `meta.query` 记录查询
来源。需要后续逐行精确回读时，SQL 应显式选择 `rowid`，再转用 `record`。

错误对象包含阶段、数据库、表名和后端等 debug 信息，但不包含数据库 key。
