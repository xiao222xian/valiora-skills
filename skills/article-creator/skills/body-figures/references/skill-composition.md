# Skill composition

## Nearby Skills Inspected

`lov-illustrate` 拥有文档级配图规划、检索、生成与回写；`lov-cover-package` 拥有分享封面与 `4:3` 首图；`lov-image-decorator` 只处理单图装饰。

## Atomic Handoffs

本模块接收文章包内的 `article.md` 与 manifest，输出 `body_figures` 判定；判定为需要时把 `article.md` 交给 `lov-illustrate`，由其写回 `figures/` 与正文引用。

## Overlap Decisions

判定权留在 Kit 内，因为它是编辑决策，依赖题材、证据结构和公众号读者契约；画图能力不在 Kit 内重复实现，避免与 `lov-illustrate` 产生第二套配图规则。

## Composition Decision

本模块只产生判定与验收结果，不把 `lov-illustrate` 的实现细节写进 Kit，也不接管封面与首图。
