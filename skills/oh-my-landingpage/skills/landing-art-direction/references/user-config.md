# Landing Module User Configuration

Resolve values from the current request, repository, environment, and shared
profile in that order:

```bash
${SKILL_PROFILE_PATH:-$HOME/.skill-publisher/skills/profile.json}
```

Use `brand` for identity sources, profile, design/voice guides, and asset
directory. Use `oh_my_landingpage` for market, locale, brand goal, primary
conversion, media, analytics, and output. Product evidence wins over generic or
stale profile language.

Infer before asking. Ask once only when a missing user-facing choice changes the
result. Credentials stay in environment or a credential store.
