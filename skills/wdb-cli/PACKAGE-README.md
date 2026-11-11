# 万能微信秘钥 · Universal WeChat Key

![Version](https://img.shields.io/badge/version-0.6.4-CC785C)

一个自包含 Skill Kit：先为本地微信准备密钥，再用隔离的 DB+WAL 副本读取聊天、
联系人、朋友圈、封面和任意表结构。

## 架构

```text
lov-wdb-cli
├── skills/wdb-init      # 获取 WDB Pro 管理的数据库密钥
└── skills/wdb-query     # 使用密钥读取 SQLCipher 数据库
```

`kit.yaml` 的 `full` 管线保证 `wdb-init` 先于 `wdb-query` 执行。
`lov-wdb-init` 当前作为付费包的内嵌模块分发，不单独列出免费入口；后续需要
独立上架时再拆出 catalog。

## 本地安装

```bash
npx skills add lov-wdb-cli -g -y
```

源码安装：

```bash
export SKILL_SOURCE_DIR="$(pwd)"
mkdir -p "${SKILL_SKILLS_INSTALL_DIR:?请设置本地 Skills 目录}"
ln -s "$SKILL_SOURCE_DIR" \
  "$SKILL_SKILLS_INSTALL_DIR/lov-wdb-cli"
```

## 使用

先诊断：

```bash
python3 skills/wdb-init/scripts/wdb_init.py status
python3 skills/wdb-init/scripts/wdb_init.py doctor
```

没有密钥时，根据诊断运行：

```bash
python3 skills/wdb-init/scripts/wdb_init.py scan \
  --account wxid_example

python3 skills/wdb-init/scripts/wdb_init.py capture \
  --account wxid_example --timeout 180
```

微信 4.1.10+ 使用 `capture`；成功后会写入
`~/Library/Application Support/ai.lovstudio.wdb-pro/database-keys/wdb-pro-managed-keys.json`。

然后查询：

```bash
python3 skills/wdb-query/scripts/wdb_cli.py chats \
  --date 2026-08-01 --contact "张三" --format jsonl

python3 skills/wdb-query/scripts/wdb_cli.py contacts \
  --match wxid_example

python3 skills/wdb-query/scripts/wdb_cli.py moments-media \
  --contact wxid_example --date 2026-08-01 --output ./moments-originals
```

## 依赖

- macOS；需使用与芯片匹配的 `wechat-key-scanner` 二进制
- Python 3.9+
- Homebrew `sqlcipher`（加密库）
- 可选 `zstandard`、`lz4`
- 可选 `ffmpeg`（解码 wxgf 图片）

## 质量门

```bash
python3 skills/wdb-query/scripts/test_wdb_cli.py
python3 skills/wdb-init/scripts/wdb_init.py doctor
python3 scripts/validate_skill.py .
```

## License

MIT。原生 scanner 的第三方许可见
[`skills/wdb-init/assets/THIRD_PARTY_NOTICES.md`](skills/wdb-init/assets/THIRD_PARTY_NOTICES.md)。
