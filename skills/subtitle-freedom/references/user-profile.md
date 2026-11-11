# User Profile contract

`lov-subtitle-freedom-skill` is connected to the shared `user-profile/v1`
contract. Independent sessions read the same user, brand, workspace,
preferences, and `skills.lov-subtitle-freedom-skill` scopes.

## Resolution order

Resolve values in this order:

1. The current request.
2. Project or media context.
3. This Skill's durable records.
4. Shared preferences and user/brand Profile fields.
5. Safe defaults declared in `skill.yaml`.

The learning level is a minimum difficulty floor. The brand Logo is read from
`brand.logo`; artistic ASS watermarks use that Logo by default and keep the
resolved path out of the committed Skill source.

## Persist direct user statements

When the user states a preference intended for later sessions, write it to the
shared Profile under `skills.lov-subtitle-freedom-skill.records` or to the
explicit shared `brand` / `user` scope. Use the local `profile_store.py` helper
with `--confirm`, and report the canonical Profile path after saving:

```bash
python3 scripts/profile_store.py record \
  --skill-id lov-subtitle-freedom-skill \
  --path records.watermark \
  --value '{"enabled":true,"source":"brand.logo"}' \
  --confirm
```

Do not persist inferred values, credentials, tokens, cookies, or secret-like
fields. The Profile writer preserves unrelated Skills and brand fields and
uses an atomic replacement.
