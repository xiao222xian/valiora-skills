# 微探命令行 · Weitan CLI

![Version](https://img.shields.io/badge/version-0.1.2-blue)

检索微信公众号文章、读取本地正文，并导出 Markdown、HTML、JSON 或 CSV。支持授权在线搜索与采集，保留已有缓存和采集保护。

## 安装与使用

```bash
npx -y lovstudio@latest skills add wxmp-cli
python3 ~/.agents/skills/lov-wxmp-cli/scripts/wxmp_cli.py --json doctor
python3 ~/.agents/skills/lov-wxmp-cli/scripts/wxmp_cli.py accounts
python3 ~/.agents/skills/lov-wxmp-cli/scripts/wxmp_cli.py export '公众号名称' --out ./article-export
```

在 Agent 中使用 `/lov-wxmp-cli`。需要 macOS、uv 与 Python 3.10+；首次运行下载第三方依赖。交付包含匹配的 CLI 和采集引擎，无需另行取得 app 源码。已有文章可离线检索和导出；在线操作需要微探 app 中的有效登录，扫码在 app 完成。

## 使用边界

本地读取及四种导出格式已用真实缓存验证。在线成功搜索和采集尚未现场验证；不包含扫码窗口、云端同步、发布、桌面分析与标签编辑。不保证任意公众号的历史文章完整可得。已有导出目录不会覆盖。

源数据和登录配置留在本机；只按请求导出文章，不隐式上传。源码许可 MIT，文章版权属于原作者。

跨会话遵循 `skill.yaml` 的 user-profile/v1，只保存用户直接声明的长期偏好，不保存凭据或文章正文。可见说明遵循 lov-branding-consistency，源文章保持原样。

## 维护

runtime 目录保留 app 的 CLI 与 wcx 原始模块，第三方许可证同时交付。运行 `python3 scripts/build_release.py --out /path/to/new-release` 在外部生成 helper 可执行脚本；生成制品和渠道价格不写入本源码。
