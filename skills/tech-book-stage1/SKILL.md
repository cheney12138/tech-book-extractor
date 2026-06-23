---
name: tech-book-stage1
description: "技术书精读前的知识骨架生成器。当用户想在读书前先画地图、分析章节价值分布、标注权重和阅读路线时激活。触发词：/tech-book-stage1、精读准备、生成骨架、分析这本书的结构。先运行 complexity_scanner.py，再生成 stage1-skeleton.json。"
---
# 阶段一 Skill：技术书结构解析器

**定位**：读整本书之前，先画地图。避免逐章硬啃，把有限精力聚焦在高价值章节。

**复杂度指标由脚本客观计算，不依赖 LLM 主观推断。**

---

## Step 0：运行预处理脚本（必须先做）

```bash
python ~/.claude/scripts/complexity_scanner.py <书的路径> [输出路径]
```

脚本扫描全书文本，计算每个小节的三项客观指标，输出 `complexity-meta.json`。

**支持格式**：

| 格式 | 依赖 | 复杂度可信度 |
|------|------|------|
| `.txt` | 无 | 高 |
| `.epub` | 无（标准库） | 高 |
| `.pdf`（文字版） | `brew install poppler` | 中（受排版影响） |
| `.pdf`（扫描件） | — | 不可用，退回 LLM 推断 |

扫描件场景：输出 JSON 中 `_meta.scan_fallback = true`，所有小节 `complexity = "unknown"`，LLM 需自行推断，并在骨架中标注 `"complexity_source": "llm_inferred"`。

---

## 输入

两种主文本输入模式，**均需先完成 Step 0**：

| 模式 | 输入内容 | 适用场景 |
|------|---------|---------|
| A（省 token） | 全书目录 + 前言/序言 + 元信息 + **complexity-meta.json** | 已有提取好的目录文本 |
| B（省人工） | 全书全文 + **complexity-meta.json** | 直接扔原文，Skill 自行提取目录和前言 |

> 模式 B 下，Skill 第一步从原文中定位目录（通常在正文前 5%）和前言/序言，再进入骨架生成。Token 成本更高但对用户零预处理要求。
>
> **无论哪种模式，`complexityHotspots` 均直接读取 `complexity-meta.json`，不再由 LLM 计算。**

## 输出

一份 JSON 知识骨架。

**输出路径**：`{output_dir}/{书名}/stage1-skeleton.json`

| 参数 | 说明 | 默认值 |
|------|------|------|
| `output_dir` | 笔记根目录，用户可在调用时指定 | 当前工作目录（`.`） |
| `{书名}` | 从输入元信息提取，去除副标题和特殊字符，如 "深入理解Java虚拟机" | — |

目录不存在时自动创建，无需用户手动建。

完整 schema：

```json
{
  "book": "深入理解Java虚拟机（第3版）",
  "author": "周志明",
  "versionNote": "基于 JDK 13，部分内容覆盖 JDK 8-17",
  "chapters": [
    {
      "id": "ch03",
      "title": "垃圾收集器与内存分配策略",
      "type": "core_principle",
      "weight": 5,
      "estimatedReading": "2-3h",
      "prerequisites": ["ch02"],
      "practiceDensity": "high",
      "keyQuestions": [
        "G1 和 ZGC 分别适合什么场景？",
        "什么时候该调大 SurvivorRatio？"
      ],
      "outdatedRisks": ["CMS 收集器已在 JDK 14 废弃"],
      "subsections": [
        {
          "title": "3.4 HotSpot的算法实现",
          "practiceChecklist": ["安全点", "安全区域", "记忆集与卡表"],
          "skipIf": "只做应用开发不做 JVM 调优",
          "complexity": "medium"
        }
      ]
    }
  ],
  "complexityHotspots": [
    {
      "section": "3.6.2",
      "topic": "ZGC 染色指针",
      "indicators": { "sectionLength": 10192, "footnoteCount": 11, "crossChapterRefs": 5 }
    }
  ],
  "readingPaths": [
    {
      "name": "应用开发者路线",
      "chapterIds": ["ch02", "ch03", "ch04", "ch07"]
    },
    {
      "name": "调优工程师路线",
      "chapterIds": ["ch02", "ch03", "ch04", "ch05", "ch08"]
    },
    {
      "name": "面试突击路线",
      "chapterIds": ["ch02", "ch03", "ch07", "ch12"]
    }
  ]
}
```

## 字段语义

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 章节唯一标识，如 ch03 |
| `type` | enum | `core_principle` 核心原理 / `practical` 实操为主 / `reference` 速查参考 / `outdated` 已过时。本枚举适用于原理+实践混合型技术书；纯教程类可扩展 `tutorial`，规范/标准类可扩展 `spec` |
| `weight` | 1-5 | 5=必精读，3=通读，1=可跳过 |
| `estimatedReading` | string | 预估阅读时长，如 "2-3h"、"45min"、"30min-1h" |
| `practiceDensity` | enum | high / medium / low |
| `keyQuestions` | string[] | 读完这章你应该能回答的问题 |
| `outdatedRisks` | string[] | 过时技术/API/参数提前标注。⚠️ 标注依赖模型知识截止日期，对近两年出版的书可能不完整，建议人工复核 |
| `skipIf` | string | 什么角色/场景下可以跳过本节 |
| `prerequisites` | string[] | 前置依赖章节 id 列表。必须无环：若 A 依赖 B，B 不可直接或间接依赖 A |
| `practiceChecklist` | string[] | 本节核心实践点关键词 |
| `complexityHotspots` | object[] | 全书中需要深度脚手架（而非精炼提纯）的复杂小节。按客观指标自动计算，不依赖主观判断 |

## 设计原则

1. **不是总结，是导航** —— 不生产知识，只标注知识的价值和位置。骨架是指南针，不是摘要
2. **权重分等级** —— 5 分必精读、3 分通读、1 分速查，拒绝平均用力。一本书真正值得精读的通常只有 3-5 章
3. **标记过时风险** —— JVM 演进快，CMS、永久代这些内容提前标注，避免白学
4. **多阅读路线** —— 不同角色（应用开发者、调优工程师、面试准备）走不同路径
5. **前置依赖链** —— 明确章节间的前置关系，防止跳读卡住
6. **可跳过提示** —— 每个小节都标注什么情况下可以跳过，最大程度节省时间
7. **问题驱动** —— 每章定义关键问题，读完后能回答才算读透了
8. **复杂度热点自动检测** —— 复杂小节（原文长 + 脚注多 + 跨章引用多）需要在 Stage 2 启用深度脚手架，而不是精炼提纯。**指标由 `complexity_scanner.py` 客观计算，LLM 直接读取结果，不自行推断。**

### 复杂度热点检测规则（由脚本执行）

`complexity_scanner.py` 按以下客观指标计算每个小节的复杂度：

| 指标 | 阈值 | 说明 |
|------|------|------|
| 原文小节字数 | > 3000 | 作者用篇幅投票，长小节通常概念层数多 |
| 脚注数 | > 3 个 | 脚注多 = 不额外解释读者无法理解 |
| 跨章引用次数 | > 2 个 | "见第 X 章"、"参见 §X.X" 出现越多，概念栈越深 |

**判定逻辑**：
- 三项全部命中 → `complexity: "high"`
- 命中 1-2 项 → `complexity: "medium"`
- 其余 → `complexity: "low"`

扫描件 PDF 无法计算，所有小节输出 `complexity: "unknown"`，由 LLM 退回推断（标注 `complexity_source: "llm_inferred"`）。

Stage 2 对复杂度为 high 的小节，在心智模型层追加"分步拆解"增量块（不改六层格式），每步回答：做了什么 → 为什么需要 → 不这样做会怎样。

## 和阶段二的关系

阶段二（深度萃取 Skill）拿这个骨架 + 具体章节文本，就能精准判断：

- 本章是原理型还是实操型？→ 决定萃取模板侧重概念解释还是实践清单
- 哪些小节可以跳过？→ 直接不喂给阶段二，省 token
- 哪些小节复杂度高？→ 阶段二启用深度脚手架（分步拆解），而非精炼提纯
- 有哪些过时风险？→ 萃取时自动标注版本差异
- 前后依赖什么？→ 如果前置章节还没读，提醒用户先补课

## 输出质量 Checklist

生成骨架后逐项校验，不通过视为不合格输出：

- [ ] 每个 chapter 都有 `type` 和 `weight`
- [ ] `weight=5` 的章节不超过全书的 30%（一本技术书真正值得精读的通常只有 3-5 章）
- [ ] 三条阅读路线的 `chapterIds` 交集不超过 50%（差异化，避免高度重叠）
- [ ] 所有 `prerequisites` 指向存在的 `chapter.id`，无悬挂引用
- [ ] 所有 `prerequisites` 引用链无环
- [ ] 每个 subsection 标注了 `complexity`，且 high 级别的 subsection 已汇总到顶层 `complexityHotspots`
- [ ] `complexity` 来自 `complexity-meta.json`（客观计算），或扫描件场景下标注了 `complexity_source: "llm_inferred"`
- [ ] 每个 `outdatedRisks` 条目都有具体技术/API/参数名称，拒绝泛泛的"部分内容可能过时"
- [ ] `keyQuestions` 每章 2-3 个，问题具体可验证，拒绝"本章讲了什么"式空洞提问
- [ ] `subsections` 中每个小节的 `skipIf` 明确了跳过条件（角色/场景），无空值

## Prompt 模板

```
你是一位资深技术书籍编辑，擅长快速评估技术书籍的价值分布。

【输入类型】
{input_mode}  // "A" = 已提取的目录+前言, "B" = 全书全文

【输出目录】{output_dir}  // 未提供时使用当前工作目录
【书名】{book_name}
【作者】{author}
【版本】{edition}
【书籍简介/前言摘要】{preface_summary}

【全书目录】
{full_toc}

【复杂度元数据】（complexity_scanner.py 输出，必须提供）
{complexity_meta_json}

【全书原文】（仅模式 B 提供）
{book_full_text}

【预处理步骤 — 仅模式 B 执行】
如果输入是模式 B（全书全文），先完成以下步骤再进入任务：
1. 在原文中定位目录页——通常在"目录"标题下，列出全部章节名和页码
2. 提取完整的章-节-小节层级（忽略页码），整理为 {full_toc}
3. 定位前言/序言章节，提取作者自述的写作意图、读者定位、版本变化
4. 用提取的目录和前言替换 {full_toc} 和 {preface_summary}，再进入主任务

【主任务】
0. 从书名提取目录名（去除副标题和特殊字符），自动创建 `{output_dir}/{书名}/` 目录（`output_dir` 未指定时使用当前工作目录）
1. 为每一章标注 type（core_principle/practical/reference/outdated）、weight（1-5）、practiceDensity
2. 从 {complexity_meta_json} 读取每个小节的 complexity（high/medium/low），不自行计算。
   若 `_meta.scan_fallback = true`，则退回自行推断，并在每个 subsection 标注 `"complexity_source": "llm_inferred"`
3. 标记过时技术风险（如 CMS 已废弃、永久代已移除等）
4. 定义 3 条阅读路线：应用开发者、调优工程师、面试突击
5. 为每章生成 2-3 个关键问题
6. 明确章节间的前置依赖关系
7. 汇总全书的 complexityHotspots（仅 high 级别），记录在顶层数组

【输出要求】
- 严格按 JSON schema 输出
- 将结果写入 `{output_dir}/{书名}/stage1-skeleton.json`（目录不存在则自动创建；`output_dir` 未指定时写入当前工作目录）
- 不要总结章节内容，只做元数据标注
- 对不确定的过时风险标注 confidence: low
- 阅读路线要差异化，避免三条路线高度重叠
- 确保 prerequisites 引用链无环：若 ch03 依赖 ch02，ch02 不可直接或间接依赖 ch03
```
