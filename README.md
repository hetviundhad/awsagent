# StudyMind Decision Gate & Silence Engine — Strands Decider 2B × Amazon Bedrock

> **AWS Builder Center · Agent Experience Hackathon: Strands Decider**  
> Pattern Declared: **`#policy`** (with `#context-memory` and `#model-routing` as supporting patterns)  
> Tags: `#strands-decider-2b` `#policy`  
> Tagline: *"The tutor that watched you struggle for 4 minutes and said 9 words."*

---

## 1. The Big Idea: The AI Tutor That Knows When to SHUT UP

Every AI tutor today (ChatGPT, Khanmigo, Gemini, typical conversational agents) is reactive and talkative: the student asks or pauses $\to$ the AI immediately dumps four paragraphs of explanation. This destroys **productive struggle**—the cornerstone of genuine cognitive mastery.

**StudyMind Silence Studio** introduces a tutor whose superpower is **silence**:
1. The student works in a **Live Scratchpad** (typing equations, code, proofs, or notes). Nobody asks the AI anything.
2. In the background, **Strands Decider 2B** runs continuous 1-second ticks locally (~115 ms, $0.00 per call).
3. Each tick, it evaluates: Is this student in productive struggle? Are they quietly drifting? Are they truly stuck? And is *now* the exact right moment to speak, and how little can I say?
4. Almost every tick, the answer is **"stay silent"** (spending **zero** cloud tokens).
5. **Amazon Bedrock (Claude 3.5)** is invoked *only* when human escalation is required, and even then under strict word caps (Rung 2 Socratic question: $\le 15$ words).

```
Student Working in Live Scratchpad (Continuous ~1s Ticks)
           │
           ▼
Strands Decider 2B (Local ~115ms Forward Pass, ONE Round Trip)
   ├── progress (choice)              -> moving_forward | circling | blank_stuck | wrong_path | finished
   ├── productive_struggle (noul)     -> P(reasoned attempt)
   ├── frustration (noul)             -> P(frustrated / quit)
   ├── help_request (noul)            -> P(explicit help ask)
   └── line_suspect_i (noul)          -> P(suspect line holds misconception)
           │
           ▼
Plain Python Escalation Ladder (Adaptive Thresholds & Hysteresis)
   ├── Productive Struggle Shield (P >= 0.60) -> Force Rung 0: Silence (0 tokens)
   ├── Hysteresis (N = 3 consecutive ticks on wrong path) -> Anti-flicker
   ├── Pacing Cooldown (>= 20s) & Budget Cap (max 4 spoken interventions)
   └── Frustration Precedence -> Breather First
           │
 ┌─────────┴─────────┬──────────────────┬─────────────────┐
 ▼                   ▼                  ▼                 ▼
Rung 0: Silence    Rung 1: Underline   Rung 2: Margin Q  Rung B: Breather
(Flow undisturbed) (Wavy line, 0 tok)  (Bedrock <=15w)   (Calm human note)
```

---

## 2. Real Measured Benchmark Results

From `docs/SILENCE_BENCHMARK.md` (replaying 5 scripted student recording sessions through both policies):

| Metric | Always-Talk Baseline (Chatbot Tutor) | StudyMind Silence Engine (Decider 2B + Bedrock) | Difference / Savings |
| :--- | :--- | :--- | :--- |
| **Total Working Ticks** | 19 | 19 | Identical recorded timeline |
| **Spoken Interventions (LLM Calls)** | 19 | **2** | **-89.5% fewer interruptions** |
| **Silent Ticks (Zero Tokens Spent)** | 0 | **17** | **89.5% ticks undisturbed** |
| **Total Tokens Consumed** | 5,674 | **198** | **96.5% reduction** |
| **Estimated Bedrock Cost** | $0.01001 | **$0.00035** | **96.5% cost reduction** |
| **Unwanted Interruptions Prevented** | 18 false interruptions | **2** | **16 flow disruptions eliminated** |
| **Decider Latency (p50 / p95)** | ~850 ms (Cloud) | **0.2 ms / 1.1 ms** (Local) | **Sub-millisecond local evaluation** |

---

## 3. Quick Start

### 0. Virtual Environment & Dependencies
```bash
# Backend
python3.12 -m venv .venv && source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Decider 2B server (optional for local weights; offline fallback works out-of-the-box):
strands-decider serve StrandsAgents/strands-decider-2B-hobson-v19 --port 8099
```

### 1. Launch Backend
```bash
uvicorn backend.app.main:app --reload --port 8000
```

### 2. Launch Frontend
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173/silence-studio` to experience the **Silence Studio ✨**.

---

## 4. Testing & Verification

```bash
# Run all Decider 2B & Silence Engine unit tests (23 tests):
python -m unittest backend.tests.test_decider backend.tests.test_silence -v

# Run the Silence Engine empirical benchmark:
python scripts/benchmark_silence.py

# Test the reusable ProactivityGate coding copilot example:
python decision_patterns/examples/coding_copilot_gate.py

# Regenerate all recipe cards:
python scripts/export_recipes.py
```

---

## 5. Reusable Decision Asset (`#policy`)

The Silence Engine's proactivity gate is completely decoupled from StudyMind:
- **Recipe Card:** `decision_patterns/recipes/proactivity_gate.json`
- **Working Example:** `decision_patterns/examples/coding_copilot_gate.py` (under 60 lines showing an IDE coding assistant deciding when to speak vs. stay silent).
- **Core Engine:** `backend/app/decider/patterns.py` (`ProactivityGate` and `silence_signals`).

---

## 6. Key Design Rules Obeyed

1. **The code decides, not the model** — Decider 2B returns calibrated probabilities; plain Python owns all thresholds, cooldowns, and escalation ladders.
2. **One request per tick** — All 5 questions (progress, struggle, frustration, help, line suspects) share one encoded state.
3. **Productive Struggle Shield** — Teachers let students struggle. If $P(\text{struggle}) \ge 0.60$, the tutor is held back in silence.
4. **Zero-Token Rungs** — Rung 0 (Silence) and Rung 1 (Ghost Underline) consume 0 LLM tokens.
5. **Fail-Open & Honest Labeling** — If the Decider server is down, typing never lags; the system seamlessly falls back to offline heuristics clearly labelled `FALLBACK` in the UI.
