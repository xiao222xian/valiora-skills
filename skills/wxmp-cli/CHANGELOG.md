# Changelog

## 0.1.2 — 2026-10-04

- Run the bundled scripts directly with `python3 "$SKILL_DIR/scripts/wxmp_cli.py"`; paid Skills now install as plain files, so the helper `exec` entry and the release packer are gone.

## 0.1.1 — 2026-09-08

- 包含匹配的 CLI 与采集引擎，无需 app 源码即可使用。
- 增加付费 helper 执行入口，临时运行代码在退出后清理。
- 复用真实缓存读取和四种格式导出验证；在线成功采集尚未现场验证。

## 0.1.0 — 2026-09-08

- 建立公众号缓存检索、文章读取、导出与授权采集命令。
