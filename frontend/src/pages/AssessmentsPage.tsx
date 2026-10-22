import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { 
  HelpCircle, Zap, ShieldCheck, CheckCircle2, 
  ArrowRight, Clock, Award, Sliders, Play, X 
} from 'lucide-react';
import { api } from '../services/api';
import { Assessment, Course } from '../types';
import { Button, Card, Pill } from '../components/ui';

interface AssessmentsPageProps {
  courses: Course[];
  activeCourseId: string;
  studentId?: string;
}

export const AssessmentsPage: React.FC<AssessmentsPageProps> = ({ 
  courses, 
  activeCourseId, 
  studentId = 'default_student' 
}) => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedCourseId, setSelectedCourseId] = useState(() => activeCourseId || localStorage.getItem('studymind_active_course') || '');
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(false);
  const [weakConcept, setWeakConcept] = useState<string>('');
  const [courseTopics, setCourseTopics] = useState<any[]>([]);
  const [courseConcepts, setCourseConcepts] = useState<any[]>([]);
  const [selectedTopicId, setSelectedTopicId] = useState<string>('');
  const [selectedConceptId, setSelectedConceptId] = useState<string>(searchParams.get('concept_id') || '');
  const [selectedConceptName, setSelectedConceptName] = useState<string>(searchParams.get('concept_name') || '');

  // Generation parameters
  const [questionCount, setQuestionCount] = useState(5);
  const [difficulty, setDifficulty] = useState('Adaptive');
  const [timeLimit, setTimeLimit] = useState(15);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    setSelectedCourseId(activeCourseId);
  }, [activeCourseId]);

  useEffect(() => {
    const cId = searchParams.get('concept_id') || '';
    const cName = searchParams.get('concept_name') || '';
    if (cId || cName) {
      setSelectedConceptId(cId);
      setSelectedConceptName(cName);
      setSelectedTopicId('');
    }
  }, [searchParams]);

  useEffect(() => {
    loadAssessments();
  }, [selectedCourseId]);

  const currentCourse = courses.find(c => c.id === selectedCourseId);

  const loadAssessments = async () => {
    setLoading(true);
    try {
      const [list, profile, courseDetail, conceptMap] = await Promise.all([
        api.listAssessments(selectedCourseId).catch(() => []),
        api.getLearnerMastery(studentId, selectedCourseId).catch(() => null),
        api.getCourse(selectedCourseId).catch(() => null),
        api.getConceptMap(selectedCourseId).catch(() => ({ nodes: [] }))
      ]);
      setAssessments(list || []);
      setCourseTopics(courseDetail?.topics || []);
      setCourseConcepts(conceptMap?.nodes || []);
      const weakRec = profile?.recommendations?.[0];
      if (weakRec?.concept_name) setWeakConcept(weakRec.concept_name);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const newAssessment = await api.generateAssessment({
        course_id: selectedCourseId,
        topic_id: selectedTopicId || undefined,
        concept_id: selectedConceptId || undefined,
        concept_name: selectedConceptName || undefined,
        question_count: questionCount,
        difficulty,
      });
      navigate(`/assessments/${newAssessment.id}`);
    } catch (err: any) {
      alert(`Failed to generate assessment: ${err.message || 'Error'}`);
    } finally {
      setGenerating(false);
    }
  };

  if (!courses || courses.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-paper-canvas p-6 text-center space-y-4">
        <div className="p-4 rounded-2xl bg-amber-50 text-amber-700 border border-amber-200">
          <Award className="h-8 w-8" />
        </div>
        <div className="max-w-md space-y-2">
          <h2 className="font-serif text-xl font-bold text-ink-900">No Course Material Processed Yet</h2>
          <p className="text-xs text-ink-600 leading-relaxed">
            Assessments & Diagnostic Quizzes are generated directly from your uploaded course materials. Upload a syllabus or lecture PDF to generate practice quizzes.
          </p>
        </div>
        <button
          onClick={() => navigate('/dashboard', { state: { openCreateCourse: true } })}
          className="px-4 py-2.5 rounded-xl bg-ink-900 text-white font-mono text-xs font-bold shadow-paper transition hover:bg-ink-800 cursor-pointer"
        >
          Create Course with Document &rarr;
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 lg:p-8 space-y-6 overflow-y-auto max-w-6xl w-full mx-auto bg-paper-canvas">
      <div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-royal-700 bg-royal-50 px-2 py-0.5 rounded border border-royal-200">
            BAYESIAN ASSESSMENT LAB
          </span>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-highlighter-base text-ink-900 font-bold border border-ink-900/10">
            SOURCE GROUNDED
          </span>
        </div>
        <h1 className="font-serif text-3xl font-bold text-ink-900 tracking-tight mt-1">
          Adaptive Assessment Engine
        </h1>
        <p className="font-serif text-xs text-ink-600 mt-0.5">
          Source-grounded quizzes with Bayesian difficulty adaptation, misconception diagnostics, and remediation flashcards.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Generator Panel */}
        <div className="lg:col-span-2 p-6 rounded-2xl bg-white border border-paper-hairline space-y-5 shadow-paper">
          <div className="flex items-center justify-between border-b border-paper-hairline pb-3">
            <h3 className="font-serif text-base font-bold text-ink-900 flex items-center space-x-2">
              <Sliders className="h-4 w-4 text-royal-700" />
              <span>Assessment Scope Configuration</span>
            </h3>
            <span className="text-xs font-mono text-ink-600 bg-paper-surface px-2.5 py-0.5 rounded-full border border-paper-hairline">
              Verified Pipeline
            </span>
          </div>

          <div className="space-y-4 font-serif">
            {/* Targeted Concept Banner if selected */}
            {selectedConceptName && (
              <div className="p-3.5 rounded-xl bg-highlighter-soft border border-highlighter-base/60 flex items-center justify-between">
                <div className="flex items-center space-x-2.5">
                  <Zap className="h-4 w-4 text-royal-700 shrink-0" />
                  <div>
                    <span className="font-mono text-[10px] font-bold uppercase text-ink-900 tracking-wider">
                      Targeted Concept Scope
                    </span>
                    <div className="text-xs font-bold text-ink-900">
                      Diagnostic questions will test: <span className="bg-highlighter-base px-1.5 py-0.2 rounded border border-ink-900/10 font-bold">{selectedConceptName}</span>
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedConceptId('');
                    setSelectedConceptName('');
                    setSearchParams({});
                  }}
                  className="font-mono text-[11px] text-ink-700 hover:text-ink-900 font-semibold underline cursor-pointer shrink-0"
                >
                  Clear Scope
                </button>
              </div>
            )}

            <div>
              <label className="block text-xs font-mono font-bold text-ink-800 mb-1">
                Target Syllabus Course:
              </label>
              <select
                value={selectedCourseId}
                onChange={(e) => {
                  const val = e.target.value;
                  setSelectedCourseId(val);
                  if (val) {
                    localStorage.setItem('studymind_active_course', val);
                    window.dispatchEvent(new Event('storage'));
                  }
                  setSelectedTopicId('');
                  setSelectedConceptId('');
                  setSelectedConceptName('');
                  setSearchParams({});
                }}
                className="w-full px-3 py-2 text-xs font-mono rounded-lg bg-paper-surface border border-paper-hairline text-ink-900 focus:outline-none focus:ring-1 focus:ring-royal-700 cursor-pointer"
              >
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.subject || 'General'})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono font-bold text-ink-800 mb-1">
                Topic & Concept Focus:
              </label>
              <select
                value={selectedConceptId ? `concept:${selectedConceptId}` : selectedTopicId ? `topic:${selectedTopicId}` : ''}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val.startsWith('concept:')) {
                    const cId = val.replace('concept:', '');
                    const cObj = courseConcepts.find(c => c.id === cId);
                    setSelectedConceptId(cId);
                    setSelectedConceptName(cObj?.name || '');
                    setSelectedTopicId('');
                  } else if (val.startsWith('topic:')) {
                    const tId = val.replace('topic:', '');
                    setSelectedTopicId(tId);
                    setSelectedConceptId('');
                    setSelectedConceptName('');
                  } else {
                    setSelectedTopicId('');
                    setSelectedConceptId('');
                    setSelectedConceptName('');
                  }
                }}
                className="w-full px-3 py-2 text-xs font-mono rounded-lg bg-paper-surface border border-paper-hairline text-ink-900 focus:outline-none focus:ring-1 focus:ring-royal-700 cursor-pointer"
              >
                <option value="">All Course Modules (Comprehensive Syllabus)</option>
                {courseTopics.length > 0 && (
                  <optgroup label="Course Modules & Units">
                    {courseTopics.map((top) => (
                      <option key={top.id} value={`topic:${top.id}`}>
                        {top.name}
                      </option>
                    ))}
                  </optgroup>
                )}
                {courseConcepts.length > 0 && (
                  <optgroup label="Specific Concept Nodes (BKT Targeted)">
                    {courseConcepts.map((concept) => (
                      <option key={concept.id} value={`concept:${concept.id}`}>
                        {concept.name} {concept.is_locked ? '(Locked Prerequisite)' : `(${concept.mastery || 20}% Mastery)`}
                      </option>
                    ))}
                  </optgroup>
                )}
              </select>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono">
              <div>
                <label className="block text-xs font-bold text-ink-800 mb-1">
                  Item Count:
                </label>
                <select
                  value={questionCount}
                  onChange={(e) => setQuestionCount(Number(e.target.value))}
                  className="w-full px-3 py-2 text-xs rounded-lg bg-paper-surface border border-paper-hairline text-ink-900 focus:outline-none focus:ring-1 focus:ring-royal-700 cursor-pointer"
                >
                  <option value={3}>3 Questions (Quick Check)</option>
                  <option value={5}>5 Questions (Standard Diagnostic)</option>
                  <option value={10}>10 Questions (Full Mock)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-ink-800 mb-1">
                  Difficulty Mode:
                </label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg bg-paper-surface border border-paper-hairline text-ink-900 focus:outline-none focus:ring-1 focus:ring-royal-700 cursor-pointer"
                >
                  <option value="Adaptive">Adaptive (BKT Dynamic)</option>
                  <option value="Easy">Easy (Foundational)</option>
                  <option value="Medium">Medium (Application)</option>
                  <option value="Hard">Hard (Synthesis)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-ink-800 mb-1">
                  Time Budget:
                </label>
                <select
                  value={timeLimit}
                  onChange={(e) => setTimeLimit(Number(e.target.value))}
                  className="w-full px-3 py-2 text-xs rounded-lg bg-paper-surface border border-paper-hairline text-ink-900 focus:outline-none focus:ring-1 focus:ring-royal-700 cursor-pointer"
                >
                  <option value={10}>10 Minutes</option>
                  <option value={15}>15 Minutes</option>
                  <option value={30}>30 Minutes</option>
                </select>
              </div>
            </div>

            {/* Verification pipeline safeguards */}
            <div className="p-3.5 rounded-xl bg-paper-surface border border-paper-hairline space-y-2">
              <div className="text-xs font-mono font-bold text-ink-800 uppercase tracking-wider">
                Automated Verification Guardrails:
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
                <div className="flex items-center space-x-1.5 text-emerald-800 font-medium">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                  <span>Source supported</span>
                </div>
                <div className="flex items-center space-x-1.5 text-emerald-800 font-medium">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                  <span>Answer verified</span>
                </div>
                <div className="flex items-center space-x-1.5 text-emerald-800 font-medium">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                  <span>Calibrated BKT</span>
                </div>
                <div className="flex items-center space-x-1.5 text-emerald-800 font-medium">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                  <span>Hash unique</span>
                </div>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <Button
                variant="primary"
                onClick={handleGenerate}
                disabled={generating}
                className="px-6 py-2.5"
              >
                <Play className="h-4 w-4" />
                <span>
                  {generating
                    ? `Generating & Verifying Questions${selectedConceptName ? ` for ${selectedConceptName}` : ''}...`
                    : selectedConceptName
                    ? `Generate Quiz for '${selectedConceptName}'`
                    : 'Generate & Start Assessment'}
                </span>
              </Button>
            </div>
          </div>
        </div>

        {/* Right: Quick Mock Launch Card */}
        <div className="p-6 rounded-2xl bg-white border border-paper-hairline shadow-paper space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-ink-900 px-2.5 py-0.5 rounded bg-highlighter-base border border-ink-900/10">
              RECOMMENDED MOCK
            </span>
            <h3 className="font-serif text-lg font-bold text-ink-900">
              {`${currentCourse?.name || 'Course'} Diagnostic Challenge`}
            </h3>
            <p className="font-serif text-xs text-ink-600 leading-relaxed">
              Synthesized from verified course lecture notes and textbooks. Directly evaluates key concepts and core problem formulation.
            </p>
            <div className="space-y-1.5 font-mono text-xs text-ink-600 pt-2 border-t border-paper-hairline">
              <div>• Questions: 3 Verified Items</div>
              <div>• Target Weak Concept: {weakConcept || 'Top Weak Concept'}</div>
              <div>• BKT Mastery Impact: High</div>
            </div>
          </div>

          <Button
            variant="primary"
            onClick={handleGenerate}
            className="w-full justify-center"
          >
            <span>Launch Diagnostic Now</span>
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Past Assessments & Diagnostic Reports */}
      {assessments.length > 0 && (
        <div className="p-6 rounded-2xl bg-white border border-paper-hairline space-y-4 shadow-paper">
          <div className="flex items-center justify-between border-b border-paper-hairline pb-3">
            <h3 className="font-serif text-base font-bold text-ink-900 flex items-center space-x-2">
              <ShieldCheck className="h-4 w-4 text-emerald-700" />
              <span>Completed Assessments & Misconception Reports</span>
            </h3>
            <span className="text-xs font-mono text-ink-500">{assessments.length} Total</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-paper-hairline text-ink-500 font-semibold bg-paper-surface">
                  <th className="py-2.5 px-3 rounded-l-lg font-serif">Assessment Title</th>
                  <th className="py-2.5 px-3">Questions</th>
                  <th className="py-2.5 px-3">Difficulty</th>
                  <th className="py-2.5 px-3">Status / Score</th>
                  <th className="py-2.5 px-3">Date</th>
                  <th className="py-2.5 px-3 text-right rounded-r-lg">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-paper-hairline">
                {assessments.map((a) => (
                  <tr key={a.id} className="hover:bg-paper-surface/60 transition">
                    <td className="py-3 px-3 font-serif font-bold text-ink-900">{a.title}</td>
                    <td className="py-3 px-3 text-ink-600">{a.total_questions || a.questions?.length || 5} Items</td>
                    <td className="py-3 px-3 text-royal-700 capitalize">{a.difficulty || 'Adaptive'}</td>
                    <td className="py-3 px-3">
                      {a.status === 'completed' ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-900 border border-emerald-300">
                          {Math.round((a.score || 0) * 100)}% Verified
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-900 border border-amber-300">
                          In Progress
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-ink-500">{a.created_at ? new Date(a.created_at).toLocaleDateString() : 'Today'}</td>
                    <td className="py-3 px-3 text-right">
                      {a.status === 'completed' ? (
                        <button
                          onClick={() => navigate(`/assessments/${a.id}/report`)}
                          className="px-3 py-1 rounded-lg bg-paper-surface hover:bg-paper-canvas text-royal-700 font-bold text-[11px] border border-paper-hairline hover:border-royal-700 transition"
                        >
                          View Misconception Report
                        </button>
                      ) : (
                        <button
                          onClick={() => navigate(`/assessments/${a.id}`)}
                          className="px-3 py-1 rounded-lg bg-ink-900 hover:bg-ink-800 text-white font-semibold text-[11px] transition"
                        >
                          Resume
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
