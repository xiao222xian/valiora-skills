# Skill Group Composition

## Nearby Skills Inspected

- `lov-wdb-cli` installed 0.3.1: only consumes existing keys and decrypted
  databases; it lacked the key acquisition stage.
- `lov-wdb-init` (new): implements WDB Pro's native scanner and login capture
  orchestration. It is the upstream atom for this package.
- `lov-wdb-query` (new): owns the original query/database semantics and stable
  record identity. It is the downstream atom.
- `wechat-key-scanner` inside `lovstudio/wdb-pro`: native macOS binary and
  source; no Agent Skill routing contract, so it is an asset, not a skill.

## Atomic Handoffs

1. `lov-wdb-init` receives a local macOS WeChat installation plus optional
   `--db-dir` / `--account`.
2. `lov-wdb-init` emits private `wdb-pro-managed-keys.json` under
   `~/Library/Application Support/ai.lovstudio.wdb-pro/database-keys/`.
3. `lov-wdb-query` receives the managed key path and emits structured JSON
   records with `databasePath + tableName + rowid`.
4. Root `lov-wdb-cli` owns the user acceptance criterion: keys exist, then the
   requested query returns without opening WeChat live DBs.

## Overlap Decisions

The old query CLI already had correct snapshot, SQLCipher, and record identity
logic. We reuse it unchanged inside `skills/wdb-query`; only the orchestration
and key-gating are new. No duplicate key parser or scanner was introduced.

## Composition Decision

This is a self-contained Skill Kit. Key preparation and querying are hard
coupled for one user-visible result, so both modules ship inside the paid
package rather than as external sibling dependencies.
