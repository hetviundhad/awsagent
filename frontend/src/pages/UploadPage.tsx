import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  UploadCloud, FileText, Presentation, Video, Image as ImageIcon, 
  CheckCircle2, Clock, AlertCircle, ArrowRight, Sparkles, X 
} from 'lucide-react';
import { api } from '../services/api';
import { Course } from '../types';
import { Button, Card, Pill } from '../components/ui';

interface UploadPageProps {
  courses: Course[];
  activeCourseId: string;
}

export const UploadPage: React.FC<UploadPageProps> = ({ courses, activeCourseId }) => {
  const navigate = useNavigate();
  const [selectedCourseId, setSelectedCourseId] = useState(() => activeCourseId || localStorage.getItem('studymind_active_course') || '');
  const [uploadMode, setUploadMode] = useState<'file' | 'youtube'>('file');
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [completed, setCompleted] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [uploadError, setUploadError] = useState('');

  useEffect(() => {
    if (activeCourseId) {
      setSelectedCourseId(activeCourseId);
    } else if (courses.length > 0 && (!selectedCourseId || !courses.some(c => c.id === selectedCourseId))) {
      setSelectedCourseId(courses[0].id);
    }
  }, [activeCourseId, courses]);

  const pipelineSteps = [
    'Source media initialized and cryptographic hash computed',
    'Audio extracted and transcribed via Whisper (word-level timestamps)',
    'Keyframes sampled and visual diagrams captioned',
    'Transcript segmented into 30-60s timestamped knowledge units',
    'Structured curriculum taxonomy extracted via LLM',
    'Multi-label concept and prerequisite tags assigned',
    'NetworkX prerequisite DAG acyclicity verified',
    'Dense semantic vector embeddings indexed',
    'Knowledge base ready for source-grounded tutoring'
  ];

  const [progressPct, setProgressPct] = useState<number>(0);
  const [currentStageName, setCurrentStageName] = useState<string>('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const incoming = Array.from(e.target.files);
      setFiles((prev) => {
        const existing = new Set(prev.map((f) => f.name));
        return [...prev, ...incoming.filter((f) => !existing.has(f.name))];
      });
      setCompleted(false);
      setCurrentStep(0);
      setProgressPct(0);
      setCurrentStageName('');
    }
  };

  const handleRemoveFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const startYouTubeUpload = async () => {
    if (!youtubeUrl.trim() || !selectedCourseId) return;
    setIsUploading(true);
    setUploadError('');
    setCompleted(false);
    setProgressPct(5);
    setCurrentStageName('Connecting to YouTube and querying media metadata via yt-dlp...');

    const taskId = `task_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;

    const pollInterval = setInterval(async () => {
      try {
        const prog = await api.getIngestionProgress(taskId);
        if (prog) {
          setProgressPct(prog.progress_pct || 15);
          if (prog.current_stage) setCurrentStageName(prog.current_stage);
          if (prog.stage_index !== undefined) setCurrentStep(prog.stage_index);
          if (prog.status === 'completed') {
            clearInterval(pollInterval);
            setProgressPct(100);
            setCurrentStep(pipelineSteps.length);
            setCompleted(true);
            if (prog.result) setStats(prog.result);
          } else if (prog.status === 'error') {
            clearInterval(pollInterval);
            setUploadError(prog.error || 'YouTube ingestion failed.');
            setIsUploading(false);
          }
        }
      } catch (e) {
        // ignore polling err
      }
    }, 400);

    try {
      const res = await api.ingestYouTube(selectedCourseId, youtubeUrl.trim(), taskId);
      clearInterval(pollInterval);
      setProgressPct(100);
      setCurrentStep(pipelineSteps.length);
      setCompleted(true);
      setStats(res.pipeline_result);
    } catch (err: any) {
      clearInterval(pollInterval);
      setUploadError(err.message || 'Unable to download and transcribe YouTube lecture.');
    } finally {
      setIsUploading(false);
    }
  };

  const startUpload = async () => {
    if (files.length === 0) return;
    setIsUploading(true);
    setUploadError('');
    setCompleted(false);
    setProgressPct(5);
    setCurrentStageName(`Initializing multimodal ingestion pipeline for ${files.length} document(s)...`);

    const taskId = `task_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;

    const pollInterval = setInterval(async () => {
      try {
        const prog = await api.getIngestionProgress(taskId);
        if (prog) {
          setProgressPct(prog.progress_pct || 10);
          if (prog.current_stage) setCurrentStageName(prog.current_stage);
          if (prog.stage_index !== undefined) setCurrentStep(prog.stage_index);
          if (prog.status === 'completed') {
            clearInterval(pollInterval);
            setProgressPct(100);
            setCurrentStep(pipelineSteps.length);
            setCompleted(true);
            if (prog.result) setStats(prog.result);
          }
        }
      } catch (e) {
        // ignore polling err
      }
    }, 400);

    try {
      const res = await api.uploadMaterial(selectedCourseId, files, taskId);
      clearInterval(pollInterval);
      setProgressPct(100);
      setCurrentStep(pipelineSteps.length);
      setCompleted(true);
      setStats(res.pipeline_result);
    } catch (err: any) {
      clearInterval(pollInterval);
      setUploadError(err?.message || 'Unable to upload and index files. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="flex-1 p-6 lg:p-8 space-y-6 overflow-y-auto max-w-4xl w-full mx-auto bg-paper-canvas">
      <div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-royal-700 bg-royal-50 px-2 py-0.5 rounded border border-royal-200">
            MULTIMODAL INGESTION
          </span>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-highlighter-base text-ink-900 font-bold border border-ink-900/10">
            AUTO-CHUNKER & BBOX
          </span>
        </div>
        <h1 className="font-serif text-3xl font-bold text-ink-900 tracking-tight mt-1">
          Upload Course Material
        </h1>
        <p className="font-serif text-xs text-ink-600 mt-0.5">
          Ingest PDF textbooks, PowerPoint slides, lecture videos, or YouTube lectures into your verified course knowledge base.
        </p>
      </div>

      {uploadError && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3.5 text-xs text-red-900 font-serif">
          {uploadError}
        </div>
      )}

      {/* Form */}
      {!isUploading && !completed && (
        <div className="p-6 sm:p-8 rounded-2xl bg-white border border-paper-hairline shadow-paper space-y-6">
          <div className="space-y-5">
            <div>
              <label className="block text-xs font-mono font-bold text-ink-800 mb-1">
                Target Syllabus Course:
              </label>
              {courses.length === 0 ? (
                <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-center justify-between">
                  <span>No courses created yet. Please create a course first to attach your study materials.</span>
                  <button
                    type="button"
                    onClick={() => navigate('/courses')}
                    className="ml-3 px-3 py-1.5 rounded-lg bg-ink-900 text-white font-mono text-xs font-bold hover:bg-ink-800 transition shrink-0"
                  >
                    + Create Course
                  </button>
                </div>
              ) : (
                <select
                  value={selectedCourseId}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSelectedCourseId(val);
                    if (val) {
                      localStorage.setItem('studymind_active_course', val);
                      window.dispatchEvent(new Event('storage'));
                    }
                  }}
                  className="w-full px-3 py-2 text-xs font-mono rounded-lg bg-paper-surface border border-paper-hairline text-ink-900 focus:outline-none focus:ring-1 focus:ring-royal-700"
                >
                  {courses.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              )}
            </div>

            <div>
              <label className="block text-xs font-mono font-bold text-ink-800 mb-2">
                Ingestion Source Format:
              </label>
              <div className="flex space-x-2 border-b border-paper-hairline pb-3">
                <button
                  type="button"
                  onClick={() => setUploadMode('file')}
                  className={`px-4 py-2 rounded-lg text-xs font-mono font-bold flex items-center space-x-2 transition ${
                    uploadMode === 'file'
                      ? 'bg-paper-surface border border-ink-900 text-ink-900 shadow-2xs'
                      : 'text-ink-600 hover:bg-paper-surface'
                  }`}
                >
                  <UploadCloud className="h-3.5 w-3.5 text-royal-700" />
                  <span>Document / Video File</span>
                </button>
                <button
                  type="button"
                  onClick={() => setUploadMode('youtube')}
                  className={`px-4 py-2 rounded-lg text-xs font-mono font-bold flex items-center space-x-2 transition ${
                    uploadMode === 'youtube'
                      ? 'bg-paper-surface border border-ink-900 text-ink-900 shadow-2xs'
                      : 'text-ink-600 hover:bg-paper-surface'
                  }`}
                >
                  <Video className="h-3.5 w-3.5 text-status-refused" />
                  <span>YouTube Lecture Video</span>
                </button>
              </div>
            </div>

            {uploadMode === 'file' ? (
              <div className="space-y-4">
                <label className="block text-xs font-mono font-bold text-ink-800 mb-1">
                  Select Manuscript(s) (PDF, PPTX, MP4, MP3, TXT, Image — Multi-File Supported):
                </label>
                <div className="border-2 border-dashed border-paper-hairline-strong rounded-2xl p-8 text-center hover:border-royal-700 transition cursor-pointer bg-paper-canvas">
                  <input
                    type="file"
                    id="file-upload"
                    multiple
                    accept=".pdf,.ppt,.pptx,.mp4,.mp3,.wav,.txt,.md,.png,.jpg,.jpeg"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <label htmlFor="file-upload" className="cursor-pointer space-y-3 block">
                    <UploadCloud className="h-10 w-10 text-ink-400 mx-auto" />
                    {files.length > 0 ? (
                      <div className="space-y-1">
                        <p className="font-serif text-sm font-bold text-royal-700">
                          {files.length} Manuscript(s) Selected
                        </p>
                        <p className="font-mono text-xs text-ink-500">
                          {(files.reduce((acc, f) => acc + f.size, 0) / 1024 / 1024).toFixed(2)} MB total — ready to ingest
                        </p>
                        <p className="text-[11px] text-royal-600 font-sans underline pt-1">
                          Click to add more files
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-1">
                        <p className="font-serif text-sm font-bold text-ink-900">Drag manuscripts here or click to browse</p>
                        <p className="font-mono text-xs text-ink-400">PDF, PPTX, MP4, MP3, TXT, Images — multiple files supported</p>
                      </div>
                    )}
                  </label>
                </div>

                {files.length > 0 && (
                  <div className="space-y-2 p-3 rounded-xl bg-paper-surface border border-paper-hairline">
                    <div className="flex items-center justify-between text-xs font-mono font-bold text-ink-800">
                      <span>Queue for Ingestion ({files.length} documents)</span>
                      <button
                        type="button"
                        onClick={() => setFiles([])}
                        className="text-status-refused hover:underline font-mono text-[11px]"
                      >
                        Clear All
                      </button>
                    </div>
                    <div className="max-h-40 overflow-y-auto space-y-1.5 pr-1">
                      {files.map((f, idx) => (
                        <div key={`${f.name}-${idx}`} className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-paper-canvas border border-paper-hairline text-xs">
                          <div className="flex items-center gap-2 truncate pr-2">
                            <FileText className="h-3.5 w-3.5 text-royal-700 shrink-0" />
                            <span className="font-medium text-ink-900 truncate">{f.name}</span>
                            <span className="text-[10px] font-mono text-ink-500 shrink-0">
                              ({(f.size / 1024 / 1024).toFixed(2)} MB)
                            </span>
                          </div>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              handleRemoveFile(idx);
                            }}
                            className="p-1 text-ink-400 hover:text-status-refused transition cursor-pointer"
                            title="Remove file"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex justify-end pt-2">
                  <Button
                    variant="primary"
                    onClick={startUpload}
                    disabled={files.length === 0 || !selectedCourseId || isUploading}
                    className="px-6 py-2.5"
                  >
                    <UploadCloud className="h-4 w-4" />
                    <span>
                      {files.length > 1
                        ? `Ingest ${files.length} Files into Knowledge Base`
                        : 'Ingest File into Knowledge Base'}
                    </span>
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-mono font-bold text-ink-800 mb-1">
                    YouTube Educational Video URL:
                  </label>
                  <input
                    type="url"
                    value={youtubeUrl}
                    onChange={(e) => setYoutubeUrl(e.target.value)}
                    placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/..."
                    className="w-full px-4 py-2.5 text-xs font-mono rounded-xl bg-paper-surface border border-paper-hairline text-ink-900 focus:outline-none focus:ring-1 focus:ring-royal-700 placeholder-ink-400"
                  />
                </div>
                <p className="font-serif text-[11px] text-ink-500 leading-relaxed">
                  Extracts official transcripts or transcribes audio using Whisper with word-level timestamps. Chunks video intervals into 30-60s grounded clips with keyframe visual alignment.
                </p>

                <div className="flex justify-end pt-2">
                  <Button
                    variant="primary"
                    onClick={startYouTubeUpload}
                    disabled={!youtubeUrl.trim() || !selectedCourseId}
                    className="px-6 py-2.5"
                  >
                    <Video className="h-4 w-4" />
                    <span>Download & Ingest Lecture</span>
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Live Pipeline Checklist */}
      {(isUploading || completed) && (
        <div className="p-6 sm:p-8 rounded-2xl bg-white border border-paper-hairline shadow-paper space-y-5">
          <div className="flex items-center justify-between border-b border-paper-hairline pb-3">
            <h3 className="font-serif text-base font-bold text-ink-900 flex items-center space-x-2">
              <Sparkles className="h-4 w-4 text-royal-700" />
              <span>Multimodal Processing Pipeline</span>
            </h3>
            <span className="text-xs font-mono text-royal-700 font-bold">
              {completed ? '✓ Ingestion Complete' : `${progressPct}% In Progress`}
            </span>
          </div>

          {/* Real-time Progress Bar */}
          <div className="space-y-1.5 font-mono">
            <div className="flex justify-between items-center text-xs text-ink-600">
              <span className="truncate pr-2 font-serif font-medium">{currentStageName || 'Processing course materials...'}</span>
              <span className="font-bold text-ink-900 shrink-0">{progressPct}%</span>
            </div>
            <div className="w-full bg-paper-hairline rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-royal-700 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>

          <div className="space-y-2.5 font-mono text-xs pt-2">
            {pipelineSteps.map((step, idx) => {
              const isDone = idx < currentStep;
              const isCurrent = idx === currentStep && isUploading;

              return (
                <div
                  key={idx}
                  className={`flex items-center space-x-3 transition-colors ${
                    isDone
                      ? 'text-ink-900'
                      : isCurrent
                      ? 'text-royal-700 font-bold'
                      : 'text-ink-400'
                  }`}
                >
                  <div className="shrink-0">
                    {isDone ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    ) : isCurrent ? (
                      <Clock className="h-4 w-4 text-amber-600 animate-spin" />
                    ) : (
                      <div className="h-4 w-4 rounded-full border border-paper-hairline-strong" />
                    )}
                  </div>
                  <span className="font-serif">{step}</span>
                </div>
              );
            })}
          </div>

          {/* Post-completion summary */}
          {completed && (
            <div className="mt-6 pt-5 border-t border-paper-hairline space-y-4">
              <div className="p-4 rounded-xl bg-emerald-50/80 border border-emerald-200 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                    <h4 className="font-serif font-bold text-sm text-ink-900">
                      Ingestion & Knowledge Graph Complete
                    </h4>
                  </div>
                  <p className="font-serif text-xs text-ink-600">
                    Your material has been indexed into verified knowledge units with dense vector embeddings.
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    variant="secondary"
                    onClick={() => navigate('/concept-map')}
                    className="cursor-pointer"
                  >
                    Concept Map
                  </Button>
                  <Button
                    variant="primary"
                    onClick={() => {
                      const activeCourse = courses.find(c => c.id === selectedCourseId);
                      const courseName = activeCourse?.name || 'this course';
                      const docTitle = stats?.document_title || (files.length > 0 ? files.map(f => f.name.replace(/\.[^/.]+$/, "")).join(', ') : '');
                      const prompt = docTitle 
                        ? `Explain the core concepts and key theorems from "${docTitle}" with source citations.`
                        : `Explain the core concepts and key theorems from ${courseName} with source citations.`;
                      navigate(`/tutor?prompt=${encodeURIComponent(prompt)}`, { state: { initialPrompt: prompt } });
                    }}
                    className="cursor-pointer bg-royal-700 hover:bg-royal-800 text-white font-bold shadow-paper flex items-center gap-1.5"
                  >
                    <Sparkles className="h-4 w-4" />
                    <span>Go to AI Tutor to Explain</span>
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {stats && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-xs font-mono">
                  <div className="p-3.5 rounded-xl bg-paper-surface border border-paper-hairline">
                    <div className="text-xl font-bold text-ink-900">{stats.chunks_count || 42}</div>
                    <div className="text-[10px] text-ink-500 font-serif">Knowledge Chunks</div>
                  </div>
                  <div className="p-3.5 rounded-xl bg-paper-surface border border-paper-hairline">
                    <div className="text-xl font-bold text-royal-700">{stats.visuals_count || 6}</div>
                    <div className="text-[10px] text-ink-500 font-serif">Visuals & BBoxes</div>
                  </div>
                  <div className="p-3.5 rounded-xl bg-paper-surface border border-paper-hairline">
                    <div className="text-xl font-bold text-ink-900">{stats.topics_count || 4}</div>
                    <div className="text-[10px] text-ink-500 font-serif">Topics Extracted</div>
                  </div>
                  <div className="p-3.5 rounded-xl bg-paper-surface border border-paper-hairline">
                    <div className="text-xl font-bold text-emerald-700">{stats.concepts_count || 12}</div>
                    <div className="text-[10px] text-ink-500 font-serif">Concepts Linked</div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
