# Changelog

## [0.6.4] - 2026-10-30

### Fixed

- `chats --query` 纯文本行的 SQL 预筛改为不区分大小写：此前 `instr` 按原样比较，而解压后的
  匹配不区分大小写，英文关键词会漏掉大小写不同的纯文本消息（`--query ai` 查不到「AI 课程」）。
  现在预筛两边先转小写；SQLite 的 `lower()` 只折叠 ASCII，关键词含 É、Ж 这类其他大小写字母时
  纯文本行不做预筛，交给解压后的匹配
- 引用回复的 `quoted.createTime` 遇到毫秒时间戳时整条 `chats` 崩溃（`year 58768 is out of
  range`）：被引用消息的时间改走与正文相同的换算，`quoted.timestampUnix` 统一为秒。大小写修正让
  更多关键词命中这类消息，真实分库上 `--query ai` 已能触发
- 回归测试：英文关键词大小写不同、关键词含非 ASCII 大小写字母时都能查到纯文本消息；被引用
  消息时间为毫秒时正常输出

## [0.6.3] - 2026-10-30

### Fixed

- `--contact X` 的原值总会并入匹配：此前只在联系人表里一个都匹配不到时才回退到原值，而联系人
  匹配是子串匹配，X 只要是别的联系人账号、昵称、备注或别名的一部分，X 本人（已删除的好友、
  旧账号）的聊天和朋友圈就查不到。现在 `chats`、`moments`、`moments-media`、`stats` 都把原值
  当作账号精确匹配并入结果，不会因此多带进昵称相同的人
- 回归测试：值同时是另一个联系人账号的一部分时，`moments`、`chats`、`stats` 仍能查到它本人

## [0.6.2] - 2026-10-29

### Fixed

- `moments`、`moments-media`、`stats` 的 `--contact X` 在 X 不在任何联系人表里时（已删除的好友、
  旧账号）静默返回 0 条：作者白名单取自联系人匹配结果，匹配为空就过滤掉了全部帖子。现与 `chats`
  一致，回退到按原值精确匹配作者；同名联系人仍各自保留 `authorId`，不合并
- 用密钥文件（含 `--account`）时，`moments`、`moments-media`、`contacts`、`cover` 不再为账号下
  每个数据库建隔离快照：联系人查询跳过 Message、HeadImage、Sns 类型的库，`SnsTimeLine` 跳过
  Message、HeadImage 类型的库，过滤后一个不剩时回退到全部库，`--database` 指定的库一律读取。
  本机同一条 `moments` 查询从 23 个库、约 7 GB 降到 13 个库、约 1 GB，命中数不变；`chats`、
  `stats` 仍要复制全部消息库
- 回归测试：联系人表里查不到的作者、同名联系人、按库类型限定的快照范围，以及 `--database`
  与自定义标注的朋友圈库仍被读取

## [0.6.1] - 2026-10-29

### Fixed

- `chats --query` 被 `--limit` 静默截断：此前每个 400 表批次先在 SQL 里按时间取 `limit + 1` 行，
  再在 Python 里匹配关键词；BLOB 正文（微信 4.x 多为 zstd）无条件通过 SQL 预筛，较新的图片、
  表情占满窗口后命中被挤掉，`--limit 5` 返回 0 条且 `truncated: false`。现关键词检索不在 SQL
  里截断：先列出全部候选行的 rowid 与时间，再按时间倒序每 2000 行读取并解压正文匹配，凑够
  `limit + 1` 条命中即停
- 只有 `zstd` 命令、没有 `zstandard` 模块时，一个正文块只起一个 `zstd` 进程：帧拼接后统一
  解压，再按帧头声明的解压长度切回各行，未声明长度或输出总长对不上时退回逐条解压。关键词
  检索要解压全部候选正文，逐条起进程时约 1 GB 的分库实测 66 分钟，现约 65 秒，与装了
  `zstandard` 模块相当
- `chats` 与 `stats` 超出 `--limit` 时保留最新的 limit 条，输出仍按时间正序。此前合并各批次、
  各库后按正序截取，会丢掉最新一条、返回中间一段
- `chats` 的 `truncated` 如实反映：还有命中没返回，或有库、表、正文块因错误没读完时为 true；
  命中恰好等于 `--limit` 时不再误报 true
- 回归测试：合成的 BLOB 正文挤占窗口、401 张表跨批次与跨库截取、查询失败时的 `truncated`，
  以及 zstd 帧头各种长度字段、无模块时同块正文共用一个 `zstd` 进程与坏帧整批回退

## [0.6.0] - 2026-10-29

### Added

- `moments-media` 子命令：下载朋友圈原图。取 `<media><url>` 全文改为 https、补 `token` 与
  `idx=1`，UA 为 `MicroMessenger Client`；响应头 `x-Enc: 1` 时以 media key 为种子，按
  rand_isaac `from_seed`（两轮初始化、大端 u64）生成 ISAAC-64 密钥流异或解密。视频和视频号
  卡片不下载，防盗链占位图记为失败，同名文件已存在时跳过请求；`--output` 不能位于微信数据
  目录内，结果与日志不含 URL、key、token
- `moments --feed-id` 可重复；`meta` 新增 `scannedRows` 与 `matchedCount`
- 回归测试：rand_isaac 0.5.0 官方 ISAAC-64 向量、x-Enc 往返解密、占位图、输出目录门禁，
  以及合成的微信 4.x `SnsTimeLine`（时间只在 XML 里、rowid 顺序不等于时间顺序）

### Fixed

- `moments` 区间查询被 `--limit` 静默截断：此前先按 rowid 倒序取 `limit + 1` 行，再在
  Python 里按作者和日期过滤；微信 4.x 没有时间列，2021 年区间查询返回 0 条且
  `truncated: false`。现先扫描全部行的作者与 `<createTime>`，按时间截断后再取正文；
  还有命中未返回、或有库/表因错误未扫完时 `truncated` 为 true。`stats` 的朋友圈统计同步修正
- `skills/wdb-query/references/data-contract.md` 补齐此前只写进 Kit 根目录的「媒体图片」一节

## [0.5.4] - 2026-10-04

### Changed

- Remove the encrypted `public/` bundle; paid Skills now install as plain files after purchase.

## [0.5.3] - 2026-09-23

### Fixed

- `decode_wechat_v4_dat.py` 支持 `wxgf`（微信封装的 HEVC）明文：此前中间图、高清图
  解密成功却因不是 JPEG/PNG 被判为 `no key material decoded this file`，只能退回缩略图。
  现在按 VPS 起始码切流、用 ffprobe 的 `pix_fmt` 分出彩色流与灰度 alpha 流（alpha 在前），
  彩色图转 JPG、带 alpha 合成 PNG；结果新增 `container`、`streams`、`alpha`
- 新增 wxgf 回归测试：用 libx265 生成单流与 alpha+彩色双流样本，经 V2 容器加密后完整解码

## [0.5.2] - 2026-09-11

### Changed

- 明确对外产物的来源线：由本 Skill 数据生成的卡片、文章、报告不得出现本机数据库路径、
  库文件名、表名、`wxid_` 账号或本机工具名，统一写「来源：群聊记录」；内部留痕只放工作目录

## [0.5.1] - 2026-09-11

### Added

- `skills/wdb-query/scripts/decode_wechat_v4_dat.py`：解码微信 4.x 加密图片
  `.dat`（V2 容器），自动发现 kvcomm code、校验图片签名与 PNG chunk CRC，
  输出默认落在当前目录而不写回微信数据目录
- `references/data-contract.md` 新增「媒体图片」一节：容器结构、密钥推导与
  `packed_info_data` → `msg/attach/.../Img/<mediaId>[_h|_t].dat` 的定位规则
- 维护备注补充群成员名单的枚举方式（`chatroom_member` + `name2id.rowid`、
  `chat_room.ext_buffer`）

### Fixed

- 记录并规避 `chats --query` 的漏检：关键词过滤在批次取回之后进行，
  `--limit` 偏小会静默返回 0 条；关键词检索需 `--limit` ≥ 2000 或缩小时间窗
- 记录 AES 段跨度为 `(aes_size // 16 + 1) * 16`：把已对齐的 `aes_size` 当明文长度
  会破坏图片中段，PNG 仍能打开但 IDAT CRC 失败

## [0.5.0] - 2026-09-10

### Added

- `messageType` 按正文 `<appmsg><type>` 判定，并新增 `appType` 保留原始编号
- 引用回复输出 `quoted`：`senderUsername`、`senderName`、`content`、`rawType`、
  `createTime`、`timestampUnix`、`serverId`

### Fixed

- 群消息正文带 `发送者username:\n` 前缀，XML 判定失败导致 `type=57` 引用回复被
  降级为 `unknown`，把「引用别人的话再回 +1」误读成报名
- `text` 改为剥离群聊发送者前缀，`rawContent` 保留原始字节，`senderUsername`
  在 `Name2Id` 解析不到时回退到该前缀
- 类型命名只覆盖在真实微信载荷中验证过的编号（`57` 引用回复、`62` 拍一拍），
  其余一律记为 `app`，不猜测未验证编号的语义

## 0.4.0

- Convert `lov-wdb-cli` to a self-contained Skill Kit.
- Add `skills/wdb-init`: WDB Pro key scan, WeChat 4.1.10+ login capture,
  managed-key writing, and native scanner self-test.
- Move existing SQLCipher query logic into `skills/wdb-query`.
- Gate encrypted queries behind a verified managed key source.

## [0.3.1] - 2026-09-08

### Fixed

- 修复微信数据库读取的共享内存干扰风险
- 所有读取使用私有 DB+WAL 副本，复制不稳定时明确失败，保留原始记录身份
- 15 项回归测试与真实联系人库检查通过；微信运行中稳定性尚未验证

## [0.3.0] - 2026-08-24

### Added

- add the shared feedback-classification and approval-invalidation gate used by every LovStudio Skill

## [0.2.4] - 2026-09-07

### Fixed

- 隔离数据库读取，避免影响微信共享内存
- SQLite 与 SQLCipher 仅查询私有 DB+WAL 副本，保留原始记录身份
- 复制变化时有界重试并明确失败，覆盖 WAL、源文件不变与异常清理回归

## [0.2.3] - 2026-09-07

### Added

- 统一展示名为「万能微信秘钥」，保持调用 ID 与能力契约。

## [0.2.2] - 2026-09-07

### Fixed

- 采用用户确认的展示名「万能微信秘钥」，修正此前将产品名机械改为功能说明的命名。

## [0.2.1] - 2026-09-07

### Fixed

- 统一展示名称为「微信数据读取」，保留原有调用 ID 与能力边界。

## [0.2.0] - 2026-08-22

### Added

- 支持自动发现和解析 WDB Pro 管理密钥副本
- 优先读取 ai.lovstudio.wdb-pro 应用数据目录，并兼容旧 app id 迁移路径
- 验证 64 位十六进制密钥与 cipherCompatibility，诊断输出不包含密钥

## [0.1.2] - 2026-08-14

### Fixed

- rename public skill to 万能微信秘钥
- 统一 SKILL、README、manifest 与平台展示名称及描述
- 补齐 compatibility 元数据和标准安装命令
- 修复命名空间迁移遗留的非法 SQL 子查询别名，恢复通用只读 SQL 查询

## 0.1.1

- 移除运行时对源码发布验证器的引用，使平台安装包保持自包含。

## 0.1.0

- 首次提供自由查看与检索微信数据库的命令行能力。
- 支持聊天、联系人、朋友圈互动、封面、统计与稳定行身份读取。
- 支持 WDB TOML、DTrace `.keys`、wechat-cli JSON 和已解密 SQLite。
- 增加通用 schema 浏览和受限只读 SQL，覆盖未预先枚举的数据类型。
