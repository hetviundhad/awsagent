# Submission Checklist — Deadline Fri Oct 23, 2026, 11:59 PM PDT

## 1. Secrets & Cleanliness
- [ ] Rotate leaked keys (Groq, Supabase service key, AWS) and confirm `.env` and `frontend/.env` are NOT in the repo (`git ls-files | grep -i "\.env$"` prints nothing).
- [ ] Public GitHub repo; remove `frontend/node_modules`, `frontend/dist`, `backend/data/storage` (already in `.gitignore`).

## 2. Model & Verification Tests
- [ ] Real Decider server running: `strands-decider serve StrandsAgents/strands-decider-2B-hobson-v19 --port 8099` (shows online + real checkpoint name in Decision Lab and Silence Meter).
- [ ] Unit tests pass: `python -m unittest backend.tests.test_decider backend.tests.test_silence -v` (23 tests OK).
- [ ] Silence Engine benchmark run: `python scripts/benchmark_silence.py` produces `docs/SILENCE_BENCHMARK.md` and `eval/charts/silence_comparison.svg`.
- [ ] Reusable coding copilot example passes: `python decision_patterns/examples/coding_copilot_gate.py` (under 80 lines).
- [ ] Recipes regenerated: `python scripts/export_recipes.py` generates all 7 recipes including `proactivity_gate.json`.
- [ ] Frontend compiles cleanly: `npm run build` in `frontend/` exits 0.

## 3. Demo Video (< 3:00)
- [ ] Video recorded following `docs/DEMO_SCRIPT.md` (2:45 max).
- [ ] Key moments captured:
  1. Hook: chat-based AI tutor talking too much vs. Silence Studio.
  2. Student working in Live Scratchpad; Decider 2B continuous watching; Silence Meter counting silent ticks.
  3. Rung 1 Ghost Underline appearing with zero words and zero tokens.
  4. Rung 2 Margin Question (9 words) and student fixing the step.
  5. Frustration triggering Breather first, followed by adaptive threshold feedback ("Helpful" / "You interrupted me").
  6. Time Machine scrubber demonstrating exact probabilities and "Why silent?" popover.
  7. Duel vs Always-Talk baseline demonstrating 96.5% token reduction and 16 false interruptions prevented.
  8. Reusable `#policy` ProactivityGate in coding copilot.
- [ ] Public video URL pasted into `docs/ARTICLE.md` and submission form.

## 4. Builder Center Article & Community Post
- [ ] Article published on AWS Builder Center using `docs/ARTICLE.md`.
- [ ] Both mandatory tags included: **#strands-decider-2b** and **#policy**.
- [ ] Pattern declared in the first paragraph: `#policy` (with `#context-memory` and `#model-routing` as supporting).
- [ ] Public GitHub repository link included.
- [ ] Real empirical benchmark numbers from `docs/SILENCE_BENCHMARK.md` included (never fudged).
- [ ] Reusable recipe linked: `decision_patterns/recipes/proactivity_gate.json` and `decision_patterns/examples/coding_copilot_gate.py`.
- [ ] Originality: StudyMind Silence Studio declared as the novel hackathon innovation built for this event.
