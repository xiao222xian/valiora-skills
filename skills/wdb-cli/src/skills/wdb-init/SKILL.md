---
name: lov-wdb-init
description: >
  WDB Pro 密钥初始化：定位微信账号和数据库，扫描或捕获 SQLCipher 密钥，生成
  lov-wdb-cli 可读取的管理副本。Use when users need to get WeChat keys,
  initialize WDB data, or capture database keys on macOS.
license: MIT
compatibility: "macOS 10.15+, Python 3.9+, arm64/x86_64 wechat-key-scanner；无需关闭 SIP。"
depends_on: []
allowed-tools:
  - Bash
  - Read
  - Write
metadata:
  author: WDB Pro Team
  version: "0.1.0"
  card_standard: lovstudio/skill-card/v1
  content_class: deterministic-output
  tags:
    - wechat
    - sqlcipher
    - key-management
    - wdb-pro
---

# WDB Pro 密钥初始化 · Universal Key Initializer

在用户自己的 Mac 上准备微信数据库读取所需的密钥清单。Skill 只把密钥写入
私有管理副本，不输出密钥内容，也不修改已安装的微信应用。

## Triggers

### Activate when

- “帮我获取微信数据库密钥”“连接微信本地数据”“初始化 WDB 数据”。
- “微信版本更新后读取不到数据了”“先抓取密钥再查询聊天”。
- “Use this skill to initialize WeChat database keys”, “capture WeChat
  SQLCipher keys”, or “prep WDB Pro managed keys on this Mac”.

### Do not activate when

- 用户只想读取已有密钥或已解密数据库；交给 `lov-wdb-query`，
  不要把查询逻辑复制进本 Skill。
- 用户要修复 WDB Pro 的 Rust/Tauri 后端或修改 `wechat-key-scanner.c`；
  应在 `lovstudio/wdb-pro` 仓库处理。
- 用户只提供截图并要求 OCR；交给图片理解能力。

## User Profile (cross-session)

This module reads the shared `user-profile/v1` contract in `skill.yaml`.
Precedence is the current request, project context, Skill records, shared
preferences, shared user/brand profile, then safe defaults. Never persist a
key, token, or full private path into profile records.

## Skill Group Composition

This Skill is an upstream atom for the self-contained `lov-wdb-cli` Kit. It
owns extraction and managed-key writing; the downstream query module owns
reading. See `references/skill-composition.md`.

## Workflow (MANDATORY)

### Step 0: Resolve the runtime

1. Verify `scripts/wdb_init.py` and the architecture-specific binary under
   `assets/bin/`.
2. Confirm the scanner has `com.apple.security.cs.debugger` entitlement.
   The CLI prepares a private signed copy before execution.
3. Require explicit user intent. Extracting keys reads local WeChat memory or
   captures a passphrase during login and must not run without consent.
4. Read the CLI and file contract in
   `references/scanner-protocol.md` before invoking the scanner.

### Step 1: Diagnose

```bash
python3 "$SKILL_DIR/scripts/wdb_init.py" status
python3 "$SKILL_DIR/scripts/wdb_init.py" doctor
```

Read `wechat.version`, `requiresLoginCapture`, `scanner.selfTest.ok`,
`accounts[].keyCount`, and the current account. Do not guess an account when
more than one account exists.

### Step 2: Select the acquisition path

- `requiresLoginCapture=false` and WeChat is running: use `scan`.
- `requiresLoginCapture=true`: use `capture`. Ask the user to fully quit
  WeChat first; the CLI will create a disposable debuggable copy, wait for
  login, collect the passphrase, restore the original app, and write keys.
- A missing scanner or failed self-test: stop and return the `debug` object.

```bash
python3 "$SKILL_DIR/scripts/wdb_init.py" scan \
  --account ACCOUNT

python3 "$SKILL_DIR/scripts/wdb_init.py" capture \
  --account ACCOUNT --timeout 180
```

### Step 3: Verify and report

- Require `status: ready`, `databaseCount > 0`, and the managed key path.
- Never print `key`, `enc_key`, or passphrase values.
- Report account, database count, managed key path, and whether capture was
  used. If capture required a relogin, tell the user it completed and that the
  original WeChat app was restored.

## Dependencies

- macOS 10.15+
- Python 3.9+
- Native `wechat-key-scanner` binaries for arm64 and x86_64
- `/usr/bin/codesign`, `/usr/bin/plutil`, `/bin/cp` for the disposable copy

## Validation

```bash
python3 scripts/test_wdb_init.py
python3 scripts/wdb_init.py doctor
```

## Runtime context (shared)

Read `skill.yaml` at the start of each run. The host supplies
`skill-runtime/v1`; resolve values in the documented order and keep keys,
tokens, and private paths out of durable records and user-facing diagnostics.
