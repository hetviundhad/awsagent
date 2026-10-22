import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  Sparkles, Bot, GitFork, Award, LineChart, Layers, Calendar,
  FileText, UploadCloud, BookOpen, ChevronsLeft, Shield, Settings, FolderArchive,
  Lock, Plus, ChevronDown, ChevronRight, LayoutDashboard, Cpu
} from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  courses?: any[];
  activeCourseId?: string;
  onOpenCreateCourse?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  isOpen, 
  onClose,
  courses = [],
  activeCourseId = '',
  onOpenCreateCourse
}) => {
  const navigate = useNavigate();
  const [showMore, setShowMore] = useState(false);

  const activeCourse = courses.find((c) => c.id === activeCourseId) || courses[0];
  const hasActiveCourse = Boolean(activeCourse);

  // Core navigation items per C4:
  // Dashboard, Tutor, Quiz, Concept Map, Progress, Revision, Study Plan, Materials, Settings
  const coreNavItems = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, exact: true },
    { to: '/silence-studio', label: 'Silence Studio ✨ (new)', icon: Sparkles },
    { to: '/tutor', label: 'AI Tutor', icon: Bot },
    { to: '/assessments', label: 'Quizzes & Tests', icon: Award },
    { to: '/concept-map', label: 'Concept Map', icon: GitFork },
    { to: '/learner', label: 'Progress & Mastery', icon: LineChart },
    { to: '/revision', label: 'Active Revision', icon: Layers },
    { to: '/study-plan', label: 'Study Plan', icon: Calendar },
    { to: '/dashboard/my-files', label: 'Course Materials', icon: FileText },
    { to: '/settings', label: 'Settings', icon: Settings },
  ];

  // Secondary items under "More" group per C4
  const moreNavItems = [
    { to: '/courses', label: 'Course Catalog', icon: BookOpen },
    { to: '/decision-lab', label: 'Decision Lab (Decider 2B)', icon: Cpu },
    { to: '/evaluation', label: 'Eval Harness', icon: Shield },
    { to: '/dashboard/library', label: 'Output History', icon: FolderArchive },
    { to: '/upload', label: 'Upload & Video Whisper', icon: UploadCloud },
  ];

  const renderNavLink = (item: { to: string; label: string; icon: any; exact?: boolean }) => {
    const Icon = item.icon;
    return (
      <NavLink
        key={item.to}
        to={item.to}
        end={item.exact}
        onClick={onClose}
        className={({ isActive }) =>
          `flex items-center justify-between px-3 py-2 rounded-xl text-xs transition duration-150 group cursor-pointer ${
            isActive
              ? 'bg-blue-50 text-blue-700 font-bold border border-blue-200 shadow-2xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`
        }
      >
        <div className="flex items-center gap-2.5 truncate">
          <Icon className="h-4 w-4 shrink-0 transition-transform group-hover:scale-105" />
          <span className="truncate">{item.label}</span>
        </div>
      </NavLink>
    );
  };

  const sidebarContent = (
    <div className="flex flex-col h-full justify-between p-4 bg-white text-slate-900 overflow-y-auto">
      <div className="space-y-4">
        {/* Mobile Close Button Header */}
        <div className="flex items-center justify-between pb-1 px-1 lg:hidden">
          <span className="font-display font-bold text-base text-slate-900">
            StudyMind AI
          </span>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition cursor-pointer"
            title="Collapse sidebar"
          >
            <ChevronsLeft className="h-5 w-5" />
          </button>
        </div>

        {/* Active Course Banner */}
        <div className="px-3 py-2.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold flex items-center justify-between">
            <span>Active Course</span>
            {hasActiveCourse && (
              <span className="h-2 w-2 rounded-full bg-emerald-500" title="Active" />
            )}
          </div>
          <div className="text-xs font-bold text-slate-900 truncate" title={activeCourse?.name}>
            {activeCourse ? activeCourse.name : 'No Course Selected'}
          </div>
          {activeCourse?.subject && (
            <div className="text-[10px] text-slate-500 truncate">
              {activeCourse.subject}
            </div>
          )}
        </div>

        {/* Primary Navigation Menu */}
        <nav className="space-y-1">
          {coreNavItems.map(renderNavLink)}
        </nav>

        {/* "More" Group Accordion */}
        <div className="pt-2 border-t border-slate-100">
          <button
            type="button"
            onClick={() => setShowMore(!showMore)}
            className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-slate-500 hover:text-slate-800 hover:bg-slate-50 rounded-xl transition cursor-pointer"
          >
            <span>More Tools & Catalog</span>
            {showMore ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          </button>

          {showMore && (
            <div className="space-y-1 pt-1 pl-1">
              {moreNavItems.map(renderNavLink)}
            </div>
          )}
        </div>
      </div>

      {/* Footer Info */}
      <div className="pt-3 border-t border-slate-100 space-y-1 px-1">
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
          <span>Personalized Tutor</span>
          <span className="text-[10px] font-bold text-slate-800 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
            2026
          </span>
        </div>
      </div>
    </div>
  );

  return (
    <>
      <aside className="hidden lg:flex w-60 border-r border-slate-200 bg-white flex-col shrink-0 shadow-xs">
        {sidebarContent}
      </aside>

      <aside
        className={`fixed top-0 left-0 h-full w-60 bg-white border-r border-slate-200 z-50 transform transition-transform duration-300 lg:hidden shadow-xl ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {sidebarContent}
      </aside>
    </>
  );
};
