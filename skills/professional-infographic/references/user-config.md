# User configuration

This public skill must not depend on a specific personal machine. Brand assets,
design guides, identity, and output paths use the following resolution order:

1. explicit CLI flags;
2. skill-specific environment variables;
3. shared environment variables;
4. shared user profile;
5. packaged public default;
6. ask once when the operation requires a value that still cannot be resolved.

## Shared profile

Default path:

```bash
${SKILL_PROFILE_PATH:-$HOME/.skill-publisher/skills/profile.json}
```

Relevant shape:

```json
{
  "workspace": {
    "output_dir": "$HOME/Documents/lov-skill-output"
  },
  "brand": {
    "name": "Your Brand",
    "profile": "$HOME/.skill-publisher/skills/professional-infographic-brand.json",
    "design_guide": "$HOME/.skill-publisher/skills/design-guide.md"
  }
}
```

## Environment variables

| Variable | Meaning |
|---|---|
| `SKILL_PROFILE_PATH` | Shared profile JSON |
| `SKILL_DESIGN_GUIDE` | Optional brand/design guide |
| `SKILL_OUTPUT_DIR` | Shared output directory |
| `SKILL_PROFESSIONAL_INFOGRAPHIC_BRAND_PROFILE` | Skill-specific brand profile |
| `SKILL_PROFESSIONAL_INFOGRAPHIC_OUTPUT_DIR` | Skill-specific output root |

CLI values take precedence over every variable.

## Initialize a brand

```bash
python3 "$SKILL_DIR/scripts/infographic_cli.py" init-brand \
  --name "Your Brand" \
  --logo "/absolute/path/to/logo.svg" \
  --site "https://example.com" \
  --primary "#1F2937" \
  --accent "#4F46E5" \
  --paper "#F7F4EF" \
  --attribution "Powered by"
```

Default output:

```text
${SKILLS_CONFIG_DIR}/professional-infographic-brand.json
```

The command refuses to overwrite an existing profile unless `--force` is
provided.

## Portability rules

- Expand `$HOME` and `~` only at runtime.
- Resolve a relative logo path from the brand-profile directory.
- Embed the resolved logo into generated HTML; do not leave a private local path.
- Never copy a private design guide into a public repository.
- Store packaged brand defaults in one profile, not throughout the workflow.
- Treat `SKILL_PROFILE_PATH` as the shared profile only. Resolve its
  `brand.profile` entry instead of parsing the shared profile as a brand profile.
- Prefer `attribution`; accept legacy `copyright` for existing version-1 profiles.
- Generated project metadata may record the resolved profile path locally, but
  published examples must use repository-relative or packaged paths.
