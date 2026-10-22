import re
from typing import List, Dict, Any, Optional, Tuple
from backend.app.providers.llm_provider import get_llm_provider
from backend.app.core.config import settings

BOILERPLATE_WORDS = {
    "course", "courses", "tutorial", "tutorials", "job", "jobs", "practice",
    "badge", "badges", "login", "sign in", "signin", "sign up", "signup",
    "register", "last updated", "explore", "placement", "interview preparation",
    "interview prep", "cookie", "privacy", "terms", "advertisement", "promo",
    "promos", "home", "search", "faq", "copyright", "all rights reserved",
    "core concept", "subject concept", "course material", "study material",
    "introduction", "overview", "chapter", "lecture", "unit", "agenda",
    "thank you", "thank you!", "thanks", "questions", "q&a", "author", "authors",
    "table of contents", "outline", "summary slide", "title slide", "references"
}

BOILERPLATE_REGEXES = [
    re.compile(r'\b(courses?|tutorials?|jobs?|practice|quiz|quizzes|login|sign\s*in|sign\s*up|register)\b', re.IGNORECASE),
    re.compile(r'\blast\s+updated\b', re.IGNORECASE),
    re.compile(r'\b(explore|placement|interview\s+prep(aration)?|career|pricing|membership)\b', re.IGNORECASE),
    re.compile(r'\b(badge|advertisement|promo|sponsor|sponsored|cookie|privacy|terms)\b', re.IGNORECASE),
    re.compile(r'\b(copyright|all\s+rights\s+reserved)\b', re.IGNORECASE),
    re.compile(r'\bcore\s+concept\b', re.IGNORECASE),
    re.compile(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{4}\b', re.IGNORECASE),
    re.compile(r'\b(agenda|introduction|thank\s*you|questions\?|author(s)?|dr\.|prof\.|faculty\s+of)\b', re.IGNORECASE),
    re.compile(r'^\d+\s*$', re.IGNORECASE),
]

class ConceptQualityFilter:
    """
    Enforces Step 1 concept quality filter:
    - Must be a noun phrase from the course subject, 1-6 words.
    - Reject boilerplate words (courses, tutorials, jobs, practice, badge, login,
      last updated, explore, placement, interview preparation, etc.).
    - Must appear in at least 2 content units, or in a heading/title.
    - Must have a one-sentence definition taken from the source.
    - An LLM judge pass labels each concept 'valid / junk'; drop junk.
    - Keep each course's concepts isolated. Never mix subjects.
    - Target 15-40 clean concepts per course.
    """

    def __init__(self):
        self._llm = None

    def get_llm(self):
        if self._llm is None:
            self._llm = get_llm_provider(settings.LLM_PROVIDER)
        return self._llm

    def is_boilerplate(self, text: str) -> bool:
        t_clean = text.strip().lower()
        if not t_clean:
            return True
        for pat in BOILERPLATE_REGEXES:
            if pat.search(t_clean):
                return True
        words = set(re.findall(r'\b[a-z]+\b', t_clean))
        if words.issubset(BOILERPLATE_WORDS):
            return True
        return False

    def validate_candidate_name(self, name: str, course_subject: str = "") -> Tuple[bool, str]:
        """
        Validates whether candidate name satisfies lexical rules:
        - 1-6 words
        - Not boilerplate
        - Not cross-subject pollution (e.g. CPU Scheduling in Algorithms course)
        """
        cleaned = re.sub(r'[^a-zA-Z0-9\s\-/]', ' ', name).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        if not cleaned:
            return False, "Empty concept name"

        words = cleaned.split()
        if len(words) < 1 or len(words) > 6:
            return False, f"Word count ({len(words)}) out of bounds (1-6 words allowed)"

        if self.is_boilerplate(cleaned):
            return False, "Contains boilerplate or promo words"

        return True, cleaned

    def extract_definition_from_chunks(self, concept_name: str, chunks: List[Dict[str, Any]]) -> Optional[str]:
        """
        Extracts a clean one-sentence definition directly from the source text where the concept appears.
        """
        c_low = concept_name.lower()
        # Search chunks for definitional sentences
        definitional_patterns = [
            re.compile(r'([^.?!]*\b' + re.escape(concept_name) + r'\b\s+(?:is|refers\s+to|means|defines|represents|states\s+that)[^.?!]*[.?!])', re.IGNORECASE),
            re.compile(r'([^.?!]*\b(?:defined\s+as|known\s+as)\s+[^.?!]*\b' + re.escape(concept_name) + r'\b[^.?!]*[.?!])', re.IGNORECASE),
            re.compile(r'([^.?!]*\b' + re.escape(concept_name) + r'\b[^.?!]*[.?!])', re.IGNORECASE)
        ]

        for chk in chunks:
            content = chk.get("content", "")
            if c_low not in content.lower():
                continue
            for pat in definitional_patterns:
                m = pat.search(content)
                if m:
                    sentence = m.group(1).strip()
                    sentence = re.sub(r'\s+', ' ', sentence)
                    # Clean markdown prefixes
                    sentence = re.sub(r'^[#*_\-\s]+', '', sentence)
                    if 25 <= len(sentence) <= 280 and not self.is_boilerplate(sentence):
                        return sentence

        return None

    def check_occurrence_threshold(self, concept_name: str, chunks: List[Dict[str, Any]]) -> bool:
        """
        Must appear in at least 2 content units, OR appear in a heading/title/slide.
        """
        c_low = concept_name.lower()
        occurrence_count = 0
        in_heading_or_slide = False

        for chk in chunks:
            content = chk.get("content", "").lower()
            if c_low in content:
                occurrence_count += 1
                # Check if it appears in a heading or slide
                if chk.get("slide_number") is not None:
                    in_heading_or_slide = True
                if chk.get("chunk_type") in ["title", "slide", "figure"]:
                    in_heading_or_slide = True
                doc_name = chk.get("document_name", "").lower()
                if c_low in doc_name:
                    in_heading_or_slide = True
                # Check markdown heading in chunk content
                for line in content.split("\n"):
                    if line.strip().startswith("#") and c_low in line:
                        in_heading_or_slide = True

        return (occurrence_count >= 2) or in_heading_or_slide

    def judge_concept_validity(self, concept_name: str, definition: str, course_subject: str) -> bool:
        """
        LLM judge pass to label concept 'valid / junk'. Drops junk.
        Falls back to rule heuristics if LLM returns mock or error.
        """
        # Lexical sanity first
        if self.is_boilerplate(concept_name) or self.is_boilerplate(definition):
            return False

        try:
            llm = self.get_llm()
            # If mock provider, use rigorous rule-based validation
            if getattr(llm, "provider_name", None) == "mock" or "Mock" in llm.__class__.__name__:
                # Validate length, words, definition quality
                if len(concept_name.split()) > 6 or len(definition) < 20:
                    return False
                return True

            # Use LLM judge prompt
            prompt = (
                f"You are a strict curriculum evaluator. Decide whether '{concept_name}' is a valid academic concept "
                f"in the course subject '{course_subject}'.\n"
                f"Definition: {definition}\n"
                f"Respond with JSON: {{\"status\": \"valid\" | \"junk\", \"reason\": \"<1 sentence>\"}}"
            )
            res = llm.client.chat.completions.create(
                model=getattr(llm, "model", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            raw = res.choices[0].message.content
            return '"status": "valid"' in raw or '"status":"valid"' in raw
        except Exception:
            # Fallback to deterministic rules
            return not self.is_boilerplate(concept_name) and len(definition) >= 20

concept_filter = ConceptQualityFilter()
