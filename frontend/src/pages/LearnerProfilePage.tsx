import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  LineChart, Brain, CheckCircle, AlertTriangle, ArrowRight, 
  HelpCircle, RefreshCw, Zap, ShieldCheck 
} from 'lucide-react';
import { api } from '../services/api';
import { LearnerProfile } from '../types';
import { Button, Card, Pill, MasteryRing } from '../components/ui';

interface LearnerProfilePageProps {
  activeCourseId: string;
  studentId?: string;
}

export const LearnerProfilePage: React.FC<LearnerProfilePageProps> = ({ 
  activeCourseId, 
  studentId = 'default_student' 
}) => {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const effectiveCourseId = activeCourseId || localStorage.getItem('studymind_active_course') || '';

  useEffect(() => {
    loadProfile();
  }, [effectiveCourseId, studentId]);

  const loadProfile = async () => {
    setLoading(true);
    try {
      let targetId = effectiveCourseId;
      if (!targetId) {
        const cList = await api.getCourses().catch(() => []);
        if (cList && cList.length > 0) {
          targetId = cList[0].id;
          localStorage.setItem('studymind_active_course', targetId);
        }
      }
      const data = await api.getLearnerMastery(studentId, targetId || undefined);
      setProfile(data);
    } catch (e) {
      console.error(e);
      setProfile(null);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-paper-canvas p-12 space-y-4">
        <div className="relative flex items-center justify-center">
          <div className="w-12 h-12 rounded-full border-2 border-royal-200 border-t-royal-600 animate-spin" />
          <Brain className="w-5 h-5 text-royal-600 absolute" />
        </div>
        <div className="text-center space-y-1">
          <p className="font-serif text-sm font-semibold text-ink-800">
            Computing Bayesian Knowledge Tracing parameters...
          </p>
          <p className="text-xs text-ink-500 font-mono">
            Calibrating mastery probabilities P(L), slip, and guess states across concepts
          </p>
        </div>
      </div>
    );
  }

  if (!profile || !profile.mastery_by_concept || profile.mastery_by_concept.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-paper-canvas p-6 text-center space-y-4">
        <div className="p-4 rounded-2xl bg-amber-50 text-amber-700 border border-amber-200">
          <LineChart className="h-8 w-8" />
        </div>
        <div className="max-w-md space-y-2">
          <h2 className="font-serif text-xl font-bold text-ink-900">No Course Material Processed Yet</h2>
          <p className="text-xs text-ink-600 leading-relaxed">
            Learner BKT Analytics tracks mastery progression across concepts extracted from your uploaded course material. Upload a syllabus or lecture PDF to start tracking.
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
    <div className="flex-1 p-6 lg:p-8 space-y-6 overflow-y-auto max-w-7xl w-full mx-auto bg-paper-canvas">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-royal-700 bg-royal-50 px-2 py-0.5 rounded border border-royal-200">
              BAYESIAN KNOWLEDGE TRACING (BKT)
            </span>
            <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-highlighter-base text-ink-900 font-bold border border-ink-900/10">
              COGNITIVE MODEL
            </span>
          </div>
          <h1 className="font-serif text-3xl font-bold text-ink-900 tracking-tight mt-1">
            Learner Profile Matrix
          </h1>
          <p className="font-serif text-xs text-ink-600 mt-0.5">
            Dynamic inference of mastery probability P(L_t), slip P(S), and guess P(G) across your course syllabus.
          </p>
        </div>

        <Button
          variant="primary"
          onClick={() => navigate('/assessments')}
        >
          <Zap className="h-4 w-4" />
          <span>Take Diagnostic Assessment</span>
        </Button>
      </div>

      {/* Concept Matrix Table */}
      <div className="p-6 rounded-2xl bg-white border border-paper-hairline space-y-4 shadow-paper">
        <div className="flex items-center justify-between border-b border-paper-hairline pb-3">
          <h3 className="font-serif text-base font-bold text-ink-900 flex items-center space-x-2">
            <Brain className="h-4 w-4 text-royal-700" />
            <span>Concept Mastery & Bayesian Parameters</span>
          </h3>
          <span className="font-mono text-xs text-ink-500">
            {profile?.mastery_by_concept.length} Tracked Concepts
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-paper-hairline text-ink-500 font-semibold bg-paper-surface">
                <th className="py-2.5 px-3 rounded-l-lg font-serif">Concept Node</th>
                <th className="py-2.5 px-3">Module</th>
                <th className="py-2.5 px-3">Mastery P(L_t)</th>
                <th className="py-2.5 px-3">Confidence</th>
                <th className="py-2.5 px-3">Attempts (C/I)</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3 text-right rounded-r-lg">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-paper-hairline">
              {profile?.mastery_by_concept.map((rec) => {
                const pct = Math.round(rec.mastery_probability * 100);
                return (
                  <tr key={rec.concept_id} className="hover:bg-paper-surface/60 transition">
                    <td className="py-3 px-3 font-serif font-bold text-ink-900">
                      {rec.concept_name}
                    </td>
                    <td className="py-3 px-3 text-ink-500 font-serif">
                      {rec.topic_name}
                    </td>
                    <td className="py-3 px-3">
                      <div className="flex items-center space-x-2">
                        <div className="w-20 bg-paper-hairline h-2 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              pct >= 70
                                ? 'bg-emerald-600'
                                : pct >= 45
                                ? 'bg-amber-500'
                                : 'bg-status-refused'
                            }`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="text-ink-900 font-bold">{pct}%</span>
                      </div>
                    </td>
                    <td className="py-3 px-3 text-ink-600">
                      {Math.round(rec.confidence * 100)}%
                    </td>
                    <td className="py-3 px-3 text-ink-500">
                      {rec.attempt_count} ({rec.correct_count} / {rec.incorrect_count})
                    </td>
                    <td className="py-3 px-3">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                          rec.status === 'Mastered'
                            ? 'bg-emerald-50 text-emerald-900 border-emerald-300'
                            : rec.status === 'Developing'
                            ? 'bg-amber-50 text-amber-900 border-amber-300'
                            : 'bg-red-50 text-red-900 border-red-300'
                        }`}
                      >
                        {rec.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={() => navigate(`/tutor?concept=${encodeURIComponent(rec.concept_name)}&mode=Practice%20Mode`)}
                        className="text-xs text-royal-700 hover:text-royal-900 font-bold px-2.5 py-1 rounded-lg bg-paper-surface hover:bg-paper-canvas border border-paper-hairline hover:border-royal-700 transition"
                      >
                        Practice
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
