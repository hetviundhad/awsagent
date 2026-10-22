import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { api } from '../services/api';
import { Course, LearnerProfile, Citation } from '../types';
import { QuizModal, DocumentItem } from '../components/QuizModal';
import { SourceViewerModal } from '../components/SourceViewerModal';
import { CourseHeader } from '../components/dashboard/CourseHeader';
import { ContinueLearningCard } from '../components/dashboard/ContinueLearningCard';
import { MasterySummaryCard } from '../components/dashboard/MasterySummaryCard';
import { DueReviewsCard } from '../components/dashboard/DueReviewsCard';
import { DocumentCardGrid } from '../components/dashboard/DocumentCardGrid';
import { CreateCourseModal } from '../components/CreateCourseModal';

interface DashboardPageProps {
  activeCourseId: string;
  studentId: string;
  studentName: string;
  onSelectCourse: (id: string) => void;
  onCoursesUpdated: () => void;
  courses: Course[];
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  activeCourseId,
  studentId,
  studentName,
  onSelectCourse,
  onCoursesUpdated,
  courses,
}) => {
  const navigate = useNavigate();
  const location = useLocation();

  const activeCourse = courses.find((c) => c.id === activeCourseId) || courses[0] || null;

  // Real data states
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [concepts, setConcepts] = useState<any[]>([]);
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [dueReviewsCount, setDueReviewsCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);

  // Modals state
  const [isQuizModalOpen, setIsQuizModalOpen] = useState(false);
  const [isCreateCourseOpen, setIsCreateCourseOpen] = useState(false);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);

  // Load real data for the active course and logged-in user
  const loadDashboardData = async () => {
    if (!activeCourse) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [docsData, conceptsData, profileData, reviewsData] = await Promise.all([
        api.getUserDocuments(activeCourse.id).catch(() => []),
        api.getConcepts(activeCourse.id).catch(() => []),
        api.getLearnerMastery(studentId || 'default_student').catch(() => null),
        api.getDueFlashcards(activeCourse.id).catch(() => []),
      ]);

      setDocuments(docsData || []);
      setConcepts(conceptsData || []);
      setProfile(profileData || null);
      setDueReviewsCount(Array.isArray(reviewsData) ? reviewsData.length : 0);
    } catch (e) {
      console.warn('Dashboard data fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, [activeCourse?.id, studentId]);

  // Open create course if triggered from state
  useEffect(() => {
    if ((location.state as any)?.openCreateCourse) {
      setIsCreateCourseOpen(true);
    }
  }, [location.state]);

  // Derive weakest concept for Continue Learning
  const weakestConcept = React.useMemo(() => {
    if (!concepts || concepts.length === 0) return null;
    const conceptStates = profile?.concept_states || {};
    
    // Sort concepts by lowest mastery probability
    const sorted = [...concepts].sort((a, b) => {
      const pA = conceptStates[a.id]?.mastery_probability ?? 0.1;
      const pB = conceptStates[b.id]?.mastery_probability ?? 0.1;
      return pA - pB;
    });

    const lowest = sorted[0];
    const p = conceptStates[lowest.id]?.mastery_probability ?? 0.15;
    return { name: lowest.name, mastery_probability: p };
  }, [concepts, profile]);

  // Handle Document Card actions
  const handleOpenDocViewer = (docId: string) => {
    const doc = documents.find(d => d.id === docId);
    if (doc) {
      setActiveCitation({
        citation_index: 1,
        chunk_id: doc.id,
        document_name: doc.name,
        document_title: doc.name,
        page: 1,
        page_or_slide: 'Page 1',
        snippet: `Opening document: ${doc.name}. Verified course content indexed.`,
        quote: `Opening document: ${doc.name}. Verified course content indexed.`,
        source_type: 'pdf',
      });
    }
  };

  const handleAskTutor = (topicOrDocName: string) => {
    navigate(`/tutor?concept=${encodeURIComponent(topicOrDocName)}`);
  };

  const handleQuizCreated = (quizData: any) => {
    navigate('/quiz', { state: quizData });
  };

  return (
    <div className="flex-1 flex flex-col bg-[#FAF8F5] overflow-y-auto">
      <div className="flex-1 p-4 sm:p-6 lg:p-8 space-y-6 max-w-6xl w-full mx-auto">
        
        {/* 1. COURSE HEADER */}
        <CourseHeader
          course={activeCourse}
          docCount={documents.length}
          conceptCount={concepts.length}
          onOpenQuiz={() => setIsQuizModalOpen(true)}
          onOpenTutor={() => navigate('/tutor')}
          onOpenConceptMap={() => navigate('/concept-map')}
          onOpenCreateCourse={() => setIsCreateCourseOpen(true)}
        />

        {/* 2. CONTINUE LEARNING (Next Recommended Action from Real Mastery) */}
        <ContinueLearningCard
          weakestConcept={weakestConcept}
          onTargetedQuiz={(concept) => setIsQuizModalOpen(true)}
          onAskTutor={handleAskTutor}
        />

        {/* 3. MASTERY SUMMARY & DUE REVIEWS GRID */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <MasterySummaryCard
            profile={profile}
            totalConcepts={concepts.length}
          />
          <DueReviewsCard
            dueCount={dueReviewsCount}
            onStartReview={() => navigate('/revision')}
          />
        </div>

        {/* 4. COURSE MATERIALS (DOCUMENT CARDS WITH DOCUMENT'S OWN CONCEPTS) */}
        <DocumentCardGrid
          documents={documents}
          onOpenQuizModalWithDoc={() => setIsQuizModalOpen(true)}
          onAskTutorWithDoc={handleAskTutor}
          onOpenDocumentViewer={handleOpenDocViewer}
          onUploadClick={() => setIsCreateCourseOpen(true)}
        />

      </div>

      {/* QUIZ MODAL */}
      <QuizModal
        isOpen={isQuizModalOpen}
        onClose={() => setIsQuizModalOpen(false)}
        activeCourse={activeCourse}
        userDocuments={documents}
        onQuizCreated={handleQuizCreated}
        onDocumentUploaded={loadDashboardData}
      />

      {/* CREATE COURSE MODAL */}
      <CreateCourseModal
        isOpen={isCreateCourseOpen}
        onClose={() => setIsCreateCourseOpen(false)}
        onCourseCreated={() => {
          onCoursesUpdated();
          loadDashboardData();
        }}
      />

      {/* DOCUMENT VIEWER MODAL */}
      {activeCitation && (
        <SourceViewerModal
          citation={activeCitation}
          onClose={() => setActiveCitation(null)}
        />
      )}
    </div>
  );
};
