import math
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from backend.app.services.database import db
from backend.app.core.config import settings, is_test_environment

class BayesianKnowledgeTracer:
    """
    Standard Bayesian Knowledge Tracing (BKT) engine with difficulty weighting,
    prerequisite dependency awareness, locked-node logic, and explainable mastery trajectory.
    All numeric parameters are calibrated and loaded directly from system settings.
    """
    @property
    def DEFAULT_P_INIT(self) -> float:
        return settings.BKT_P_INIT

    @property
    def DEFAULT_P_TRANSIT(self) -> float:
        return settings.BKT_P_TRANSIT

    @property
    def DEFAULT_P_SLIP(self) -> float:
        return settings.BKT_P_SLIP

    @property
    def DEFAULT_P_GUESS(self) -> float:
        return settings.BKT_P_GUESS

    @property
    def PREREQ_UNLOCK_THRESHOLD(self) -> float:
        return settings.BKT_UNLOCK_THRESHOLD

    def _compute_next_review_date(self, mastery_p: float) -> str:
        from datetime import timedelta
        now = datetime.utcnow()
        if mastery_p < settings.BKT_MASTERY_LOW:
            delta = timedelta(days=settings.REVIEW_DAYS_LOW)
        elif mastery_p < settings.BKT_MASTERY_HIGH:
            delta = timedelta(days=settings.REVIEW_DAYS_MED)
        else:
            delta = timedelta(days=settings.REVIEW_DAYS_HIGH)
        return (now + delta).isoformat()

    def get_or_create_mastery(self, student_id: str, course_id: str, concept_id: str) -> Dict[str, Any]:
        records = db.list_all("learner_mastery", lambda m: m.get("student_id") == student_id and m.get("concept_id") == concept_id)
        if records:
            return records[0]

        concept = db.get_by_id("concepts", concept_id)
        concept_name = concept.get("name", "Unknown Concept") if concept else "Unknown"

        new_record = {
            "id": str(uuid.uuid4()),
            "student_id": student_id,
            "course_id": course_id,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "mastery_probability": self.DEFAULT_P_INIT,
            "confidence": settings.FLOAT_HALF,
            "p_transit": self.DEFAULT_P_TRANSIT,
            "p_slip": self.DEFAULT_P_SLIP,
            "p_guess": self.DEFAULT_P_GUESS,
            "attempt_count": 0,
            "correct_count": 0,
            "incorrect_count": 0,
            "last_attempt": None,
            "last_review": None,
            "next_review_date": self._compute_next_review_date(self.DEFAULT_P_INIT),
            "created_at": datetime.utcnow().isoformat()
        }
        return db.insert("learner_mastery", new_record)

    def check_concept_locked(
        self, 
        student_id: str, 
        course_id: str, 
        concept_id: str, 
        mastery_map: Optional[Dict[str, Any]] = None,
        prereqs_map: Optional[Dict[str, List[str]]] = None,
        concepts_map: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Phase 3 Locked-node logic:
        A concept is locked if any prerequisite foundation is below PREREQ_UNLOCK_THRESHOLD.
        """
        concept = (concepts_map.get(concept_id) if concepts_map else None) or db.get_by_id("concepts", concept_id)
        if not concept:
            return {"is_locked": False, "reason": None, "blocking_prerequisite": None}

        # Gather prerequisites from concept record and concept_prerequisites relation table
        prereq_ids = list(concept.get("prerequisites", []))
        if prereqs_map is not None:
            for p_id in prereqs_map.get(concept_id, []):
                if p_id and p_id not in prereq_ids:
                    prereq_ids.append(p_id)
        else:
            rel_prereqs = db.list_all("concept_prerequisites", lambda p: p.get("concept_id") == concept_id)
            for r in rel_prereqs:
                p_id = r.get("prerequisite_id")
                if p_id and p_id not in prereq_ids:
                    prereq_ids.append(p_id)

        for raw_p in prereq_ids:
            if not raw_p or not isinstance(raw_p, str):
                continue

            # Resolve raw_p: might be a concept ID OR a concept name
            p_concept = None
            p_id = raw_p
            if concepts_map:
                p_concept = concepts_map.get(raw_p)
                if not p_concept:
                    raw_lower = raw_p.strip().lower()
                    for cand in concepts_map.values():
                        if cand.get("name", "").strip().lower() == raw_lower:
                            p_concept = cand
                            p_id = cand["id"]
                            break
            else:
                p_concept = db.get_by_id("concepts", raw_p)
                if not p_concept:
                    raw_lower = raw_p.strip().lower()
                    matched = db.list_all("concepts", lambda c: c.get("course_id") == course_id and c.get("name", "").strip().lower() == raw_lower)
                    if matched:
                        p_concept = matched[0]
                        p_id = matched[0]["id"]

            if not p_concept:
                # If prerequisite is not an indexed concept in this course, don't lock
                continue

            if mastery_map is not None:
                p_mastery_rec = mastery_map.get(p_id) or {}
            else:
                p_mastery_rec = self.get_or_create_mastery(student_id, course_id, p_id)
            attempts = p_mastery_rec.get("attempt_count", 0)
            p_prob = p_mastery_rec.get("mastery_probability", self.DEFAULT_P_INIT)
            if p_prob < self.PREREQ_UNLOCK_THRESHOLD:
                p_name = p_concept.get("name", "Foundational Concept")
                return {
                    "is_locked": True,
                    "reason": f"You need more practice on '{p_name}' (Mastery: {int(p_prob * settings.FLOAT_HUNDRED)}%) before unlocking '{concept.get('name', 'this concept')}'.",
                    "blocking_prerequisite": {
                        "id": p_id,
                        "name": p_name,
                        "attempts": attempts,
                        "mastery": round(p_prob * settings.FLOAT_HUNDRED, 1),
                        "required_mastery": round(self.PREREQ_UNLOCK_THRESHOLD * settings.FLOAT_HUNDRED, 1)
                    }
                }

        return {"is_locked": False, "reason": None, "blocking_prerequisite": None}

    def update_mastery(
        self,
        student_id: str,
        course_id: str,
        concept_id: str,
        is_correct: bool,
        difficulty: str = "Medium",
        source: str = "quiz", # quiz or tutor_check
        student_confidence: Optional[str] = None # "Sure" | "Not sure" | "Guess"
    ) -> Dict[str, Any]:
        """
        Executes standard BKT Bayesian update with prerequisite-aware propagation:
        1. Difficulty-weighted Slip / Guess calculation
        2. Posterior calculation: P(L_t | observation)
        3. Confidence Calibration & Brier score calculation (Part 5)
        4. Prerequisite propagation: if prerequisite foundation is weak, transition rate is throttled
        5. Knowledge transition update: P(L_t+1) = Posterior + (1 - Posterior) * P(T_effective)
        """
        record = self.get_or_create_mastery(student_id, course_id, concept_id)
        p_l = record["mastery_probability"]
        p_s = record["p_slip"]
        p_g = record["p_guess"]
        p_t = record.get("p_transit", self.DEFAULT_P_TRANSIT)

        # Prerequisite throttling: if prerequisites are locked/weak, knowledge transition is impeded
        lock_info = self.check_concept_locked(student_id, course_id, concept_id)
        if lock_info.get("is_locked"):
            prereq_mastery = lock_info["blocking_prerequisite"]["mastery"] / settings.FLOAT_HUNDRED
            p_t = p_t * max(settings.BKT_ATTEMPT_MIN_CORRECT_WEIGHT, prereq_mastery)

        # 1. Posterior calculation
        if is_correct:
            numerator = p_l * (settings.FLOAT_ONE - p_s)
            denominator = numerator + ((settings.FLOAT_ONE - p_l) * p_g)
            p_l_obs = numerator / max(denominator, settings.FLOAT_EPSILON)
            record["correct_count"] += 1
        else:
            numerator = p_l * p_s
            denominator = numerator + ((settings.FLOAT_ONE - p_l) * (settings.FLOAT_ONE - p_g))
            p_l_obs = numerator / max(denominator, settings.FLOAT_EPSILON)
            record["incorrect_count"] += 1

        # Confidence Calibration & Brier Score Calculation (Part 5)
        if student_confidence:
            c_str = str(student_confidence).strip().lower()
            if "sure" in c_str and "not" not in c_str and "un" not in c_str:
                subj_p = settings.BKT_SUBJ_PROB_SURE
            elif "guess" in c_str:
                subj_p = settings.BKT_SUBJ_PROB_GUESS
            else:
                subj_p = settings.BKT_SUBJ_PROB_NOT_SURE

            actual_o = settings.FLOAT_ONE if is_correct else settings.FLOAT_ZERO
            brier_loss = (subj_p - actual_o) ** 2
            record["brier_sum"] = round(record.get("brier_sum", settings.FLOAT_ZERO) + brier_loss, 4)
            record["brier_attempts"] = record.get("brier_attempts", 0) + 1
            record["brier_score"] = round(record["brier_sum"] / record["brier_attempts"], 4)

            # 1. Correct Guess: discount mastery gain because outcome was likely lucky guess
            if is_correct and ("guess" in c_str):
                discount = settings.BKT_CONFIDENCE_GUESS_DISCOUNT
                p_l_obs = p_l + (p_l_obs - p_l) * discount
            
            # 2. Confident Wrong: penalty for ingrained misconceptions
            elif (not is_correct) and ("sure" in c_str and "not" not in c_str):
                record["confident_wrong_count"] = record.get("confident_wrong_count", 0) + 1
                penalty = settings.BKT_CONFIDENCE_WRONG_PENALTY
                p_l_obs = max(settings.BKT_PROB_FLOOR, p_l_obs / penalty)
                p_t = p_t * settings.FLOAT_HALF

        # Smaller weight for conversational tutor turns vs explicit assessment
        is_tutor = source in ("tutor", "tutor_turn", "tutor_check")
        if is_tutor:
            tutor_wt = getattr(settings, "BKT_TUTOR_WEIGHT", settings.BKT_REINFORCE_DECAY)
            p_l_obs = p_l + (p_l_obs - p_l) * tutor_wt
            p_t = p_t * tutor_wt

        p_l_new = p_l_obs + ((settings.FLOAT_ONE - p_l_obs) * p_t)
        p_l_new = max(settings.BKT_PROB_FLOOR, min(settings.BKT_PROB_CEIL, p_l_new))

        record["attempt_count"] += 1
        record["mastery_probability"] = round(p_l_new, 4)
        record["confidence"] = round(min(settings.FLOAT_HALF + (record["attempt_count"] * settings.BKT_CONFIDENCE_ATTEMPT_WEIGHT), settings.BKT_CONFIDENCE_CAP), 2)
        record["last_attempt"] = datetime.utcnow().isoformat()
        record["last_review"] = datetime.utcnow().isoformat()
        record["next_review_date"] = self._compute_next_review_date(record["mastery_probability"])

        db.update("learner_mastery", record["id"], record)
        self.record_study_activity(student_id)
        return record


    def record_study_activity(self, student_id: str) -> None:
        if not db.supabase_client or str(student_id).startswith("sim_") or is_test_environment():
            return
        def _bg_update():
            try:
                response = db.supabase_client.table("profiles").select("streak,last_active").eq("id", student_id).limit(1).execute()
                rows = response.data or []
                if not rows:
                    return
                profile = rows[0]
                today = datetime.utcnow().date()
                last_active = profile.get("last_active")
                previous_day = datetime.fromisoformat(last_active[:10]).date() if last_active else None
                streak = int(profile.get("streak") or 0)
                if previous_day == today:
                    streak = max(streak, 1)
                elif previous_day == today.fromordinal(today.toordinal() - 1):
                    streak += 1
                else:
                    streak = 1
                db.supabase_client.table("profiles").update({
                    "streak": streak,
                    "last_active": datetime.utcnow().isoformat()
                }).eq("id", student_id).execute()
            except Exception as e:
                pass
        try:
            db._sync_executor.submit(_bg_update)
        except Exception:
            pass

    def get_learner_profile(self, student_id: str, course_id: str) -> Dict[str, Any]:
        """
        Compiles high-level dashboard and learner analytics including locked states.
        """
        all_concepts = db.list_all("concepts", lambda c: c.get("course_id") == course_id)
        concepts_map = {c["id"]: c for c in all_concepts}
        all_topics = db.list_all("topics", lambda t: t.get("course_id") == course_id)
        
        # Pre-fetch existing mastery records and prereqs in one pass
        existing_records = db.list_all("learner_mastery", lambda m: m.get("student_id") == student_id and m.get("course_id") == course_id)
        m_map = {m["concept_id"]: m for m in existing_records}

        all_prereqs = db.list_all("concept_prerequisites")
        prereqs_map: Dict[str, List[str]] = {}
        for p in all_prereqs:
            cid = p.get("concept_id")
            pid = p.get("prerequisite_id")
            if cid and pid:
                prereqs_map.setdefault(cid, []).append(pid)

        mastery_records = []
        total_p = settings.FLOAT_ZERO
        total_attempts = 0
        total_correct = 0

        topic_scores: Dict[str, List[float]] = {}

        for c in all_concepts:
            m = m_map.get(c["id"])
            if not m:
                m = {
                    "id": str(uuid.uuid4()),
                    "student_id": student_id,
                    "course_id": course_id,
                    "concept_id": c["id"],
                    "concept_name": c.get("name", "Unknown Concept"),
                    "mastery_probability": self.DEFAULT_P_INIT,
                    "confidence": settings.FLOAT_HALF,
                    "attempt_count": 0,
                    "correct_count": 0,
                    "incorrect_count": 0,
                    "created_at": datetime.utcnow().isoformat()
                }
                m_map[c["id"]] = m
                db.data.setdefault("learner_mastery", {})[m["id"]] = m
                db._dirty = True

            p_val = m["mastery_probability"]
            total_p += p_val
            total_attempts += int(m.get("attempt_count", 0))
            total_correct += int(m.get("correct_count", 0))

            topic = db.get_by_id("topics", c.get("topic_id", ""))
            t_name = topic.get("name", "General") if topic else "General"
            topic_scores.setdefault(t_name, []).append(p_val)

            lock_info = self.check_concept_locked(
                student_id, course_id, c["id"],
                mastery_map=m_map,
                prereqs_map=prereqs_map,
                concepts_map=concepts_map
            )

            if lock_info["is_locked"]:
                status = "Locked"
            elif p_val >= settings.BKT_MASTERY_HIGH:
                status = "Mastered"
            elif p_val >= settings.BKT_MASTERY_LOW:
                status = "Developing"
            else:
                status = "Needs Attention"

            mastery_records.append({
                "concept_id": c["id"],
                "concept_name": c["name"],
                "topic_name": t_name,
                "mastery_probability": p_val,
                "confidence": float(m.get("confidence", settings.BKT_DEFAULT_RECORD_CONFIDENCE)),
                "attempt_count": int(m.get("attempt_count", 0)),
                "correct_count": int(m.get("correct_count", 0)),
                "incorrect_count": int(m.get("incorrect_count", 0)),
                "status": status,
                "is_locked": lock_info["is_locked"],
                "locked_reason": lock_info["reason"],
                "blocking_prerequisite": lock_info["blocking_prerequisite"],
                "last_review": m.get("last_review")
            })

        overall_mastery = round(total_p / len(all_concepts), 3) if all_concepts else settings.FLOAT_ZERO
        overall_mastery_pct = round(overall_mastery * settings.FLOAT_HUNDRED, 1)

        # Topic summary
        weak_topics = []
        topics_mastered = 0
        topics_needing_revision = 0
        for t_name, scores in topic_scores.items():
            avg_t = sum(scores) / len(scores)
            if avg_t >= settings.BKT_TOPIC_MASTERY_HIGH:
                topics_mastered += 1
            else:
                topics_needing_revision += 1
                weak_topics.append({
                    "topic_name": t_name,
                    "mastery": round(avg_t * settings.FLOAT_HUNDRED, 1),
                    "concept_count": len(scores)
                })

        accuracy = round(total_correct / max(total_attempts, 1) * settings.FLOAT_HUNDRED, 1) if total_attempts > 0 else settings.FLOAT_ZERO
        concept_ids = {c["id"] for c in all_concepts}
        answer_events = db.list_all("attempts", lambda a: a.get("user_id") == student_id and a.get("concept_id") in concept_ids)
        by_day: Dict[str, List[bool]] = {}
        for event in answer_events:
            day = str(event.get("created_at", ""))[:10]
            if day:
                by_day.setdefault(day, []).append(bool(event.get("correct")))
        attempt_history = [
            {"date": day, "accuracy": round(sum(values) / len(values) * settings.FLOAT_HUNDRED, 1), "attempts": len(values)}
            for day, values in sorted(by_day.items())
        ]

        # Calculate source coverage %
        docs = db.list_all("documents", lambda d: d.get("course_id") == course_id)
        coverage = min(settings.FLOAT_HUNDRED, len(docs) * settings.BKT_DOC_COVERAGE_SCALE) if docs else settings.FLOAT_ZERO

        recommendations = self.generate_recommendations(
            student_id, course_id,
            mastery_map=m_map,
            prereqs_map=prereqs_map,
            concepts_map=concepts_map
        )
        streak_days = self.compute_study_streak(student_id, course_id)

        return {
            "student_id": student_id,
            "overall_mastery": overall_mastery,
            "overall_mastery_pct": overall_mastery_pct,
            "topics_mastered_count": topics_mastered,
            "concepts_mastered_count": sum(1 for m in mastery_records if m["mastery_probability"] >= settings.BKT_TOPIC_MASTERY_HIGH),
            "topics_needing_revision_count": topics_needing_revision,
            "questions_answered_total": total_attempts,
            "current_study_streak_days": streak_days,
            "assessment_accuracy": accuracy,
            "attempt_history": attempt_history,
            "source_coverage_percentage": round(coverage, 1),
            "mastery_by_concept": mastery_records,
            "weak_topics": weak_topics,
            "recommendations": recommendations
        }

    def compute_study_streak(self, student_id: str, course_id: str) -> int:
        records = db.list_all("learner_mastery", lambda m: m.get("student_id") == student_id and m.get("course_id") == course_id)
        attempt_dates = set()
        for r in records:
            last = r.get("last_attempt")
            if last and r.get("attempt_count", 0) > 0:
                try:
                    d_str = last[:10]
                    attempt_dates.add(datetime.fromisoformat(d_str).date())
                except Exception:
                    pass
        if not attempt_dates:
            return 0
        
        today = datetime.utcnow().date()
        current = today
        from datetime import timedelta
        if current not in attempt_dates:
            yesterday = today - timedelta(days=1)
            if yesterday in attempt_dates:
                current = yesterday
            else:
                return 0
        
        streak = 0
        while current in attempt_dates:
            streak += 1
            current -= timedelta(days=1)
        return streak

    def generate_recommendations(
        self, 
        student_id: str, 
        course_id: str, 
        limit: Optional[int] = 4,
        mastery_map: Optional[Dict[str, Any]] = None,
        prereqs_map: Optional[Dict[str, List[str]]] = None,
        concepts_map: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Prerequisite-aware recommendation algorithm:
        Inspects weak concepts and verifies if their prerequisites are mastered.
        """
        if concepts_map is None:
            all_concepts = db.list_all("concepts", lambda c: c.get("course_id") == course_id)
            concepts_map = {c["id"]: c for c in all_concepts}
        
        if mastery_map is None:
            existing_records = db.list_all("learner_mastery", lambda m: m.get("student_id") == student_id and m.get("course_id") == course_id)
            mastery_map = {m["concept_id"]: m for m in existing_records}
            for c_id, c in concepts_map.items():
                if c_id not in mastery_map:
                    mastery_map[c_id] = self.get_or_create_mastery(student_id, course_id, c_id)

        if prereqs_map is None:
            all_prereqs = db.list_all("concept_prerequisites")
            prereqs_map = {}
            for p in all_prereqs:
                cid = p.get("concept_id")
                pid = p.get("prerequisite_id")
                if cid and pid:
                    prereqs_map.setdefault(cid, []).append(pid)

        recommendations = []
        for c_id, c_data in concepts_map.items():
            m_rec = mastery_map.get(c_id) or {}
            m_prob = m_rec.get("mastery_probability", self.DEFAULT_P_INIT)
            if m_prob < settings.BKT_INTERVENT_THRESHOLD: # Concept needs attention
                last_review = m_rec.get("last_review")
                review_boost = settings.FLOAT_ZERO
                if last_review:
                    try:
                        days_since_review = max(0, (datetime.utcnow().date() - datetime.fromisoformat(last_review[:10]).date()).days)
                        review_boost = min(days_since_review, 30) / 3
                    except ValueError:
                        pass
                lock_info = self.check_concept_locked(
                    student_id, course_id, c_id,
                    mastery_map=mastery_map,
                    prereqs_map=prereqs_map,
                    concepts_map=concepts_map
                )
                if lock_info["is_locked"]:
                    blocker = lock_info["blocking_prerequisite"]
                    recommendations.append({
                        "concept_id": blocker["id"],
                        "concept_name": blocker["name"],
                        "target_concept": c_data["name"],
                        "current_mastery": blocker["mastery"],
                        "recommendation_type": "Prerequisite Foundation First",
                        "reason": f"'{c_data['name']}' is locked! Strengthen foundational prerequisite '{blocker['name']}' first.",
                        "estimated_minutes": 20,
                        "action_label": f"Review {blocker['name']}",
                        "priority_score": settings.BKT_RECOM_URGENCY_OFFSET - blocker["mastery"] + review_boost
                    })
                else:
                    recommendations.append({
                        "concept_id": c_id,
                        "concept_name": c_data["name"],
                        "target_concept": c_data["name"],
                        "current_mastery": round(m_prob * settings.FLOAT_HUNDRED, 1),
                        "recommendation_type": "Targeted Concept Practice",
                        "reason": f"Prerequisites are unlocked! Practice is needed to master '{c_data['name']}'.",
                        "estimated_minutes": 25,
                        "action_label": f"Practice {c_data['name']}",
                        "priority_score": settings.BKT_RECOM_PRIORITY_OFFSET - (m_prob * settings.BKT_RECOM_PRIORITY_SCALE) + review_boost
                    })

        # Deduplicate and sort by priority_score descending
        seen = set()
        unique_recs = []
        recommendations.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        for r in recommendations:
            if r["concept_name"] not in seen:
                seen.add(r["concept_name"])
                unique_recs.append(r)

        if limit is not None:
            return unique_recs[:limit]
        return unique_recs

    def calibrate_from_intake(
        self,
        student_id: str,
        course_id: str,
        familiar_concepts: Optional[List[str]] = None,
        experience_level: str = "Beginner",
        diagnostic_score_pct: Optional[float] = None,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Calibrates initial BKT prior knowledge P(L_0) for new students with no history.
        """
        concepts = db.list_all("concepts", lambda c: c.get("course_id") == course_id)
        if not concepts:
            return {"status": "no_concepts", "course_id": course_id, "mastery_profile": None}

        base_prior = settings.BKT_INTAKE_BEGINNER_PRIOR
        if experience_level.lower() == "intermediate":
            base_prior = settings.BKT_INTAKE_INTERMEDIATE_PRIOR
        elif experience_level.lower() == "advanced":
            base_prior = settings.BKT_INTAKE_ADVANCED_PRIOR

        if diagnostic_score_pct is not None:
            base_prior = max(
                settings.BKT_INTAKE_DIAGNOSTIC_MIN,
                min(
                    settings.BKT_INTAKE_DIAGNOSTIC_MAX,
                    (diagnostic_score_pct / settings.FLOAT_HUNDRED) * settings.BKT_INTAKE_DIAGNOSTIC_MAX
                )
            )

        familiar_lower = [f.lower().strip() for f in (familiar_concepts or [])]
        notes_lower = notes.lower()

        updated_count = 0
        for c in concepts:
            c_name_lower = c["name"].lower()
            is_familiar = any(f in c_name_lower or c_name_lower in f for f in familiar_lower)
            if not is_familiar and notes_lower:
                is_familiar = any(term in notes_lower for term in c_name_lower.split() if len(term) >= 5)

            assigned_prior = settings.BKT_INTAKE_FAMILIAR_PRIOR if is_familiar else base_prior
            m_rec = self.get_or_create_mastery(student_id, course_id, c["id"])
            m_rec["mastery_probability"] = assigned_prior
            m_rec["confidence"] = settings.BKT_INTAKE_FAMILIAR_CONFIDENCE if is_familiar else settings.BKT_INTAKE_UNFAMILIAR_CONFIDENCE
            m_rec["last_review"] = datetime.utcnow().isoformat()
            m_rec["next_review_date"] = self._compute_next_review_date(assigned_prior)
            db.update("learner_mastery", m_rec["id"], m_rec, save_disk=True)
            updated_count += 1

        profile = self.get_learner_profile(student_id, course_id)
        return {
            "status": "calibrated",
            "student_id": student_id,
            "course_id": course_id,
            "experience_level": experience_level,
            "concepts_calibrated": updated_count,
            "overall_mastery_pct": profile.get("overall_mastery_pct", settings.FLOAT_HUNDRED * settings.BKT_INTAKE_BEGINNER_PRIOR),
            "profile": profile
        }

    def apply_time_decay(
        self,
        student_id: str,
        course_id: str,
        elapsed_days: Optional[float] = None,
        half_life_days: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Applies Ebbinghaus forgetting curve decay to concept mastery over time:
        P(L_t) = P_floor + (P(L) - P_floor) * exp(-lambda * delta_t)
        """
        h_days = half_life_days if half_life_days is not None else settings.BKT_HALF_LIFE_DEFAULT
        records = db.list_all("learner_mastery", lambda m: m.get("student_id") == student_id and m.get("course_id") == course_id)
        decayed = []
        decay_constant = math.log(2) / max(h_days, settings.FLOAT_ONE)
        now = datetime.utcnow()
        for r in records:
            if elapsed_days is not None:
                days = elapsed_days
            else:
                last = r.get("last_review") or r.get("last_attempt")
                if last:
                    try:
                        last_dt = datetime.fromisoformat(last.replace("Z", ""))
                        days = max(settings.FLOAT_ZERO, (now - last_dt).total_seconds() / settings.BKT_DAY_SECONDS)
                    except Exception:
                        days = settings.FLOAT_ZERO
                else:
                    days = settings.FLOAT_ZERO

            if days > 0:
                p_current = r.get("mastery_probability", self.DEFAULT_P_INIT)
                p_floor = self.DEFAULT_P_INIT
                decay_factor = math.exp(-decay_constant * days)
                p_decayed = p_floor + (p_current - p_floor) * decay_factor
                r["mastery_probability"] = round(max(settings.BKT_PROB_FLOOR, min(settings.BKT_PROB_CEIL, p_decayed)), 4)
                r["next_review_date"] = self._compute_next_review_date(r["mastery_probability"])
                db.update("learner_mastery", r["id"], r)
                decayed.append(r)
        return decayed

    def propagate_prerequisite_mastery(
        self,
        student_id: str,
        course_id: str,
        prerequisite_concept_id: str
    ) -> Dict[str, Any]:
        """
        Propagates mastery gains from a prerequisite to dependent concepts:
        When a prerequisite crosses PREREQ_UNLOCK_THRESHOLD, dependent concepts
        unlock and receive foundational readiness progression.
        """
        prereq_mastery = self.get_or_create_mastery(student_id, course_id, prerequisite_concept_id)
        p_val = prereq_mastery.get("mastery_probability", self.DEFAULT_P_INIT)

        all_concepts = db.list_all("concepts", lambda c: c.get("course_id") == course_id)
        rel_prereqs = db.list_all("concept_prerequisites", lambda p: p.get("prerequisite_id") == prerequisite_concept_id)
        dependent_concept_ids = {r.get("concept_id") for r in rel_prereqs if r.get("concept_id")}

        for c in all_concepts:
            if prerequisite_concept_id in c.get("prerequisites", []):
                dependent_concept_ids.add(c["id"])

        unlocked_concepts = []
        for dep_id in dependent_concept_ids:
            dep_mastery = self.get_or_create_mastery(student_id, course_id, dep_id)
            lock_info = self.check_concept_locked(student_id, course_id, dep_id)
            if not lock_info.get("is_locked"):
                unlocked_concepts.append(dep_id)
                # Foundational readiness progression
                if dep_mastery.get("mastery_probability", self.DEFAULT_P_INIT) <= self.DEFAULT_P_INIT:
                    dep_mastery["mastery_probability"] = round(self.DEFAULT_P_INIT + settings.BKT_PREREQ_READINESS_BOOST, 4)
                    db.update("learner_mastery", dep_mastery["id"], dep_mastery)

        return {
            "prerequisite_id": prerequisite_concept_id,
            "prerequisite_mastery": p_val,
            "dependent_concept_count": len(dependent_concept_ids),
            "unlocked_concepts": unlocked_concepts
        }

bkt_engine = BayesianKnowledgeTracer()
