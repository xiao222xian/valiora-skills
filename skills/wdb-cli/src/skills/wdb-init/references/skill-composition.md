# Skill Group Composition

## Nearby Skills Inspected

- `lov-wdb-cli` v0.3.1: only consumed existing keys and decrypted databases.
  This Skill supplies the missing upstream step.
- `lov-wdb-query` in the same package: reads managed keys and owns isolated
  query semantics.
- WDB Pro desktop source in `lovstudio/wdb-pro`: owns the native scanner and
  portable managed-copy logic. It is the implementation source, not a Skill.

## Atomic Handoffs

1. Input: local macOS WeChat installation and an optional account selector.
2. Output: `wdb-pro-managed-keys.json` under the WDB Pro Application Support
   directory.
3. Downstream owner: `lov-wdb-query`.
4. Acceptance: `status: ready`, `databaseCount > 0`, no key printed, original
   WeChat app restored after capture.

## Overlap Decisions

No extraction logic is duplicated in the query module. Scanner binaries, C
source, and entitlements are vendored once in this Skill's `assets/` directory.

## Composition Decision

This is an upstream atom inside the self-contained `lov-wdb-cli` Kit. External
sibling dependencies are not required: the Kit ships both modules and runs
the `full` pipeline.
