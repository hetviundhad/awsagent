import React from 'react';
import { BookOpen, Sparkles, Plus, Award, Bot, GitFork } from 'lucide-react';
import { Course } from '../../types';

interface CourseHeaderProps {
  course: Course | null;
  docCount: number;
  conceptCount: number;
  onOpenQuiz: () => void;
  onOpenTutor: () => void;
  onOpenConceptMap: () => void;
  onOpenCreateCourse: () => void;
}

export const CourseHeader: React.FC<CourseHeaderProps> = ({
  course,
  docCount,
  conceptCount,
  onOpenQuiz,
  onOpenTutor,
  onOpenConceptMap,
  onOpenCreateCourse,
}) => {
  if (!course) {
    return (
      <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Welcome to StudyMind AI</h1>
          <p className="text-xs text-slate-500 mt-1">
            Create or select a course desk to begin personalized, grounded learning.
          </p>
        </div>
        <button
          onClick={onOpenCreateCourse}
          className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition shadow-xs flex items-center gap-2 cursor-pointer"
        >
          <Plus className="h-4 w-4" />
          <span>Create Course</span>
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-3xl p-6 border border-slate-200 shadow-xs space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
              {course.subject || 'Academic Course'}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            {course.name}
          </h1>
          <div className="text-xs font-mono text-slate-500 mt-1">
            {docCount} document{docCount !== 1 ? 's' : ''} • {conceptCount} concept{conceptCount !== 1 ? 's' : ''}
          </div>
        </div>

        {/* Quick action buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={onOpenTutor}
            className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs transition flex items-center gap-1.5 cursor-pointer"
          >
            <Bot className="h-4 w-4 text-blue-600" />
            <span>Ask Tutor</span>
          </button>
          <button
            onClick={onOpenQuiz}
            className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition shadow-xs flex items-center gap-1.5 cursor-pointer"
          >
            <Award className="h-4 w-4" />
            <span>Take Quiz</span>
          </button>
          <button
            onClick={onOpenConceptMap}
            className="px-4 py-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold text-xs transition flex items-center gap-1.5 cursor-pointer"
          >
            <GitFork className="h-4 w-4 text-purple-600" />
            <span>Concept Map</span>
          </button>
        </div>
      </div>
    </div>
  );
};
