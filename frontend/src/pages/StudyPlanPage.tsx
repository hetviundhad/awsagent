import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar, Clock, AlertTriangle, CheckCircle2, RefreshCw, Sparkles, BookOpen } from 'lucide-react';
import { api } from '../services/api';
import { Button, Card, Pill } from '../components/ui';

interface StudyPlanPageProps {
  activeCourseId: string;
  studentId?: string;
}

export const StudyPlanPage: React.FC<StudyPlanPageProps> = ({ 
  activeCourseId, 
  studentId = 'default_student' 
}) => {
  const navigate = useNavigate();
  const [studyPlan, setStudyPlan] = useState<any>(null);
  const [examDate, setExamDate] = useState('');
  const [dailyMinutes, setDailyMinutes] = useState(60);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');

  const [courseDetail, setCourseDetail] = useState<any>(null);

  const effectiveCourseId = activeCourseId || localStorage.getItem('studymind_active_course') || '';

  useEffect(() => {
    loadPlan();
  }, [effectiveCourseId]);

  const loadPlan = async () => {
    setLoading(true);
    setError('');
    try {
      let targetId = effectiveCourseId;
      if (!targetId) {
        const cList = await api.getCourses().catch(() => []);
        if (cList && cList.length > 0) {
          targetId = cList[0].id;
          localStorage.setItem('studymind_active_course', targetId);
        }
      }

      if (targetId) {
        const [data, courseData] = await Promise.all([
          api.getStudyPlan(targetId, studentId).catch(() => null),
          api.getCourse(targetId).catch(() => null),
        ]);
        setStudyPlan(data);
        setCourseDetail(courseData);
        if (data?.exam_date) {
          setExamDate(data.exam_date);
        } else if (courseData) {
          setExamDate(courseData.course?.exam_date || courseData.exam_date || '');
        }
      }
    } catch (e) {
      console.error(e);
      setError('Unable to load your study plan. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setError('');
    try {
      const targetId = effectiveCourseId || activeCourseId;
      const data = await api.generateStudyPlan(targetId, examDate, dailyMinutes, studentId);
      setStudyPlan(data);
    } catch (e) {
      setError('Unable to generate a study plan. Set an exam date and make sure your course has concepts to review.');
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-paper-canvas p-12 space-y-4">
        <div className="relative flex items-center justify-center">
          <div className="w-12 h-12 rounded-full border-2 border-royal-200 border-t-royal-600 animate-spin" />
          <Calendar className="w-5 h-5 text-royal-600 absolute" />
        </div>
        <div className="text-center space-y-1">
          <p className="font-serif text-sm font-semibold text-ink-800">
            Computing optimal spaced repetition schedule and forgetting curve intervals...
          </p>
          <p className="text-xs text-ink-500 font-mono">
            Allocating daily review minutes against your exam milestones
          </p>
        </div>
      </div>
    );
  }

  const docCount = courseDetail?.documents?.length || 0;
  const conceptCount = courseDetail?.concepts?.length || 0;

  if ((error && !studyPlan) || (!studyPlan && !loading)) {
    if (docCount > 0 || conceptCount > 0) {
      return (
        <div className="flex-1 flex flex-col items-center justify-center bg-paper-canvas p-6 text-center space-y-4">
          <div className="p-4 rounded-2xl bg-royal-50 text-royal-700 border border-royal-200">
            <Calendar className="h-8 w-8" />
          </div>
          <div className="max-w-md space-y-2">
            <h2 className="font-serif text-xl font-bold text-ink-900">
              {courseDetail?.course?.name || 'Active Course'} Material Ready
            </h2>
            <p className="text-xs text-ink-600 leading-relaxed">
              We indexed {docCount} document(s) and {conceptCount} concept(s). Choose your target exam date and generate your adaptive study plan.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <input
              type="date"
              value={examDate}
              onChange={(e) => setExamDate(e.target.value)}
              className="px-3 py-2 rounded-xl border border-paper-hairline bg-white text-xs font-mono text-ink-900 shadow-2xs focus:outline-none"
            />
            <Button
              variant="primary"
              onClick={handleGenerate}
              disabled={generating}
              className="cursor-pointer"
            >
              <Sparkles className="h-4 w-4 mr-2" />
              <span>{generating ? 'Scheduling...' : 'Generate Study Plan'}</span>
            </Button>
          </div>
          {error && <p className="text-xs text-red-600 font-mono mt-2">{error}</p>}
        </div>
      );
    }

    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-paper-canvas p-6 text-center space-y-4">
        <div className="p-4 rounded-2xl bg-amber-50 text-amber-700 border border-amber-200">
          <Calendar className="h-8 w-8" />
        </div>
        <div className="max-w-md space-y-2">
          <h2 className="font-serif text-xl font-bold text-ink-900">No Course Material Processed Yet</h2>
          <p className="text-xs text-ink-600 leading-relaxed">
            Adaptive Study Plans calculate spaced repetition timelines based on your uploaded syllabus and upcoming exam date. Upload your materials to generate a plan.
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
    <div className="flex-1 p-6 lg:p-8 space-y-6 overflow-y-auto max-w-5xl w-full mx-auto bg-paper-canvas">
      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-900 font-serif">
          {error}
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-royal-700 bg-royal-50 px-2 py-0.5 rounded border border-royal-200">
              EBBINGHAUS FORGETTING CURVE
            </span>
            <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-highlighter-base text-ink-900 font-bold border border-ink-900/10">
              SPACED REPETITION
            </span>
          </div>
          <h1 className="font-serif text-3xl font-bold text-ink-900 tracking-tight mt-1">
            Personalized Study Schedule
          </h1>
          <p className="font-serif text-xs text-ink-600 mt-0.5">
            Optimized for exam proximity, prerequisite hierarchy, and calibrated review intervals.
          </p>
        </div>

        <Button
          variant="primary"
          onClick={handleGenerate}
          disabled={generating || !examDate}
        >
          <Sparkles className="h-4 w-4" />
          <span>{generating ? 'Re-optimizing...' : 'Calculate Schedule'}</span>
        </Button>
      </div>

      {/* Parameter Controls */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-5 rounded-2xl bg-white border border-paper-hairline shadow-paper">
        <div>
          <label className="block text-xs font-mono font-bold text-ink-800 mb-1">
            Target Exam Date:
          </label>
          <input
            type="date"
            value={examDate}
            min={new Date().toISOString().slice(0, 10)}
            onChange={(e) => setExamDate(e.target.value)}
            className="w-full px-3 py-2 text-xs font-mono rounded-xl bg-paper-surface border border-paper-hairline text-ink-900 focus:outline-none focus:ring-1 focus:ring-royal-700"
          />
        </div>

        <div>
          <div className="flex justify-between items-center mb-1 text-xs font-mono">
            <span className="font-bold text-ink-800">Daily Study Allocation:</span>
            <span className="text-royal-700 font-bold">{dailyMinutes} Minutes</span>
          </div>
          <input
            type="range"
            min={20}
            max={180}
            step={10}
            value={dailyMinutes}
            onChange={(e) => setDailyMinutes(Number(e.target.value))}
            className="w-full accent-royal-700 cursor-pointer mt-2"
          />
        </div>
      </div>

      {/* Spaced Review Callout */}
      {studyPlan?.spaced_review_alert && (
        <div className="p-4 rounded-xl bg-highlighter-soft border border-highlighter-base flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Clock className="h-5 w-5 text-royal-700 shrink-0" />
            <div>
              <div className="text-xs font-mono font-bold text-ink-900 uppercase tracking-wider">
                Forgetting Curve Notification:
              </div>
              <div className="text-xs font-serif text-ink-800 mt-0.5">
                {studyPlan.spaced_review_alert}
              </div>
            </div>
          </div>
          <span className="text-[10px] font-mono uppercase bg-highlighter-base text-ink-900 px-2.5 py-1 rounded border border-ink-900/10 font-bold shrink-0">
            Due Today
          </span>
        </div>
      )}

      {/* Schedule timeline */}
      <div className="space-y-4">
        <h3 className="font-serif text-base font-bold text-ink-900 flex items-center space-x-2">
          <Calendar className="h-4 w-4 text-royal-700" />
          <span>Upcoming Review Calendar</span>
        </h3>

        <div className="space-y-3">
          {studyPlan?.schedule?.length ? studyPlan.schedule.map((item: any, idx: number) => (
            <div
              key={idx}
              className="p-4 rounded-xl bg-white border border-paper-hairline hover:border-royal-700 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-paper-sm"
            >
              <div className="flex items-start space-x-3.5">
                <div className="px-3 py-1.5 rounded-lg bg-paper-surface border border-paper-hairline text-xs font-mono font-bold text-ink-900 text-center shrink-0">
                  {item.date ? new Date(`${item.date}T00:00:00`).toLocaleDateString([], { month: 'short', day: 'numeric' }) : item.day}
                </div>
                <div>
                  <div className="font-serif text-sm font-bold text-ink-900">{item.topic}</div>
                  <div className="font-serif text-xs text-ink-600 mt-0.5">{item.focus}</div>
                </div>
              </div>

              <div className="flex items-center space-x-3 shrink-0 font-mono text-xs">
                <span className="text-ink-700 bg-paper-surface px-2.5 py-1 rounded border border-paper-hairline font-semibold">
                  {item.duration_min} Mins
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                    item.urgency === 'Highest'
                      ? 'bg-red-50 text-red-900 border-red-200'
                      : item.urgency === 'High'
                      ? 'bg-amber-50 text-amber-900 border-amber-200'
                      : 'bg-emerald-50 text-emerald-900 border-emerald-200'
                  }`}
                >
                  {item.urgency} Priority
                </span>
              </div>
            </div>
          )) : (
            <p className="rounded-xl border border-paper-hairline bg-white p-6 text-center text-sm font-serif text-ink-500 shadow-paper-sm">
              No study schedule calculated yet. Choose your target exam date above to calculate your spaced repetition plan.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
