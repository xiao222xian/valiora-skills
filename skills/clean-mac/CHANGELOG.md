# Changelog

## [0.6.0] - 2026-09-26

### Added

- `list-staged` 与 `purge-staged` 支持 `migrate` 留下的 `<name>.migrated` 回滚项，新增可重复的 `--archive-root`。
  回收前读取归档根目录的迁移日志，确认原路径仍是解析到记录目标的符号链接且归档目标存在；不满足时
  `list-staged` 标记为 `blocked` 并给出原因，`purge-staged` 整条拒绝，删除每个 `.migrated` 项前再复核一次。
- 回滚根目录可以是 `~/.Trash` 的子目录，与 `migrate --rollback-root` 保持一致即可。

### Fixed

- 迁移到 HFS+ 归档卷后，`--verify metadata` 把 NFD 文件名误判为 `missing` + `extra`（如带重音或日文浊音的
  文件名）。清单改按 Unicode NFC 比对，规范化后重名直接报错；`--verify checksum` 按两侧实际磁盘路径配对。
- `migrate` 生成的回滚项只能手动删除，与 Step 6 的精确回收流程不一致。

### Changed

- `list-staged` 的 `total_bytes` / `total_gb` 只统计 `pending` 项。

## [0.5.0] - 2026-09-14

### Added

- 引用感知保护：扫描 Obsidian vault 插件、Chromium 系浏览器未打包扩展、VS Code 扩展、`npm`/`pnpm` link
  与 Agent Skill 链接，把被指向的目录标记为 `in-use`，不进自动计划，`stage-cleanup` 与 `migrate` 直接拒绝。
- 候选新增 `accessed_at` 字段与 `recently-accessed` 分类，供人工复核参考。

### Fixed

- `dist`、`build` 等名称在白名单内即被当作可重建产物，导致作为插件或扩展安装位置的构建目录被清掉、
  对应集成静默失效。

### Notes

- 访问时间只作信号：一次全盘备份或迁移会把大批文件的 atime 刷新到同一天，因此不用它拦截或保留候选。

## [0.4.1] - 2026-09-07

### Added

- 统一展示名为「Mac 清理助手」，保持调用 ID 与能力契约。

## [0.4.0] - 2026-08-26

### Added

- protect application-managed recording workspaces
- block cleanup and migration of Screen Studio recordings and overlapping protected paths

## [0.3.0] - 2026-08-23

### Added

- rename public Skill identifier to lov-clean-mac
- preserve legacy trigger discovery and existing preference/storage contracts
- add portable npx installation instructions and frontmatter compatibility validation

## 0.2.0

- 增加 `list-staged` 与 `purge-staged`，只按显式 `.cleanup` 路径回收本轮回滚项。
- 移除最终流程对 Finder 批量删除和自动重试的依赖，避免锁定项目引发连续确认弹窗。
- 为多路径 `stage-cleanup` 增加失败回滚与结构化错误状态。
- 增加直接文件系统回收的回归测试，并更新运行手册与安全边界。

## 0.1.0

- 创建目标容量驱动的 macOS 磁盘优化工作流。
- 增加只读盘点、最小计划、归档卷预检、可回滚清理、事务式迁移和真实容量验收 CLI。
- 增加稳定归档结构、保护数据分类、失败恢复与可移植用户配置。
