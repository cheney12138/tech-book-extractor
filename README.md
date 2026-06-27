# tech-book-extractor

Claude Code 技能：技术书深度萃取——两阶段流水线。

[![npm version](https://img.shields.io/npm/v/tech-book-extractor-skills)](https://www.npmjs.com/package/tech-book-extractor-skills)

## 安装

```bash
npx tech-book-extractor-skills
```

**更新：**

```bash
npx tech-book-extractor-skills@latest
```

## 使用

### 日常工作流：只用 `/chapter-drill`

```
/chapter-drill 书文件路径.epub 第三章
```

一步完成。首次使用时会自动在后台生成知识骨架（透明），后续章节直接复用。不需要手动跑 `/book-map`。

### 可选：`/book-map` — 单独校对骨架

如果想要调整某章的权重、过时标注或阅读路线后再萃取：

```
/book-map 书文件路径.epub
```

骨架生成后可手动编辑 `stage1-skeleton.json`，然后 `/chapter-drill` 会读取你的改动。

### 示例

```bash
# 直接钻，骨架第一次自动建
/chapter-drill ~/books/jvm.epub 第二章

# 钻完继续钻，骨架复用
/chapter-drill ~/books/jvm.epub 第三章

# 偶尔跑一下，校对骨架内容
/book-map ~/books/jvm.epub
```

## 命令

| 命令 | 日常使用频率 | 职责 |
|------|------------|------|
| `/chapter-drill` | ⭐⭐⭐ 每次都跑 | 单章萃取 + 自动建骨架。complexity=high 的小节深度脚手架 |
| `/book-map` | ⭐ 校对时跑 | 显式重建全书骨架，方便手动调整元数据后提升萃取质量 |

## 设计思路

- **Stage 1 画地图**——标注知识价值分布，聚焦高权重章节
- **Stage 2 搭脚手架**——复杂小节（如 ZGC 染色指针）不精炼提纯，而是分步拆解：做了什么 → 为什么需要 → 不这样做会怎样
- **复杂度客观检测**——小节长度、脚注密度、跨章引用数 → 自动判定 complexity，不靠 LLM 主观判断
- **一套模板 + 增量**——六层格式统一，complexity=high 仅在心智模型层追加分步拆解
