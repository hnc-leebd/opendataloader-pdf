# TriageProcessor Research: PDF Page Classification Techniques

This document summarizes research on PDF page triage and classification techniques for determining optimal processing paths (fast heuristic vs AI-based).

---

## Implementation Plan

### Design Decisions

| Question | Decision |
|----------|----------|
| Priority | Lightweight heuristics with low overhead first |
| Approach | Heuristics only (no ML models for triage) |
| VLM path | Deferred (will integrate with docling VLM later) |
| Math symbols | Hardcoded character list (faster, fewer false positives) |
| Chart detection | Deferred (requires additional data beyond IChunk) |
| Structure | Extend existing `TriageSignals` class |

### Phase 1: Lightweight Heuristics (This Sprint)

**New signals to add to `TriageSignals`:**

```java
// Formula detection
private final boolean hasMathSymbols;        // ∑∫√±≠≤≥∞∂∇ etc.
private final boolean hasGreekLetters;       // αβγδεζηθικλμνξοπρστυφχψω
private final boolean hasSuperSubscript;     // Font size variation pattern

// Enhanced table detection
private final int columnCount;               // X-coordinate clustering
private final double columnRegularity;       // Column spacing uniformity

// OCR enhancement
private final int uniqueFontCount;           // Font diversity (low = likely scanned)

// Complexity
private final double layoutDensity;          // Elements per unit area
```

**New `PageTriage` fields:**

```java
private final boolean needsFormulaProcessing;
private final double complexityScore;  // 0.0 (simple) to 1.0 (complex)
```

### Implementation Order

1. **Math symbol detection** - Simple Unicode character check
2. **Greek letter detection** - Unicode range U+0370-U+03FF
3. **Unique font count** - Count distinct font names
4. **Column detection** - X-coordinate clustering with tolerance
5. **Superscript/subscript detection** - Font size ratio within proximity
6. **Layout density** - Element count / page area
7. **Complexity score** - Weighted combination of signals

### Phase 2: Future Enhancements (Deferred)

- Chart/diagram detection (requires PDF graphics analysis)
- VLM path integration (docling)
- Multi-column layout detection
- Reading order complexity

---

## Current Implementation Analysis

The current `TriageProcessor` analyzes the following signals:

| Signal | Description |
|--------|-------------|
| `imageAreaRatio` | Image area relative to page area |
| `textCoverage` | Text area relative to page area |
| `missingToUnicodeRatio` | Ratio of fonts without ToUnicode mapping |
| `hasType3Fonts` | Presence of Type3 fonts (image-based glyphs) |
| `hasGridAlignedText` | Grid-aligned text pattern (table signal) |
| `hasSuspiciousTextGaps` | Suspicious horizontal gaps (table signal) |

---

## Related Research

### 1. PDF Page Classification (Scanned vs Native)

**[Automatic PDF Document Classification (IDEAL 2024)](https://link.springer.com/chapter/10.1007/978-3-031-77731-8_40)**
- Automated pipeline integrating OCR and ML
- Distinguishes scanned vs digital documents
- Uses BERT and Random Forest for 51-category classification

**[Printed Document Layout Analysis (Nature 2025)](https://www.nature.com/articles/s41598-025-07439-y)**
- YOLOv4/YOLOv8-based layout analysis
- Identifies titles, text paragraphs, tables, and images

### 2. Table Detection (Borderless Tables)

**[PDF-TREX](https://www.researchgate.net/publication/4288170_Table_Recognition_and_Understanding_from_PDF_Files)**
- Heuristic bottom-up approach
- Recognizes tables using spatial features only: whitespace, horizontal/vertical distance distribution, vertical overlap ratios

**[TabbyPDF](https://link.springer.com/article/10.1007/s42979-022-01659-z)**
- Uses textual information and graphical features
- Horizontal/vertical distances, font properties, ruling lines
- **Detects borderless tables by exploiting ruling lines embedded in PDF**

**[Table Cell Core Analysis](https://link.springer.com/article/10.1007/s42979-022-01041-z)**
- Analyzes text gap information to detect table cell cores
- Works regardless of table boundary lines or separating rule-lines

**[PdfTable Toolkit (2024)](https://arxiv.org/html/2409.05125v1)**
- Unified deep learning-based table extraction toolkit

### 3. Mathematical Formula Detection

**[Mathematical Formula Identification (IJDAR 2014)](https://link.springer.com/article/10.1007/s10032-013-0216-1)**
- Combines ML techniques and heuristic rules
- Distinguishes isolated vs embedded formulas
- Key features: geometric layout, character and context content

**[MathSeer Pipeline (ICDAR 2021)](https://www.cs.rit.edu/~rlaz/files/ICDAR2021_MathSeer_Pipeline.pdf)**
- Complete framework for math formula extraction and evaluation
- Leverages character information in born-digital PDFs
- SSD-based formula detector

**Heuristic-based formula detection features:**
- Mathematical symbol models (fuzzy logic)
- Subscript/superscript detection
- Non-Latin symbol detection (∑, ∫, √, etc.)

### 4. Chart/Diagram Detection

**[ChartOCR (WACV 2021)](https://huggingface.co/blog/vlms-2025)**
- Deep Hybrid Framework for data extraction from chart images

**[UniChart (EMNLP 2023)](https://huggingface.co/blog/vlms-2025)**
- Vision-Language pretrained model for chart comprehension and reasoning

**VLM-based approach:**
- Complex charts/diagrams are effectively handled by VLMs (LLaVA-NeXT, PaliGemma)
- Traditional parsers struggle to extract semantic meaning

### 5. Lightweight Layout Analysis

**[GLAM (ICDAR 2023)](https://dl.acm.org/doi/10.1007/978-3-031-41734-4_4)**
- Represents PDF metadata as structured graph
- **1/10 the size of existing models with SOTA performance**
- Graph Neural Network based

**[PP-DocLayout](https://github.com/huridocs/pdf-document-layout-analysis)**
- Recognizes 23 types of layout regions
- 12.7ms per page on T4 GPU (balanced model)
- Fast mode: CPU-only with slightly reduced accuracy

**[HURIDOCS Fast Mode](https://huridocs.org/2024/08/new-open-source-ai-tool-unlocks-content-and-structure-of-pdfs-effortlessly/)**
- Non-visual lightweight models
- CPU-only, speed-prioritized

---

## Signal Status Summary

### A. OCR Detection Signals

| Signal | Description | Status |
|--------|-------------|--------|
| Image Area Ratio | Image ratio relative to page | ✅ Implemented |
| Text Coverage | Text coverage | ✅ Implemented |
| Missing ToUnicode | Missing font mapping | ✅ Implemented |
| Type3 Fonts | Image-based glyphs | ✅ Implemented |
| **Font Uniformity** | Scanned docs have low font diversity | 🔜 Phase 1 |
| Text/Image Overlap | Text-image overlap (watermark vs scan) | ⏸️ Deferred |
| DPI Analysis | Image resolution analysis | ⏸️ Deferred |

### B. Complex Table Detection Signals

| Signal | Description | Status |
|--------|-------------|--------|
| Grid Aligned Text | Grid alignment pattern | ✅ Implemented |
| Suspicious Text Gaps | Large horizontal gaps | ✅ Implemented |
| **Column Detection** | Detect columns via X-coordinate clustering | 🔜 Phase 1 |
| **Column Regularity** | Column spacing uniformity | 🔜 Phase 1 |
| Row Baseline Clustering | Detect rows via Y-coordinate clustering | ⏸️ Deferred |
| Ruling Lines | Detect lines from PDF graphic objects | ⏸️ Deferred |

### C. Formula Detection Signals

| Signal | Description | Status |
|--------|-------------|--------|
| **Math Symbols** | Math symbol presence (∑, ∫, √, ±, ≠, ≤, ≥) | 🔜 Phase 1 |
| **Greek Letters** | Greek letter frequency | 🔜 Phase 1 |
| **Superscript/Subscript** | Font size variation pattern | 🔜 Phase 1 |
| Font Size Variation | Font size variation within local region | ⏸️ Deferred |
| Horizontal Nesting | Horizontal nesting structure (fractions) | ⏸️ Deferred |

### D. Chart/Diagram Detection Signals

| Signal | Description | Status |
|--------|-------------|--------|
| Vector Graphics | PDF vector graphic object analysis | ⏸️ Deferred (Phase 2) |
| Axis-like Lines | Axis-like line patterns | ⏸️ Deferred (Phase 2) |
| Legend Patterns | Legend patterns (small text + color boxes) | ⏸️ Deferred (Phase 2) |
| Geometric Shapes | Circles, rectangles, arrows, etc. | ⏸️ Deferred (Phase 2) |
| Image with Adjacent Text | Caption text next to images | ⏸️ Deferred (Phase 2) |

### E. Page Complexity Score

| Signal | Description | Status |
|--------|-------------|--------|
| **Layout Density** | Layout density (element count / area) | 🔜 Phase 1 |
| Font Variety | Number of font types used | ✅ (via uniqueFontCount) |
| Multi-column | Multi-column layout detection | ⏸️ Deferred |
| Reading Order Complexity | Reading order complexity | ⏸️ Deferred |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     TriageProcessor                          │
├─────────────────────────────────────────────────────────────┤
│  Input: List<IChunk>, BoundingBox, Config                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ OCR Signals │  │Table Signals│  │Formula Signs│          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          │                                   │
│                   ┌──────┴──────┐                            │
│                   │ Complexity  │                            │
│                   │   Score     │                            │
│                   └──────┬──────┘                            │
│                          │                                   │
├─────────────────────────────────────────────────────────────┤
│  Output: PageTriage                                          │
│    - path: "fast" | "ai"                                    │
│    - needsOcr: boolean                                       │
│    - needsTableAi: boolean                                   │
│    - needsFormulaProcessing: boolean  (NEW)                  │
│    - complexityScore: double          (NEW)                  │
│    - signals: TriageSignals (expanded)                       │
└─────────────────────────────────────────────────────────────┘
```

---

## References

### Document Classification
- [Automatic PDF Document Classification (IDEAL 2024)](https://link.springer.com/chapter/10.1007/978-3-031-77731-8_40)
- [Printed Document Layout Analysis (Nature 2025)](https://www.nature.com/articles/s41598-025-07439-y)
- [docTR - Document Text Recognition](https://github.com/mindee/doctr)

### Table Detection
- [PDF-TREX: Table Recognition from PDF](https://www.researchgate.net/publication/4288170_Table_Recognition_and_Understanding_from_PDF_Files)
- [Borderless Table Detection](https://www.researchgate.net/publication/363256556_Borderless_Table_Detection_and_Extraction_in_Scanned_Documents)
- [Table Cell Core Analysis](https://link.springer.com/article/10.1007/s42979-022-01041-z)
- [PdfTable Toolkit](https://arxiv.org/html/2409.05125v1)
- [Flexible Hybrid Table System](https://link.springer.com/article/10.1007/s42979-022-01659-z)

### Formula Detection
- [Mathematical Formula Identification (IJDAR 2014)](https://link.springer.com/article/10.1007/s10032-013-0216-1)
- [MathSeer Pipeline (ICDAR 2021)](https://www.cs.rit.edu/~rlaz/files/ICDAR2021_MathSeer_Pipeline.pdf)
- [Deep Learning Formula Detection](https://www.researchgate.net/publication/322779583_A_Deep_Learning-Based_Formula_Detection_Method_for_PDF_Documents)

### Layout Analysis
- [GLAM - Graph-based Layout Analysis (ICDAR 2023)](https://dl.acm.org/doi/10.1007/978-3-031-41734-4_4)
- [PP-DocLayout](https://github.com/huridocs/pdf-document-layout-analysis)
- [HURIDOCS Fast Mode](https://huridocs.org/2024/08/new-open-source-ai-tool-unlocks-content-and-structure-of-pdfs-effortlessly/)
- [DocLayout-YOLO](https://github.com/topics/document-layout-analysis)

### VLM/Charts
- [Vision Language Models 2025](https://huggingface.co/blog/vlms-2025)
- [PDFTriage (arXiv)](https://arxiv.org/abs/2309.08872)
- [VLM Survey](https://github.com/jingyi0000/VLM_survey)
