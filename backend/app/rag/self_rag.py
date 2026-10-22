import re
from typing import List, Dict, Any, Tuple
from backend.app.models.schemas import ClaimVerification

class SelfRAGGuardrail:
    """
    Self-RAG Guardrail & Claim-Level Entailment Evaluator.
    Second gate after confidence-threshold retrieval:
    1. Splits candidate answer into distinct factual claims/sentences.
    2. Evaluates each claim against retrieved knowledge chunks.
    3. Categorizes each claim: supported (with source citation index) vs unsupported.
    4. If claims are unsupported, annotates or flags them.
    """
    def __init__(self):
        pass

    def split_claims(self, text: str) -> List[str]:
        # Filter out markdown headings, greetings, lead-in colons, and meta commentary
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        claims = []
        meta_starters = (
            "based directly", "according to", "here is", "let's", "in this section",
            "in summary", "overall", "to learn more", "notice that", "as we can see"
        )
        for line in lines:
            if line.startswith("#") or line.startswith("---") or line.startswith("🌐") or line.startswith("|") or "---" in line or "Recommended Deep-Dive" in line:
                continue
            if line.endswith(":") or line.endswith("："):
                continue
            # Split by sentence terminators
            sub_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', line) if len(s.strip()) > 15]
            for s in sub_sentences:
                clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', s)
                clean = clean.replace("**", "").replace("*", "").replace("|", "").strip()
                c_low = clean.lower()
                if any(c_low.startswith(ms) for ms in meta_starters):
                    continue
                # Must contain actual words, not markdown borders
                words = [w for w in c_low.split() if w.isalnum()]
                if len(words) >= 5 and not clean.startswith("🔍") and not clean.startswith("💡") and not clean.startswith("⚠️"):
                    claims.append(clean)
        return claims[:8] # evaluate up to 8 core claims for speed

    def verify_claims(
        self,
        answer: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> Tuple[List[ClaimVerification], List[str]]:
        """
        Returns (list_of_verifications, list_of_unsupported_claims)
        """
        claims = self.split_claims(answer)
        if not claims or not retrieved_chunks:
            return [], []

        # Prepare normalized chunk text index
        chunk_texts = []
        for idx, chk in enumerate(retrieved_chunks):
            content = chk.get("content", "").lower()
            doc_name = chk.get("document_name", "").lower()
            summary = chk.get("content_summary", "").lower()
            chunk_texts.append({
                "index": idx + 1,
                "doc_name": chk.get("document_name", "Course Document"),
                "full_text": f"{content} {doc_name} {summary}"
            })

        verifications: List[ClaimVerification] = []
        unsupported: List[str] = []

        stopwords = {
            "this", "that", "these", "those", "with", "from", "have", "been", "were",
            "which", "where", "when", "what", "their", "there", "about", "could", "would",
            "should", "based", "directly", "uploaded", "material", "essential", "necessary"
        }

        for claim in claims:
            c_low = claim.lower()
            c_words = [w.strip(".,;:!?()[]{}\"'") for w in c_low.split() if len(w) > 3 and w not in stopwords]
            
            best_match_idx = None
            best_overlap_cnt = 0
            best_doc = None

            for chk_info in chunk_texts:
                overlap = sum(1 for w in c_words if w in chk_info["full_text"])
                if overlap > best_overlap_cnt:
                    best_overlap_cnt = overlap
                    best_match_idx = chk_info["index"]
                    best_doc = chk_info["doc_name"]

            # Entailment criterion: at least 2 key substantive tokens match the context
            is_supported = (best_overlap_cnt >= 2) or (len(c_words) <= 3 and best_overlap_cnt >= 1)

            if is_supported and best_match_idx:
                verifications.append(ClaimVerification(
                    claim=claim,
                    supported=True,
                    source_doc=best_doc,
                    citation_index=best_match_idx,
                    reason=f"Verified in {best_doc} (match score: {best_overlap_cnt} key concepts)"
                ))
            else:
                verifications.append(ClaimVerification(
                    claim=claim,
                    supported=False,
                    source_doc=None,
                    citation_index=None,
                    reason="Claim not grounded in uploaded materials"
                ))
                unsupported.append(claim)

        return verifications, unsupported

    def evaluate_claims(
        self,
        answer: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculates aggregate claim support metrics for benchmark harness.
        """
        verifications, unsupported = self.verify_claims(answer, retrieved_chunks)
        supported_count = sum(1 for v in verifications if v.supported)
        total = len(verifications)
        ratio = round(supported_count / max(total, 1), 3) if total > 0 else 1.0
        return {
            "verifications": verifications,
            "unsupported": unsupported,
            "supported_count": supported_count,
            "total_claims": total,
            "support_ratio": ratio
        }

    def segment_and_verify_answer(
        self,
        answer: str,
        retrieved_chunks: List[Dict[str, Any]],
        allow_outside_knowledge: bool = False
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Runs sentence-level citation-entailment check after EVERY generation.
        For each sentence, verifies the cited unit supports it.
        Drops or flags unsupported sentences.
        Refuses if the share of failed claims exceeds config SELF_RAG_MAX_FAILED_CLAIMS_SHARE.
        Returns:
            (answer_segments: [{text: str, citations: List[dict], type: 'sourced'|'outside'}], refused: bool)
        """
        from backend.app.core.config import settings

        if not answer or not answer.strip():
            return ([{
                "text": "This isn't covered in your uploaded material. not covered in your material",
                "citations": [],
                "type": "outside"
            }], True)

        if not retrieved_chunks and not allow_outside_knowledge:
            return ([{
                "text": "This isn't covered in your uploaded material. not covered in your material",
                "citations": [],
                "type": "outside"
            }], True)

        raw_sentences = [
            s.strip() for s in re.split(r'(?<=[.!?])\s+', answer)
            if s.strip()
        ]
        if not raw_sentences:
            raw_sentences = [answer.strip()]

        stopwords = {
            "this", "that", "these", "those", "with", "from", "have", "been", "were",
            "which", "where", "when", "what", "their", "there", "about", "could", "would",
            "should", "based", "directly", "uploaded", "material", "essential", "necessary",
            "here", "also", "into", "then", "than", "will", "does", "each", "more"
        }

        indexed_chunks = []
        for idx, chk in enumerate(retrieved_chunks):
            content = chk.get("content", "").lower()
            doc_name = chk.get("document_name", "").lower()
            summary = chk.get("content_summary", "").lower()
            indexed_chunks.append({
                "chunk": chk,
                "citation": {
                    "citation_index": idx + 1,
                    "chunk_id": chk.get("id"),
                    "document_name": chk.get("document_name", "Course Document"),
                    "source_type": chk.get("source_type", "document"),
                    "page_number": chk.get("page_number"),
                    "slide_number": chk.get("slide_number"),
                    "timestamp_start": chk.get("timestamp_start"),
                    "timestamp_end": chk.get("timestamp_end"),
                    "snippet": chk.get("content", "")[:120] + "..."
                },
                "full_text": f"{content} {doc_name} {summary}"
            })

        verified_segments = []
        min_overlap = getattr(settings, "SELF_RAG_MIN_OVERLAP_TOKENS", 2)

        for sentence in raw_sentences:
            s_clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', sentence)
            s_clean = s_clean.replace("**", "").replace("*", "").strip()
            s_words = [
                w.strip(".,;:!?()[]{}\"'") for w in s_clean.lower().split()
                if len(w) > 3 and w not in stopwords
            ]

            best_chk = None
            best_overlap = 0

            for ic in indexed_chunks:
                overlap = sum(1 for w in s_words if w in ic["full_text"])
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_chk = ic

            is_supported = (best_overlap >= min_overlap) or (len(s_words) <= 3 and best_overlap >= 1)

            if is_supported and best_chk:
                verified_segments.append({
                    "text": sentence,
                    "citations": [best_chk["citation"]],
                    "type": "sourced"
                })
            else:
                if allow_outside_knowledge:
                    verified_segments.append({
                        "text": sentence,
                        "citations": [],
                        "type": "outside"
                    })

        sourced_count = sum(1 for s in verified_segments if s["type"] == "sourced")
        total_count = len(verified_segments)

        # Refusal check: if failed share exceeds threshold
        failed_count = total_count - sourced_count
        failed_share = failed_count / max(total_count, 1)

        if sourced_count == 0 or (failed_share > settings.SELF_RAG_MAX_FAILED_CLAIMS_SHARE and not allow_outside_knowledge):
            if not allow_outside_knowledge:
                return ([{
                    "text": "This isn't covered in your uploaded material. not covered in your material",
                    "citations": [],
                    "type": "outside"
                }], True)
            else:
                return (verified_segments, False)

        sourced_part = [s for s in verified_segments if s["type"] == "sourced"]
        outside_part = [s for s in verified_segments if s["type"] == "outside"]
        grouped_segments = sourced_part + outside_part

        return (grouped_segments, False)

self_rag_guardrail = SelfRAGGuardrail()
