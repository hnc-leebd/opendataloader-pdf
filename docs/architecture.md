# OpenDataLoader PDF Hybrid Architecture

**Version:** 2.0
**Date:** 2025-12-31

## Overview

OpenDataLoader PDF uses a **single-pass hybrid architecture** that combines fast heuristic processing with AI-powered analysis. The key innovation is that the PDF is opened only once by the Java JAR, which performs both triage and extraction in a single pass.

### Goals

- **Speed**: 3-10x faster than pure AI processing
- **Quality**: Match AI quality where needed
- **Efficiency**: Single PDF parse, minimal I/O overhead

---

## Architecture Diagram

```
                              PDF Input
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Java JAR (Single Pass)                              │
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │  PDF Parser     │───▶│  Triage Engine  │───▶│  Conditional Output     │  │
│  │  (VeraPDF)      │    │                 │    │                         │  │
│  └─────────────────┘    │  Per-page:      │    │  Fast Path pages:       │  │
│                         │  - Image ratio  │    │   → JSON extraction     │  │
│                         │  - Text coverage│    │                         │  │
│                         │  - Font analysis│    │  AI Path pages:         │  │
│                         │  - Table signals│    │   → Page images (PNG)   │  │
│                         └─────────────────┘    └─────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
        ┌───────────────────┐       ┌───────────────────────────┐
        │   Fast Path       │       │      AI Path              │
        │   JSON Output     │       │   Page Images (PNG)       │
        │                   │       │                           │
        │  - Text blocks    │       │      ┌─────────────────┐  │
        │  - Tables         │       │      │  docling models │  │
        │  - Images         │       │      │  (image input)  │  │
        │  - Reading order  │       │      │                 │  │
        │  - Bounding boxes │       │      │  - OCR          │  │
        │                   │       │      │  - TableFormer  │  │
        │                   │       │      │  - Layout       │  │
        └───────────────────┘       │      └─────────────────┘  │
                    │               │               │           │
                    │               └───────────────┼───────────┘
                    │                               │
                    ▼                               ▼
        ┌─────────────────────────────────────────────────────────┐
        │                    Result Merger                        │
        │                                                         │
        │  - Combine Fast Path JSON + AI Path results             │
        │  - Normalize to unified schema                          │
        │  - Apply reading order                                  │
        └─────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                         Final Output (JSON/MD/HTML)
```

---

## Key Design Decisions

### 1. Single PDF Parse

**Problem**: Original design opened PDF 3 times:
1. pypdf for triage
2. Java JAR for fast path
3. docling for AI path

**Solution**: JAR handles everything in one pass:
- Triage during initial parse
- Extract JSON for fast pages
- Render images for AI pages

### 2. Image-Based AI Processing

**Insight**: docling AI models (OCR, TableFormer, Layout) accept **images**, not PDF objects.

**Benefit**:
- JAR renders page images once
- AI models process images directly
- No duplicate PDF parsing in Python

### 3. Triage in Java

Triage signals available during PDF parsing:
- Font metadata (ToUnicode, Type3)
- XObject image dimensions
- Text chunk positions (for table detection)
- Text character count

---

## Triage Algorithm

### OCR Signals

| Signal | Threshold | Description |
|--------|-----------|-------------|
| Image area ratio | > 5% | Page has significant embedded images |
| Text coverage | < 10% | Low extractable text |
| Missing ToUnicode | > 30% fonts | Fonts lack Unicode mapping |
| Type3 fonts | any | Image-based glyphs |

### Table AI Signals

| Signal | Threshold | Description |
|--------|-----------|-------------|
| Grid-aligned text | detected | Text in tabular arrangement |
| No table borders | true | Borderless table candidate |
| Suspicious text gaps | detected | Large X-gaps on same baseline |

### Suspicious Text Detection (from VeraPDF)

```java
// Text chunks that suggest table structure:
// 1. Text going backwards (multi-column layout)
if (previousChunk.getTopY() < currentChunk.getBottomY()) {
    return true;
}
// 2. Same baseline but large X gap (table cell boundary)
if (sameBaseline && xGap > charHeight * 3) {
    return true;
}
```

---

## CLI Interface

### New Options

```bash
# Hybrid mode with triage
java -jar opendataloader-pdf.jar document.pdf \
    --hybrid \
    --output-dir /tmp/hybrid_output/

# Output structure:
#   /tmp/hybrid_output/
#     triage.json         (page routing decisions)
#     fast_pages.json     (fast path extraction results)
#     ai_pages/
#       page_003.png      (AI path page images)
#       page_007.png
```

### Triage JSON Output

```json
{
  "pages": [
    {"page": 1, "path": "fast"},
    {"page": 2, "path": "fast"},
    {"page": 3, "path": "ai", "needs_ocr": true, "needs_table_ai": false},
    {"page": 4, "path": "fast"}
  ]
}
```

---

## Python API

### Basic Usage

```python
from opendataloader_pdf import convert, convert_with_ai

# Heuristic only (fast, ~100 pages/sec)
result = convert("document.pdf")

# Hybrid with AI (accurate, ~10-20 pages/sec)
result = convert_with_ai("document.pdf")
```

### Advanced Configuration

```python
from opendataloader_pdf import convert_with_ai
from opendataloader_pdf.hybrid import HybridPipelineConfig, AIModelConfig

config = HybridPipelineConfig(
    # Triage thresholds
    triage=TriageConfig(
        image_area_threshold=0.05,
        text_coverage_threshold=0.10,
    ),
    # AI model settings
    ai_models=AIModelConfig(
        ocr=OCRConfig(enabled=True, engine='rapidocr'),
        table=TableConfig(enabled=True, mode='accurate'),
    ),
)

result = convert_with_ai("document.pdf", config=config)
```

### Internal Flow

```
convert_with_ai("document.pdf")
    │
    ▼
1. Create temp directory
2. Call JAR with --hybrid --output-dir /tmp/xxx/
3. JAR outputs:
   - triage.json (routing decisions)
   - fast_pages.json (heuristic extraction)
   - ai_pages/*.png (page images for AI)
4. Load triage.json
5. Process ai_pages/*.png with docling models
6. Merge fast_pages.json + AI results
7. Cleanup temp directory
    │
    ▼
ConversionResult (JSON/MD/HTML)
```

---

## Performance

### Expected Throughput

| Document Type | Fast Pages | AI Pages | Speed |
|---------------|------------|----------|-------|
| Simple text | 100% | 0% | ~100 pages/sec |
| Mixed content | 70% | 30% | ~10-20 pages/sec |
| Scanned PDF | 10% | 90% | ~2-3 pages/sec |

### Comparison

| Approach | PDF Opens | Speed (mixed) | Quality |
|----------|-----------|---------------|---------|
| JAR only | 1 | ~100 p/s | Medium |
| docling only | 1 | ~1.4 p/s | High |
| Old hybrid | 3 | ~5 p/s | High |
| **New hybrid** | **1** | **~10-20 p/s** | **High** |

---

## Implementation Phases

### Phase 1: JAR Triage + Image Export
- [ ] Add `--hybrid` CLI option
- [ ] Implement TriageProcessor in Java
- [ ] Export page images for AI pages
- [ ] Output triage.json

### Phase 2: Python Integration
- [ ] Update pipeline to use JAR hybrid mode
- [ ] Remove pypdf dependency
- [ ] Process images with docling models
- [ ] Merge results

### Phase 3: Optimization
- [ ] Parallel image processing
- [ ] GPU batching for AI models
- [ ] Streaming output for large documents
