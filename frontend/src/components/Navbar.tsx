import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { BookOpen, RefreshCw, Flame, ChevronDown, Menu, LogOut, CheckCircle2, Sparkles } from 'lucide-react';
import { Course } from '../types';
import { useAuth } from '../context/AuthContext';

interface NavbarProps {
  courses: Course[];
  activeCourseId: string;
  onSelectCourse: (id: string) => void;
  supabaseConnected: boolean;
  onRefreshDemo: () => void;
  studentName: string;
  initials: string;
  streak: number;
  onMenuToggle: () => void;
  onOpenCreateCourse?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  courses,
  activeCourseId,
  onSelectCourse,
  supabaseConnected,
  onRefreshDemo,
  studentName,
  initials,
  streak,
  onMenuToggle,
  onOpenCreateCourse,
}) => {
  const navigate = useNavigate();
  const { signOut, user, profile } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const displayEmail = user?.email || '';
  const displayPlan = profile?.plan || 'Free Plan';

  // Deduplicate courses by name to provide a clean, organized course switcher
  const uniqueCourses = courses.filter((c, idx, arr) => 
    arr.findIndex(x => (x.name || '').trim().toLowerCase() === (c.name || '').trim().toLowerCase()) === idx
  );

  return (
    <header className="h-16 border-b border-[#EAE6DF] bg-white px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30 shadow-paper-sm">
      {/* Left: Hamburger (mobile) + StudyMind AI Brand */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-2 rounded-xl text-[#5E5A52] hover:text-[#16130F] hover:bg-[#F3EFE8] transition cursor-pointer min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Toggle navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="h-9 w-9 rounded-xl bg-[#FAF8F5] border border-[#EAE6DF] flex items-center justify-center text-[#1D4ED8] shadow-xs group-hover:border-[#FFE45C] group-hover:bg-[#FFFBEB] transition-colors shrink-0">
            <Sparkles className="h-4.5 w-4.5 text-[#1D4ED8]" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-display font-bold text-lg tracking-tight text-[#16130F]">
                StudyMind
              </span>
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-[#FFE45C] text-[#16130F] border border-[#E5C936]">
                AI
              </span>
            </div>
            <p className="text-[10px] font-mono uppercase tracking-wider text-[#7B766C] hidden md:block">
              Source-Grounded Tutor
            </p>
          </div>
        </Link>
      </div>

      {/* Center: Course Selector */}
      <div className="hidden md:flex items-center gap-2.5 max-w-md w-full mx-4">
        <div className="relative flex-1">
          <BookOpen className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#7B766C] pointer-events-none" />
          <select
            value={activeCourseId}
            onChange={(e) => onSelectCourse(e.target.value)}
            className="w-full pl-9 pr-8 py-2 text-xs rounded-xl bg-[#FAF8F5] border border-[#EAE6DF] text-[#16130F] font-medium focus:outline-none focus:border-[#1D4ED8] focus:bg-white transition cursor-pointer appearance-none min-h-[40px]"
            aria-label="Select active course"
          >
            {!activeCourseId && (
              <option value="">+ No Active Course (Upload Document)</option>
            )}
            {uniqueCourses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.semester || 'Current'})
              </option>
            ))}
          </select>
          <ChevronDown className="h-3.5 w-3.5 absolute right-3 top-1/2 -translate-y-1/2 text-[#7B766C] pointer-events-none" />
        </div>

        <button
          onClick={() => {
            if (onOpenCreateCourse) {
              onOpenCreateCourse();
            } else {
              navigate('/courses');
            }
          }}
          title="Create or manage your courses"
          className="px-3 py-2 text-xs font-semibold text-[#16130F] bg-white hover:bg-[#F3EFE8] border border-[#EAE6DF] rounded-xl flex items-center gap-1 transition shadow-xs shrink-0 cursor-pointer min-h-[40px]"
        >
          <span>+ New Course</span>
        </button>

        {/* Database state pill */}
        <div
          title={supabaseConnected ? 'Connected to Supabase PostgreSQL' : 'Using Local Persistent Store (Offline Mode)'}
          className="hidden xl:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#ECFDF5] border border-[#A7F3D0] text-[#059669] text-[11px] font-mono shrink-0"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-[#059669] animate-pulse" />
          <span>{supabaseConnected ? 'Supabase' : 'Local Disk'}</span>
        </div>
      </div>

      {/* Right: Streak, Demo Course, User Menu */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Streak Pill with Highlighter Flame */}
        {streak > 0 && (
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-full bg-[#FFFBEB] border border-[#FDE68A] text-[#16130F] font-mono font-medium text-xs">
            <Flame className="h-3.5 w-3.5 text-[#D97706] fill-[#FFE45C]" />
            <span>{streak}-Day Streak</span>
          </div>
        )}

        {/* User Avatar + Dropdown */}
        <div className="relative pl-1">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 hover:opacity-90 transition p-1 rounded-xl cursor-pointer min-h-[44px]"
            aria-label="User account menu"
            aria-expanded={showUserMenu}
          >
            <div className="h-8 w-8 rounded-full bg-[#16130F] text-[#FFE45C] font-mono flex items-center justify-center text-xs font-bold shadow-xs shrink-0 border border-[#16130F]">
              {initials || 'ST'}
            </div>
            <div className="hidden lg:block text-left">
              <div className="text-xs font-semibold text-[#16130F] truncate max-w-[120px]">
                {studentName}
              </div>
              <div className="text-[10px] font-mono text-[#7B766C] truncate max-w-[120px]">
                {displayPlan}
              </div>
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-[#7B766C] hidden sm:block" />
          </button>

          {showUserMenu && (
            <div className="absolute right-0 top-full mt-2 w-56 bg-white border border-[#EAE6DF] rounded-2xl shadow-paper-lg z-50 py-1.5 text-xs">
              <div className="px-4 py-3 border-b border-[#EAE6DF]">
                <div className="font-semibold text-[#16130F] truncate">{studentName}</div>
                <div className="text-[11px] font-mono text-[#7B766C] truncate mt-0.5">{displayEmail}</div>
                <div className="mt-2 flex items-center gap-1.5">
                  <span className="text-[10px] font-mono font-bold text-[#059669] bg-[#ECFDF5] border border-[#A7F3D0] px-2 py-0.5 rounded-full">
                    {displayPlan}
                  </span>
                  <span className="text-[10px] font-mono text-[#7B766C]">
                    Active Session
                  </span>
                </div>
              </div>

              <div className="py-1">
                <Link
                  to="/"
                  onClick={() => setShowUserMenu(false)}
                  className="w-full flex items-center px-4 py-2 text-[#5E5A52] hover:text-[#16130F] hover:bg-[#FAF8F5] transition"
                >
                  <span>Welcome / Landing Page</span>
                </Link>

                <Link
                  to="/dashboard"
                  onClick={() => setShowUserMenu(false)}
                  className="w-full flex items-center px-4 py-2 text-[#5E5A52] hover:text-[#16130F] hover:bg-[#FAF8F5] transition"
                >
                  <span>AI Tools Dashboard</span>
                </Link>

                <Link
                  to="/dashboard/library"
                  onClick={() => setShowUserMenu(false)}
                  className="w-full flex items-center px-4 py-2 text-[#5E5A52] hover:text-[#16130F] hover:bg-[#FAF8F5] transition"
                >
                  <span>Output History</span>
                </Link>

                <Link
                  to="/dashboard/my-files"
                  onClick={() => setShowUserMenu(false)}
                  className="w-full flex items-center px-4 py-2 text-[#5E5A52] hover:text-[#16130F] hover:bg-[#FAF8F5] transition"
                >
                  <span>My Ingested Files</span>
                </Link>

                <Link
                  to="/settings"
                  onClick={() => setShowUserMenu(false)}
                  className="w-full flex items-center px-4 py-2 text-[#5E5A52] hover:text-[#16130F] hover:bg-[#FAF8F5] transition"
                >
                  <span>System & AI Settings</span>
                </Link>
              </div>

              <div className="border-t border-[#EAE6DF] pt-1">
                <button
                  onClick={() => {
                    setShowUserMenu(false);
                    signOut();
                    navigate('/welcome');
                  }}
                  className="w-full flex items-center gap-2 px-4 py-2 text-[#DC2626] hover:bg-[#FEF2F2] transition cursor-pointer font-medium"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

