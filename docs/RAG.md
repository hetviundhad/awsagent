# StudyMind AI — Grounded RAG Pipeline & Zero-Hallucination Architecture

---

## 1. RAG Design Principles

StudyMind AI enforces a strict epistemic boundary between:
1. **Source-Backed Knowledge**: Information directly grounded in uploaded textbook pages, lecture slides, or video transcripts.
2. **Outside Knowledge**: World knowledge or unverified claims not found in the student's syllabus.

The system will **never hallucinate an answer** when evidence is missing.

---

## 2. Ingestion & Indexing Pipeline

```
Upload (PDF, PPTX, Video)
  │
  ├── PDF: PyPDF extracts pages & detects diagrams
  ├── PPTX: python-pptx extracts slides & shape layouts
  └── Video/Audio: Whisper STT generates timestamp segments [12:43 - 13:26]
  │
Visual Element Extraction ──► Vision Model analyzes figures & tables
  │
Sliding Window Chunking ──► Preserves exact page / slide / timestamp metadata
  │
Topic & Concept Extraction ──► Links chunks to curricular graph
  │
384-Dim Normalized Embeddings ──► Stored in Vector Knowledge Base
```

---

## 3. Retrieval Architecture

Retrieval operates as a **Hybrid Fusion** model:
$$\text{Score}(q, d) = 0.70 \times \text{CosineSimilarity}(\vec{e}_q, \vec{e}_d) + 0.30 \times \text{LexicalOverlap}(q, d)$$

Candidate chunks are filtered by topic or document constraints, followed by score gating.

---

## 4. Confidence Threshold & Unsupported Query Detection

Every query undergoes a confidence check against `RETRIEVAL_CONFIDENCE_THRESHOLD` (default: 0.35):

- **If $\text{TopScore} < \text{Threshold}$**:
  The system refuses to fabricate an answer and responds:
  > *"I couldn't find sufficient evidence for this in your uploaded course material."*
  > *Searched: Units 1–5, Algorithms.pdf, Lecture Slides.*
  > *Best Match Confidence: 18% (Required: 35%).*
  > *[Ask Using Outside Knowledge]*

- **If "Outside Knowledge" is explicitly activated**:
  The tutor responds with a prominent cautionary banner:
  > ⚠️ **Outside Knowledge — not from your course material.**
  > *"Regarding 'quantum computing': In general physics/CS principles..."*

---

## 5. Structured Citation Preservation

Answers never use vague phrases like "According to the slides...". They return structured metadata that the frontend renders as clickable citation cards:

```json
{
  "citation_index": 1,
  "source_type": "pdf",
  "document_name": "Algorithms.pdf",
  "page_number": 42,
  "snippet": "Optimal substructure means that an optimal solution...",
  "chunk_id": "chk_dp_opt_sub"
}
```

Clicking `[Open Page]` or `[Jump to Timestamp]` launches the **Source Viewer Modal**, presenting the exact page text, slide frame, or synchronized video segment.
