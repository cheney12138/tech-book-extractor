# tech-book-extractor

Claude Code 技能：技术书深度萃取——两阶段流水线。

## 结构

| 阶段 | 文件 | 职责 |
|------|------|------|
| Stage 1 | [stage1/skill-stage1-structure-parser.md](stage1/skill-stage1-structure-parser.md) | 全书骨架解析：标注 type/weight/complexity/keyQuestions/outdatedRisks/阅读路线 |
| Stage 2 | [stage2/skill-stage2-chapter-extractor.md](stage2/skill-stage2-chapter-extractor.md) | 单章深度萃取：六层结构 + 复杂热点深度脚手架 |

## 安装（Agent Skill）

```bash
npx @cheney99/tech-book-extractor-skills
```

安装完成后即可使用 `/tech-book-stage1` 和 `/tech-book-stage2`。

**更新到最新版本：**

```bash
npx @cheney99/tech-book-extractor-skills@latest
```

## 设计思路

- **Stage 1 画地图**——读整本书之前，先标注知识价值分布，聚焦高权重章节
- **Stage 2 搭脚手架**——复杂小节（如 ZGC 染色指针）不精炼提纯，而是分步拆解：做了什么 → 为什么需要 → 不这样做会怎样
- **复杂度客观检测**——用小节长度、脚注密度、跨章引用数自动判定 complexity，不依赖 LLM 主观判断
- **一套模板 + 增量**——六层输出格式统一，complexity=high 的小节在心智模型层追加分步拆解，不断开新模板
