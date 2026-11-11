# 万能微信秘钥 · Universal WeChat Key

![Version](https://img.shields.io/badge/version-0.6.4-CC785C)

一把面向本地微信数据的通用钥匙：让 Agent 使用已有密钥或已解密数据库，自由查看、检索并精准读取聊天、联系人、朋友圈、封面、统计及其他微信数据，输出适合分析、归档和自动化处理的结构化结果。

该模块是 `lov-wdb-cli` Skill Kit 的查询层。密钥准备由
`../wdb-init` 负责；没有 `wdb-pro-managed-keys.json` 时先运行
`scripts/wdb_init.py scan` 或 `scripts/wdb_init.py capture`。

## 特点

- 自动发现 WDB Pro 管理副本，兼容新 app id `ai.lovstudio.wdb-pro` 与旧 app id 迁移路径
- 兼容 `wdb-pro-managed-keys.json`、`keys.toml`、DTrace `.keys`、wechat-cli `all_keys.json`
- 支持加密 SQLCipher 数据库和已解密 SQLite
- 查询仅在私有 DB + WAL 副本上执行，避免外部数据库引擎操作微信的共享内存
- 每条记录携带 `databasePath + tableName + rowid` 稳定身份
- 可浏览任意数据库结构，并执行单条受限只读 SQL，适配未知表和版本变化
- 为聊天、联系人、朋友圈、封面和统计等高频任务提供语义化快捷命令
- JSON、JSONL 和简洁文本三种输出
- 密钥仅通过 SQLCipher 标准输入使用，不进入命令行参数或诊断输出

## 本地安装

从 LovStudio 统一目录安装：

```bash
npx skills add lov-wdb-cli -g -y
```

或链接当前源码目录：

```bash
export SKILL_SOURCE_DIR="$(pwd)"
mkdir -p "${SKILL_SKILLS_INSTALL_DIR:?请设置本地 Skills 目录}"
ln -s "$SKILL_SOURCE_DIR" \
  "$SKILL_SKILLS_INSTALL_DIR/lov-wdb-cli"
```

当前源码若已由 Skill Creator 安装，可核对：

```bash
readlink "$SKILL_SKILLS_INSTALL_DIR/lov-wdb-cli"
```

## 依赖

基础环境：

```bash
python3 --version
```

读取加密数据库：

```bash
brew install sqlcipher
```

解析微信 4.x 或旧版压缩正文（推荐）：

```bash
python3 -m pip install zstandard lz4
```

## 使用

先诊断数据源：

```bash
python3 scripts/wdb_cli.py doctor
```

CLI 会优先读取 WDB Pro 保存的私有管理副本：
`~/Library/Application Support/ai.lovstudio.wdb-pro/database-keys/wdb-pro-managed-keys.json`。
也可用 `--keys PATH` 或 `WDB_KEYS_FILE` 显式覆盖自动发现结果。

查某天与某人的聊天：

```bash
python3 scripts/wdb_cli.py --keys /path/to/keys.toml chats \
  --date 2026-08-01 --contact "张三" --format jsonl
```

获取好友资料与朋友圈封面：

```bash
python3 scripts/wdb_cli.py --keys ~/.wechat-cli/all_keys.json contacts --match wxid_example
python3 scripts/wdb_cli.py --keys ~/.wechat-cli/all_keys.json cover --contact wxid_example
```

读取朋友圈互动或自然日统计：

```bash
python3 scripts/wdb_cli.py --keys ~/.wechat-cli/all_keys.json moments --date 2026-08-01
python3 scripts/wdb_cli.py --keys ~/.wechat-cli/all_keys.json stats --date 2026-08-01
```

下载朋友圈原图（`x-Enc` 加密图自动解密，不能保存到微信数据目录内）：

```bash
python3 scripts/wdb_cli.py --keys ~/.wechat-cli/all_keys.json moments-media \
  --contact wxid_example --date 2026-08-01 --output ./moments-originals
```

查看未知数据或新版本表结构：

```bash
python3 scripts/wdb_cli.py --keys ~/.wechat-cli/all_keys.json schema --table favorite
python3 scripts/wdb_cli.py --keys ~/.wechat-cli/all_keys.json sql \
  --database /path/to/favorites.db \
  --query 'SELECT rowid, * FROM Favorites ORDER BY rowid DESC LIMIT 20'
```

按稳定身份精确读取一行：

```bash
python3 scripts/wdb_cli.py --keys /path/to/keys.toml record \
  --database /path/to/msg_0.db --table Msg_HASH --rowid 42
```

所有命令都可使用 `--format json|jsonl|text`。全局参数放在子命令前，
子命令参数放在子命令后。

## 数据契约

见 [references/data-contract.md](references/data-contract.md)。

读取时先复制数据库及其 WAL，不复制微信的 `-shm`。复制前后检查文件身份、大小及
修改时间；变化时最多尝试三次，仍不稳定则返回 `snapshot` 错误，绝不直连原库。
临时目录权限为 `0700`，副本权限为 `0600`，保留加密状态，命令退出时清理。
需要足够容纳本次所访问数据库及 WAL 的临时空间；强制终止进程时可能残留私有副本。
结果是每个库在本次调用中的固定副本，不是跨库原子快照；再次调用会重新复制。

## 质量门

```bash
python3 scripts/test_wdb_cli.py
python3 scripts/validate_skill.py .
```

## License

MIT
