# CLI Contract — lov-wxmp-cli

## Project

- Name: wxmp
- Backend: vendored wcx
- Console command: `lov-wxmp-cli`
- Package: `lov_wxmp_cli`

## Built-in commands

- `doctor` checks the project root and backend runtime.
- `info` reports project and harness identity.
- `capabilities` returns the complete machine-readable command inventory.

## Project-specific commands

| Command | Mutates | Description |
|---|---:|---|
| `status` | no | 查看本地登录配置与缓存概况 |
| `accounts` | no | 列出已缓存的公众号 |
| `articles` | no | 检索公众号缓存文章 |
| `article` | no | 读取一篇缓存文章 |
| `export` | yes | 导出公众号缓存文章 |
| `search` | no | 在线搜索公众号 |
| `fetch` | yes | 采集已选定公众号的文章 |

## JSON and exit behavior

Use global `--json` before the command. Exit code 0 means success; 2 is usage or
contract failure; 3 is a missing runtime/project dependency; 4 is backend or
postcondition failure; 5 is an unsafe/conflicting state.

## Backend boundary

The CLI must call the project's real executable, API, protocol, or native
renderer. Generated fixed argv prefixes are executed with `shell=False`.

## State and safety

`accounts`, `articles`, `article`, `status` use the native SQLite cache in read-only
transactions. `doctor` never creates a cache. `search` is read-only for article
data but updates wcx request-guard state. `fetch` uses the same maintained wcx
command used by the app, including its cross-process request guard and incremental
commits. Its result is checked for account identity, list availability, and saved
account/record count. A valid zero-item response differs from unavailable results.

`export` reserves a new destination, invokes wcx exporters in staging, and reads
back records and file hashes. It never overwrites an existing path; article folders
use SHA-256 of article identity to avoid title collisions. `manifest.json` is the
completion record. There is no CLI undo or REPL; native incremental fetch is
resumable, while repeating an export to the same target returns conflict.

JSON success: `ok`, `command`, `data`, `meta.duration_ms`.
JSON failure: `ok=false`, `command`, `error.code`, `error.message`,
`error.context_id`, `error.hint`. Errors never echo raw network exceptions.
Exit codes: 0 success; 2 arguments; 3 dependency/cache missing; 4 runtime or
postcondition failure; 5 selection/output conflict; 130 interrupted.
For parse failures the command may be `help` because parsing did not complete.

Global configuration: `--project-root` > `LOV_WXMP_PROJECT_ROOT` >
`LOV_CLI_PROJECT_ROOT` > editable source location. Cache: `--db` > `LOV_WXMP_DB`
> wcx platform default. Global options precede subcommands. Distribution is local
editable installation; wheel installations need an explicit project root and the
same vendored wcx installed in their environment.
