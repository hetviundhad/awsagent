import re
import numpy as np
from typing import List, Dict, Any, Optional
from backend.app.services.database import db
from backend.app.providers.embedding_provider import get_embedding_provider
from backend.app.providers.llm_provider import get_llm_provider, get_topic_links
from backend.app.core.config import settings

class RAGEngine:
    def __init__(self):
        self.embedding_provider = get_embedding_provider(settings.EMBEDDING_PROVIDER, settings.OPENAI_API_KEY)
        self.llm_provider = get_llm_provider(settings.LLM_PROVIDER)
        self.confidence_threshold = settings.RETRIEVAL_CONFIDENCE_THRESHOLD

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        if not vec_a or not vec_b:
            return settings.FLOAT_ZERO
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return settings.FLOAT_ZERO
        return float(dot / (norm_a * norm_b))

    def _verify_support_with_llm(self, chunks: List[Dict[str, Any]], query: str) -> bool:
        """
        NLI / LLM Support Gate Check:
        Evaluates whether the retrieved course chunks entail sufficient factual evidence
        to answer the student's question, rejecting out-of-distribution queries without static keywords.
        """
        if not chunks:
            return False

        combined_text = " ".join([c.get("content", "") for c in chunks[:3]]).strip()
        if not combined_text:
            return False

        try:
            prompt = (
                f"Course material excerpts:\n\"\"\"{combined_text[:1500]}\"\"\"\n\n"
                f"Student question:\n\"{query}\"\n\n"
                "Does the course material excerpt above provide relevant concepts, methods, or factual evidence to explain or answer the student's question? "
                "Answer strictly with 'YES' if the excerpt discusses the concepts in the question (even if partial or foundational), or 'NO' if completely off-topic or unrelated."
            )
            if hasattr(self.llm_provider, "api_key") and self.llm_provider.api_key and self.llm_provider.api_key != "none":
                import httpx
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.llm_provider.api_key}"
                }
                base_url = getattr(self.llm_provider, "base_url", "https://api.groq.com/openai/v1")
                model = getattr(self.llm_provider, "model", settings.LLM_MODEL)
                with httpx.Client(timeout=settings.RAG_HTTP_TIMEOUT_SHORT) as client:
                    resp = client.post(
                        f"{base_url}/chat/completions",
                        headers=headers,
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": settings.RAG_NLI_MAX_TOKENS,
                            "temperature": settings.RAG_TEMPERATURE_DETERMINISTIC
                        }
                    )
                    if resp.status_code == 200:
                        msg = resp.json()["choices"][0]["message"]
                        ans = (msg.get("content") or "").strip().upper()
                        if not ans and msg.get("reasoning"):
                            ans = msg["reasoning"].strip().upper()
                        return "YES" in ans
        except Exception:
            pass

        # Heuristic fallback if LLM is unavailable:
        q_tokens = set(re.findall(r'\b[a-zA-Z]{3,}\b', query.lower()))
        c_tokens = set(re.findall(r'\b[a-zA-Z]{3,}\b', combined_text.lower()))
        stopwords = {
            "what", "when", "where", "which", "who", "whom", "this", "that", "these", "those",
            "from", "with", "have", "more", "explain", "tell", "about", "does", "build", "make",
            "give", "help", "need", "like", "know", "code", "table", "write"
        }
        substantive = q_tokens - stopwords
        if not substantive:
            return True
        overlap = len(substantive.intersection(c_tokens))
        return (overlap / len(substantive)) >= settings.RAG_SUPPORT_HEURISTIC_THRESHOLD

    def get_calibrated_threshold(self) -> float:
        import json, os
        paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "eval", "refusal_calibration_results.json"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "backend", "data", "refusal_calibration_results.json")
        ]
        for p in paths:
            norm_p = os.path.normpath(p)
            if os.path.exists(norm_p):
                try:
                    with open(norm_p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        val = data.get("optimal_refusal_threshold")
                        if val is not None and isinstance(val, (int, float)):
                            return float(val)
                except Exception:
                    pass
        return settings.RETRIEVAL_REFUSAL_THRESHOLD

    def retrieve_chunks(
        self,
        course_id: str,
        query: str,
        top_k: int = 5,
        topic_filter: Optional[str] = None,
        user_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval combining semantic dense vector similarity and BM25 (rank_bm25),
        merged with Reciprocal Rank Fusion (RRF), with optional metadata filtering.
        Returns top-k with {dense_score, bm25_score, fused_score} and concept_ids.
        """
        query_vector = self.embedding_provider.embed_text(query)
        common_stopwords = {
            "what", "when", "where", "which", "who", "whom", "this", "that", "these", "those",
            "from", "with", "have", "more", "explain", "tell", "about", "does", "build", "make",
            "give", "help", "need", "like", "know", "code", "table", "write", "and", "the", "for",
            "are", "was", "were", "been", "being", "how", "can", "could", "should", "would", "you",
            "your", "into", "their", "there", "then", "than", "over", "such", "also", "most", "some"
        }
        all_words = [w for w in re.findall(r'[a-zA-Z0-9_-]{2,}', query.lower())]
        substantive = [w for w in all_words if w not in common_stopwords]
        q_tokens = substantive if substantive else all_words

        # Fetch candidate chunks for course and user verification
        all_chunks = db.list_all("knowledge_chunks", lambda c: c.get("course_id") == course_id)
        if user_id:
            course = db.get_by_id("courses", course_id)
            if course and course.get("owner_id") and str(course.get("owner_id")) != str(user_id):
                return []
        candidates = [c for c in all_chunks if not (topic_filter and c.get("topic_id") != topic_filter)]
        if document_ids:
            doc_id_set = set(document_ids)
            candidates = [c for c in candidates if c.get("document_id") in doc_id_set]
        
        if not candidates:
            return []

        # Check if query targets a specific document by filename or stem
        q_norm = query.lower().replace("_", " ")
        doc_matched = []
        for chk in candidates:
            doc_name = (chk.get("document_name") or "").lower()
            doc_stem = doc_name.rsplit(".", 1)[0] if "." in doc_name else doc_name
            if doc_name and (doc_name in q_norm or (len(doc_stem) >= 3 and (doc_stem in q_norm.split() or f" {doc_stem} " in f" {q_norm} "))):
                doc_matched.append(chk)
        if doc_matched:
            candidates = doc_matched

        # 1. Dense Semantic Ranking
        dense_scores = []
        for chk in candidates:
            v = chk.get("embedding", [])
            sim = self._cosine_similarity(query_vector, v)
            dense_scores.append((chk, sim))
        dense_scores.sort(key=lambda x: x[1], reverse=True)
        dense_rank_map = {item[0]["id"]: rank for rank, item in enumerate(dense_scores, start=1)}

        # 2. BM25 Lexical Ranking (rank_bm25)
        bm25_rank_map = {}
        bm25_raw_scores = {}
        try:
            from rank_bm25 import BM25Okapi
            corpus_tokens = [
                f"{chk.get('document_name', '')} {chk.get('content', '')}".lower().replace('.', ' ').split() for chk in candidates
            ]
            bm25 = BM25Okapi(corpus_tokens)
            scores = bm25.get_scores(q_tokens) if q_tokens else [settings.FLOAT_ZERO] * len(candidates)
            bm25_pairs = list(zip(candidates, scores))
            bm25_pairs.sort(key=lambda x: x[1], reverse=True)
            for rank, (chk, sc) in enumerate(bm25_pairs, start=1):
                bm25_rank_map[chk["id"]] = rank
                bm25_raw_scores[chk["id"]] = sc
        except Exception:
            # Fallback keyword overlap ranking
            for rank, chk in enumerate(candidates, start=1):
                c_set = set(f"{chk.get('document_name', '')} {chk.get('content', '')}".lower().replace('.', ' ').split())
                overlap = len(set(q_tokens).intersection(c_set))
                bm25_rank_map[chk["id"]] = rank
                bm25_raw_scores[chk["id"]] = overlap

        # 3. Reciprocal Rank Fusion (RRF)
        k_const = getattr(settings, "RRF_K", 60)
        mode = getattr(settings, "HYBRID_SEARCH_MODE", "rrf")

        scored_candidates = []
        max_bm = max(bm25_raw_scores.values() or [settings.FLOAT_ONE])

        for chk in candidates:
            chk_id = chk["id"]
            d_rank = dense_rank_map.get(chk_id, len(candidates))
            b_rank = bm25_rank_map.get(chk_id, len(candidates))
            v_sim = next((item[1] for item in dense_scores if item[0]["id"] == chk_id), settings.FLOAT_ZERO)
            bm_raw = bm25_raw_scores.get(chk_id, settings.FLOAT_ZERO)
            bm_norm = (bm_raw / max(max_bm, settings.FLOAT_ONE)) if max_bm > settings.FLOAT_ZERO else settings.FLOAT_ZERO

            c_content_lower = f"{chk.get('document_name', '')} {chk.get('content', '')}".lower()
            overlap_cnt = sum(1 for tok in q_tokens if tok in c_content_lower)
            overlap_ratio = overlap_cnt / max(len(q_tokens), 1)

            if mode == "dense_only":
                final_score = v_sim
            elif mode == "bm25_only":
                final_score = bm_norm
            elif mode == "linear":
                final_score = (settings.RAG_SEMANTIC_WEIGHT * v_sim) + (settings.RAG_BM25_WEIGHT * bm_norm)
            else: # default: RRF
                rrf_score = (settings.FLOAT_ONE / (k_const + d_rank)) + (settings.FLOAT_ONE / (k_const + b_rank))
                # Gate score when both dense semantic similarity and substantive token overlap are negligible
                if v_sim < settings.RETRIEVAL_REFUSAL_THRESHOLD and overlap_ratio < settings.RAG_SUPPORT_HEURISTIC_THRESHOLD:
                    final_score = round(max(v_sim, settings.FLOAT_ZERO), 4)
                else:
                    signal = max(v_sim, bm_norm * settings.RAG_BM_SIGNAL_BOOST if bm_raw > settings.FLOAT_ZERO else settings.FLOAT_ZERO)
                    final_score = round(rrf_score * settings.RAG_RRF_MULTIPLIER * min(settings.FLOAT_ONE, signal * settings.RAG_SIGNAL_MULTIPLIER), 4)

            # Preserve visual elements, bboxes, keyframes, scores, and concept_ids
            candidate = dict(chk)
            candidate["score"] = float(round(final_score, 4))
            candidate["fused_score"] = float(round(final_score, 4))
            candidate["dense_similarity"] = float(round(v_sim, 4))
            candidate["dense_score"] = float(round(v_sim, 4))
            candidate["bm25_score"] = float(round(bm_norm, 4))
            candidate["concept_ids"] = chk.get("concept_ids", [])
            candidate["visual_element"] = chk.get("visual_element")
            scored_candidates.append(candidate)

        # Sort descending by hybrid/RRF score
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        return scored_candidates[:top_k]

    def answer_query(
        self,
        course_id: str,
        query: str,
        conversation_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        difficulty: str = "Medium",
        mode: str = "Simple",
        style: Optional[str] = None,
        language: str = "en",
        allow_outside_knowledge: bool = True,
        learner_context: Optional[str] = None,
        owner_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Executes grounded RAG workflow:
        Query -> Hybrid Retrieval -> Confidence Threshold Check -> Grounded Generation / Unsupported Fallback
        """
        self.llm_provider = get_llm_provider(settings.LLM_PROVIDER)

        # URL Extraction & Live Study Link Explanation
        url_match = re.search(r'https?://[^\s]+', query)
        if url_match:
            target_url = url_match.group(0).rstrip(".,;)>]")
            try:
                from backend.app.services.web_extractor import web_extractor
                scrape_res = web_extractor.fetch_and_clean_url(target_url)
                if scrape_res.get("success"):
                    llm_expl = self.llm_provider.explain_study_material_url(
                        target_url, scrape_res["title"], scrape_res["text"]
                    )
                    # Store web content in DB so future questions & quizzes can reference it
                    try:
                        from backend.app.ingestion.pipeline import ingestion_pipeline
                        ingestion_pipeline.ingest_raw_text(
                            course_id=course_id,
                            title=f"Web: {scrape_res['title'][:36]}",
                            text=scrape_res["text"][:3000],
                            source_type="link",
                            owner_id=owner_id
                        )
                    except Exception:
                        pass
                    
                    return {
                        "answer": llm_expl["explanation"],
                        "grounded": True,
                        "is_outside_knowledge": False,
                        "citations": [{
                            "citation_index": 1,
                            "source_type": "link",
                            "document_name": scrape_res["title"],
                            "snippet": f"Extracted from {scrape_res['domain']}: {scrape_res['text'][:140]}...",
                            "chunk_id": "chk_live_link"
                        }],
                        "external_links": [{
                            "title": scrape_res["title"],
                            "url": target_url,
                            "source": scrape_res["domain"],
                            "snippet": f"Full article and code examples on {scrape_res['domain']}"
                        }],
                        "confidence_score": settings.RAG_HIGH_CONFIDENCE,
                        "searched_topics": ["Web Study Resource"],
                        "closest_source": None,
                        "conversation_id": conversation_id or "new_conv",
                        "follow_up_questions": [
                            "Quiz me on this study material",
                            "Explain the code/formula in simple terms",
                            "Connect this to my course exams"
                        ],
                        "verification_check_question": "What is the core takeaway of this study material?"
                    }
            except Exception:
                pass

        # Step 0: Conversational Greetings & Chitchat Check
        q_lower = query.lower().strip()
        chitchat_triggers = [
            "hi", "hello", "hey", "hola", "greetings", "good morning", "good evening", "good afternoon",
            "how are you", "how are you bro", "how are you doing", "how r u", "what's up", "whats up",
            "who are you", "what can you do", "thanks", "thank you", "thx", "cool", "great", "nice",
            "ok", "okay", "bye", "goodbye"
        ]
        
        # Check if query is conversational chitchat
        is_chitchat = any(q_lower == t or q_lower.startswith(t + " ") or q_lower.endswith(" " + t) for t in chitchat_triggers)
        if is_chitchat and len(query.split()) <= 6:
            course = db.get_by_id("courses", course_id)
            c_name = course.get("name", "your course") if course else "your course"
            topics = db.list_all("topics", lambda t: t.get("course_id") == course_id)
            topic_names = [t.get("name") for t in topics] if topics else ["Algorithm Analysis", "Dynamic Programming", "Graph Algorithms"]
            
            if any(w in q_lower for w in ["how are you", "how r u", "how are you bro", "whats up", "what's up"]):
                reply_text = (
                    f"I'm doing great, thank you for asking! 😊 I'm fully synchronized with your **{c_name}** materials and ready to help you study.\n\n"
                    f"We can dive into:\n"
                    f"• {', '.join(topic_names)}\n"
                    f"• Or explore any uploaded slides, videos, and textbook chapters.\n\n"
                    f"What concept or problem would you like to work on right now?"
                )
            elif any(w in q_lower for w in ["thanks", "thank you", "thx", "great", "cool", "nice", "ok", "okay"]):
                reply_text = (
                    f"You're very welcome! Keep up the momentum. 🚀 Let me know whenever you want to test a concept, practice a problem, or clarify any slide from **{c_name}**."
                )
            else:
                reply_text = (
                    f"Hello! 👋 I am your AI study companion for **{c_name}**.\n\n"
                    f"I have thoroughly ingested and indexed your uploaded course material. "
                    f"I can teach concepts, explain diagrams, step through video timestamps, or test you with adaptive questions across:\n"
                    f"• {', '.join(topic_names)}\n\n"
                    f"What concept or problem would you like to explore?"
                )

            return {
                "answer": reply_text,
                "grounded": True,
                "is_outside_knowledge": False,
                "citations": [],
                "external_links": get_topic_links(query),
                "confidence_score": settings.RAG_PERFECT_CONFIDENCE,
                "searched_topics": topic_names,
                "closest_source": None,
                "conversation_id": conversation_id or "new_conv",
                "follow_up_questions": [
                    f"Explain the core concept of {topic_names[0] if topic_names else c_name}",
                    f"Quiz me on {c_name}",
                    f"Give me a practical real-world example in {c_name}",
                    "Summarize the key exam takeaways"
                ],
                "verification_check_question": None
            }

        # Step 0.5: Course Overview & Syllabus Exploration Query Check
        meta_course_keywords = [
            "what topics", "topics covered", "what is covered", "list topics", 
            "what can you teach", "syllabus", "course summary", "what is in this course",
            "show topics", "what concepts", "course material"
        ]
        if any(mk in query.lower() for mk in meta_course_keywords) and len(query.split()) < 12:
            course = db.get_by_id("courses", course_id)
            c_name = course.get("name", "Course Knowledge Base") if course else "Course Knowledge Base"
            topics = db.list_all("topics", lambda t: t.get("course_id") == course_id)
            concepts = db.list_all("concepts", lambda c: c.get("course_id") == course_id)
            docs = db.list_all("documents", lambda d: d.get("course_id") == course_id)
            
            overview_lines = [
                f"### 📚 Course Syllabus & Knowledge Base for **{c_name}**\n",
                "Here are the core topics and concepts indexed directly from your uploaded material:\n"
            ]
            for t in topics:
                t_concepts = [c.get("name") for c in concepts if c.get("topic_id") == t.get("id")]
                concept_str = f" ({', '.join(t_concepts)})" if t_concepts else ""
                overview_lines.append(f"• **{t.get('name')}**: {t.get('description', '')}{concept_str}")
            
            overview_lines.append("\n**Indexed Multimodal Materials:**")
            citations = []
            for i, d in enumerate(docs):
                overview_lines.append(f"• {d.get('filename')} ({d.get('file_type', '').upper()})")
                d_chunks = db.list_all("knowledge_chunks", lambda c: c.get("document_id") == d.get("id"))
                first_chk = d_chunks[0] if d_chunks else None
                citations.append({
                    "citation_index": i + 1,
                    "source_type": d.get("file_type", "pdf"),
                    "document_name": d.get("filename", "Course Document"),
                    "page_number": first_chk.get("page_number", 1) if first_chk and d.get("file_type") == "pdf" else (1 if d.get("file_type") == "pdf" else None),
                    "slide_number": first_chk.get("slide_number", 1) if first_chk and d.get("file_type") == "slide" else (1 if d.get("file_type") == "slide" else None),
                    "timestamp_start": first_chk.get("timestamp_start", settings.FLOAT_ZERO) if first_chk and d.get("file_type") == "video" else (settings.FLOAT_ZERO if d.get("file_type") == "video" else None),
                    "timestamp_end": first_chk.get("timestamp_end") if first_chk else None,
                    "snippet": (first_chk.get("content", "")[:200] + "...") if first_chk else f"Indexed unit from {d.get('filename')}.",
                    "chunk_id": first_chk.get("id", f"chk_meta_{i}") if first_chk else f"chk_meta_{i}"
                })

            return {
                "answer": "\n".join(overview_lines),
                "grounded": True,
                "is_outside_knowledge": False,
                "citations": citations,
                "external_links": get_topic_links(query, course_id=course_id),
                "confidence_score": settings.RAG_PERFECT_CONFIDENCE,
                "searched_topics": [t.get("name") for t in topics],
                "closest_source": citations[0] if citations else None,
                "conversation_id": conversation_id or "new_conv",
                "follow_up_questions": [
                    f"Explain the fundamentals of {topics[0].get('name') if topics else c_name}",
                    f"Quiz me on {c_name}",
                    f"Give an intuitive real-world application of {c_name}",
                    f"What should I study first in {c_name}?"
                ],
                "verification_check_question": None
            }

        # Step 1: Fetch recent conversation history for conversational context
        conv_history = []
        if conversation_id:
            messages = db.list_all("messages", lambda m: m.get("conversation_id") == conversation_id)
            messages = sorted(messages, key=lambda m: m.get("created_at", ""))
            for m in messages[-6:]:
                conv_history.append({"role": m.get("role", "user"), "content": m.get("content", "")})

        # Formulate contextual retrieval query and resolve generic upload placeholders
        effective_query = query
        generic_placeholders = [
            '"the newly uploaded lecture"', 'the newly uploaded lecture',
            '"the newly uploaded study material"', 'the newly uploaded study material',
            '"the newly uploaded document"', 'the newly uploaded document',
            '"newly uploaded lecture"', 'newly uploaded lecture',
            '"newly uploaded study material"', 'newly uploaded study material'
        ]
        for ph in generic_placeholders:
            if ph in effective_query.lower():
                course = db.get_by_id("courses", course_id)
                c_name = course.get("name", "our course material") if course else "our course material"
                effective_query = re.sub(re.escape(ph), f'"{c_name}"', effective_query, flags=re.IGNORECASE)

        retrieval_query = effective_query
        followup_cues = ["in java", "in python", "in c++", "in cpp", "working code", "give code", "full code", "code for this", "explain this", "why", "how so", "what about", "more details", "another example", "can you explain", "step by step"]
        q_words_list = [w.strip("?,.!;:\"'").lower() for w in effective_query.split()]
        is_short_followup = len(q_words_list) <= 5 or any(cue in effective_query.lower() for cue in followup_cues)
        if is_short_followup and conv_history:
            user_past_msgs = [m.get("content", "") for m in conv_history if m.get("role") == "user" and len(m.get("content", "").split()) >= 3]
            if user_past_msgs:
                retrieval_query = f"{user_past_msgs[-1]} {effective_query}"

        # Step 2: Retrieve candidate chunks
        retrieved = self.retrieve_chunks(course_id, retrieval_query, top_k=settings.MAX_RETRIEVED_CHUNKS, topic_filter=topic_id, document_ids=document_ids)
        if not retrieved and retrieval_query != effective_query:
            retrieved = self.retrieve_chunks(course_id, effective_query, top_k=settings.MAX_RETRIEVED_CHUNKS, topic_filter=topic_id, document_ids=document_ids)
        
        # Step 2.5: Strands Decider 2B scores each chunk's relevance BEFORE it is injected (never empties the context)
        try:
            from backend.app.decider.service import decider_service
            retrieved = decider_service.filter_context(effective_query, retrieved)
        except Exception as _decider_err:
            print(f"[Decider] context scoring skipped: {_decider_err}")

        # Step 3: Assess retrieval confidence & support gate
        top_dense = retrieved[0].get("dense_similarity", settings.FLOAT_ZERO) if retrieved else settings.FLOAT_ZERO
        top_score = retrieved[0]["score"] if retrieved else settings.FLOAT_ZERO
        calibrated_threshold = self.get_calibrated_threshold()

        is_supported = False
        only_in_syllabus = False
        syl_doc_name = "course syllabus"
        if retrieved:
            non_syl_chunks = [c for c in retrieved if "syllabus" not in (c.get("document_name", "")).lower()]
            syl_chunks = [c for c in retrieved if "syllabus" in (c.get("document_name", "")).lower()]
            if syl_chunks and (not non_syl_chunks or non_syl_chunks[0].get("score", 0) < settings.RAG_SYLLABUS_REFUSAL_THRESHOLD):
                only_in_syllabus = True
                syl_doc_name = syl_chunks[0].get("document_name", "Course Syllabus")

            if only_in_syllabus:
                is_supported = False
            elif is_short_followup and conv_history:
                is_supported = True
            elif top_dense >= calibrated_threshold or top_score >= settings.RETRIEVAL_CONFIDENCE_THRESHOLD:
                is_supported = self._verify_support_with_llm(retrieved[:3], effective_query)

        # Step 4: If not supported, flag as unsupported unless outside knowledge is explicitly allowed
        if (not is_supported or only_in_syllabus) and not allow_outside_knowledge:
            closest_source = None
            if retrieved:
                top = retrieved[0]
                closest_source = {
                    "citation_index": 1,
                    "source_type": top.get("source_type", "document"),
                    "document_name": top.get("document_name", "Uploaded material"),
                    "page_number": top.get("page_number"),
                    "slide_number": top.get("slide_number"),
                    "timestamp_start": top.get("timestamp_start"),
                    "timestamp_end": top.get("timestamp_end"),
                    "snippet": top.get("content", "")[:150] + "...",
                    "chunk_id": top.get("id", "")
                }

            searched_topics = list({c.get("topic_id", "General") for c in retrieved if c.get("topic_id")})

            # Check if query matches a known syllabus topic
            is_in_syllabus = only_in_syllabus
            syl_topic_name = effective_query
            try:
                from backend.app.services.syllabus import syllabus_auditor
                syl_audit = syllabus_auditor.audit_coverage(course_id)
                if syl_audit.get("has_syllabus"):
                    syl_doc_name = syl_audit.get("syllabus_document", {}).get("name", syl_doc_name)
                    q_lower = query.lower()
                    for it in syl_audit.get("items", []):
                        it_name = it.get("topic_name", "").lower()
                        if it_name and (it_name in q_lower or any(w in q_lower for w in it_name.split() if len(w) > 4)):
                            is_in_syllabus = True
                            syl_topic_name = it.get("topic_name")
                            break
            except Exception:
                pass

            if is_in_syllabus or only_in_syllabus:
                refusal_text = (
                    f"This topic ('{syl_topic_name}') is in your course syllabus, but no uploaded study material covers it yet.\n\n"
                    f"🔍 **Syllabus Coverage Audit Notice**:\n"
                    f"• Prescribed in: {syl_doc_name}\n"
                    f"• Status: Listed in curriculum, but missing from your uploaded lecture notes and slides.\n\n"
                    "Upload lecture slides or notes for this unit, or click 'Outside knowledge (not from your course)' to discuss general theory."
                )
            else:
                refusal_text = (
                    "This isn't covered in your uploaded material. not covered in your material\n\n"
                    "🔍 **Search Summary**:\n"
                    f"• Searched in: {', '.join(searched_topics) if searched_topics else 'All uploaded units'}\n"
                    f"• Best retrieval match confidence: {int(top_score * settings.FLOAT_HUNDRED)}% (threshold required: {int(calibrated_threshold * settings.FLOAT_HUNDRED)}%)\n\n"
                    "You can upload lecture slides or chapters covering this topic, or click **'Outside knowledge (not from your course)'** below."
                )

            return {
                "answer": refusal_text,
                "answer_segments": [{
                    "text": refusal_text,
                    "citations": [],
                    "type": "outside"
                }],


                "refused": True,
                "grounded": False,
                "is_outside_knowledge": False,
                "citations": [],
                "external_links": get_topic_links(query, course_id=course_id),
                "confidence_score": top_score,
                "searched_topics": searched_topics,
                "closest_source": closest_source,
                "conversation_id": conversation_id or "new_conv",
                "follow_up_questions": [
                    "Explain this using outside AI knowledge",
                    "What topics are covered in my course material?",
                    "Quiz me on my active course topics"
                ],
                "verification_check_question": None
            }

        # Step 4.5: Personalization: adapt depth based on p_known of retrieved concepts
        retrieved_concept_ids = []
        for chk in (retrieved[:3] if is_supported else []):
            for cid in chk.get("concept_ids", []):
                if cid and cid not in retrieved_concept_ids:
                    retrieved_concept_ids.append(cid)

        student_id = owner_id or learner_context
        if student_id and retrieved_concept_ids:
            try:
                from backend.app.learner.bkt import BayesianKnowledgeTracer
                bkt = BayesianKnowledgeTracer()
                probs = []
                for cid in retrieved_concept_ids:
                    rec = bkt.get_or_create_mastery(str(student_id), course_id, cid)
                    probs.append(rec.get("mastery_probability", settings.BKT_P_INIT))
                if probs:
                    avg_p = sum(probs) / len(probs)
                    if avg_p < settings.ADAPTIVE_DEPTH_BEGINNER_THRESHOLD:
                        difficulty = "Beginner (step by step with an intuitive real-world example)"
                    elif avg_p > settings.ADAPTIVE_DEPTH_ADVANCED_THRESHOLD:
                        difficulty = "Advanced (concise, high-density, conceptual rigor)"
            except Exception:
                pass

        # Step 5: Generate grounded tutor response
        effective_mode = style or mode or "Simple"
        result = self.llm_provider.generate_grounded_tutor_response(
            query=effective_query,
            retrieved_contexts=retrieved if is_supported else [],
            conversation_history=conv_history,
            mode=effective_mode,
            difficulty=difficulty,
            language=language,
            allow_outside_knowledge=allow_outside_knowledge,
            learner_context=learner_context
        )

        if not is_supported and allow_outside_knowledge:
            result["is_outside_knowledge"] = True
            result["grounded"] = False
            result["citations"] = []
            if "outside knowledge" not in result.get("answer", "").lower():
                result["answer"] = "⚠️ **Outside Knowledge (not from your course):**\n\n" + result.get("answer", "")

        # Check for active cross-document source conflicts
        try:
            conflicts = db.list_all("conflicts", lambda cf: cf.get("course_id") == course_id and cf.get("status") == "active")
            for cf in conflicts:
                attr = cf.get("attribute", "").lower()
                if attr and (attr in effective_query.lower() or any(attr in (chk.get("content", "").lower()) for chk in retrieved[:3])):
                    conflict_notice = (
                        f"\n\n⚠️ **Source Disagreement Alert**: Your course materials present differing figures on **{cf.get('attribute')}**:\n"
                        f"• According to *{cf['claim_a']['document_name']}* (Page/Slide {cf['claim_a']['page_number']}): \"{cf['claim_a']['statement']}\"\n"
                        f"• However, *{cf['claim_b']['document_name']}* (Page/Slide {cf['claim_b']['page_number']}): \"{cf['claim_b']['statement']}\"\n"
                        f"*(You can mark which source to trust in Course Materials → Source Conflicts)*."
                    )
                    if conflict_notice not in result.get("answer", ""):
                        result["answer"] += conflict_notice
        except Exception:
            pass

        # Enrich citations with precise layout bbox and video keyframes
        enriched_citations = []
        for i, c in enumerate(result.get("citations", [])):
            matching_chk = next((chk for chk in retrieved if chk.get("id") == c.get("chunk_id")), None)
            c_dict = dict(c) if isinstance(c, dict) else c.model_dump()
            if matching_chk:
                if matching_chk.get("bbox") and not c_dict.get("bbox"):
                    c_dict["bbox"] = matching_chk["bbox"]
                if matching_chk.get("keyframe_path") and not c_dict.get("keyframe_path"):
                    c_dict["keyframe_path"] = matching_chk["keyframe_path"]
                if matching_chk.get("visual_frame_summary") and not c_dict.get("visual_frame_summary"):
                    c_dict["visual_frame_summary"] = matching_chk["visual_frame_summary"]
            enriched_citations.append(c_dict)
        result["citations"] = enriched_citations

        # Step 6: Sentence-level citation-entailment check
        from backend.app.rag.self_rag import self_rag_guardrail
        ans_text = result.get("answer", "")
        answer_segments, refused = self_rag_guardrail.segment_and_verify_answer(
            answer=ans_text,
            retrieved_chunks=retrieved,
            allow_outside_knowledge=allow_outside_knowledge
        )
        result["answer_segments"] = answer_segments
        result["refused"] = refused

        if refused:
            result["grounded"] = False
            result["answer"] = "This isn't covered in your uploaded material. not covered in your material"
            result["citations"] = []
        else:
            result["answer"] = ans_text
            final_citations = []
            seen_ids = set()
            for seg in answer_segments:
                if seg["type"] == "sourced":
                    for cit in seg.get("citations", []):
                        cid = cit.get("chunk_id")
                        if cid and cid not in seen_ids:
                            seen_ids.add(cid)
                            final_citations.append(cit)
            if final_citations:
                result["citations"] = final_citations
            result["grounded"] = len(result["citations"]) > 0

        verifications, unsupported = self_rag_guardrail.verify_claims(ans_text, retrieved)
        result["claims_verification"] = [v.model_dump() for v in verifications]
        result["unsupported_claims"] = unsupported

        result["confidence_score"] = top_score
        result["searched_topics"] = list({c.get("topic_id", "General") for c in retrieved if c.get("topic_id")})
        result["conversation_id"] = conversation_id or "new_conv"
        return result

    query_tutor = answer_query

rag_engine = RAGEngine()
