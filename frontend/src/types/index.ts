export interface CourseUnit {
  id: string;
  course_id: string;
  unit_number: number;
  title: string;
  description?: string;
}

export interface Course {
  id: string;
  name: string;
  description?: string;
  subject?: string;
  semester?: string;
  exam_date?: string;
  created_at: string;
  units?: CourseUnit[];
  document_count: number;
  chunk_count?: number;
  topic_count: number;
  concept_count: number;
  overall_mastery: number;
  topics?: any[];
  concepts?: any[];
}

export interface DocumentItem {
  id: string;
  course_id: string;
  filename: string;
  file_type: 'pdf' | 'slide' | 'video' | 'audio' | 'image' | string;
  file_size?: number;
  page_count?: number;
  slide_count?: number;
  duration_seconds?: number;
  status: 'pending' | 'processing' | 'processed' | 'error';
  created_at: string;
}

export interface VisualElement {
  id: string;
  document_id: string;
  course_id: string;
  element_type: string;
  page_number?: number;
  slide_number?: number;
  caption: string;
  structured_description: string;
  image_url?: string;
}

export interface Citation {
  citation_index: number;
  source_type: 'pdf' | 'slide' | 'video' | 'image' | 'link' | string;
  document_name: string;
  document_title?: string;
  source_document?: string;
  page_number?: number;
  slide_number?: number;
  page_or_slide?: string;
  page?: number;
  timestamp_start?: number;
  timestamp_end?: number;
  bbox?: number[]; // [x0, y0, x1, y1]
  keyframe_path?: string;
  visual_frame_summary?: string;
  snippet: string;
  quote?: string;
  chunk_id: string;
  visual_description?: string;
}

export interface ClaimVerification {
  claim: string;
  supported: boolean;
  source_doc?: string;
  citation_index?: number;
  reason?: string;
}

export interface ExternalLink {
  title: string;
  url: string;
  source: string;
  snippet?: string;
}

export interface AnswerSegment {
  text: string;
  citations: Citation[];
  type: 'sourced' | 'outside';
}

export interface DecisionItem {
  key: string;
  pattern: string;
  kind: string;
  label: string;
  measure: number;
  threshold: number;
  threshold_key: string;
  triggered: boolean;
  confidence: number;
  probabilities: Record<string, number>;
  action?: string | null;
  fallback: boolean;
}

export interface DecisionTrace {
  trace_id?: string;
  action: string;
  route: { tier: string; model_id?: string | null; reason?: string };
  decisions: DecisionItem[];
  decider_mode: 'model' | 'fallback' | 'unavailable' | 'skipped';
  decider_ms: number;
  learner_hint?: string;
  skipped_reason?: string | null;
  context?: { scores?: { chunk_id?: string; document?: string; relevance?: number }[]; dropped?: number };
  generated_by?: { provider: string; model_id?: string; latency_ms?: number } | null;
}

export interface ChatMessage {
  id: string;
  decision_trace?: DecisionTrace;
  role: 'user' | 'assistant';
  content: string;
  grounded?: boolean;
  is_outside_knowledge?: boolean;
  refused?: boolean;
  refusal?: boolean;
  refusal_category?: string;
  check_yourself_question?: string;
  answer_segments?: AnswerSegment[];
  citations?: Citation[];
  external_links?: ExternalLink[];
  confidence_score?: number;
  follow_ups?: string[];
  verification_question?: string;
  claims_verification?: ClaimVerification[];
  unsupported_claims?: string[];
  timestamp: string;
  interactive_quiz?: {
    question_id: string;
    question_text: string;
    options: string[];
    correct_answer: string;
    explanation: string;
    concept_id?: string;
    user_selected?: string;
    is_correct?: boolean;
    xp_awarded?: number;
  };
}

export interface Question {
  id: string;
  course_id: string;
  concept_id?: string;
  question_text: string;
  question_type: string;
  difficulty: 'Easy' | 'Medium' | 'Hard' | string;
  options?: string[];
  correct_answer: string;
  explanation: string;
  source_document: string;
  source_location: string;
  source_chunk_id?: string;
  question_hash?: string;
  verification_status?: string;
  verification_details?: any;
}

export interface Assessment {
  id: string;
  course_id: string;
  title: string;
  topic_name?: string;
  total_questions: number;
  difficulty: string;
  time_limit_minutes: number;
  status: 'pending' | 'in_progress' | 'completed';
  score: number;
  auto_submitted?: boolean;
  safe_mode_violation?: string;
  questions: Question[];
  created_at: string;
}

export interface AnswerFeedback {
  question_id: string;
  question_text: string;
  student_answer: string;
  correct_answer: string;
  is_correct: boolean;
  explanation: string;
  source_document: string;
  source_location: string;
  likely_misconception?: string;
  concept_name: string;
  difficulty: string;
}

export interface AssessmentReport {
  assessment_id: string;
  total_questions: number;
  correct_count: number;
  score_percentage: number;
  time_spent_seconds: number;
  auto_submitted?: boolean;
  safe_mode_violation?: string;
  topic_performance: Record<string, number>;
  difficulty_performance: Record<string, number>;
  weak_concepts: string[];
  detected_misconceptions: string[];
  recommended_next_step: {
    action: string;
    details: string;
    practice_recs: Array<{ count: number; difficulty: string; topic: string }>;
  };
  detailed_feedbacks: AnswerFeedback[];
}

export interface LearnerMasteryRecord {
  concept_id: string;
  concept_name: string;
  topic_name: string;
  mastery_probability: number;
  confidence: number;
  attempt_count: number;
  correct_count: number;
  incorrect_count: number;
  status: 'Mastered' | 'Developing' | 'Needs Attention';
  last_review?: string;
}

export interface LearnerProfile {
  student_id: string;
  concept_states?: Record<string, any>;
  overall_mastery: number;
  overall_mastery_pct: number;
  topics_mastered_count: number;
  concepts_mastered_count: number;
  topics_needing_revision_count: number;
  questions_answered_total: number;
  current_study_streak_days: number;
  assessment_accuracy: number;
  attempt_history: Array<{ date: string; accuracy: number; attempts: number }>;
  source_coverage_percentage: number;
  mastery_by_concept: LearnerMasteryRecord[];
  weak_topics: Array<{ topic_name: string; mastery: number; concept_count: number }>;
  recommendations: Array<{
    concept_id: string;
    concept_name: string;
    target_concept: string;
    current_mastery: number;
    recommendation_type: string;
    reason: string;
    estimated_minutes: number;
    action_label: string;
  }>;
}

export interface EvaluationMetrics {
  faithfulness: number;
  answer_relevancy: number;
  context_precision: number;
  context_recall: number;
  citation_accuracy: number;
  unsupported_rate: number;
  question_verification_rate: number;
  question_repetition_rate: number;
  false_refusal_rate?: number;
  bkt_auc?: number;
  bkt_log_loss?: number;
  total_test_cases: number;
  evaluated_at: string;
  is_live_measurement: boolean;
  test_results: Array<{
    case_id: string;
    question: string;
    type: string;
    result: string;
    details: string;
    grounded: boolean;
  }>;
  simulation_results?: Array<{
    student_id: string;
    archetype: string;
    initial_mastery: number;
    final_mastery: number;
    mastery_gain: number;
    sessions: Array<{ session: string; mastery_pct: number; questions_attempted: number }>;
  }>;
}

export interface DecisionItem {
  key: string;
  pattern: string;
  kind: string;
  label: string;
  measure: number;
  threshold: number;
  threshold_key: string;
  triggered: boolean;
  confidence: number;
  probabilities: Record<string, number>;
  action?: string | null;
  fallback: boolean;
}

// --------------------------------------------------------------------------- //
// Silence Engine Types                                                       //
// --------------------------------------------------------------------------- //
export interface SilenceDecision {
  rung: number | string;
  rung_name: string;
  token_class: string;
  held_back_by: string | null;
  probabilities: {
    productive_struggle?: number;
    frustration?: number;
    help_request?: number;
    stuck?: number;
    [key: string]: number | undefined;
  };
  suspect_lines: number[];
  action_type: string;
  spoken: boolean;
  latency_ms: number;
  decider_mode: 'model' | 'fallback' | 'unavailable' | 'skipped';
  target_misconception_id?: string | null;
  target_misconception_name?: string | null;
}

export interface SilenceSpokenMessage {
  rung: number | string;
  text: string;
  target_line: number | null;
  word_count: number;
  provider: string;
  model_id: string;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  retried: boolean;
  flagged_template: boolean;
}

export interface SilenceSessionStats {
  session_id: string;
  total_ticks: number;
  silent_ticks: number;
  spoken_interventions: number;
  tokens_used: number;
  avg_decider_ms: number;
  patience_dial: number;
  current_rung: number;
  decider_mode: string;
  tagline: string;
}

export interface SilenceTickResult {
  tick_index?: number;
  decision?: SilenceDecision;
  spoken_message?: SilenceSpokenMessage | null;
  session_stats?: SilenceSessionStats;
  skipped?: boolean;
  skipped_reason?: string;
  error?: string;
}

export interface SilenceAtlas {
  problem: string;
  course_name: string;
  misconceptions: Array<{
    id: string;
    name: string;
    description: string;
    concept: string;
  }>;
  milestones: string[];
  fallback: boolean;
  generated_by: string;
}

export interface SilenceReplayTick {
  tick_index: number;
  timestamp: number;
  scratchpad: string;
  diff: string;
  probabilities: Record<string, number>;
  rung: number | string;
  rung_name: string;
  token_class: string;
  held_back_by: string | null;
  action_type: string;
  spoken: boolean;
  spoken_text: string | null;
  spoken_target_line: number | null;
  decider_mode: string;
  decider_ms: number;
  llm_tokens: number;
}

export interface SilenceReplaySession {
  session_id: string;
  student_id: string;
  course_id: string;
  problem: string;
  course_name: string;
  atlas_summary: {
    misconception_count: number;
    milestone_count: number;
    fallback: boolean;
    misconceptions: Array<{ id: string; name: string; concept: string }>;
    milestones: string[];
  };
  created_at: number;
  patience_dial: number;
  stats: Record<string, any>;
  ticks: SilenceReplayTick[];
}

export interface SilenceDuelResult {
  session_id: string;
  total_ticks: number;
  silence_engine: {
    name: string;
    llm_calls: number;
    silent_ticks: number;
    total_tokens: number;
    input_tokens: number;
    output_tokens: number;
    avg_decider_ms: number;
    interruptions: number;
    false_interruption_count: number;
    false_interruption_rate_pct: number;
    estimated_cost_usd: number;
  };
  always_talk_baseline: {
    name: string;
    llm_calls: number;
    silent_ticks: number;
    total_tokens: number;
    input_tokens: number;
    output_tokens: number;
    avg_llm_latency_ms: number;
    interruptions: number;
    false_interruption_count: number;
    false_interruption_rate_pct: number;
    estimated_cost_usd: number;
  };
  comparison: {
    token_reduction_pct: number;
    interruption_reduction_pct: number;
    unwanted_interruption_prevention: number;
    note: string;
  };
}

