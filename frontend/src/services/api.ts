import { Course, LearnerProfile, Assessment, AssessmentReport, EvaluationMetrics } from '../types';
import { supabase } from '../lib/supabase';

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';

export async function getStudentId(): Promise<string> {
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.user?.id) return session.user.id;
  } catch (err) {
    console.warn('Session check failed:', err);
  }

  try {
    const demo = localStorage.getItem('aitutor_demo_user');
    if (demo) {
      const parsed = JSON.parse(demo);
      if (parsed?.user?.id) return parsed.user.id;
    }
  } catch {}

  return 'demo_student';
}

async function authHeaders(): Promise<Record<string, string>> {
  let token = '';
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      token = session.access_token;
    }
  } catch {}

  if (!token) {
    try {
      const demo = localStorage.getItem('aitutor_demo_user');
      if (demo) {
        const parsed = JSON.parse(demo);
        if (parsed?.session?.access_token) {
          token = parsed.session.access_token;
        }
      }
    } catch {}
  }

  if (!token) {
    token = 'token_default_student_' + Date.now();
  }

  const headers: Record<string, string> = { 
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  };
  return headers;
}

export const api = {
  async get(endpoint: string): Promise<any> {
    const headers = await authHeaders();
    const clean = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const res = await fetch(`${API_BASE}${clean}`, { headers });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Error (${res.status})` }));
      throw new Error(err.detail || `Request failed (${res.status})`);
    }
    return res.json();
  },

  async post(endpoint: string, body?: any): Promise<any> {
    const headers = await authHeaders();
    const clean = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const res = await fetch(`${API_BASE}${clean}`, {
      method: 'POST',
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Error (${res.status})` }));
      throw new Error(err.detail || `Request failed (${res.status})`);
    }
    return res.json();
  },

  // Courses
  async getCourses(): Promise<Course[]> {

    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/courses`, { headers });
    if (!res.ok) throw new Error('Failed to fetch courses');
    return res.json();
  },

  async getCourse(id: string): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/courses/${id}`, { headers });
    if (!res.ok) throw new Error('Failed to fetch course details');
    return res.json();
  },

  async createCourse(data: { name: string; description: string; subject: string; semester?: string; exam_date?: string }): Promise<Course> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/courses`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to create course');
    }
    return res.json();
  },

  async deleteCourse(id: string): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/courses/${id}`, {
      method: 'DELETE',
      headers,
    });
    if (!res.ok) throw new Error('Failed to delete course');
    return res.json();
  },

  async getConcepts(courseId: string): Promise<any[]> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/courses/${courseId}/concepts`, { headers });
    if (!res.ok) return [];
    return res.json();
  },

  async generateCurriculum(courseId: string): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/courses/${courseId}/generate-curriculum`, {
      method: 'POST',
      headers,
    });
    if (!res.ok) throw new Error('Failed to generate curriculum');
    return res.json();
  },

  async uploadMaterial(courseId: string, fileOrFiles: File | File[], taskId?: string): Promise<any> {
    const studentId = await getStudentId();
    let token = '';
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.access_token) token = session.access_token;
    } catch {}
    if (!token) {
      try {
        const localDemo = localStorage.getItem('aitutor_demo_user');
        if (localDemo) {
          const parsed = JSON.parse(localDemo);
          token = parsed?.session?.access_token || `token_${studentId}`;
        }
      } catch {}
    }

    const formData = new FormData();
    if (Array.isArray(fileOrFiles)) {
      fileOrFiles.forEach(f => formData.append('files', f));
    } else {
      formData.append('file', fileOrFiles);
      formData.append('files', fileOrFiles);
    }
    if (taskId) formData.append('task_id', taskId);
    const headers: Record<string, string> = {
      'X-Student-Id': studentId,
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE}/courses/${courseId}/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  },

  async uploadDocument(courseId: string, fileOrFiles: File | File[], taskId?: string): Promise<any> {
    return this.uploadMaterial(courseId, fileOrFiles, taskId);
  },

  async ingestYouTube(courseId: string, url: string, taskId?: string): Promise<any> {
    const headers = await authHeaders();
    headers['Content-Type'] = 'application/json';
    const res = await fetch(`${API_BASE}/courses/${courseId}/youtube`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ url, task_id: taskId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'YouTube ingestion failed');
    }
    return res.json();
  },

  async getIngestionProgress(taskId: string): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/ingestion/progress/${taskId}`, { headers });
    if (!res.ok) return { progress_pct: 100, status: 'completed' };
    return res.json();
  },

  // Tutor
  async queryTutor(payload: {
    course_id: string;
    query: string;
    conversation_id?: string;
    topic_id?: string;
    difficulty?: string;
    mode?: string;
    style?: string;
    document_ids?: string[];
    language?: string;
    allow_outside_knowledge?: boolean;
  }): Promise<any> {
    const studentId = await getStudentId();
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/tutor/query`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ ...payload, student_id: studentId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Tutor server error (${res.status})` }));
      throw new Error(err.detail || `Tutor query error (${res.status})`);
    }
    return res.json();
  },

  async getSuggestedQuestions(courseId: string): Promise<string[]> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/courses/${encodeURIComponent(courseId)}/suggested-questions`, { headers });
    if (!res.ok) return [];
    const data = await res.json().catch(() => ({}));
    return data.suggested_questions || [];
  },

  async listConversations(courseId?: string): Promise<any[]> {
    const headers = await authHeaders();
    const url = courseId ? `${API_BASE}/conversations?course_id=${encodeURIComponent(courseId)}` : `${API_BASE}/conversations`;
    const res = await fetch(url, { headers });
    if (!res.ok) return [];
    return res.json();
  },

  async getConversationMessages(conversationId: string): Promise<any[]> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/conversations/${encodeURIComponent(conversationId)}/messages`, { headers });
    if (!res.ok) return [];
    return res.json();
  },

  async deleteConversation(conversationId: string): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/conversations/${encodeURIComponent(conversationId)}`, {
      method: 'DELETE',
      headers,
    });
    if (!res.ok) throw new Error('Failed to delete conversation');
    return res.json();
  },

  async getSource(chunkId: string): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/tutor/sources/${chunkId}`, { headers });
    if (!res.ok) throw new Error('Failed to fetch source details');
    return res.json();
  },

  async evaluateTeachBack(courseId: string, conceptId: string, explanation: string): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/tutor/teach-back`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        course_id: courseId,
        concept_id: conceptId,
        explanation: explanation,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Evaluation failed (${res.status})` }));
      throw new Error(err.detail || `Teach-back evaluation failed (${res.status})`);
    }
    return res.json();
  },


  async explainUrl(url: string, courseId?: string, saveToKnowledgeBase = true): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/tutor/explain-url`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ url, course_id: courseId, save_to_knowledge_base: saveToKnowledgeBase }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to explain URL' }));
      throw new Error(err.detail || 'Failed to explain study material link');
    }
    return res.json();
  },

  async addNote(courseId: string, title: string, content: string): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/courses/${courseId}/add-note`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ course_id: courseId, title, content }),
    });
    if (!res.ok) throw new Error('Failed to save study notes');
    return res.json();
  },

  // Assessments
  async getQuizQuota(): Promise<{ quota_limit: number | null; quizzes_used: number; remaining: number | null }> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/assessments/quota`, { headers });
    if (!res.ok) return { quota_limit: null, quizzes_used: 0, remaining: null };
    return res.json();
  },

  async generateAssessment(payload: {
    course_id: string;
    document_ids?: string[];
    concept_ids?: string[];
    topic_ids?: string[];
    topic_id?: string;
    concept_id?: string;
    concept_name?: string;
    question_count: number;
    difficulty: string;
    types?: string[];
    language?: string;
    mode?: string;
    practical_ratio?: number;
  }): Promise<Assessment> {
    const studentId = await getStudentId();
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/assessments/generate`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ ...payload, student_id: studentId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to generate assessment' }));
      throw new Error(err.detail || 'Failed to generate assessment');
    }
    return res.json();
  },

  async generateChatQuiz(payload: {
    course_id: string;
    conversation_id?: string;
    question_count?: number;
  }): Promise<Assessment> {
    const studentId = await getStudentId();
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/assessments/chat-quiz`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ ...payload, student_id: studentId }),
    });
    if (!res.ok) throw new Error('Failed to generate chat quiz');
    return res.json();
  },

  async getAssessment(id: string): Promise<Assessment> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/assessments/${id}`, { headers });
    if (!res.ok) throw new Error('Failed to fetch assessment');
    return res.json();
  },

  async submitAssessment(
    id: string,
    answers: Record<string, string>,
    timeSpentSeconds: number,
    autoSubmitted = false,
    safeModeViolation?: string,
    studentConfidences?: Record<string, string>
  ): Promise<AssessmentReport> {
    const studentId = await getStudentId();
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/assessments/${id}/submit`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        student_answers: answers,
        student_confidences: studentConfidences || {},
        time_spent_seconds: timeSpentSeconds,
        auto_submitted: autoSubmitted,
        safe_mode_violation: safeModeViolation,
        student_id: studentId,
      }),
    });
    if (!res.ok) throw new Error('Failed to submit assessment');
    return res.json();
  },

  async getAssessmentReport(id: string): Promise<AssessmentReport> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/assessments/${id}/report`, { headers });
    if (!res.ok) throw new Error('Failed to fetch assessment report');
    return res.json();
  },

  async testLlm(config: any): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/settings/test-llm`, {
      method: 'POST',
      headers,
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error('Failed to test AI provider');
    return res.json();
  },

  // Learner Model & BKT
  async getLearnerMastery(studentId?: string, courseId?: string): Promise<LearnerProfile> {
    const resolvedId = studentId && studentId !== 'default_student' ? studentId : await getStudentId();
    const headers = await authHeaders();
    const url = courseId
      ? `${API_BASE}/learner/${resolvedId}/mastery?course_id=${courseId}`
      : `${API_BASE}/learner/${resolvedId}/mastery`;
    const res = await fetch(url, { headers });
    if (!res.ok) throw new Error('Failed to fetch learner profile');
    return res.json();
  },

  async updateLearnerState(conceptId: string, isCorrect: boolean, courseId: string, difficulty = 'Medium'): Promise<any> {
    const studentId = await getStudentId();
    const headers = await authHeaders();
    const res = await fetch(
      `${API_BASE}/learner/update?concept_id=${conceptId}&is_correct=${isCorrect}&course_id=${courseId}&difficulty=${difficulty}&student_id=${studentId}`,
      { method: 'POST', headers }
    );
    if (!res.ok) throw new Error('Failed to update learner state');
    return res.json();
  },

  // Concept Map
  async getConceptMap(courseId: string): Promise<any> {
    const studentId = await getStudentId();
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/course/${courseId}/concept-map?student_id=${studentId}`, { headers });
    if (!res.ok) throw new Error('Failed to fetch concept map');
    return res.json();
  },

  // Revision & Study Plan
  async getRevision(courseId: string, studentId?: string): Promise<any> {
    const resolvedId = studentId && studentId !== 'default_student' ? studentId : await getStudentId();
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/revision/${courseId}?student_id=${resolvedId}`, { headers });
    if (!res.ok) throw new Error('Failed to fetch revision pack');
    return res.json();
  },

  async generateRevision(courseId: string, topicName?: string, studentId?: string): Promise<any> {
    const resolvedId = studentId && studentId !== 'default_student' ? studentId : await getStudentId();
    const headers = await authHeaders();
    const params = new URLSearchParams({ student_id: resolvedId });
    if (topicName) params.set('topic_name', topicName);
    const res = await fetch(
      `${API_BASE}/revision/${courseId}/generate?${params.toString()}`,
      { method: 'POST', headers }
    );
    if (!res.ok) throw new Error('Failed to generate revision pack');
    return res.json();
  },

  async getStudyPlan(courseId: string, studentId?: string): Promise<any> {
    const resolvedId = studentId && studentId !== 'default_student' ? studentId : await getStudentId();
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/study-plan/${courseId}?student_id=${resolvedId}`, { headers });
    if (!res.ok) throw new Error('Failed to fetch study plan');
    return res.json();
  },

  async generateStudyPlan(courseId: string, examDate: string, dailyMinutes: number, studentId?: string): Promise<any> {
    const resolvedId = studentId && studentId !== 'default_student' ? studentId : await getStudentId();
    const headers = await authHeaders();
    const res = await fetch(
      `${API_BASE}/study-plan/${courseId}/generate?exam_date=${examDate}&daily_minutes=${dailyMinutes}&student_id=${resolvedId}`,
      { method: 'POST', headers }
    );
    if (!res.ok) throw new Error('Failed to generate study plan');
    return res.json();
  },

  // Phase 3 Adaptive Learning & Misconceptions
  async getAssessmentValidationMetrics(): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/assessment/validation-metrics`, { headers });
    if (!res.ok) throw new Error('Failed to fetch validation metrics');
    return res.json();
  },

  async getMisconceptionBrief(misconception: string, conceptName?: string): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/assessment/misconception-brief`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ misconception, concept_name: conceptName }),
    });
    if (!res.ok) throw new Error('Failed to generate misconception brief');
    return res.json();
  },

  async getMisconceptionFlashcards(misconception: string, conceptName?: string): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/assessment/misconception-flashcards`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ misconception, concept_name: conceptName }),
    });
    if (!res.ok) throw new Error('Failed to generate misconception flashcards');
    return res.json();
  },

  // Evaluation
  async getEvaluationResults(): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/evaluation/results`, { headers });
    if (!res.ok) throw new Error('Failed to fetch evaluation metrics');
    return res.json();
  },

  async runEvaluation(courseId?: string): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/evaluation/run`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ course_id: courseId, run_simulation: true }),
    });
    if (!res.ok) throw new Error('Failed to run evaluation benchmark');
    return res.json();
  },

  async runStudentSimulation(courseId?: string): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/evaluation/simulate${courseId ? `?course_id=${courseId}` : ''}`, {
      method: 'POST',
      headers,
    });
    if (!res.ok) throw new Error('Failed to run student simulation');
    return res.json();
  },

  async streamStudentSimulation(courseId: string, onEvent: (event: any) => void): Promise<void> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/evaluation/simulator-stream?course_id=${encodeURIComponent(courseId)}`, { headers });
    if (!res.ok || !res.body) throw new Error('Unable to start learner simulation stream');
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';
      for (const raw of events) {
        const dataLine = raw.split('\n').find((line) => line.startsWith('data:'));
        if (dataLine) onEvent(JSON.parse(dataLine.slice(5).trim()));
      }
    }
  },

  // Settings & Demo
  async getSettings(): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/settings`, { headers });
    if (!res.ok) throw new Error('Failed to fetch settings');
    return res.json();
  },

  async updateSettings(data: any): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/settings`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update settings');
    return res.json();
  },

  async seedDemo(): Promise<any> {
    return this.loadSampleCourse();
  },

  async loadSampleCourse(): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/courses/sample`, { method: 'POST', headers });
    if (!res.ok) throw new Error('Failed to load sample course');
    return res.json();
  },

  // User Documents
  async getUserDocuments(courseId?: string): Promise<any[]> {
    const headers = await authHeaders();
    const url = courseId 
      ? `${API_BASE}/user/documents?course_id=${encodeURIComponent(courseId)}`
      : `${API_BASE}/user/documents`;
    const res = await fetch(url, { headers });
    if (!res.ok) return [];
    return res.json();
  },

  async deleteUserDocument(documentId: string): Promise<boolean> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/user/documents/${documentId}`, {
      method: 'DELETE',
      headers,
    });
    return res.ok;
  },

  getDocumentDownloadUrl(documentId: string): string {
    return `${API_BASE}/user/documents/${documentId}/download`;
  },

  async reanalyzeDocument(documentId: string): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/documents/${documentId}/reanalyze`, {
      method: 'POST',
      headers,
    });
    if (!res.ok) throw new Error('Failed to re-run document analysis');
    return res.json();
  },

  async reanalyzeCourse(courseId: string): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/courses/${courseId}/reanalyze`, {
      method: 'POST',
      headers,
    });
    if (!res.ok) throw new Error('Failed to re-run course analysis');
    return res.json();
  },

  // AI Study Tools
  async summarize(formData: FormData): Promise<any> {
    const headers = await authHeaders();
    delete headers['Content-Type'];
    const res = await fetch(`${API_BASE}/tools/summarize`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) throw new Error('Failed to generate summary');
    return res.json();
  },

  async solveHomework(formData: FormData): Promise<any> {
    const headers = await authHeaders();
    delete headers['Content-Type'];
    const res = await fetch(`${API_BASE}/tools/solve-homework`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) throw new Error('Failed to solve problem');
    return res.json();
  },

  async generateFlashcards(formData: FormData): Promise<any> {
    const headers = await authHeaders();
    delete headers['Content-Type'];
    const res = await fetch(`${API_BASE}/tools/generate-flashcards`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) throw new Error('Failed to generate flashcards');
    return res.json();
  },

  async calibrateLearnerIntake(payload: {
    course_id: string;
    familiar_concepts?: string[];
    experience_level?: string;
    diagnostic_score_pct?: number;
    notes?: string;
  }): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/learner/intake`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to calibrate learner intake');
    return res.json();
  },

  async listAssessments(courseId?: string): Promise<Assessment[]> {
    const headers = await authHeaders();
    const url = courseId ? `${API_BASE}/assessments?course_id=${encodeURIComponent(courseId)}` : `${API_BASE}/assessments`;
    const res = await fetch(url, { headers });
    if (!res.ok) return [];
    return res.json();
  },

  async createStructuredCourse(formData: FormData): Promise<any> {
    const headers = await authHeaders();
    delete headers['Content-Type'];
    const res = await fetch(`${API_BASE}/tools/create-structured-course`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Error creating structured course (${res.status})` }));
      throw new Error(err.detail || 'Failed to create structured course');
    }
    return res.json();
  },

  async generateQuizFromMaterial(formData: FormData): Promise<any> {
    const headers = await authHeaders();
    delete headers['Content-Type'];
    const res = await fetch(`${API_BASE}/tools/generate-quiz-from-material`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Quiz generation failed (${res.status})` }));
      throw new Error(err.detail || 'Failed to generate quiz');
    }
    return res.json();
  },

  async getAiHealth(): Promise<{
    llm_ok: boolean;
    model: string;
    embedding_ok: boolean;
    vision_ok: boolean;
    vision_reason?: string | null;
    stt_ok: boolean;
    error: string | null;
  }> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/health/ai`, { headers });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return {
        llm_ok: false,
        model: 'unknown',
        embedding_ok: false,
        vision_ok: false,
        vision_reason: 'Endpoint failed',
        stt_ok: false,
        error: err.detail || `AI Health endpoint returned ${res.status}`,
      };
    }
    return res.json();
  },

  async getDueFlashcards(studentId: string, courseId?: string): Promise<{
    student_id: string;
    course_id: string | null;
    due_count: number;
    cards_due: any[];
    all_cards: any[];
    flashcards: any[];
  }> {
    const headers = await authHeaders();
    const url = courseId 
      ? `${API_BASE}/learner/${studentId}/flashcards/due?course_id=${encodeURIComponent(courseId)}`
      : `${API_BASE}/learner/${studentId}/flashcards/due`;
    const res = await fetch(url, { headers });
    if (!res.ok) throw new Error('Failed to fetch due flashcards');
    return res.json();
  },

  async getCourseDebug(courseId: string): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/courses/${encodeURIComponent(courseId)}/debug`, { headers });
    if (!res.ok) throw new Error('Failed to fetch course debug info');
    return res.json();
  },

  async getSlideAlignments(courseId: string): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/courses/${encodeURIComponent(courseId)}/slide-alignments`, { headers });
    if (!res.ok) throw new Error('Failed to fetch slide alignments');
    return res.json();
  },

  async getSlideForMoment(courseId: string, timestamp: number): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/courses/${encodeURIComponent(courseId)}/slide-for-moment?timestamp=${timestamp}`, { headers });
    if (!res.ok) throw new Error('Failed to fetch slide for moment');
    return res.json();
  },

  async getMomentsForSlide(courseId: string, document: string, slide: number): Promise<any> {
    const headers = await authHeaders();
    const res = await fetch(`${API_BASE}/courses/${encodeURIComponent(courseId)}/moments-for-slide?document=${encodeURIComponent(document)}&slide=${slide}`, { headers });
    if (!res.ok) throw new Error('Failed to fetch moments for slide');
    return res.json();
  },

  // Silence Engine
  async startSilenceSession(data: { problem: string; course_id?: string; course_name?: string; topics?: string[]; weak_concepts?: string[] }): Promise<any> {
    return this.post('/silence/start', data);
  },

  async sendSilenceTick(data: { session_id: string; text: string; keystroke_meta?: any }): Promise<any> {
    return this.post('/silence/tick', data);
  },

  async sendSilenceFeedback(data: { session_id: string; helpful: boolean; rung?: any }): Promise<any> {
    return this.post('/silence/feedback', data);
  },

  async setSilencePatience(data: { session_id: string; patience: number }): Promise<any> {
    return this.post('/silence/patience', data);
  },

  async getSilenceReplay(sessionId: string): Promise<any> {
    return this.get(`/silence/replay/${sessionId}`);
  },

  async getSilenceStats(sessionId: string): Promise<any> {
    return this.get(`/silence/stats/${sessionId}`);
  },

  async getSilenceBaseline(sessionId: string): Promise<any> {
    return this.post(`/silence/baseline/${sessionId}`);
  }
};


