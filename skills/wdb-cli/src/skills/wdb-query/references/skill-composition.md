# Skill Group Composition

## Nearby Skills Inspected

- `lov-wdb-init`: prepares `wdb-pro-managed-keys.json` from a local WeChat
  installation. It is the required upstream atom for encrypted database access.
- `lov-wdb-cli` root: owns the combined user outcome "get keys, then query".
  It composes this module instead of duplicating key discovery.
- `lov-wdb-cli` old standalone source: kept as compatibility knowledge, but the
  query capability is now an embedded module of the same package.

## Atomic Handoffs

1. Upstream: `lov-wdb-init` writes
   `~/Library/Application Support/ai.lovstudio.wdb-pro/database-keys/wdb-pro-managed-keys.json`.
2. Ownership: `lov-wdb-init` owns correctness of extraction and account scoping.
3. Downstream: this module reads the managed JSON through `wdb_cli.py` and owns
   query correctness, isolated snapshots, and stable record identity.
4. Acceptance: downstream starts only after upstream reports `status: ready`.

## Overlap Decisions

No overlap was found. The old `wdb_cli.py` only consumed keys; it intentionally
never duplicates scanner or login-capture logic.

## Composition Decision

This is a Kit module inside the self-contained `lov-wdb-cli` package. The
upstream key extraction is an embedded module, not an external sibling skill,
so users cannot install half the pipeline or bypass the paid package.
