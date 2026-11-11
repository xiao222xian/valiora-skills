# User Configuration

This Skill is portable. It does not assume a private workspace or one brand.
Resolve values from the task and repository before persistent configuration.

## First-run behavior

1. Inspect the request, repository, existing page, brand files, and assets.
2. Read environment overrides and the shared profile.
3. Infer market, locale, conversion, media, and analytics from current evidence.
4. Ask once only for a user-facing choice that remains ambiguous and changes the result.
5. Show non-secret values before saving them with the user's knowledge.

Do not ask whether configuration is needed or create a hidden internal mode.

## Shared profile

```bash
${SKILL_PROFILE_PATH:-$HOME/.skill-publisher/skills/profile.json}
```

Recommended fields:

```json
{
  "workspace": {
    "root": "$HOME/projects",
    "output_dir": "$HOME/Documents/landing-page-output"
  },
  "brand": {
    "name": "Your Brand",
    "site": "https://example.com",
    "profile": "$HOME/.skill-publisher/skills/brand.json",
    "design_guide": "$HOME/.skill-publisher/skills/design-guide.md",
    "voice_guide": "$HOME/.skill-publisher/skills/voice-guide.md",
    "asset_dir": "$HOME/.skill-publisher/skills/brand-assets"
  },
  "oh_my_landingpage": {
    "brand_goal": "clarify",
    "market": "overseas",
    "locale": "en",
    "primary_conversion": "start_trial",
    "preferred_image_provider": "auto",
    "preferred_video_host": "youtube",
    "analytics_provider": "existing-project",
    "asset_output_dir": "$HOME/Documents/landing-page-output/assets"
  }
}
```

Example values show schema shape only. Persist actual values in the user's
profile, never in reusable Skill source.

`brand_goal` may be `launch`, `clarify`, `reposition`, or `refresh`. It guides
the pipeline but never overrides explicit task language.

## Environment overrides

| Variable | Meaning |
|----------|---------|
| `SKILL_PROFILE_PATH` | Shared profile JSON |
| `SKILL_WORKSPACE_ROOT` | Default target workspace |
| `SKILL_OUTPUT_DIR` | Default deliverable output |
| `SKILL_PROFILE_PATH` | Brand profile |
| `SKILL_DESIGN_GUIDE` | Design guide |
| `SKILL_OH_MY_LANDINGPAGE_BRAND_ASSET_DIR` | Approved brand assets |
| `SKILL_OH_MY_LANDINGPAGE_MARKET` | `domestic`, `overseas`, or `mixed` |
| `SKILL_OH_MY_LANDINGPAGE_IMAGE_PROVIDER` | Configured image provider |
| `SKILL_OH_MY_LANDINGPAGE_VIDEO_HOST` | Configured video host |

Credentials remain in environment or a credential store and never enter the
profile, page, repository, or analytics payload.

## Resolution order

1. Current request and explicit path/URL.
2. Target repository instructions, product truth, and existing configuration.
3. Approved brand profile, guide, and assets.
4. Environment variables.
5. Shared profile.
6. Safe inference from locale, domain, and current channels.
7. One focused question for a remaining product decision.
