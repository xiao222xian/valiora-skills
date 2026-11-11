# Learner Profile 与 Glossary 契约

Profile 定义“什么算必要语言单元”的最低难度线和提示密度，不改变原英文对白。选择某个 Profile 时，保留该级别及以上的必要词汇，而不是只保留恰好属于该级别的词。语言单元可以是词、短语、习语/谚语、俚语、文化表达或复杂句子。显式请求优先于运行时 Profile；没有 Profile 时只问一个聚焦问题，不猜测学习者水平。

## 默认水平

| Profile | 选择策略 | 默认呈现 |
|---|---|---|
| `a2` | 从 A2 往上解释影响基本句意的动词、短语、习语、场景词，以及更高难度的关键表达；不解释人名。 | 每条最多 2 个词条，首次出现 |
| `b1` | 从 B1 往上解释明显超出常用词汇的表达、习语/俚语、术语和剧情关键句。 | 每条最多 2 个词条，首次出现 |
| `cet4` | 从 CET4 往上解释四级边缘词、古英语/诗意表达、关键习语/俚语、文化表达、奇幻术语和难以直读的复杂句子。 | 每条最多 3 个词条，首次出现 |
| `b2` | 从 B2 往上解释文学、历史、专业或世界观术语，以及确实影响理解的隐含句意。 | 每条最多 1 个词条，首次出现 |
| `cet6` | 从 CET6 往上解释罕见词、古体词、双关、俚语文化语境或专业术语。 | 默认不加普通词汇提示 |
| `custom` | 按请求中的目标词表、语言和密度执行。 | 必须在请求中说明规则 |

“首次出现”按整个字幕文件计算，而不是按每条 cue 计算。若同一词在后文含义明显改变，可以使用不同的 `key` 或显式要求重复。

## 最低难度线

这是供 Skill 选择和过滤使用的产品级阶梯，不是把 CEFR 与 CET 分数做成严格等价换算：

`a2 < b1 < cet4 < b2 < cet6 < advanced`

例如：

- 选择 `cet4`：保留 `cet4`、`b2`、`cet6`、`advanced`。
- 选择 `cet6`：保留 `cet6`、`advanced`。
- 选择 `b1`：保留 `b1` 以及其右侧全部级别。
- 选择 `custom`：不自动按阶梯过滤，完全执行用户写明的规则。

Agent 在生成 glossary 时应为每个新条目写明 `level`。必要的文化、奇幻或语境表达也要按其实际学习难度标注，而不是因为它属于专名就绕过难度线。旧 glossary 缺少 `level` 时，脚本会保留该条目并在运行摘要中标记为 `ungraded`，这样不会静默丢失用户已有词条。

## Glossary JSON

脚本接收一个 JSON 对象：

```json
{
  "profile": "cet4",
  "annotation_language": "zh-CN",
  "repeat": "first",
  "max_notes_per_cue": 3,
  "items": [
    {
      "kind": "word",
      "term": "forging",
      "meaning": "锻造；打造（金属物）",
      "level": "cet4",
      "key": "forge",
      "repeat": "first"
    },
    {
      "kind": "idiom",
      "term": "above all else",
      "meaning": "胜过一切；最重要的是",
      "level": "b2",
      "key": "above-all-else"
    },
    {
      "kind": "sentence",
      "term": "You shall be the fellowship of the ring.",
      "meaning": "你们将成为魔戒远征队（理解整句的语义，而非逐词直译）",
      "level": "advanced",
      "label": "句意",
      "key": "fellowship-sentence"
    }
  ]
}
```

字段规则：

- `kind`：`word`、`phrase`、`idiom`、`proverb`、`slang`、`culture`、`sentence` 或 `term`；只记录分类，不改变原文。
- `term`：按字面匹配的英文单词、短语或一个需要解释的完整句子，大小写不敏感；不要写正则表达式。
- `meaning`：面向学习者的短释义，避免长句翻译、剧透和内部提示。
- `level`：新 glossary 条目的难度标签，可用 `a2`、`b1`、`cet4`、`b2`、`cet6` 或 `advanced`。运行时按“选定 Profile 及以上”保留；旧输入可以省略，省略项会作为 `ungraded` 保留。
- `label`：可选的短分类前缀，例如 `句意`、`语境义` 或 `俚语`；不需要时省略。
- `key`：可选；同一词的词形变体可共用一个 key，避免同一文件重复解释。
- `repeat`：`first` 或 `all`；默认为全局首次出现，只有明确有必要时才用 `all`。
- `max_notes_per_cue`：默认 3；不要为了覆盖词表而让一条字幕塞满注释。

脚本的筛选发生在注释前：如果运行参数是 `--profile cet6`，标成 `a2`、`b1`、`cet4` 或 `b2` 的条目会被过滤，`cet6`、`advanced` 和未标级别的旧条目会进入注释候选。脚本输出会报告 `profile_floor`、`glossary_candidates`、`eligible_glosses`、`glossary_matched`、`glossary_applied`、`glossary_unmatched`、`glossary_suppressed`、`filtered_below_profile` 和 `ungraded_glosses_retained`。其中未命中项标记为 `no_literal_match`，被抑制项会记录重叠、单条字幕注释上限、重复键或首次出现规则等原因。

注释格式默认是 `original word【中文释义】`。如果用户要纯英文说明，应将 `meaning` 写成简短英文，而不是改动原句。

## 选词门槛

优先选择：

1. 不理解就会错过剧情因果的词、短语或句子。
2. 奇幻、历史、法律、技术等领域术语。
3. 诗歌、古体、习语、谚语、俚语或语境义明显不同于常见义的表达。
4. 中国学习者不能仅靠字面组合或画面推断的复杂句式。

默认不选择：

- 人名、地名、普通称谓和用户能从画面直接理解的物品名。
- 每个生词都解释、每句都翻译、语法讲义和剧透性说明。
- 只有“句子很长”但不影响理解的对白。
