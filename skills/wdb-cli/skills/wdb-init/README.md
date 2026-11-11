# lov-wdb-init

![Version](https://img.shields.io/badge/version-0.1.0-CC785C)

为本地微信准备 SQLCipher 数据库密钥，并写入 WDB Pro 管理的私有 JSON 文件。
支持内存扫描与微信 4.1.10+ 登录期捕获，不要求关闭 SIP。

## 本地安装

```bash
export SKILL_SOURCE_DIR="$(pwd)"
mkdir -p "${SKILL_SKILLS_INSTALL_DIR:?请设置本地 Skills 目录}"
ln -s "$SKILL_SOURCE_DIR" \
  "$SKILL_SKILLS_INSTALL_DIR/lov-wdb-init"
```

## 使用

诊断本机状态：

```bash
python3 scripts/wdb_init.py status
python3 scripts/wdb_init.py doctor
```

旧版微信可先尝试内存扫描：

```bash
python3 scripts/wdb_init.py scan --account ACCOUNT
```

微信 4.1.10+ 使用登录期捕获：

```bash
python3 scripts/wdb_init.py capture --account ACCOUNT --timeout 180
```

成功输出会包含 `managedKeys` 路径，不包含密钥值。查询请使用
`lov-wdb-query` 的 `wdb_cli.py`。

扫描器与密钥文件契约见
[`references/scanner-protocol.md`](references/scanner-protocol.md)。

## 验证

```bash
python3 scripts/test_wdb_init.py
python3 scripts/wdb_init.py doctor
```

## License

MIT。原生 scanner 许可见 `assets/THIRD_PARTY_NOTICES.md`。
