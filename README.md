# tech-book-extractor

Claude Code 技能：技术书深度萃取——两阶段流水线。

## 安装

```bash
npx tech-book-extractor-skills
```

**更新：**

```bash
npx tech-book-extractor-skills@latest
```

## 使用

### `/book-map` — 画地图

先读骨架，再决定从哪里开始钻。

```
/book-map 书文件路径.epub
```

产出 `stage1-skeleton.json`，包含每章的权重、复杂度热点、阅读路线。不是给你读的——是给 `/chapter-drill` 用来自动判断萃取深度的。

### `/chapter-drill` — 钻章节

一本书一钻，直接给章节号。

```
/chapter-drill 书文件路径.epub 第三章
```

第一次会自动生成骨架（透明，不打扰），后续钻其他章节直接复用。

### 示例

```bash
# 画地图
/book-map ~/books/jvm.epub

# 钻读
/chapter-drill ~/books/jvm.epub 第三章
/chapter-drill ~/books/jvm.epub 第八章
```

## 结构

| 命令 | 阶段 | 职责 |
|------|------|------|
| `/book-map` | Stage 1 | 全书骨架：type、weight、complexity、keyQuestions、阅读路线 |
| `/chapter-drill` | Stage 2 | 单章萃取：六层结构。complexity=high 的小节自动深度脚手架 |

## 设计思路

- **Stage 1 画地图**——标注知识价值分布，聚焦高权重章节
- **Stage 2 搭脚手架**——复杂小节（如 ZGC 染色指针）不精炼提纯，而是分步拆解：做了什么 → 为什么需要 → 不这样做会怎样
- **复杂度客观检测**——小节长度、脚注密度、跨章引用数 → 自动判定 complexity，不靠 LLM 主观判断
- **一套模板 + 增量**——六层格式统一，complexity=high 仅在心智模型层追加分步拆解
