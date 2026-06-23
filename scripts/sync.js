#!/usr/bin/env node
/**
 * 从 stage1/stage2 源文件重新生成 skills/ 下的 SKILL.md。
 * 每次发布新版本前运行：npm run sync
 */

const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");

const SKILLS = [
  {
    src: "stage1/skill-stage1-structure-parser.md",
    dest: "skills/tech-book-stage1/SKILL.md",
    frontmatter: [
      "---",
      "name: tech-book-stage1",
      'description: "技术书精读前的知识骨架生成器。当用户想在读书前先画地图、分析章节价值分布、标注权重和阅读路线时激活。触发词：/tech-book-stage1、精读准备、生成骨架、分析这本书的结构。先运行 complexity_scanner.py，再生成 stage1-skeleton.json。"',
      "---",
      "",
    ].join("\n"),
    // npm 安装用户没有 stage1/ 目录，脚本装在 ~/.claude/scripts/
    replace: [
      ["python stage1/complexity_scanner.py", "python ~/.claude/scripts/complexity_scanner.py"],
    ],
  },
  {
    src: "stage2/skill-stage2-chapter-extractor.md",
    dest: "skills/tech-book-stage2/SKILL.md",
    frontmatter: [
      "---",
      "name: tech-book-stage2",
      'description: "技术书章节深度萃取器。当用户想精读某章节、把内容读薄提炼为可用知识时激活。需要 Stage 1 骨架作为输入。触发词：/tech-book-stage2、萃取这章、精读这章、深度提炼。输出六层结构的 Markdown 笔记。"',
      "---",
      "",
    ].join("\n"),
  },
];

for (const { src, dest, frontmatter, replace } of SKILLS) {
  const srcPath = path.join(root, src);
  const destPath = path.join(root, dest);

  if (!fs.existsSync(srcPath)) {
    console.error(`✗ Source not found: ${src}`);
    process.exit(1);
  }

  fs.mkdirSync(path.dirname(destPath), { recursive: true });
  let content = fs.readFileSync(srcPath, "utf8");
  for (const [from, to] of replace ?? []) {
    content = content.replaceAll(from, to);
  }
  fs.writeFileSync(destPath, frontmatter + content);
  console.log(`✓ ${src} → ${dest}`);
}

console.log("\nSync complete. Run `npm version patch && npm publish` to release.");
