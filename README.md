# tech-book-extractor

Claude Code skills for deep technical book reading — a two-stage pipeline that maps a book's knowledge structure, then distills each chapter into executable decision rules, diagnostic checklists, and self-contained Q&A.

[![npm version](https://img.shields.io/npm/v/tech-book-extractor-skills)](https://www.npmjs.com/package/tech-book-extractor-skills)

## Installation

```bash
npx tech-book-extractor-skills
```

This installs two Claude Code skills (`book-map` and `chapter-drill`) and four Python utility scripts into your `~/.claude/` directory. The skills are then available as slash commands in any Claude Code session.

**Upgrade:**

```bash
npx tech-book-extractor-skills@latest
```

## How It Works

The pipeline has two stages. You normally only run the second.

### Stage 1 — `/book-map` (run once per book)

Scans the full table of contents and preface, then produces a `stage1-skeleton.json` that annotates every chapter with metadata:

| Field | Purpose |
|-------|---------|
| `type` | `core_principle` / `practical` / `reference` / `outdated` — drives which extraction template to use |
| `weight` | 1–5 — drives extraction depth and token budget (weight ≥ 3 gets full two-pass; weight ≤ 2 gets lightweight; weight = 1 is skipped) |
| `keyQuestions` | 2–3 per chapter — injected into the "Key Q&A" section of the extraction |
| `outdatedRisks` | Specific APIs/params that are now obsolete — injected into "Outdated Notes" |
| `prerequisites` | Chapter dependency chain (cycle-free) — ensures cross-reference consistency |
| `subsections` | Per-subsection `complexity` (objectively computed by `complexity_scanner.py`), `skipIf` conditions, and `practiceChecklist` |

It also generates three differentiated reading paths (Application Developer / Performance Engineer / Interview Prep) and a `complexityHotspots` array of sections that need deep scaffolding rather than standard distillation.

### Stage 2 — `/chapter-drill` (run per chapter)

Reads the skeleton for navigation metadata, then runs a **two-pass** process on the full chapter text:

- **Pass 1** — Internal understanding notes: core arguments, organization logic, knowledge classification (new vs. filler), precise data to preserve, terminology map, outdated risk supplements.
- **Pass 2** — Produces a six-layer extraction Markdown file driven by the skeleton's `type` and `weight`.

#### The Six-Layer Output

```
# Chapter N · Title

> Type | Weight | Estimated Reading | Prerequisites | Key Questions

## 1. One-Sentence Kernel  (≤80 characters)
   Analogy / core causal statement / action guide / positioning — varies by type

## 2. Mental Model
   Feynman-style restatement + causal chains (arrow notation) + boundary conditions
   → Complexity=high subsections get "step decomposition" blocks:
       What was done → Why this step → What happens if skipped
       Ends with "What to focus on when reading the original"

## 3. Decision Rules
   when → then → why triples for every actionable scenario
   + Parameter quick-reference table (only params with explicit book guidance)

## 4. Diagnostic Manual
   Symptom → probe commands → decision tree (condition → root cause → fix)

## 5. Outdated Notes
   Specific technology/API/param → current status → replacement

## 6. Key Q&A
   Covers every skeleton keyQuestion + extension questions discovered in extraction
```

#### Four Extraction Templates

The skeleton's `type` field selects the template; `weight` controls depth:

| Template | Type | Focus |
|----------|------|-------|
| **A** | `core_principle` | Analogy kernel, causal chains, boundary conditions, full diagnostic trees |
| **B** | `practical` | Action-guide kernel, decision rules, diagnostic manual, parameter tables |
| **C** | `reference` | Positioning kernel, terminology index (term → explanation → section → downstream refs), lightweight Q&A |
| **D** | `outdated` | Replacement kernel, per-item: obsolete → replacement → version → still worth knowing? |

### Complexity Hotspot Handling

`complexity_scanner.py` computes objective metrics per subsection:

| Metric | Threshold |
|--------|-----------|
| Section word count | > 3,000 |
| Footnote count | > 3 |
| Cross-chapter references | > 2 |

All three exceeded → `complexity: high`. Stage 2 then appends **step-decomposition scaffolding** in the Mental Model layer for those subsections, rather than standard distillation. Each step answers: *what was done → why this step → what happens if skipped*, and ends with a 2–3 point "read the original with this lens" hint.

If the text is a scanned PDF (no extractable text layer), the scanner outputs `scan_fallback: true` and complexity defaults to `llm_inferred`.

## Usage

### Daily workflow — just `/chapter-drill`

```
/chapter-drill ~/books/understanding-jvm.epub Chapter 3
```

The first run automatically generates the skeleton in the background (transparent to you). Subsequent chapters reuse it. You never need to run `/book-map` manually.

### Optional — `/book-map` for skeleton review

```
/book-map ~/books/understanding-jvm.epub
```

Use this when you want to inspect or hand-edit chapter weights, outdated risks, or reading paths before extraction. Then `/chapter-drill` picks up your edits.

### Output

Everything lands under `{output_dir}/{book-name}/`:

```
~/note/book/Understanding the JVM/
├── stage1-skeleton.json          ← Stage 1: book knowledge map
└── chapters/
    ├── ch02-extract.md           ← Stage 2: six-layer extraction
    ├── ch03-extract.md
    └── ...
```

## Supported Formats

| Format | Full-text extraction | Complexity scanner |
|--------|---------------------|-------------------|
| `.epub` | ✅ (stdlib) | ✅ (high confidence) |
| `.pdf` (text layer) | ✅ (PyMuPDF) | ✅ (medium confidence) |
| `.pdf` (scanned) | ❌ (needs OCR) | ❌ (falls back to `llm_inferred`) |
| `.txt` / `.md` | ✅ (no extraction needed) | ✅ (high confidence) |

## Design Principles

1. **Not summaries — navigation.** The skeleton doesn't produce knowledge; it annotates where knowledge lives and how valuable it is.
2. **Uneven effort allocation.** Weight 5 chapters get full two-pass depth. Weight 1 chapters get skipped. A technical book typically has only 3–5 chapters worth deep reading.
3. **Objective complexity detection.** The scanner computes complexity from measurable signals (length, footnotes, cross-refs), not LLM vibes.
4. **Unified format + incremental scaffolding.** All chapters share the six-layer structure. Only `complexity=high` subsections get extra step-decomposition blocks — nothing else changes.
5. **Precise, not diluted.** Decision rules retain exact parameter names, version numbers, and confidence annotations. Facts the model is unsure about are marked `[confidence: low]`.
6. **No silent truncation.** Every subsection has an explicit `skipIf` condition — if content is skipped, the reader knows why.

## License

MIT
