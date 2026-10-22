import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  BookOpen, UploadCloud, Bot, HelpCircle, Layers, 
  FileText, Presentation, Video, Image as ImageIcon, ArrowLeft, CheckCircle 
} from 'lucide-react';
import { api } from '../services/api';
import { Course, CourseUnit, DocumentItem } from '../types';
import { Button, Card, Pill } from '../components/ui';

interface CourseDetailPageProps {
  activeCourseId?: string;
  onSelectCourse?: (id: string) => void;
}

export const CourseDetailPage: React.FC<CourseDetailPageProps> = ({
  activeCourseId,
  onSelectCourse,
}) => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [course, setCourse] = useState<Course | null>(null);
  const [units, setUnits] = useState<CourseUnit[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [topics, setTopics] = useState<any[]>([]);
  const [overallMastery, setOverallMastery] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      loadDetail(id);
    }
  }, [id]);

  const loadDetail = async (courseId: string) => {
    try {
      const data = await api.getCourse(courseId);
      setCourse(data.course);
      setUnits(data.units || []);
      setDocuments(data.documents || []);
      setTopics(data.topics || []);
      setOverallMastery(data.overall_mastery || 0);

      if (!activeCourseId && onSelectCourse) {
        onSelectCourse(courseId);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const isActive = id && activeCourseId === id;

  const handleMakeActive = () => {
    if (id && onSelectCourse) {
      onSelectCourse(id);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-paper-canvas text-ink-500 font-serif text-xs">
        Loading course syllabus and materials...
      </div>
    );
  }

  if (!course) {
    return (
      <div className="flex-1 p-8 max-w-md mx-auto flex flex-col items-center justify-center text-center space-y-4 my-auto">
        <h2 className="text-xl font-bold text-ink-900 font-serif">Course Not Found</h2>
        <p className="text-xs text-ink-600 font-serif">
          The requested course could not be loaded. Please return to the catalog or create a new course desk.
        </p>
        <Button variant="primary" onClick={() => navigate('/courses')}>
          <ArrowLeft className="h-4 w-4 mr-1.5" />
          <span>Back to Courses</span>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 lg:p-8 space-y-6 overflow-y-auto max-w-7xl w-full mx-auto bg-paper-canvas">
      {/* Header */}
      <div className="space-y-3">
        <button
          onClick={() => navigate('/courses')}
          className="flex items-center space-x-1.5 text-xs font-mono font-bold text-royal-700 hover:text-royal-900 transition"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to courses</span>
        </button>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 font-mono">
              <span className="text-[10px] uppercase font-bold text-royal-700 bg-royal-50 px-2 py-0.5 rounded border border-royal-200">
                {course.subject || 'Academic Course'} • {course.semester || 'Undergraduate • 2026'}
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-highlighter-base text-ink-900 border border-ink-900/10 font-bold">
                Mastery: {overallMastery}%
              </span>
              {isActive ? (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-ink-900 text-white">
                  Active Workspace
                </span>
              ) : (
                <button
                  onClick={handleMakeActive}
                  className="text-[10px] font-semibold px-2.5 py-0.5 rounded bg-paper-surface hover:bg-paper-canvas text-ink-700 border border-paper-hairline transition cursor-pointer"
                >
                  Set as Active
                </button>
              )}
            </div>
            <h1 className="font-serif text-3xl font-bold text-ink-900 tracking-tight mt-1.5">
              {course.name || 'Course Curriculum Workspace'}
            </h1>
            <p className="font-serif text-xs text-ink-600 max-w-2xl mt-1 leading-relaxed">
              {course.description || 'Comprehensive curriculum workspace and grounding materials.'}
            </p>
          </div>

          <div className="flex items-center space-x-3 font-mono">
            <Button
              variant="secondary"
              onClick={() => {
                if (id && onSelectCourse) onSelectCourse(id);
                navigate('/upload');
              }}
            >
              <UploadCloud className="h-4 w-4 text-royal-700" />
              <span>Upload Materials</span>
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                if (id && onSelectCourse) onSelectCourse(id);
                navigate('/tutor');
              }}
            >
              <Bot className="h-4 w-4" />
              <span>Open AI Tutor</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Grid: Units & Syllabus Structure */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Syllabus Units */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="font-serif text-base font-bold text-ink-900 flex items-center space-x-2">
            <Layers className="h-4 w-4 text-royal-700" />
            <span>Course Units & Learning Outcomes</span>
          </h2>

          <div className="space-y-3 font-serif">
            {units.length > 0 ? (
              units.map((unit) => (
                <div
                  key={unit.id}
                  className="p-4 sm:p-5 rounded-2xl bg-white border border-paper-hairline hover:border-royal-700 transition space-y-1 shadow-paper-sm"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-ink-900">{unit.title}</h3>
                    <span className="font-mono text-[10px] text-royal-700 bg-royal-50 px-2 py-0.5 rounded border border-royal-200 font-bold">
                      Unit {unit.unit_number}
                    </span>
                  </div>
                  <p className="text-xs text-ink-600 leading-relaxed">{unit.description}</p>
                </div>
              ))
            ) : (
              <div className="p-8 rounded-2xl bg-white border border-paper-hairline text-center text-xs text-ink-500 shadow-paper-sm">
                Units automatically extracted during multimodal document ingestion.
              </div>
            )}
          </div>
        </div>

        {/* Right: Ingested Multimodal Files */}
        <div className="space-y-4">
          <h2 className="font-serif text-base font-bold text-ink-900 flex items-center space-x-2">
            <FileText className="h-4 w-4 text-royal-700" />
            <span>Ingested Documents & Media</span>
          </h2>

          <div className="space-y-3 font-serif">
            {documents.length > 0 ? (
              documents.map((doc) => (
                <div
                  key={doc.id}
                  className="p-3.5 rounded-xl bg-white border border-paper-hairline flex items-center justify-between shadow-paper-sm"
                >
                  <div className="flex items-center space-x-2.5">
                    <div className="p-2 rounded-lg bg-paper-surface border border-paper-hairline">
                      {doc.file_type === 'slide' && <Presentation className="h-4 w-4 text-royal-700" />}
                      {doc.file_type === 'video' && <Video className="h-4 w-4 text-amber-700" />}
                      {doc.file_type === 'pdf' && <FileText className="h-4 w-4 text-emerald-700" />}
                      {doc.file_type === 'image' && <ImageIcon className="h-4 w-4 text-ink-800" />}
                      {doc.file_type !== 'slide' && doc.file_type !== 'video' && doc.file_type !== 'pdf' && doc.file_type !== 'image' && (
                        <FileText className="h-4 w-4 text-royal-700" />
                      )}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-ink-900 line-clamp-1">
                        {doc.filename || (doc as any).name || 'Course Document'}
                      </div>
                      <div className="font-mono text-[10px] text-ink-500">
                        {doc.page_count ? `${doc.page_count} Pages` : ''}
                        {doc.slide_count ? `${doc.slide_count} Slides` : ''}
                        {doc.duration_seconds ? `${Math.floor(doc.duration_seconds/60)} Mins` : ''}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-1 font-mono text-[10px] text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-bold">
                    <CheckCircle className="h-3 w-3 text-emerald-600" />
                    <span>Indexed</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-6 rounded-xl bg-white border border-paper-hairline text-center text-xs text-ink-500 shadow-paper-sm">
                No files uploaded yet. Upload slides or PDFs to ground your tutor.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
