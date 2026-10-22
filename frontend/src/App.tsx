import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, Link } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { OutputHistoryPage } from './pages/OutputHistoryPage';
import { MyFilesPage } from './pages/MyFilesPage';
import { QuizPlayerPage } from './pages/QuizPlayerPage';
import { CoursesPage } from './pages/CoursesPage';
import { CourseDetailPage } from './pages/CourseDetailPage';
import { UploadPage } from './pages/UploadPage';
import { TutorPage } from './pages/TutorPage';
import { AssessmentsPage } from './pages/AssessmentsPage';
import { QuizPage } from './pages/QuizPage';
import { AssessmentReportPage } from './pages/AssessmentReportPage';
import { LearnerProfilePage } from './pages/LearnerProfilePage';
import { ConceptMapPage } from './pages/ConceptMapPage';
import { RevisionPage } from './pages/RevisionPage';
import { StudyPlanPage } from './pages/StudyPlanPage';
import { EvaluationPage } from './pages/EvaluationPage';
import { DecisionLabPage } from './pages/DecisionLabPage';
import { SilenceStudioPage } from './pages/SilenceStudioPage';
import { SettingsPage } from './pages/SettingsPage';
import { CreateCourseModal } from './components/CreateCourseModal';
import { api } from './services/api';
import { Course } from './types';

const AppShell: React.FC = () => {
  const { user, profile } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  // Initialize active course immediately from localStorage
  const [activeCourseId, setActiveCourseIdState] = useState<string>(() => {
    return localStorage.getItem('studymind_active_course') || '';
  });
  const [supabaseConnected, setSupabaseConnected] = useState<boolean>(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isCreateCourseModalOpen, setIsCreateCourseModalOpen] = useState(false);
  const [aiHealth, setAiHealth] = useState<{
    llm_ok: boolean;
    model: string;
    embedding_ok: boolean;
    vision_ok: boolean;
    vision_reason?: string | null;
    stt_ok: boolean;
    error: string | null;
  } | null>(null);

  const [bannerDismissed, setBannerDismissed] = useState<boolean>(false);

  const checkAiHealth = async () => {
    try {
      const health = await api.getAiHealth();
      setAiHealth(health);
    } catch (e: any) {
      setAiHealth({
        llm_ok: false,
        model: 'unknown',
        embedding_ok: false,
        vision_ok: false,
        stt_ok: false,
        error: e.message || 'AI service check failed',
      });
    }
  };

  useEffect(() => {
    checkAiHealth();
    loadInitialState();
  }, []);

  const getUserCourseKey = () => user?.id ? `studymind_active_course_${user.id}` : 'studymind_active_course';

  const handleSelectCourse = (id: string) => {
    setActiveCourseIdState(id);
    const key = getUserCourseKey();
    if (id) {
      localStorage.setItem(key, id);
      localStorage.setItem('studymind_active_course', id);
    } else {
      localStorage.removeItem(key);
      localStorage.removeItem('studymind_active_course');
      if (user?.id) localStorage.removeItem(`studymind_chose_demo_${user.id}`);
    }
  };

  useEffect(() => {
    loadInitialState();
  }, [user]);

  const loadInitialState = async () => {
    try {
      const [coursesData, settingsData] = await Promise.all([
        api.getCourses(),
        api.getSettings(),
      ]);
      setCourses(coursesData);

      // Restore active course:
      // Select saved course if available, otherwise default to first available course so course desk is unlocked.
      if (coursesData.length > 0) {
        const userCourseKey = user?.id ? `studymind_active_course_${user.id}` : null;
        const savedCourseId = (userCourseKey ? localStorage.getItem(userCourseKey) : null) || localStorage.getItem('studymind_active_course');
        const found = savedCourseId ? coursesData.find((c: Course) => c.id === savedCourseId) : null;
        const targetId = found ? found.id : coursesData[0].id;
        setActiveCourseIdState(targetId);
        if (userCourseKey) localStorage.setItem(userCourseKey, targetId);
        localStorage.setItem('studymind_active_course', targetId);
      } else {
        setActiveCourseIdState('');
      }

      setSupabaseConnected(settingsData.supabase_connected);
    } catch (e) {
      console.error('Could not connect to backend:', e);
    }
  };

  const handleRefreshDemo = async () => {
    try {
      await api.loadSampleCourse();
      await loadInitialState();
      alert('Sample course loaded successfully from fixtures (Sample data)!');
    } catch (e) {
      alert('Failed to load sample course');
    }
  };

  // Derive student name and initials from profile
  const studentName = profile?.full_name || user?.email?.split('@')[0] || 'Student';
  const initials = studentName
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
  const studentId = user?.id || '';

  const location = useLocation();
  const isQuizView = location.pathname.startsWith('/quiz');

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#FAF8F5] text-slate-800 font-sans">
      {!isQuizView && (
        <Navbar
          courses={courses}
          activeCourseId={activeCourseId}
          onSelectCourse={handleSelectCourse}
          supabaseConnected={supabaseConnected}
          onRefreshDemo={handleRefreshDemo}
          studentName={studentName}
          initials={initials}
          streak={profile?.streak || 0}
          onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
          onOpenCreateCourse={() => setIsCreateCourseModalOpen(true)}
        />
      )}

      {/* System Status Banner: compact, only when something is wrong or degraded, dismissible, with link to Settings */}
      {aiHealth && !bannerDismissed && (!aiHealth.llm_ok || !aiHealth.embedding_ok) && (
        <div className="bg-red-600 text-white px-4 py-1.5 text-xs font-mono flex items-center justify-between shrink-0 shadow-sm z-50">
          <div className="flex items-center gap-2">
            <span className="font-bold uppercase tracking-wider bg-red-800 px-1.5 py-0.5 rounded text-[10px]">
              AI DEGRADED
            </span>
            <span>
              {aiHealth.error || 'AI services degraded (LLM or embeddings unavailable)'}.
            </span>
            <Link to="/settings" className="underline font-bold text-white hover:text-white/80 ml-1">
              Check Settings
            </Link>
          </div>
          <button
            onClick={() => setBannerDismissed(true)}
            className="text-white/80 hover:text-white cursor-pointer text-base font-bold leading-none px-1"
            title="Dismiss notice"
          >
            &times;
          </button>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar 
          isOpen={sidebarOpen} 
          onClose={() => setSidebarOpen(false)} 
          courses={courses}
          activeCourseId={activeCourseId}
        />

        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-20 bg-slate-900/40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <main className="flex-1 overflow-hidden flex flex-col relative bg-[#FAF8F5]">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            {/* AI Tools Suite requested by user */}
            <Route 
              path="/dashboard" 
              element={
                <DashboardPage 
                  activeCourseId={activeCourseId} 
                  studentId={studentId} 
                  studentName={studentName} 
                  onSelectCourse={handleSelectCourse} 
                  onCoursesUpdated={loadInitialState} 
                  courses={courses}
                />
              } 
            />
            <Route path="/dashboard/my-files" element={<MyFilesPage activeCourseId={activeCourseId} courses={courses} />} />
            <Route path="/dashboard/library" element={<OutputHistoryPage />} />
            <Route path="/history" element={<Navigate to="/dashboard/library" replace />} />
            <Route path="/quiz" element={<QuizPlayerPage />} />

            {/* Shortcuts */}
            <Route path="/library" element={<Navigate to="/dashboard/library" replace />} />
            <Route path="/my-files" element={<Navigate to="/dashboard/my-files" replace />} />

            {/* Deep Learning Modules */}
            <Route path="/courses" element={<CoursesPage activeCourseId={activeCourseId} onSelectCourse={handleSelectCourse} onCoursesUpdated={loadInitialState} studentId={studentId} />} />
            <Route path="/courses/:id" element={<CourseDetailPage activeCourseId={activeCourseId} onSelectCourse={handleSelectCourse} />} />
            <Route path="/upload" element={<UploadPage courses={courses} activeCourseId={activeCourseId} />} />
            <Route path="/tutor" element={<TutorPage courses={courses} activeCourseId={activeCourseId} studentId={studentId} studentName={studentName} />} />
            <Route path="/assessments" element={<AssessmentsPage courses={courses} activeCourseId={activeCourseId} studentId={studentId} />} />
            <Route path="/assessments/:id" element={<QuizPage />} />
            <Route path="/assessments/:id/report" element={<AssessmentReportPage />} />
            <Route path="/learner" element={<LearnerProfilePage activeCourseId={activeCourseId} studentId={studentId} />} />
            <Route path="/progress" element={<LearnerProfilePage activeCourseId={activeCourseId} studentId={studentId} />} />
            <Route path="/concept-map" element={<ConceptMapPage activeCourseId={activeCourseId} studentId={studentId} />} />
            <Route path="/revision" element={<RevisionPage activeCourseId={activeCourseId} studentId={studentId} />} />
            <Route path="/study-plan" element={<StudyPlanPage activeCourseId={activeCourseId} studentId={studentId} />} />
            <Route path="/evaluation" element={<EvaluationPage activeCourseId={activeCourseId} />} />
            <Route path="/decision-lab" element={<DecisionLabPage activeCourseId={activeCourseId} />} />
            <Route path="/silence-studio" element={<SilenceStudioPage activeCourseId={activeCourseId} />} />
            <Route path="/silence" element={<Navigate to="/silence-studio" replace />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </main>
      </div>

      {/* Global AI Course Creator Modal accessible from navbar or any desk */}
      <CreateCourseModal
        isOpen={isCreateCourseModalOpen}
        onClose={() => setIsCreateCourseModalOpen(false)}
        onCourseCreated={loadInitialState}
        onSelectCourse={handleSelectCourse}
        studentId={studentId}
      />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Welcome / Landing Page on root localhost */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/welcome" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
