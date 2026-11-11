# 写书专家 · Book Writing Expert

![Version](https://img.shields.io/badge/version-0.6.0-CC785C) ![Pro](https://img.shields.io/badge/Pro-blueviolet)

从大纲开始，逐章写出一本完整的书 —— 技术、教程、专著多种风格。

LovStudio 付费 Skill。登录后使用 Credits 兑换并安装。

## What you get

不是只生成几段示例文字，而是一整本写完的书：

- **任意长度** — 写到第 20 章时 AI 依然清楚第 1 章说过什么，前后呼应、术语一致
- **多种文体** — O'Reilly 实战派、学术专著、教程系列等，按主题切换
- **三格式交付** — 排好版的 PDF 定稿 + 可编辑的 DOCX 书稿 + 适合在线阅读的 HTML 站点
- **出版级中文排版** — 自带 PDF/DOCX 构建脚本：引号与标点禁则、表格跨页与续表、章末短页回收、Word 目录域；新书只填一份 `typeset.yaml`
- **过程可追溯** — 每本书一个独立项目，每章都有版本记录

适合：技术专著、行业教材、毕业论文、长篇教程、白皮书。

## Install

```bash
npx lovstudio skills add write-professional-book
```

排版构建另需 pandoc、xelatex 与 `pip3 install pymupdf python-docx pyyaml`。详情见 [LovStudio](https://lovstudio.ai)。

## Usage

直接说出想写什么：

```
/lov-write-professional-book
我想写一本面向后端工程师的 Kubernetes 实战教程，
12 章左右，O'Reilly 风格
```

Skill 会带你走完五个阶段：**定大纲 → 找素材 → 逐章写 → 通审润色 → 出成书**，期间随时可以打断、改方向、加章节。

## License

Commercial — All rights reserved.
