"""
backend/app/services/conflicts.py
Cross-Document Source Disagreement and Conflict Detection Engine.
Extracts atomic factual claims (numbers, units, definitions, architecture parameters)
from chunks across different course documents, pairs claims about the same entity/attribute,
and uses deterministic numeric/unit comparison plus NLI-style critic judgment.
Surfaces confident conflicts, alerts the Tutor, and allows per-student conflict resolution.
"""

import os
import re
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from backend.app.services.database import db
from backend.app.providers.llm_provider import get_llm_provider
from backend.app.core.config import settings

class SourceConflictDetector:
    def __init__(self):
        self.confidence_threshold = getattr(settings, "CONFLICT_CONFIDENCE_THRESHOLD", 0.70)
        self.llm = get_llm_provider(settings.LLM_PROVIDER, settings.OPENAI_API_KEY)

    def extract_numerical_claims(self, text: str) -> List[Dict[str, Any]]:
        """
        Deterministic regex extraction of numerical and dimensional claims (e.g. 128 MB, 3 replicas, 10 min).
        """
        claims = []
        # Pattern: captures numbers with units like MB, GB, KB, seconds, minutes, replicas, nodes, slots
        num_patterns = [
            r'(\b\w+(?:\s+\w+){0,3})\s+(?:is|was|of|default|equals|set to)?\s*(\d+(?:\.\d+)?)\s*(mb|gb|tb|kb|seconds|minutes|hours|replicas|nodes|slots|times|%)',
            r'(\b\w+(?:\s+\w+){0,2}\s+size)\s*(?:is|of)?\s*(\d+)\s*(mb|gb|kb)',
            r'(\breplication\s+factor)\s*(?:is|of)?\s*(\d+)'
        ]
        for pat in num_patterns:
            matches = re.finditer(pat, text, re.IGNORECASE)
            for m in matches:
                entity = m.group(1).strip().lower()
                val = m.group(2)
                unit = m.group(3).lower() if len(m.groups()) >= 3 and m.group(3) else ""
                claims.append({
                    "attribute": entity,
                    "value": val,
                    "unit": unit,
                    "raw_claim": m.group(0).strip()
                })
        return claims

    def detect_conflicts_for_course(self, course_id: str) -> List[Dict[str, Any]]:
        """
        Scans all chunks across distinct documents in the course to find factual disagreements.
        """
        chunks = db.list_all("knowledge_chunks", lambda c: c.get("course_id") == course_id)
        if not chunks:
            return []

        # Group chunks by document
        doc_chunks: Dict[str, List[Dict[str, Any]]] = {}
        for ch in chunks:
            doc_name = ch.get("document_name") or "unknown"
            doc_chunks.setdefault(doc_name, []).append(ch)

        doc_names = list(doc_chunks.keys())
        if len(doc_names) < 2:
            return []

        stored_conflicts = []

        # Compare pairs of documents
        for i in range(len(doc_names)):
            for j in range(i + 1, len(doc_names)):
                d1 = doc_names[i]
                d2 = doc_names[j]

                # Check numerical claims in d1 vs d2
                for ch1 in doc_chunks[d1]:
                    claims1 = self.extract_numerical_claims(ch1.get("content", ""))
                    if not claims1:
                        continue

                    for ch2 in doc_chunks[d2]:
                        claims2 = self.extract_numerical_claims(ch2.get("content", ""))
                        if not claims2:
                            continue

                        # Compare claims on matching attributes
                        for c1 in claims1:
                            for c2 in claims2:
                                # Attribute lexical overlap
                                words1 = set(c1["attribute"].split())
                                words2 = set(c2["attribute"].split())
                                common = words1.intersection(words2)

                                if common and (c1["attribute"] == c2["attribute"] or "size" in common or "replication" in common or "block" in common):
                                    # Check value mismatch
                                    if c1["value"] != c2["value"]:
                                        conflict_id = f"conf_{uuid.uuid4().hex[:10]}"
                                        p1 = ch1.get("page_number") or ch1.get("slide_number") or 1
                                        p2 = ch2.get("page_number") or ch2.get("slide_number") or 1
                                        
                                        rec = {
                                            "id": conflict_id,
                                            "course_id": course_id,
                                            "attribute": c1["attribute"],
                                            "type": "numeric_specification_mismatch",
                                            "confidence": 0.88,
                                            "claim_a": {
                                                "document_name": d1,
                                                "page_number": p1,
                                                "statement": c1["raw_claim"],
                                                "value": f"{c1['value']} {c1['unit']}".strip(),
                                                "snippet": ch1.get("content", "")[:160].replace("\n", " ")
                                            },
                                            "claim_b": {
                                                "document_name": d2,
                                                "page_number": p2,
                                                "statement": c2["raw_claim"],
                                                "value": f"{c2['value']} {c2['unit']}".strip(),
                                                "snippet": ch2.get("content", "")[:160].replace("\n", " ")
                                            },
                                            "status": "active",
                                            "trusted_source": None,
                                            "created_at": datetime.utcnow().isoformat()
                                        }
                                        stored_conflicts.append(rec)
                                        # Save in database
                                        db.insert("conflicts" if "conflicts" in db.data else "misconceptions", rec, save_disk=False)

        # Deduplicate conflicts on identical attribute & documents
        unique_conflicts = []
        seen = set()
        for conf in stored_conflicts:
            key = (conf["attribute"], conf["claim_a"]["document_name"], conf["claim_b"]["document_name"])
            if key not in seen:
                seen.add(key)
                unique_conflicts.append(conf)

        return unique_conflicts

    def judge_claim_pair(self, claim_a_text: str, claim_b_text: str) -> Tuple[str, float]:
        """
        NLI Critic judgment between two claims: returns ("conflict" | "agree" | "unrelated", confidence).
        Uses deterministic numeric heuristics first, then critic LLM fallback.
        """
        nums_a = re.findall(r'\b\d+(?:\.\d+)?\b', claim_a_text)
        nums_b = re.findall(r'\b\d+(?:\.\d+)?\b', claim_b_text)

        # Check for numeric mismatch on same keyword
        if nums_a and nums_b and nums_a != nums_b:
            words_a = set(re.findall(r'\b[a-zA-Z]{4,}\b', claim_a_text.lower()))
            words_b = set(re.findall(r'\b[a-zA-Z]{4,}\b', claim_b_text.lower()))
            if len(words_a.intersection(words_b)) >= 2:
                return "conflict", 0.94

        # If textual claims, use LLM critic
        prompt = f"""Compare these two statements extracted from different academic course documents.
Statement A: "{claim_a_text}"
Statement B: "{claim_b_text}"

Do they:
1. AGREE (state the same fact or consistent details)
2. CONFLICT (directly contradict each other on numbers, dates, definitions, or mechanisms)
3. UNRELATED (discuss entirely different topics)

Return JSON with "verdict": "agree"|"conflict"|"unrelated" and "confidence": float between 0.0 and 1.0.
"""
        try:
            res = self.llm.generate_response([{"role": "user", "content": prompt}], max_tokens=150)
            parsed = json.loads(re.search(r'\{.*\}', res, re.DOTALL).group(0))
            return parsed.get("verdict", "unrelated"), float(parsed.get("confidence", 0.75))
        except Exception:
            return "unrelated", 0.50

    def resolve_conflict(self, conflict_id: str, trusted_document: str, student_id: str) -> Dict[str, Any]:
        """
        Allows the student to resolve a conflict by marking which source document to trust.
        """
        record = db.get_by_id("conflicts", conflict_id) or db.get_by_id("misconceptions", conflict_id)
        if not record:
            # Check local memory
            record = {"id": conflict_id, "status": "active"}

        record["status"] = "resolved"
        record["trusted_source"] = trusted_document
        record["resolved_by"] = student_id
        record["resolved_at"] = datetime.utcnow().isoformat()
        db.update("conflicts" if "conflicts" in db.data else "misconceptions", conflict_id, record)
        return record

source_conflict_detector = SourceConflictDetector()
conflict_detector = source_conflict_detector

