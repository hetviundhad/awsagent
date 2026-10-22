import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  UploadCloud,
  X,
  RefreshCw,
  AlertCircle,
  ArrowRight,
  BookOpen,
  CheckCircle,
  Layers,
} from 'lucide-react';
import { api } from '../services/api';
import { Course } from '../types';

interface CreateCourseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCourseCreated?: (course: Course) => void;
  onSelectCourse?: (id: string) => void;
  studentId?: string;
  initialTopic?: string;
  initialFiles?: File[];
  initialSubject?: string;
}

export const CreateCourseModal: React.FC<CreateCourseModalProps> = ({
  isOpen,
  onClose,
  onCourseCreated,
  onSelectCourse,
  studentId,
  initialTopic,
  initialFiles,
  initialSubject,
}) => {
  const navigate = useNavigate();

  const [courseSourceType, setCourseSourceType] = useState<'topic' | 'notes' | 'file'>('topic');
  const [courseTopic, setCourseTopic] = useState('');
  const [courseNotes, setCourseNotes] = useState('');
  const [courseFiles, setCourseFiles] = useState<File[]>([]);
  const [courseSubject, setCourseSubject] = useState('Computer Science');
  const [courseDifficulty, setCourseDifficulty] = useState('Undergraduate');
  const [courseUnitsCount, setCourseUnitsCount] = useState(4);
  const [courseFocusAreas, setCourseFocusAreas] = useState('');

  const [isCreatingCourse, setIsCreatingCourse] = useState(false);
  const [courseCreationStage, setCourseCreationStage] = useState(1);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [courseError, setCourseError] = useState<string | null>(null);
  const [createdCourseResult, setCreatedCourseResult] = useState<any | null>(null);

  React.useEffect(() => {
    let timer: any;
    if (isCreatingCourse) {
      setElapsedSeconds(0);
      timer = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isCreatingCourse]);

  React.useEffect(() => {
    if (isOpen) {
      if (initialTopic) setCourseTopic(initialTopic);
      if (initialFiles && initialFiles.length > 0) {
        setCourseFiles(initialFiles);
        setCourseSourceType('file');
      }
      if (initialSubject) setCourseSubject(initialSubject);
    }
  }, [isOpen, initialTopic, initialFiles, initialSubject]);

  if (!isOpen) return null;

  const handleAddCourseFiles = (filesList: FileList | File[]) => {
    const incoming = Array.from(filesList);
    setCourseFiles((prev) => {
      const existingNames = new Set(prev.map((f) => f.name));
      const filtered = incoming.filter((f) => !existingNames.has(f.name));
      return [...prev, ...filtered].slice(0, 10);
    });
    if (!courseTopic && incoming.length > 0) {
      const cleanName = incoming[0].name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
      setCourseTopic(cleanName);
    }
  };

  const handleRemoveCourseFile = (idx: number) => {
    setCourseFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const resetForm = () => {
    setCreatedCourseResult(null);
    setCourseTopic('');
    setCourseNotes('');
    setCourseFiles([]);
    setCourseFocusAreas('');
    setCourseError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleCreateStructuredCourse = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const effectiveTopic = (
      courseTopic.trim() ||
      (courseFiles.length > 0
        ? courseFiles[0].name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ')
        : '') ||
      'Academic Course Desk'
    ).trim();

    if (!effectiveTopic) {
      setCourseError('Please select a file or enter a course topic.');
      return;
    }

    setCourseError(null);
    setIsCreatingCourse(true);
    setCourseCreationStage(1);

    try {
      const formData = new FormData();
      formData.append('topic', effectiveTopic);
      formData.append('subject', courseSubject);
      formData.append('difficulty', courseDifficulty);
      formData.append('num_units', String(courseUnitsCount));
      if (courseNotes.trim()) formData.append('notes', courseNotes.trim());
      if (courseFocusAreas.trim()) formData.append('focus_areas', courseFocusAreas.trim());

      courseFiles.forEach((f) => {
        formData.append('files', f);
      });
      if (courseFiles.length > 0) {
        formData.append('file', courseFiles[0]);
      }

      const result = await api.createStructuredCourse(formData);
      setCourseCreationStage(4);

      if (result?.course?.id) {
        setCreatedCourseResult(result);

        // Persist to user storage
        if (studentId) {
          const userKey = `studymind_created_courses_${studentId}`;
          const current = JSON.parse(localStorage.getItem(userKey) || '[]');
          if (!current.includes(result.course.id)) current.push(result.course.id);
          localStorage.setItem(userKey, JSON.stringify(current));

          localStorage.setItem(`studymind_active_course_${studentId}`, result.course.id);
        }
        localStorage.setItem('studymind_active_course', result.course.id);

        onSelectCourse?.(result.course.id);
        onCourseCreated?.(result.course);
      }
    } catch (err: any) {
      setCourseError(err.message || 'Failed to create course. Please try again.');
    } finally {
      setIsCreatingCourse(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-xl w-full p-6 sm:p-7 space-y-4 shadow-2xl relative max-h-[92vh] overflow-y-auto">
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Header */}
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#1D4ED8] bg-[#EFF6FF] px-2 py-0.5 rounded border border-[#BFDBFE]">
              COURSE ARCHITECT
            </span>
            <span className="text-[10px] font-mono text-[#7B766C] bg-[#FAF8F5] px-2 py-0.5 rounded border border-[#EAE6DF]">
              Adaptive Curriculum Engine
            </span>
          </div>
          <h2 className="text-xl font-bold text-[#16130F] mt-1.5 font-sans">
            {createdCourseResult ? 'Course Desk Created Successfully!' : 'Create Your Course Desk'}
          </h2>
          <p className="text-xs text-[#7B766C] mt-0.5">
            {createdCourseResult
              ? 'Your structured curriculum, documents, and foundational knowledge units are ready.'
              : 'Generate a complete academic course with units, syllabus, and verified learning materials from any topic, notes, or uploaded documents.'}
          </p>
        </div>

        {/* IF COURSE CREATED SUCCESSFULLY */}
        {createdCourseResult ? (
          <div className="space-y-4 pt-1">
            <div className="p-4 rounded-2xl bg-teal-50/70 border border-teal-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase text-teal-800 bg-teal-100/80 px-2 py-0.5 rounded">
                  {createdCourseResult.course?.subject || courseSubject}
                </span>
                <span className="text-xs text-teal-700 font-semibold">
                  {createdCourseResult.course?.semester || `${courseDifficulty} • 2026`}
                </span>
              </div>
              <h3 className="text-lg font-bold text-slate-900">
                {createdCourseResult.course?.name}
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                {createdCourseResult.course?.description}
              </p>
            </div>

            <div className="space-y-2">
              <div className="text-xs font-bold text-slate-700 flex items-center justify-between">
                <span>Generated Course Units ({createdCourseResult.units?.length || 0})</span>
                <span className="text-[10px] text-teal-600 font-semibold">Ready in AI Tutor</span>
              </div>
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1 divide-y divide-slate-100">
                {createdCourseResult.units?.map((u: any, idx: number) => (
                  <div key={u.id || idx} className="pt-2 first:pt-0 pb-1">
                    <div className="text-xs font-semibold text-slate-800 flex items-center space-x-2">
                      <span className="h-5 w-5 rounded-full bg-teal-100 text-teal-700 text-[10px] font-bold flex items-center justify-center shrink-0">
                        {u.unit_number || idx + 1}
                      </span>
                      <span className="truncate">{u.title}</span>
                    </div>
                    {u.description && (
                      <p className="text-[11px] text-slate-500 mt-1 pl-7 line-clamp-2">
                        {u.description}
                      </p>
                    )}
                    {u.key_concepts && u.key_concepts.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1 pl-7">
                        {u.key_concepts.slice(0, 3).map((kc: string, i: number) => (
                          <span
                            key={i}
                            className="text-[9px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded"
                          >
                            {kc}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-[#EAE6DF] flex flex-wrap items-center justify-between gap-2">
              <button
                type="button"
                onClick={resetForm}
                className="text-xs text-slate-500 hover:text-slate-700 font-semibold py-2 px-3 rounded-lg border border-slate-200 cursor-pointer"
              >
                + Create Another Course
              </button>

              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => {
                    const cId = createdCourseResult.course.id;
                    onSelectCourse?.(cId);
                    handleClose();
                    navigate('/tutor');
                  }}
                  className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs transition cursor-pointer"
                >
                  Open in AI Tutor
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const cId = createdCourseResult.course.id;
                    onSelectCourse?.(cId);
                    handleClose();
                    navigate(`/courses/${cId}`);
                  }}
                  className="px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs transition shadow-sm flex items-center space-x-1.5 cursor-pointer"
                >
                  <span>Go to Course Workspace</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* COURSE CREATION FORM */
          <form onSubmit={handleCreateStructuredCourse} className="space-y-4">
            {/* Source Selection Tabs */}
            <div className="space-y-1.5">
              <label className="block text-xs font-bold text-[#16130F]">Course Creation Source</label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setCourseSourceType('file')}
                  className={`p-2.5 rounded-xl border text-left text-xs transition cursor-pointer ${
                    courseSourceType === 'file'
                      ? 'border-[#1D4ED8] bg-[#EFF6FF] text-[#1E3A8A] font-semibold'
                      : 'border-[#EAE6DF] hover:bg-[#FAF8F5] text-[#524E48]'
                  }`}
                >
                  <div className="font-bold">Uploaded Files</div>
                  <div className="text-[10px] text-[#7B766C] mt-0.5">PDF, PPTX, DOCX, TXT</div>
                </button>
                <button
                  type="button"
                  onClick={() => setCourseSourceType('topic')}
                  className={`p-2.5 rounded-xl border text-left text-xs transition cursor-pointer ${
                    courseSourceType === 'topic'
                      ? 'border-[#1D4ED8] bg-[#EFF6FF] text-[#1E3A8A] font-semibold'
                      : 'border-[#EAE6DF] hover:bg-[#FAF8F5] text-[#524E48]'
                  }`}
                >
                  <div className="font-bold">Topic / Idea</div>
                  <div className="text-[10px] text-[#7B766C] mt-0.5">Generate from subject</div>
                </button>
                <button
                  type="button"
                  onClick={() => setCourseSourceType('notes')}
                  className={`p-2.5 rounded-xl border text-left text-xs transition cursor-pointer ${
                    courseSourceType === 'notes'
                      ? 'border-[#1D4ED8] bg-[#EFF6FF] text-[#1E3A8A] font-semibold'
                      : 'border-[#EAE6DF] hover:bg-[#FAF8F5] text-[#524E48]'
                  }`}
                >
                  <div className="font-bold">From Notes</div>
                  <div className="text-[10px] text-[#7B766C] mt-0.5">Paste notes or syllabus</div>
                </button>
              </div>
            </div>

            {/* Course Topic / Title */}
            <div className="space-y-1">
              <label className="block text-xs font-bold text-slate-700">
                Course Topic or Subject Title <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                value={courseTopic}
                onChange={(e) => setCourseTopic(e.target.value)}
                placeholder="e.g. Distributed Systems & Consensus, Quantum Physics, Deep Learning"
                className="w-full p-2.5 text-xs rounded-xl bg-[#FAF8F5] border border-[#E2DDD5] text-slate-800 focus:outline-none focus:border-teal-500 font-sans"
              />
            </div>

            {/* Source Specific: Notes / Syllabus */}
            {courseSourceType === 'notes' && (
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700">
                  Paste Notes, Transcript, or Syllabus Outline
                </label>
                <textarea
                  rows={4}
                  value={courseNotes}
                  onChange={(e) => setCourseNotes(e.target.value)}
                  placeholder="Paste your syllabus structure, lecture notes, textbook contents, or curriculum goals here..."
                  className="w-full p-3 text-xs rounded-xl bg-[#FAF8F5] border border-[#E2DDD5] text-slate-800 focus:outline-none focus:border-teal-500 font-sans"
                />
              </div>
            )}

            {/* Source Specific: File Dropzone */}
            {courseSourceType === 'file' && (
              <div className="space-y-2">
                <label className="block text-xs font-bold text-slate-700">
                  Upload Reference Material (Multi-File Supported)
                </label>
                <label className="border-2 border-dashed border-slate-300 hover:border-teal-500 rounded-xl p-4 flex flex-col items-center justify-center text-center cursor-pointer bg-[#FAF8F5] transition">
                  <UploadCloud className="h-6 w-6 text-teal-600 mb-1" />
                  <span className="text-xs font-semibold text-slate-700">
                    {courseFiles.length > 0
                      ? `${courseFiles.length} file(s) selected (${(
                          courseFiles.reduce((acc, f) => acc + f.size, 0) /
                          (1024 * 1024)
                        ).toFixed(1)} MB)`
                      : 'Drop your syllabus, slides, or documents here'}
                  </span>
                  <span className="text-[10px] text-slate-400 mt-0.5">
                    Supports multiple PDF, PPTX, DOCX, TXT files
                  </span>
                  <input
                    type="file"
                    multiple
                    className="hidden"
                    accept=".pdf,.docx,.txt,.pptx,.ppt,.doc,.md"
                    onChange={(e) => {
                      if (e.target.files && e.target.files.length > 0) {
                        handleAddCourseFiles(e.target.files);
                      }
                    }}
                  />
                </label>

                {courseFiles.length > 0 && (
                  <div className="max-h-28 overflow-y-auto space-y-1 p-2 rounded-lg bg-teal-50/50 border border-teal-200 text-xs">
                    {courseFiles.map((f, idx) => (
                      <div
                        key={`${f.name}-${idx}`}
                        className="flex items-center justify-between py-0.5 px-1"
                      >
                        <span className="truncate text-slate-700 font-medium">{f.name}</span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRemoveCourseFile(idx);
                          }}
                          className="text-slate-400 hover:text-rose-600 ml-2 cursor-pointer"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Grid for Subject, Difficulty & Number of Units */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Discipline</label>
                <select
                  value={courseSubject}
                  onChange={(e) => setCourseSubject(e.target.value)}
                  className="w-full p-2 text-xs rounded-xl bg-[#FAF8F5] border border-[#E2DDD5] text-slate-800 focus:outline-none focus:border-teal-500"
                >
                  <option value="Computer Science">Computer Science</option>
                  <option value="Mathematics & Statistics">Mathematics & Statistics</option>
                  <option value="Physics & Engineering">Physics & Engineering</option>
                  <option value="Chemistry & Physical Science">Chemistry & Physical Science</option>
                  <option value="Biology & Life Sciences">Biology & Life Sciences</option>
                  <option value="Business & Economics">Business & Economics</option>
                  <option value="Medicine & Healthcare">Medicine & Healthcare</option>
                  <option value="Humanities & Social Sciences">Humanities & Social Sciences</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Target Level</label>
                <select
                  value={courseDifficulty}
                  onChange={(e) => setCourseDifficulty(e.target.value)}
                  className="w-full p-2 text-xs rounded-xl bg-[#FAF8F5] border border-[#E2DDD5] text-slate-800 focus:outline-none focus:border-teal-500"
                >
                  <option value="Beginner">Beginner / Foundational</option>
                  <option value="Undergraduate">Undergraduate / Core</option>
                  <option value="Advanced">Advanced / Graduate</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Curriculum Units</label>
                <select
                  value={courseUnitsCount}
                  onChange={(e) => setCourseUnitsCount(Number(e.target.value))}
                  className="w-full p-2 text-xs rounded-xl bg-[#FAF8F5] border border-[#E2DDD5] text-slate-800 focus:outline-none focus:border-teal-500"
                >
                  <option value={3}>3 Units (Intensive Crash Course)</option>
                  <option value={4}>4 Units (Standard Module)</option>
                  <option value={6}>6 Units (Comprehensive Semester)</option>
                  <option value={8}>8 Units (Full Mastery Track)</option>
                </select>
              </div>
            </div>

            {/* Optional Focus Areas */}
            <div className="space-y-1">
              <label className="block text-xs font-bold text-slate-700">
                Focus Areas & Instructions{' '}
                <span className="text-slate-400 font-normal">(Optional)</span>
              </label>
              <input
                type="text"
                value={courseFocusAreas}
                onChange={(e) => setCourseFocusAreas(e.target.value)}
                placeholder="e.g. Include rigorous proofs, practical coding scenarios, and exam high-yield tips"
                className="w-full p-2 text-xs rounded-xl bg-[#FAF8F5] border border-[#E2DDD5] text-slate-800 focus:outline-none focus:border-teal-500 font-sans"
              />
            </div>

            {courseError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center space-x-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{courseError}</span>
              </div>
            )}

            {/* Footer with Submit button */}
            <div className="pt-2 flex items-center justify-between border-t border-[#EAE6DF]">
              <span className="text-[11px] text-slate-500 font-medium">
                {isCreatingCourse ? (
                  <span className="text-emerald-700 font-mono font-semibold animate-pulse">
                    ⚡ Ingesting {courseFiles.length > 0 ? `${courseFiles.length} file(s)` : 'topic'} &bull; {elapsedSeconds}s elapsed
                  </span>
                ) : (
                  '⚡ Instant BKT & Vector Graph Integration'
                )}
              </span>

              <button
                type="submit"
                disabled={isCreatingCourse || (!courseTopic.trim() && courseFiles.length === 0)}
                className={`px-6 py-2.5 rounded-xl font-mono text-xs font-bold flex items-center space-x-2 transition shadow-paper-sm cursor-pointer ${
                  courseFiles.length > 0 
                    ? 'bg-[#059669] hover:bg-[#047857] text-white' 
                    : 'bg-[#16130F] hover:bg-[#2A241F] text-white disabled:opacity-50'
                }`}
              >
                {isCreatingCourse ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin text-[#FFE45C]" />
                    <span>
                      {elapsedSeconds < 5 && 'Architecting Syllabus...'}
                      {elapsedSeconds >= 5 && elapsedSeconds < 16 && `Extracting ${courseFiles.length ? `${courseFiles.length} Files` : 'Content'} & Figures...`}
                      {elapsedSeconds >= 16 && elapsedSeconds < 32 && 'Vectorizing Chunks & Embeddings...'}
                      {elapsedSeconds >= 32 && 'Building Concept DAG & BKT Graph...'}
                      {` (${elapsedSeconds}s)`}
                    </span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-3.5 w-3.5 text-[#FFE45C]" />
                    <span>
                      {courseFiles.length > 0 
                        ? `Create Course Desk from ${courseFiles.length} Document${courseFiles.length > 1 ? 's' : ''}` 
                        : 'Create Course & Unlock All 5 Tools'}
                    </span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
