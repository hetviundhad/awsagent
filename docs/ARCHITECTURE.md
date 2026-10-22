# StudyMind AI — System Architecture Specification

**Multimodal AI Hackathon 2026 – Track D: Personalized Tutoring & Adaptive Learning**

---

## 1. High-Level Architecture Overview

StudyMind AI is an end-to-end multimodal learning platform designed for university students and professors. Unlike generic chatbots, StudyMind AI ingests lecture videos, textbooks, PDFs, and slide decks, converting them into a source-linked multimodal knowledge base with verified claims, explainable Bayesian Knowledge Tracing, and quantitative benchmarks.

```
                             STUDENT / USER
                                   │
                                   ▼
              React 18 + Vite + Tailwind CSS + Recharts
         (Persistent 30/70 Split View • Voice STT/TTS • Deep-Links)
                                   │
                                   ▼
                        FastAPI Microservice (Python)
      ┌────────────────────────────┼────────────────────────────┐
      ▼                            ▼                            ▼
Grounded Tutor & Self-RAG    Adaptive Assessment         Bayesian Knowledge
   Claim Guardrail Engine     Cross-Model Verifier        Tracing (BKT Engine)
      │                            │                            │
      └────────────────────────────┼────────────────────────────┘
                                   ▼
                         Hybrid Retrieval Layer
               Dense Cosine (384d) + BM25 Lexical (RRF k=60)
                                   │
                     ┌─────────────┴─────────────┐
                     ▼                           ▼
            Supabase PostgreSQL            Local Persistent
            + pgvector (17 Tables)        Storage Engine (Fallback)
                     │                           │
                     └─────────────┬─────────────┘
                                   ▼
           Multimodal Ingestion Pipeline (PyMuPDF, OpenCV, Whisper)
```

---

## 2. Multimodal Ingestion Pipeline (`backend/app/ingestion/pipeline.py`)

StudyMind processes unstructured academic media through a strict 9-stage extraction pipeline:

1. **Format Detection & Validation**: Supports `.pdf`, `.pptx`, `.mp4`, `.mp3`, `.wav`, `.png`, `.jpg`, and public web study URLs.
2. **Layout-Aware PDF Extraction**:
   - Uses `PyMuPDF` (`fitz`) to extract text blocks along with precise normalized bounding boxes `[x0, y0, x1, y1]`.
   - Extracts embedded diagrams and charts with coordinates for visual deep-linking.
3. **OpenCV Keyframe & Slide-Change Detection**:
   - Computes frame-by-frame structural similarity to detect slide transitions in lecture videos.
   - Extracts keyframes and aligns them with Whisper audio transcript intervals (`timestamp_start`, `timestamp_end`).
4. **PPTX Slide & Speaker Notes Parsing**:
   - Extracts structured shape text, embedded slide titles, and professor speaker notes (`python-pptx`).
5. **Vision Model Diagram Description**:
   - Visual elements are routed to the `VisionProvider` to produce descriptive captions (e.g. recurrence trees, state tables, memory layouts) that are indexed alongside text.
6. **Concept & Topic Extraction**:
   - Hierarchically structures content into Course $\rightarrow$ Unit $\rightarrow$ Topic $\rightarrow$ Concept nodes.
7. **Prerequisite DAG Construction & Cycle Detection**:
   - Uses `networkx.DiGraph` to build a directed dependency graph.
   - Validates that the graph is strictly acyclic (`networkx.is_directed_acyclic_graph`), preventing circular dependencies.
8. **Vector Embedding & BM25 Indexing**:
   - Chunks are vectorized into 384-dimensional normalized embeddings and indexed in `pgvector` alongside a BM25 inverted index.
9. **Real-time SSE Streaming**:
   - Streams stage-by-stage progress percentages over Server-Sent Events (`/api/ingestion/progress/{task_id}/stream`) to the UI.

---

## 3. Retrieval & Grounding Architecture

### A. Hybrid Search via Reciprocal Rank Fusion (RRF)
To balance semantic conceptual matching with exact technical term precision, StudyMind uses RRF ($k=60$):
$$\text{RRF}(d) = w_{\text{dense}} \cdot \frac{1}{60 + r_{\text{dense}}(d)} + w_{\text{bm25}} \cdot \frac{1}{60 + r_{\text{bm25}}(d)}$$
- Dense similarity provides semantic generalization across synonyms (e.g., "caching" $\leftrightarrow$ "memoization").
- BM25 provides lexical precision for formulas, variables, and specific theorem names.

### B. Self-RAG Claim Verification Guardrail (`backend/app/rag/self_rag.py`)
Answers are not blindly served to the student:
1. The tutor response is parsed into atomic factual claims.
2. Each claim is verified for natural language entailment against retrieved source excerpts.
3. Claims are assigned verification statuses:
   - 🟢 **Verified Claim**: Directly entailed by source text (with document, page/slide/timestamp reference).
   - 🟡 **Ambiguous Claim**: Partially supported or extrapolated.
   - 🔴 **Unsupported Claim**: Refused or flagged when confidence falls below the calibrated refusal threshold ($\tau = 0.22$).

### C. "Show Me" Deep-Link Cards (`SourceViewerModal.tsx`)
Citations feature interactive deep-links:
- **Video Citations**: Launches a playable video modal with automatic `timestamp_start` seeking, timeline playback, and auto-pause at `timestamp_end`.
- **PDF Citations**: Renders a side-by-side PDF preview with an animated highlight bounding box over the exact paragraph.
- **Slide Citations**: Displays the high-resolution slide keyframe with highlighted speaker notes.

---

## 4. Adaptive Learning & Learner Modeling

### A. Bayesian Knowledge Tracing (BKT) Formulation (`backend/app/learner/bkt.py`)
For each concept $k$, the student's mastery $P(L_t)$ is updated after each attempt:
$$P(L_t | \text{Correct}) = \frac{P(L_{t-1}) \cdot (1 - P(S))}{P(L_{t-1}) \cdot (1 - P(S)) + (1 - P(L_{t-1})) \cdot P(G)}$$
$$P(L_t | \text{Incorrect}) = \frac{P(L_{t-1}) \cdot P(S)}{P(L_{t-1}) \cdot P(S) + (1 - P(L_{t-1})) \cdot (1 - P(G))}$$
$$P(L_{t+1}) = P(L_t | \text{Obs}) + (1 - P(L_t | \text{Obs})) \cdot P(T)$$
Parameters ($P(L_0), P(T), P(S), P(G)$) are dynamically calibrated based on question difficulty:
- **Easy**: $P(G) = 0.25$, $P(S) = 0.10$
- **Medium**: $P(G) = 0.18$, $P(S) = 0.14$
- **Hard**: $P(G) = 0.12$, $P(S) = 0.20$

### B. Prerequisite Lock Propagation
- Concepts with $P(L) < 0.60$ trigger a **Prerequisite Lock** on dependent downstream concepts.
- The UI renders locked badges with lock icons and a 1-click **"Remediate in Tutor"** CTA that directly asks the AI tutor to teach the foundational requirement.

### C. Cross-Model Assessment Verification (`generator.py`)
Assessment questions must pass:
1. **Source Entailment**: The question and correct answer must be fully entailed by course excerpts.
2. **Blind Solver Test**: An independent model instance must correctly solve the question without seeing the ground-truth key. Questions failing this check are discarded (with discard rate metrics tracked).
3. **SHA-256 Deduplication**: Question hashes prevent repetitive questions across sessions.

---

## 5. Multi-Agent Synthetic Student Simulator (`simulator.py`)

To quantitatively demonstrate personalized adaptation across heterogeneous learning speeds without waiting weeks for student data, StudyMind simulates 3 distinct persona agents over 10 sequential sessions:
- ⚡ **Fast Learner**: High initial capability ($P_{\text{correct}} = 0.90$), rapid concept unlocks, accelerates to advanced space-saving tabulation.
- 📐 **Struggles with Math**: Weak on proofs ($P_{\text{correct}} = 0.42$), blocked by locked nodes until foundation is remediated, achieving recovery by Session 8.
- 🎧 **Skips Lectures**: Attempts quizzes without viewing lecture slides ($P_{\text{correct}} = 0.52$), exhibits plateaued mastery and high slip until routed to video keyframe citations.

Results stream live over Server-Sent Events (`/api/evaluation/simulator-stream`) to the Judge Dashboard.

---

## 6. Evaluation Benchmark Suite (`ragas_eval.py`)

StudyMind AI rejects fabricated numbers. The evaluation suite runs against a 30-item Golden Evaluation Benchmark (15 source-answerable, 6 multimodal [3 video, 3 visual], 9 unsupported off-syllabus) and computes:
- **Faithfulness**: Claim entailment against context.
- **Answer Relevancy**: Query-answer cosine similarity.
- **Context Precision & Recall**: Retrieval quality against gold chunks.
- **Citation Accuracy**: Valid coordinate targeting.
- **Unsupported Refusal Rate**: Zero-hallucination detection accuracy.
- **False Refusal Rate**: Rejection of valid course questions.
- **BKT Prediction Accuracy**: Empirical Area Under ROC Curve (AUC) and Log-Loss on student attempts.
- **Data Export**: Full CSV and JSON export endpoints for third-party auditing.

---

## 7. Frontend User Experience & Voice Architecture

- **Persistent 30/70 Split View**: Left 30% panel displays the live BKT knowledge graph, prerequisite lock indicators, and study goals; right 70% panel hosts the interactive grounded tutor chat.
- **Voice-to-Voice Interaction**: Powered by WebSpeech STT and TTS with natural Hinglish system prompting ("English technical terms preserved, conversational explanation in natural Hinglish").
- **3-State Visual Indicator**:
  - 🔵 **Listening**: Blue pulsing ring with audio level feedback.
  - 🟡 **Thinking / Grounding**: Amber spinning indicator during hybrid retrieval and Self-RAG claim validation.
  - 🟢 **Speaking / TTS**: Emerald animated soundwave bars during audio response.
- **1-Click Demo Seed**: Prominent header button allows judges to seed and explore the entire multimodal knowledge base in under 60 seconds without manual file uploads.
