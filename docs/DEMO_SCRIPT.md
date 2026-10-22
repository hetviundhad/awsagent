# StudyMind Silence Engine — Video Demo Script (2:45 Max)

**Title:** The AI Tutor That Knows When to SHUT UP  
**Length:** 2 minutes 45 seconds  
**Target Audience:** AWS Builder Center Judges & Community  
**Tags:** `#strands-decider-2b` `#policy`  

---

### Shot 1: The Hook (0:00 – 0:15)
- **Visual:** Quick cut of ChatGPT or a generic AI tutor window being asked a simple question and immediately dumping 4 huge paragraphs of text. Red "X" stamp appears over it.
- **Voiceover:**
  > "Every AI tutor today has the exact same problem: it talks too much. The moment a student pauses, it dumps paragraphs of text—destroying productive struggle. But what if an AI tutor’s superpower... was silence?"

---

### Shot 2: Silence Studio & Continuous Watching (0:15 – 0:50)
- **Visual:** Cut to **StudyMind Silence Studio**. Live Scratchpad open with a student typing through a dynamic programming problem. The camera zooms slightly on the **Silence Meter** in the top right (calm green eye blinking on each tick, counter increasing: "Watched 14 ticks · Spoke 0 times · 0 tokens spent on the other 14").
- **Voiceover:**
  > "Meet StudyMind Silence Studio. Here, the student works in a live scratchpad. Nobody asked the AI anything. Instead, a local 2-billion parameter model—Strands Decider 2B—watches in the background every single second. Running in just 115 milliseconds locally with zero per-token cost, it judges: is the student productively struggling? If yes, it stays completely silent."

---

### Shot 3: Rung 1 — The Ghost Underline (0:50 – 1:10)
- **Visual:** The student types an off-by-one error or greedy sorting mistake. The **Heartbeat strip** along the bottom pulses amber. A soft, wavy underline gently fades in beneath line 4. No sound. No popups. No dialogue boxes.
- **Voiceover:**
  > "When the student quietly drifts onto a wrong path, the engine doesn't lecture. It activates Rung 1 of the Escalation Ladder: the Ghost Underline. A subtle wavy line under the suspect step. Zero words. Zero Bedrock tokens. Leaving the student in their problem-solving flow."

---

### Shot 4: Rung 2 — The 9-Word Margin Question (1:10 – 1:30)
- **Visual:** The student stays paused on that line for 3 ticks. The Ghost Margin reveals a handwritten-style note anchored to line 4: *"What happens to remaining capacity when ratio is maximized?"* (9 words). The student edits the line to a 2D DP array.
- **Voiceover:**
  > "Only after 3 consecutive ticks on the wrong path does the engine open its mouth. And when it speaks through Amazon Bedrock, it obeys strict word caps: exactly ONE Socratic question in the margin under 15 words. Here: just nine words. The student reads it, has an 'aha!' moment, and fixes the recurrence."

---

### Shot 5: Frustration & The Human Breather (1:30 – 1:55)
- **Visual:** Student types: *"I hate this, none of this makes sense, I give up."* The Heartbeat line spikes purple. At the bottom, a calm lavender banner appears: *"Take a breath. You are doing real, hard thinking here—it is completely normal to pause."* Two feedback buttons: "Helpful" / "You interrupted me".
- **Voiceover:**
  > "If frustration spikes, the engine never lectures. It triggers a Breather first—a calm human reassurance with zero academic content. And when students click 'Helpful' or 'You interrupted me', adaptive thresholds calibrate live without static bias."

---

### Shot 6: Time Machine Scrubber (1:55 – 2:15)
- **Visual:** Switch to the **Time Machine** tab. Drag the scrubber bar backwards across the session timeline. The scratchpad rewinds to tick 6. The popover displays: *"Why stayed silent: productive_struggle_shield (0.82 >= 0.60)"*.
- **Voiceover:**
  > "In the Time Machine, judges can inspect every single second. Hovering any dot shows the exact calibrated probabilities and the plain Python rule that held the tutor back."

---

### Shot 7: The Duel vs. Always-Talk (2:15 – 2:35)
- **Visual:** Click **"Run Duel Comparison"**. Side-by-side empirical cards appear:
  - Silence Engine: 2 LLM calls, 198 tokens, $0.00035, 0 false interruptions.
  - Always-Talk: 19 LLM calls, 5,674 tokens, $0.01001, 16 false interruptions.
- **Voiceover:**
  > "Clicking 'Duel' replays this identical session timeline through a conventional chatbot tutor. The numbers are real: Silence Engine cut tokens and costs by 96.5%, and prevented 16 unwanted interruptions while the student was in productive flow."

---

### Shot 8: Reusable Recipe & Call to Action (2:35 – 2:45)
- **Visual:** VS Code view of `decision_patterns/examples/coding_copilot_gate.py` showing `ProactivityGate` running in under 50 lines for a developer coding assistant. Graphic showing `#strands-decider-2b` and `#policy`.
- **Voiceover:**
  > "This proactivity gate is completely reusable for coding copilots, writing agents, and autonomous assistants. Check out the recipe in our open repo. The future of AI tutors isn't talking more—it's knowing when to shut up."
