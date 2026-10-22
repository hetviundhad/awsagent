import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Plus, Calendar, Layers, FileText, ArrowRight, X, Sparkles, Trash2, Bot, HelpCircle, CheckCircle, UploadCloud } from 'lucide-react';
import { api } from '../services/api';
import { Course } from '../types';
import { Button, Card, Pill } from '../components/ui';
import { CreateCourseModal } from '../components/CreateCourseModal';

interface CoursesPageProps {
  activeCourseId?: string;
  onSelectCourse?: (id: string) => void;
  onCoursesUpdated?: () => void;
  studentId?: string;
}

export const CoursesPage: React.FC<CoursesPageProps> = ({
  activeCourseId,
  onSelectCourse,
  onCoursesUpdated,
  studentId,
}) => {
  const navigate = useNavigate();
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [generatingCurriculumId, setGeneratingCurriculumId] = useState<string | null>(null);

  useEffect(() => {
    loadCourses();
  }, []);

  const loadCourses = async () => {
    try {
      const data = await api.getCourses();
      setCourses(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCourse = async (e: React.MouseEvent, courseId: string) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this course and all its study materials from the database?')) return;
    try {
      await api.deleteCourse(courseId);
      await loadCourses();
      onCoursesUpdated?.();
    } catch (err) {
      alert('Error deleting course');
    }
  };

  const handleGenerateCurriculum = async (e: React.MouseEvent, courseId: string) => {
    e.stopPropagation();
    setGeneratingCurriculumId(courseId);
    try {
      await api.generateCurriculum(courseId);
      await loadCourses();
      onCoursesUpdated?.();
      alert('Curriculum topics and concepts generated and saved in backend database!');
    } catch (err: any) {
      alert(`Failed to generate curriculum: ${err.message}`);
    } finally {
      setGeneratingCurriculumId(null);
    }
  };

  return (
    <div className="flex-1 p-6 lg:p-8 space-y-6 overflow-y-auto max-w-6xl w-full mx-auto bg-paper-canvas">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-royal-700 bg-royal-50 px-2 py-0.5 rounded border border-royal-200">
              ACADEMIC REPOSITORY
            </span>
            <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-highlighter-base text-ink-900 font-bold border border-ink-900/10">
              PERSISTENT DB
            </span>
          </div>
          <h1 className="font-serif text-3xl font-bold text-ink-900 tracking-tight mt-1">
            Courses & Disciplines
          </h1>
          <p className="font-serif text-xs text-ink-600 mt-0.5">
            Organize course materials across any college subject. AI generates structured topics, concept dependencies, and quizzes grounded in your uploaded files.
          </p>
        </div>

        <Button
          variant="primary"
          onClick={() => setShowCreateModal(true)}
        >
          <Plus className="h-4 w-4" />
          <span>Create New Course</span>
        </Button>
      </div>

      {loading ? (
        <div className="text-ink-500 font-serif text-xs py-12 text-center">Loading your courses from database...</div>
      ) : courses.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-white border border-paper-hairline space-y-4 shadow-paper">
          <BookOpen className="h-10 w-10 text-royal-700 mx-auto" />
          <div className="space-y-1">
            <h3 className="font-serif text-base font-bold text-ink-900">No courses created yet</h3>
            <p className="font-serif text-xs text-ink-600 max-w-md mx-auto">
              Start by creating a course. The AI tutor will generate structured topics, concepts, quizzes, and tutoring grounded directly in your syllabus materials.
            </p>
          </div>
          <Button
            variant="primary"
            onClick={() => setShowCreateModal(true)}
          >
            Create Your First Course
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {courses.map((course) => {
            const isActive = course.id === activeCourseId;
            return (
              <div
                key={course.id}
                onClick={() => {
                  if (onSelectCourse) onSelectCourse(course.id);
                  navigate(`/courses/${course.id}`);
                }}
                className={`p-5 rounded-2xl border transition-all cursor-pointer group flex flex-col justify-between space-y-4 ${
                  isActive
                    ? 'bg-white border-royal-700 ring-2 ring-royal-400/20 shadow-paper-md'
                    : 'bg-white border-paper-hairline hover:border-ink-900/30 hover:shadow-paper'
                }`}
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between font-mono">
                    <div className="flex items-center space-x-2">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded uppercase bg-paper-surface text-ink-700 border border-paper-hairline">
                        {course.subject || 'General'}
                      </span>
                      {isActive && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-highlighter-base text-ink-900 border border-ink-900/10">
                          Active
                        </span>
                      )}
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-[11px] text-ink-400">{course.semester}</span>
                      <button
                        onClick={(e) => handleDeleteCourse(e, course.id)}
                        title="Delete this course and its materials"
                        className="p-1 rounded text-ink-400 hover:text-status-refused transition"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>

                  <h3 className="font-serif text-base font-bold text-ink-900 group-hover:text-royal-700 transition-colors">
                    {course.name}
                  </h3>
                  <p className="font-serif text-xs text-ink-600 line-clamp-2 leading-relaxed">
                    {course.description || `Academic course knowledge base covering ${course.name}.`}
                  </p>
                </div>

                <div className="pt-2 border-t border-paper-hairline grid grid-cols-3 gap-2 text-center text-xs font-mono">
                  <div className="p-2 rounded-lg bg-paper-surface border border-paper-hairline">
                    <div className="font-bold text-ink-900">{course.document_count || 0}</div>
                    <div className="text-[10px] text-ink-500 font-serif">Docs</div>
                  </div>
                  <div className="p-2 rounded-lg bg-paper-surface border border-paper-hairline">
                    <div className="font-bold text-ink-900">{course.topic_count || 0}</div>
                    <div className="text-[10px] text-ink-500 font-serif">Topics</div>
                  </div>
                  <div className="p-2 rounded-lg bg-paper-surface border border-paper-hairline">
                    <div className="font-bold text-royal-700">
                      {Math.round((course.overall_mastery || 0) * 100)}%
                    </div>
                    <div className="text-[10px] text-ink-500 font-serif">Mastery</div>
                  </div>
                </div>

                {/* Quick Action Buttons */}
                <div className="pt-1 flex items-center justify-between gap-1.5 border-t border-paper-hairline/60 font-mono" onClick={(e) => e.stopPropagation()}>
                  <button
                    onClick={() => {
                      if (onSelectCourse) onSelectCourse(course.id);
                      navigate('/upload');
                    }}
                    className="flex-1 py-1.5 px-2 rounded-lg bg-paper-surface hover:bg-paper-canvas text-ink-800 hover:text-royal-700 text-[11px] font-bold flex items-center justify-center space-x-1 border border-paper-hairline transition"
                    title="Upload study materials, PDFs, PPTs, videos"
                  >
                    <UploadCloud className="h-3.5 w-3.5 text-royal-700" />
                    <span>Upload</span>
                  </button>
                  <button
                    onClick={() => {
                      if (onSelectCourse) onSelectCourse(course.id);
                      navigate('/tutor');
                    }}
                    className="flex-1 py-1.5 px-2 rounded-lg bg-paper-surface hover:bg-paper-canvas text-royal-700 text-[11px] font-bold flex items-center justify-center space-x-1 border border-paper-hairline transition"
                  >
                    <Bot className="h-3.5 w-3.5" />
                    <span>AI Tutor</span>
                  </button>
                  <button
                    onClick={() => {
                      if (onSelectCourse) onSelectCourse(course.id);
                      navigate('/assessments');
                    }}
                    className="flex-1 py-1.5 px-2 rounded-lg bg-paper-surface hover:bg-paper-canvas text-ink-800 text-[11px] font-bold flex items-center justify-center space-x-1 border border-paper-hairline transition"
                  >
                    <HelpCircle className="h-3.5 w-3.5" />
                    <span>Quiz</span>
                  </button>
                  {(!course.topic_count || course.topic_count === 0) && (
                    <button
                      onClick={(e) => handleGenerateCurriculum(e, course.id)}
                      disabled={generatingCurriculumId === course.id}
                      className="py-1.5 px-2 rounded-lg bg-highlighter-soft hover:bg-highlighter-base text-ink-900 text-[11px] font-bold flex items-center space-x-1 border border-ink-900/10 transition"
                    >
                      <Sparkles className="h-3.5 w-3.5 text-royal-700" />
                      <span>{generatingCurriculumId === course.id ? '...' : 'Syllabus'}</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Unified AI Create Course Modal */}
      <CreateCourseModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCourseCreated={() => {
          loadCourses();
          onCoursesUpdated?.();
        }}
        onSelectCourse={onSelectCourse}
        studentId={studentId}
      />
    </div>
  );
};
