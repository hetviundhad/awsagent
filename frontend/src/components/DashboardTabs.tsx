import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Sparkles, FolderArchive, FileText, Crown, Bot, GitFork,
  Award, LineChart, Layers, Calendar, UploadCloud, BookOpen, Shield
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const DashboardTabs: React.FC = () => {
  const { user, profile } = useAuth();

  const userEmail = user?.email || '';
  const planName = profile?.plan || 'Free Plan';

  const tabs = [
    { to: '/dashboard', label: 'Study Tools', icon: Sparkles, exact: true },
    { to: '/tutor', label: 'AI Socratic Tutor', icon: Bot },
    { to: '/concept-map', label: 'Concept Map', icon: GitFork },
    { to: '/assessments', label: 'Assessments', icon: Award },
    { to: '/learner', label: 'Learner BKT', icon: LineChart },
    { to: '/revision', label: 'Revision Hub', icon: Layers },
    { to: '/study-plan', label: 'Study Plan', icon: Calendar },
    { to: '/upload', label: 'Upload Materials', icon: UploadCloud },
    { to: '/courses', label: 'Courses', icon: BookOpen },
    { to: '/evaluation', label: 'Eval Harness', icon: Shield },
    { to: '/dashboard/library', label: 'Output History', icon: FolderArchive },
    { to: '/dashboard/my-files', label: 'Course Files', icon: FileText },
  ];

  return (
    <div className="bg-white border-b border-[#EAE6DF] px-4 sm:px-6 py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-paper-sm shrink-0">
      {/* Scrollable Tabs with Hairline Styling */}
      <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-0.5">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.exact}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs transition duration-150 shrink-0 cursor-pointer ${
                  isActive
                    ? 'bg-[#EFF6FF] text-[#1D4ED8] font-bold border border-[#BFDBFE] shadow-2xs'
                    : 'text-[#5E5A52] hover:text-[#16130F] hover:bg-[#FAF8F5]'
                }`
              }
            >
              <Icon className="h-3.5 w-3.5 shrink-0" />
              <span>{tab.label}</span>
            </NavLink>
          );
        })}
      </div>

      {/* Right: User Email & Plan Badge */}
      <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
        <div className="flex items-center gap-2 bg-[#FAF8F5] border border-[#EAE6DF] px-3 py-1.5 rounded-xl shadow-xs">
          <div className="h-5 w-5 rounded-full bg-[#16130F] text-[#FFE45C] font-mono flex items-center justify-center text-[10px] font-bold">
            {userEmail[0].toUpperCase()}
          </div>
          <span className="text-xs font-mono text-[#5E5A52] truncate max-w-[140px] sm:max-w-[200px]">
            {userEmail}
          </span>
          <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-[#059669] bg-[#ECFDF5] px-2 py-0.5 rounded-full border border-[#A7F3D0]">
            <Crown className="h-2.5 w-2.5 text-[#059669]" />
            <span>{planName}</span>
          </span>
        </div>
      </div>
    </div>
  );
};
