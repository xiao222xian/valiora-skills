# 论文翻译官 · Paper Translator

![Version](https://img.shields.io/badge/version-0.2.1-CC785C)

将英文论文、arXiv 文稿和技术 PDF 翻译为简体中文 PDF，并按需求保留页码对应、双语页面、图片、公式与近似原始排版。

## 安装

```bash
npx skills add lovstudio/lov-paper-translator
```

本地安装时也可以将目录放入 `CODEX_SKILLS_DIR` 或 `SKILLS_DIR` 下，并保持目录名为 `lov-paper-translator`。

## 使用

在 Agent 对话中调用：

```text
$lov-paper-translator 把这篇英文论文翻译成中文，保留图片和公式。
```

默认生成精修的关键页双语版本及中文单语版本。纯文本回退脚本、无密钥 JSON 交接、输出命名和版式校验规则见 [SKILL.md](SKILL.md)。

## 迁移

公共 Skill 标识已由 `translate-paper-pdf` 更新为 `lov-paper-translator`。旧版翻译 JSON 仍可读取；新任务应使用 `$lov-paper-translator`。

## 许可

MIT
