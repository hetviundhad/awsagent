# StudyMind AI — Learner Modeling & Bayesian Knowledge Tracing (BKT)

---

## 1. Mathematical Formulation

StudyMind AI uses **Bayesian Knowledge Tracing (BKT)** to dynamically update the probability that a student knows each concept $c_k$:

- $P(L_0)$: Initial prior knowledge probability (default: 0.20)
- $P(T)$: Transition probability of learning between attempts (default: 0.15)
- $P(S)$: Slip probability (student knows concept but errs; default: 0.10)
- $P(G)$: Guess probability (student doesn't know concept but guesses correctly; default: 0.20)

### Observation Update (Bayes' Theorem):

**Case 1: Observation is Correct**
$$P(L_t \mid \text{Correct}) = \frac{P(L_{t-1}) \cdot (1 - P(S))}{P(L_{t-1}) \cdot (1 - P(S)) + (1 - P(L_{t-1})) \cdot P(G)}$$

**Case 2: Observation is Incorrect**
$$P(L_t \mid \text{Incorrect}) = \frac{P(L_{t-1}) \cdot P(S)}{P(L_{t-1}) \cdot P(S) + (1 - P(L_{t-1})) \cdot (1 - P(G))}$$

### Knowledge Transition Update:
$$P(L_{t+1}) = P(L_t \mid \text{Obs}) + (1 - P(L_t \mid \text{Obs})) \cdot P(T)$$

---

## 2. Difficulty Calibration

Slip and Guess probabilities are adjusted based on question difficulty:
- **Hard Questions**: $P(G)$ is reduced (harder to guess correctly); answering correctly yields a stronger positive mastery update.
- **Easy Questions**: $P(S)$ is reduced (unlikely to slip on basic definitions); failing an easy question penalizes mastery more sharply.

---

## 3. Prerequisite-Aware Recommendations

The learner engine traverses the **Concept Prerequisite Graph**:
- If Concept $B$ is weak ($P(L_B) < 0.60$) and its foundational prerequisite Concept $A$ is also weak ($P(L_A) < 0.60$):
  **Recommendation**: *"Before mastering '$B$', strengthen its foundational prerequisite '$A$' first."*
- If Concept $A$ is mastered ($P(L_A) \ge 0.75$) and Concept $B$ is weak:
  **Recommendation**: *"Your foundational prerequisites are solid. Practice targeted state transitions on '$B$'."*

---

## 4. Misconception Detection

When an incorrect response is submitted, the evaluation layer checks for recurring cognitive traps:
- Confusing the **greedy-choice property** with **optimal substructure**.
- Confusing **top-down memoization** with **bottom-up tabulation**.
- Omitting capacity constraints in knapsack state representations.
- Assuming unbalanced worst-case linear traversal for balanced binary search trees.

The detected misconception is recorded, displayed on the post-assessment report, and factored into the student's revision pack.
