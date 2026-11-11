# 官网小能手 · Website Whiz

![Version](https://img.shields.io/badge/version-0.4.1-CC785C)

从品牌内核出发，把整体形象、内容叙事、转化文案、UI、媒体、真实交互与上线验收统一落成一个可识别、可使用、可转化的 Landing Page。

它不再把品牌当作最后一道“美化”。先建立可执行的 Brand Spine，再让页面策略、文案、视觉、内容、交互和验收共同表达同一个品牌观点。

## 核心变化

- 从产品、创始人、用户与现有资产中提炼真实品牌内核，不凭空生成品牌价值观。
- 建立语言人格、视觉签名、内容原则、交互性格和证据行为。
- 用“品牌主张 → 产品体验 → 真实证据 → 行动”组织故事，而不是堆砌标准章节。
- 明确区分产品价值、产品机制、证据与分发方式，避免把 App、Web、CLI、Skill 或下载选项误写成产品特色。
- 每个产品都从类别、用户、使用情境、信任风险和既有品牌资产独立推导视觉风格，不沿用上一个项目的审美默认值。
- 把审美要求翻译为适配该产品的材料与行为，并按可见图形边界检查 Logo 光学对齐。
- 同时验收品牌记忆、访客理解和真实交互，避免只看编译通过或页面是否漂亮。
- 严格区分沟通背景、可发布主张、已验证证据与待补证据。

## Skill Kit

```text
lov-oh-my-landingpage
├── landing-brand           品牌内核、Brand Spine 与表达系统
├── landing-strategy        叙事、文案、内容、证据与转化路径
├── landing-art-direction   视觉世界、UI 语法、产品舞台与媒体
├── landing-builder         仓库内实现、品牌令牌、SEO、埋点与响应式
└── landing-review          品牌记忆、访客路径、技术质量与复验
```

内置流水线：

- `initialize`：品牌 → 策略 → 视觉 → 构建 → 验收
- `optimize`：诊断 → 品牌 → 策略 → 视觉 → 修改 → 复验
- `rebrand`：现状审视 → 品牌重塑 → 全链路重构 → 复验
- `refresh-copy`：品牌约束 → 叙事与文案 → 实现 → 复验
- `refresh-assets`：品牌约束 → 视觉与媒体 → 实现 → 复验
- `audit`：只读审查

## 使用示例

- “从品牌角度重构我们的官网，包括整体形象、UI、文案和内容。”
- “这个首页什么都有，但换掉 Logo 就像任何 AI 产品，分析后直接改。”
- “保留品牌内核，重新组织首页叙事和产品展示。”
- “Build a distinctive branded landing page and implement the real conversion path.”

## 本地安装

从公开仓库安装：

```bash
npx skills add lovstudio/oh-my-landingpage-skill
```

开发中的本地源码可以使用符号链接：

```bash
export SKILL_SOURCE_DIR="$(pwd)"
mkdir -p "${SKILL_SKILLS_INSTALL_DIR:?请设置本地 Skills 目录}"
ln -s "$SKILL_SOURCE_DIR" \
  "$SKILL_SKILLS_INSTALL_DIR/lov-oh-my-landingpage"
```

## 用户配置

首先从任务、仓库与真实品牌资料中推断，再读取共享 profile。只有会改变公开结果的必要事实仍缺失时才询问。

```bash
${SKILL_PROFILE_PATH:-$HOME/.skill-publisher/skills/profile.json}
```

详见 `references/user-config.md`。

## 质量门

```bash
python3 scripts/validate_skill.py .
```

页面任务还应运行目标仓库原生的格式化、lint、类型检查、测试、生产构建，并完成品牌记忆、320 px、键盘、IME、CTA 和完整访客路径验收。

## 依赖

- Python 3.8+ 与 PyYAML（Skill 源校验）
- 目标项目自己的前端工具链
- 可选：网页研究、图像/视频生成、无障碍与视觉检查能力

## License

MIT
