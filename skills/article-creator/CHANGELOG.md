# Changelog

## [0.10.1] - 2026-11-01

### Fixed

- 价格卡文案：去掉人民币金额和“公开源码、公开仓库”的过期说法，价格仍是 280 Credits
- skill-card.yaml、skill-card.md、pricing-card.yaml 改为“源码保存在私有仓库，购买后按版本下载”；复评条件里“从公开源码切换为加密交付”改为“交付方式变化”
- skill-card.md 的 Skill Version 从过期的 0.4.2 更正为 0.10.1；官网上架状态从 not_published / pending_launch 改为 live

## [0.10.0] - 2026-10-30

### Added

- 叙事与招募长文：图跟着故事走，强调只用加粗；validate 新增重复句、高亮写法、wxid 与配图密度检查
- body-figures 0.3.0→0.4.0：用真实故事串起履历的叙事与招募长文默认需要正文配图。图跟在点名它的段落后面；讲到演讲和活动的图要看得到作者本人，单页幻灯片封面不算；成就与数字配官网、论坛等原始页面截图或汇总证据图；引用原帖配去掉他人信息的原帖证据图；引用作品配打动作者的那一帧；点名的场地和联办方都有图；活动主视觉与视频号宣传片放在开头。
- 素材优先级：公开页面的真实截图优先于根据同一数据自制的名称墙或汇总卡。
- article-template：新增招募长文的默认语义顺序和「强调」一节：承重句和感悟只用加粗，不用底色高亮、彩色字或 ==高亮==（Lovpen 公众号主题不解析 ==）。
- article-writing 0.6.0→0.7.0：视频脚本或口播稿改成文章时按故事重写成连续段落；同一句话、同一组数字只出现一次。
- quality-gate 0.4.1→0.5.0：validate_article_package.py 把重复整句（10 字符以上）、==高亮==、<mark> 与底色内联样式、公开文本里的 wxid_ 判为错误；相邻媒体之间可见文字中位数低于 60 字或连续 3 处少于 40 字时给出密度警告；新增 tests/test_validate_article_package.py。
- 来源：用户对一篇招募长文的逐轮反馈（口播稿“还没读几个字就插一张图片”、Skill 名称墙改用官网截图、外滩大会配图只有幻灯片封面“没有我的信息”、黄色底色“过于强调”改为直接加粗、重复句等）和最终认可“这期文章还不错”。被否定的做法（底色高亮、用单页幻灯片代替现场、逐句配图）只作为反例写入。

## [0.9.0] - 2026-10-01

### Changed

- body-figures 0.2.0→0.3.0：招募、活动、探店、旅行和空间介绍类文章默认需要正文配图，
  不再“一节一张代表图”。读者将去的每个地点配相邻实拍；同主题 3 张以上素材做成
  手机可读的组图（1800px、12px 白色间距、图上不加字、最多 3 列）；真实产物（报告页、
  产品截图）用组图展示，演示数据在图注写明；可加等权重的致谢 Logo 条；组图同样过
  人脸、车牌、电话、WiFi、第三方二维码的隐私门禁，店铺身份未确认不点名。
- 入口 Step 4 判定门同步上述题材默认值。
- 来源：用户对南头古城招募公众号文章包的直接反馈“图片资料不够丰富，而且部分需要组图”，
  与深度调研富媒体反馈同类，属跨任务第 2 次出现的可复用信号。

## [0.8.1] - 2026-09-15

### Fixed

- `build_article_package.py`：正文图片已在包内时 `shutil.copy2` 抛 `SameFileError` 直接中断打包。
  Step 4 明确要求「回写完成后重跑 build_article_package.py」，所以这是正常路径而不是异常；
  改为源与目标同一文件时跳过拷贝，仍计入 `body_image_paths`。
  复现：正文用 `figures/xxx.jpg` 相对路径引用包内图片，再对同一包重跑构建脚本。

## [0.8.0] - 2026-09-12

### Added

- 子模块加固：实录转写模式、完整存档判定、章节编号核对来源、标点/段落/措辞规则
- article-writing 0.5.1→0.6.0：新增实录转写模式、全角标点默认、段落节奏、事实中立与第三方措辞规则
- body-figures 0.1.1→0.2.0：区分完整存档与编辑精选，去除重复样板图注
- editorial-template 0.4.1→0.5.0：章节编号/命名默认核对来源结构

## [0.7.0] - 2026-09-11

### Changed

- 展示名升级为「天才写手 · Genius Writer」，调用 ID `lov-article-creator` 与能力契约保持不变。
- 转为一次性付费交付：280 Credits（≈ ¥19.9）解锁完整文章包工作流，采用公开源码交付，不提供源码保密。

## [0.6.2] - 2026-09-08

- 文章包要求最终正文散列绑定的文风审读记录；缺失或过期不再升级 prepared。

## [0.6.1] - 2026-09-07

### Added

- 统一展示名为「公众号写手」，保持调用 ID 与能力契约。

## [0.6.0] - 2026-09-05

### Added

- add the body-figure stage and hand it off to lov-illustrate
- decide body figures explicitly and record the decision in article-manifest.json
- add references/body-figures.md with the genre gate and evidence-first material order
- add --figures/--figures-reason to build_article_package.py
- fail validation when body_figures.decision is undecided, or required with no figure

## [0.5.0] - 2026-09-01

### Added

- 建立创作战略、交互场景与标题层级的统一契约。

## [0.4.2] - 2026-09-01

### Changed

- 微信正文默认隐藏 canonical H1，文章标题只进入平台标题字段。
- 正文中的资料来源、补充链接与引申阅读默认使用低对比度的小字斜体资料注。

## [0.4.1] - 2026-09-01

### Fixed

- 将 Pillow 保留在 runtime compatibility 与文档中，不再误写进只接受 Skill ID 的 `metadata.dependencies`。

## [0.4.0] - 2026-08-31

### Changed

- 统一通过 `lov-writing-style → lov-human-writing` 处理个人文风与作者性，删除文章 Kit 的重复规则所有权。
- 将公众号品牌化合并为 `brand` 管线，并统一正文首图为 `4:3` 横向资产。
- 将忠实转载合并为 `repost` 管线，迁入来源冻结、图片账本与保真审计脚本。
- 将远端已有草稿操作路由到 `lov-publish-wechat-article`。

## [0.3.0] - 2026-08-31

### Added

- 为研究评测类公众号文章加入可复现方法链与论文式章节质量门。
- 正文首图由漂移的 3:4 竖图升级为独立的 4:3 横向资产，并保留 v1 历史包兼容校验。
- 构建文章包时复制正文引用的本地图片，并由 manifest 与质量门核对，避免本地 `prepared` 到发布预检之间丢图。

## 0.2.0

- 为公众号最终稿新增 `reader contract` 与零会话 cold-reader 门禁。
- 将旧稿轮次、用户反馈和 Agent 审稿过程明确划为内部上下文。
- 质量脚本新增标题 + 开头 300 字的会话泄漏回归测试。

## 0.1.2

- 将母品牌 `LovStudio` 与公众号发布主体 `手工川` 分开建模。
- 封面改用手工川官方白色横向 Logo lockup。
- 合成器新增白色像素比例校验，橙色和其他非白色变体直接报错。
- article/cover manifest 与质量门新增发布主体一致性检查。

## 0.1.1

- 封面品牌资产统一为发布主体官方横向 Logo lockup。
- 合成器按非透明内容框校验 Logo 宽高比，方形图标直接报错。
- cover manifest 与质量门新增横向 Logo 变体及比例回读。
- Agent Harness 案例重新生成横版封面与竖版首图。

## 0.1.0

- 创建自包含 `article-writing → editorial-template → cover-package → quality-gate` Kit。
- 固定公众号文章模板、手工川写作基线与 LovStudio Warm Academic 品牌规则。
- 输出 `2.35:1` 横版封面和 `3:4` 竖版正文首图。
- 增加文章包装、官方 Logo 合成、尺寸与 SHA-256 回读脚本。
- 以 Agent Harness System Prompt 长文完成首个真实 `prepared` 案例。
