#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const os = require("os");

const skillsSource = path.join(__dirname, "..", "skills");
const skillsDest = path.join(os.homedir(), ".claude", "skills");
const scriptsSrc = path.join(__dirname, "..", "stage1", "complexity_scanner.py");
const scriptsDest = path.join(os.homedir(), ".claude", "scripts");

fs.mkdirSync(skillsDest, { recursive: true });
fs.mkdirSync(scriptsDest, { recursive: true });

// 复制 skills
const skills = fs.readdirSync(skillsSource).filter((f) =>
  fs.statSync(path.join(skillsSource, f)).isDirectory()
);

if (skills.length === 0) {
  console.error("No skills found in package.");
  process.exit(1);
}

for (const skill of skills) {
  const src = path.join(skillsSource, skill);
  const dest = path.join(skillsDest, skill);
  fs.mkdirSync(dest, { recursive: true });

  for (const file of fs.readdirSync(src)) {
    fs.copyFileSync(path.join(src, file), path.join(dest, file));
  }

  console.log(`✓ skill: ${skill} → ${dest}`);
}

// 复制预处理脚本
const scannerDest = path.join(scriptsDest, "complexity_scanner.py");
fs.copyFileSync(scriptsSrc, scannerDest);
console.log(`✓ script: complexity_scanner.py → ${scannerDest}`);

console.log(`\n${skills.length} skill(s) installed.`);
