"""
Misconception Atlas - Generated once per problem via Amazon Bedrock (Haiku fast).

Division of labour:
  - Bedrock: rare and creative (analyzes the problem and derives 3-6 likely
    misconceptions and 3-5 correct solution milestones).
  - Strands Decider 2B: frequent, local, calibrated judge (judges every tick against the Atlas).

If Bedrock fails or is unavailable, falls back to a deterministic generic atlas flagged `fallback=True`.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class Misconception:
    id: str
    name: str
    description: str  # How the student's text looks when they hold this misconception
    concept: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Atlas:
    problem: str
    course_name: str
    misconceptions: List[Misconception]
    milestones: List[str]
    fallback: bool = False
    generated_by: str = "bedrock"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "problem": self.problem,
            "course_name": self.course_name,
            "misconceptions": [m.to_dict() for m in self.misconceptions],
            "milestones": self.milestones,
            "fallback": self.fallback,
            "generated_by": self.generated_by,
        }

    def summary(self) -> Dict[str, Any]:
        return {
            "misconception_count": len(self.misconceptions),
            "milestone_count": len(self.milestones),
            "fallback": self.fallback,
            "misconceptions": [{"id": m.id, "name": m.name, "concept": m.concept} for m in self.misconceptions],
            "milestones": self.milestones,
        }


def _generic_atlas(problem: str, course_name: str, weak_concepts: Sequence[str] = ()) -> Atlas:
    """Deterministic generic fallback when Bedrock is unavailable. Visibly flagged."""
    weak = [w for w in weak_concepts if w]
    c1 = weak[0] if weak else "Core Concept"
    c2 = weak[1] if len(weak) > 1 else "Analysis & Syntax"

    misconceptions = [
        Misconception(
            id="m_premature_simplification",
            name="Premature Simplification",
            description="The student overlooks edge cases or drops necessary constraints in their reasoning.",
            concept=c1,
        ),
        Misconception(
            id="m_inverted_relationship",
            name="Inverted Relationship",
            description="The student confuses cause and effect, inputs and outputs, or inverse operations.",
            concept=c2,
        ),
        Misconception(
            id="m_syntax_or_off_by_one",
            name="Boundary or Index Error",
            description="The student has an off-by-one boundary, loop condition flaw, or arithmetic sign mistake.",
            concept="Execution",
        ),
        Misconception(
            id="m_unjustified_assumption",
            name="Unjustified Assumption",
            description="The student introduces an unstated premise or skips the key intermediate proof/step.",
            concept=course_name or "Methodology",
        ),
    ]

    milestones = [
        "1. Identify the given state, inputs, and constraints accurately.",
        "2. Formulate the core governing equation, recurrence, or hypothesis.",
        "3. Work through the intermediate reasoning steps with explicit working.",
        "4. Validate the outcome against base conditions and constraints.",
    ]

    return Atlas(
        problem=problem,
        course_name=course_name,
        misconceptions=misconceptions,
        milestones=milestones,
        fallback=True,
        generated_by="generic_fallback",
    )


ATLAS_PROMPT = """You are an expert pedagogy designer for a computer science and STEM learning platform.
Analyze this problem and produce a structured Misconception Atlas for an AI supervisor that watches student reasoning in a live scratchpad.

Problem: {problem}
Course: {course_name}
Topics: {topics}
Student Weak Areas (from BKT learner model): {weak_concepts}

Respond with ONLY valid JSON (no markdown formatting, no code fences, no commentary) matching this schema:
{{
  "misconceptions": [
    {{
      "id": "m1",
      "name": "Short Name (3-5 words)",
      "description": "One sentence describing exactly how the student's text looks when they hold this misconception (e.g. 'Student adds elements without checking if already visited').",
      "concept": "Concept name"
    }}
  ],
  "milestones": [
    "Milestone 1: description of first correct step",
    "Milestone 2: description of second correct step",
    "Milestone 3: description of third correct step"
  ]
}}

Requirements:
- 3 to 6 misconceptions.
- 3 to 5 milestones in chronological solution order.
- Descriptions MUST focus on concrete patterns in the student's written text, not abstract thoughts.
- NEVER include negated descriptions.
"""


def build_atlas(
    problem: str,
    course_name: str = "Computer Science",
    topics: Sequence[str] = (),
    weak_concepts: Sequence[str] = (),
) -> Atlas:
    """Build the Misconception Atlas once per problem using Bedrock Haiku, with robust fallback."""
    problem_clean = (problem or "").strip()
    if not problem_clean:
        return _generic_atlas("General Practice", course_name, weak_concepts)

    topics_txt = ", ".join(list(topics)[:8]) or "Core Syllabus"
    weak_txt = ", ".join(list(weak_concepts)[:6]) or "None recorded"

    prompt = ATLAS_PROMPT.format(
        problem=problem_clean[:1500],
        course_name=course_name or "General",
        topics=topics_txt,
        weak_concepts=weak_txt,
    )

    # 1. Try Bedrock fast tier (Haiku)
    try:
        from backend.app.providers.bedrock_provider import get_bedrock
        br = get_bedrock()
        if br.available():
            msgs = [{"role": "user", "content": prompt}]
            resp = br.converse(msgs, tier="fast", max_tokens=1000, temperature=0.2)
            raw_text = resp.get("text", "").strip()
            # Clean JSON if wrapped in markdown
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text).strip()
            data = json.loads(raw_text)

            miscs = []
            for i, m in enumerate(data.get("misconceptions", [])[:6]):
                if isinstance(m, dict) and m.get("name") and m.get("description"):
                    mid = str(m.get("id") or f"m{i+1}")
                    miscs.append(
                        Misconception(
                            id=mid,
                            name=str(m["name"])[:60],
                            description=str(m["description"])[:250],
                            concept=str(m.get("concept") or course_name)[:60],
                        )
                    )

            stones = [str(s)[:150] for s in data.get("milestones", []) if s][:5]

            if len(miscs) >= 2 and len(stones) >= 2:
                return Atlas(
                    problem=problem_clean,
                    course_name=course_name,
                    misconceptions=miscs,
                    milestones=stones,
                    fallback=False,
                    generated_by="bedrock-haiku",
                )
    except Exception as exc:
        print(f"[silence.atlas] Bedrock atlas generation failed ({exc}); falling back to generic atlas")

    # 2. Try App LLM provider (Groq / OpenAI) if configured
    try:
        from backend.app.providers.llm_provider import get_llm_provider
        from backend.app.core.config import settings
        if settings.GROQ_API_KEY:
            prov = get_llm_provider("groq")
            res = prov.generate_completion(
                [{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.2,
            )
            raw_text = res.get("content", "").strip()
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text).strip()
            data = json.loads(raw_text)

            miscs = []
            for i, m in enumerate(data.get("misconceptions", [])[:6]):
                if isinstance(m, dict) and m.get("name") and m.get("description"):
                    mid = str(m.get("id") or f"m{i+1}")
                    miscs.append(
                        Misconception(
                            id=mid,
                            name=str(m["name"])[:60],
                            description=str(m["description"])[:250],
                            concept=str(m.get("concept") or course_name)[:60],
                        )
                    )
            stones = [str(s)[:150] for s in data.get("milestones", []) if s][:5]
            if len(miscs) >= 2 and len(stones) >= 2:
                return Atlas(
                    problem=problem_clean,
                    course_name=course_name,
                    misconceptions=miscs,
                    milestones=stones,
                    fallback=False,
                    generated_by="groq-haiku-fallback",
                )
    except Exception as exc:
        print(f"[silence.atlas] Secondary LLM provider failed ({exc})")

    # 3. Fallback
    return _generic_atlas(problem_clean, course_name, weak_concepts)
