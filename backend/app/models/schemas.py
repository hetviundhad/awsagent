from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class CourseCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    subject: Optional[str] = "Computer Science"
    semester: Optional[str] = None
    exam_date: Optional[str] = None

class CourseUnit(BaseModel):
    id: str
    course_id: str
    unit_number: int
    title: str
    description: Optional[str] = ""

class Course(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""
    subject: Optional[str] = "General"
    semester: Optional[str] = "Current"
    exam_date: Optional[str] = None
    created_at: str
    units: List[CourseUnit] = []
    document_count: int = 0
    topic_count: int = 0
    concept_count: int = 0
    overall_mastery: float = 0.0

class VisualElement(BaseModel):
    id: str
    document_id: str
    course_id: str
    element_type: str # diagram, chart, table, figure, screenshot
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    caption: str
    structured_description: str
    image_url: Optional[str] = None

class KnowledgeChunk(BaseModel):
    id: str
    course_id: str
    document_id: str
    topic_id: Optional[str] = None
    concept_id: Optional[str] = None
    source_type: str # pdf, slide, video, image, document
    document_name: str
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    bbox: Optional[List[float]] = None # [x0, y0, x1, y1] normalized or pts
    chunk_type: Optional[str] = "text" # text, figure, table, keyframe
    keyframe_path: Optional[str] = None
    visual_frame_summary: Optional[str] = None
    content: str
    content_summary: Optional[str] = None
    visual_element: Optional[VisualElement] = None
    score: Optional[float] = None

class Citation(BaseModel):
    citation_index: int
    source_type: str # pdf, slide, video, image, link
    document_name: str
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    bbox: Optional[List[float]] = None # [x0, y0, x1, y1]
    keyframe_path: Optional[str] = None
    visual_frame_summary: Optional[str] = None
    snippet: str
    chunk_id: str
    visual_description: Optional[str] = None

class ClaimVerification(BaseModel):
    claim: str
    supported: bool
    source_doc: Optional[str] = None
    citation_index: Optional[int] = None
    reason: Optional[str] = None

class PrerequisiteEdge(BaseModel):
    concept: str
    prerequisite_of: str
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    reason: Optional[str] = None

class TutorQueryRequest(BaseModel):
    course_id: str
    query: str
    conversation_id: Optional[str] = None
    topic_id: Optional[str] = None
    difficulty: Optional[str] = "Medium"
    mode: Optional[str] = "Simple" # Simple, Detailed, Quiz me (or legacy Quick Explanation/Deep Dive)
    style: Optional[str] = "Simple" # Simple (default) / Detailed / Quiz me
    document_ids: Optional[List[str]] = None
    language: Optional[str] = "en" # en, hi, hinglish
    allow_outside_knowledge: bool = True

class TutorQueryResponse(BaseModel):
    answer: str
    grounded: bool
    is_outside_knowledge: bool
    citations: List[Citation]
    confidence_score: float
    searched_topics: List[str]
    closest_source: Optional[Citation] = None
    conversation_id: str
    follow_up_questions: List[str] = []
    verification_check_question: Optional[str] = None
    claims_verification: Optional[List[ClaimVerification]] = None
    unsupported_claims: Optional[List[str]] = None

class Concept(BaseModel):
    id: str
    course_id: str
    topic_id: str
    name: str
    description: str
    difficulty: str = "Medium"
    prerequisites: List[str] = [] # List of concept IDs
    mastery_probability: float = 0.20
    confidence: float = 0.50
    attempt_count: int = 0
    correct_count: int = 0
    last_review: Optional[str] = None

class Topic(BaseModel):
    id: str
    course_id: str
    unit_id: Optional[str] = None
    name: str
    description: str
    concepts: List[Concept] = []
    mastery_percentage: float = 0.0

class Question(BaseModel):
    id: str
    course_id: str
    concept_id: Optional[str] = None
    question_text: str
    question_type: str # mcq, short_answer, numerical, true_false, application
    difficulty: str # Easy, Medium, Hard
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: str
    source_document: str
    source_location: str
    source_chunk_id: Optional[str] = None
    question_hash: str
    verification_status: str = "verified" # verified, needs_review, rejected
    verification_details: Optional[Dict[str, Any]] = None

class AssessmentGenerateRequest(BaseModel):
    course_id: str
    unit_id: Optional[str] = None
    topic_id: Optional[str] = None
    concept_id: Optional[str] = None
    concept_name: Optional[str] = None
    document_ids: Optional[List[str]] = None
    concept_ids: Optional[List[str]] = None
    topic_ids: Optional[List[str]] = None
    question_count: int = 5
    question_types: List[str] = ["mcq"]
    difficulty: str = "Adaptive"
    language: str = "English"
    mode: Optional[str] = "standard"
    practical_ratio: Optional[float] = 0.70
    time_limit_minutes: int = 15

class Assessment(BaseModel):
    id: str
    course_id: str
    title: str
    topic_name: Optional[str] = None
    total_questions: int
    difficulty: str
    time_limit_minutes: int
    status: str = "pending" # pending, in_progress, completed
    score: float = 0.0
    questions: List[Question]
    coverage: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    created_at: str

class AssessmentSubmitRequest(BaseModel):
    student_answers: Dict[str, str] # question_id -> student answer
    student_confidences: Optional[Dict[str, str]] = None # question_id -> "Sure" | "Not sure" | "Guess"
    time_spent_seconds: int = 0
    auto_submitted: bool = False
    safe_mode_violation: Optional[str] = None


class AnswerFeedback(BaseModel):
    question_id: str
    student_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str
    source_document: str
    source_location: str
    likely_misconception: Optional[str] = None
    concept_name: str
    difficulty: str

class AssessmentReport(BaseModel):
    assessment_id: str
    total_questions: int
    correct_count: int
    score_percentage: float
    time_spent_seconds: int
    auto_submitted: bool = False
    safe_mode_violation: Optional[str] = None
    topic_performance: Dict[str, float]
    difficulty_performance: Dict[str, float]
    weak_concepts: List[str]
    detected_misconceptions: List[str]
    recommended_next_step: Dict[str, Any]
    detailed_feedbacks: List[AnswerFeedback]

class ExplainUrlRequest(BaseModel):
    url: str
    course_id: Optional[str] = None
    save_to_knowledge_base: bool = True

class YouTubeIngestRequest(BaseModel):
    url: str
    task_id: Optional[str] = None

class AddNoteRequest(BaseModel):
    course_id: str
    title: str
    content: str
    task_id: Optional[str] = None

class LearnerMasteryRecord(BaseModel):
    concept_id: str
    concept_name: str
    topic_name: str
    mastery_probability: float
    confidence: float
    attempt_count: int
    correct_count: int
    incorrect_count: int
    status: str # Mastered, Developing, Needs Attention
    last_review: Optional[str] = None

class LearnerProfile(BaseModel):
    student_id: str
    overall_mastery: float
    topics_mastered_count: int
    topics_needing_revision_count: int
    questions_answered_total: int
    current_study_streak_days: int
    assessment_accuracy: float
    source_coverage_percentage: float
    mastery_by_concept: List[LearnerMasteryRecord]
    weak_topics: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]

class RevisionPack(BaseModel):
    course_id: str
    topic_name: str
    summary: str
    key_definitions: List[Dict[str, str]]
    key_formulas: List[Dict[str, str]]
    common_mistakes: List[Dict[str, str]]
    practice_problems: List[Question]
    flashcards: List[Dict[str, str]]

class StudyPlan(BaseModel):
    course_id: str
    exam_date: Optional[str]
    daily_study_minutes: int
    schedule: List[Dict[str, Any]] # Day, Topic, Duration, Focus, Why

class EvaluationRunRequest(BaseModel):
    course_id: Optional[str] = None
    run_simulation: bool = True

class EvaluationMetrics(BaseModel):
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    citation_accuracy: float
    unsupported_rate: float
    question_verification_rate: float
    question_repetition_rate: float
    total_test_cases: int
    evaluated_at: str
    is_live_measurement: bool = True
    test_results: List[Dict[str, Any]]
    simulation_results: Optional[List[Dict[str, Any]]] = None

class ExtractedConcept(BaseModel):
    name: str
    definition: str
    difficulty: int = Field(default=3, ge=1, le=5)
    prerequisites: List[str] = Field(default_factory=list)
    supporting_chunk_ids: List[str] = Field(default_factory=list)

class ExtractedSubtopic(BaseModel):
    name: str
    concepts: List[ExtractedConcept] = Field(default_factory=list)

class ExtractedTopic(BaseModel):
    name: str
    subtopics: List[ExtractedSubtopic] = Field(default_factory=list)

class ExtractedCurriculum(BaseModel):
    topics: List[ExtractedTopic] = Field(default_factory=list)

class TeachBackRequest(BaseModel):
    course_id: str
    concept_id: str
    explanation: str

