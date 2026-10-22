import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  FileText, UploadCloud, Search, Trash2, BookOpen, 
  HelpCircle, Layers, CheckSquare, Square, Sparkles, 
  ArrowRight, Download, Filter, Eye, Check, AlertCircle, RefreshCw, File, Video, Clock
} from 'lucide-react';
import { api } from '../services/api';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Pill } from '../components/ui/Pill';

interface UserFile {
  id: string;
  name: string;
  size: string;
  uploadDate: string;
  type: string;
  chunk_count: number;
  concept_count: number;
  status: string;
  last_error?: string | null;
  topics: string[];
  course_id?: string;
  course_name?: string;
}

interface MyFilesPageProps {
  activeCourseId?: string;
  courses?: any[];
}

export const MyFilesPage: React.FC<MyFilesPageProps> = ({ activeCourseId = '', courses = [] }) => {
  const navigate = useNavigate();
  const initialCourse = activeCourseId || localStorage.getItem('studymind_active_course') || 'all';
  const [selectedCourseId, setSelectedCourseId] = useState<string>(initialCourse);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [reanalyzingDocId, setReanalyzingDocId] = useState<string | null>(null);
  const [reanalyzingCourse, setReanalyzingCourse] = useState(false);
  const [files, setFiles] = useState<UserFile[]>([]);
  const [activeTab, setActiveTab] = useState<'materials' | 'conflicts' | 'syllabus' | 'alignments'>('materials');
  const [conflicts, setConflicts] = useState<any[]>([]);
  const [loadingConflicts, setLoadingConflicts] = useState(false);
  const [syllabusReport, setSyllabusReport] = useState<any | null>(null);
  const [loadingSyllabus, setLoadingSyllabus] = useState(false);
  const [alignments, setAlignments] = useState<any[]>([]);
  const [loadingAlignments, setLoadingAlignments] = useState(false);

  useEffect(() => {
    if (activeCourseId) {
      setSelectedCourseId(activeCourseId);
    } else {
      const stored = localStorage.getItem('studymind_active_course');
      if (stored) setSelectedCourseId(stored);
    }
  }, [activeCourseId]);

  useEffect(() => {
    if (activeTab === 'conflicts') {
      loadConflicts();
    } else if (activeTab === 'syllabus') {
      loadSyllabus();
    } else if (activeTab === 'alignments') {
      loadAlignments();
    }
  }, [activeTab, selectedCourseId]);

  const loadAlignments = async () => {
    if (!selectedCourseId || selectedCourseId === 'all') return;
    try {
      setLoadingAlignments(true);
      const res = await api.getSlideAlignments(selectedCourseId);
      setAlignments(res?.alignments || []);
    } catch (e) {
      console.error('Failed to load slide alignments:', e);
      setAlignments([]);
    } finally {
      setLoadingAlignments(false);
    }
  };

  const loadSyllabus = async () => {
    if (!selectedCourseId || selectedCourseId === 'all') return;
    try {
      setLoadingSyllabus(true);
      const res = await api.get(`/courses/${selectedCourseId}/syllabus-coverage`);
      setSyllabusReport(res);
    } catch (e) {
      console.error('Failed to load syllabus coverage:', e);
    } finally {
      setLoadingSyllabus(false);
    }
  };


  const loadConflicts = async () => {
    if (!selectedCourseId || selectedCourseId === 'all') return;
    try {
      setLoadingConflicts(true);
      const res = await api.get(`/courses/${selectedCourseId}/conflicts`);
      setConflicts(res?.conflicts || []);
    } catch (e) {
      console.error('Failed to load conflicts:', e);
      setConflicts([]);
    } finally {
      setLoadingConflicts(false);
    }
  };

  const handleResolveConflict = async (conflictId: string, trustedDoc: string) => {
    try {
      await api.post(`/courses/${selectedCourseId}/conflicts/${conflictId}/resolve`, {
        trusted_document: trustedDoc
      });
      setConflicts(prev => prev.map(c => c.id === conflictId ? { ...c, status: 'resolved', trusted_source: trustedDoc } : c));
    } catch (e) {
      alert('Failed to resolve conflict');
    }
  };

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const queryCourse = selectedCourseId === 'all' ? undefined : selectedCourseId;
      const docs = await api.getUserDocuments(queryCourse);
      if (docs && docs.length > 0) {
        setFiles(docs.map((d: any) => ({
          id: d.id,
          name: d.name,
          size: d.size,
          uploadDate: d.date || 'Recently',
          type: (d.type || 'pdf').toUpperCase(),
          chunk_count: d.chunk_count || 0,
          concept_count: d.concept_count || 0,
          status: d.status || 'processed',
          last_error: d.last_error || null,
          course_id: d.course_id,
          course_name: d.course_name,
          topics: d.topics || ['Course Curriculum', 'Academic Knowledge']
        })));
      } else {
        setFiles([]);
      }
    } catch (e) {
      console.error('Failed to load user documents:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleReanalyzeDoc = async (id: string) => {
    setReanalyzingDocId(id);
    try {
      await api.reanalyzeDocument(id);
      await loadDocuments();
    } catch (err: any) {
      alert(`Re-analysis failed: ${err.message || 'Server error'}`);
    } finally {
      setReanalyzingDocId(null);
    }
  };

  const handleReanalyzeCourse = async () => {
    const targetCourse = selectedCourseId === 'all' ? (activeCourseId || (courses[0]?.id || '')) : selectedCourseId;
    if (!targetCourse) {
      alert('Please select a course to re-analyze.');
      return;
    }
    setReanalyzingCourse(true);
    try {
      await api.reanalyzeCourse(targetCourse);
      await loadDocuments();
    } catch (err: any) {
      alert(`Course re-analysis failed: ${err.message || 'Server error'}`);
    } finally {
      setReanalyzingCourse(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [selectedCourseId]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFiles = Array.from(e.target.files);
      setUploadProgress(15);
      const taskId = `task_${Date.now()}`;
      
      const pollTimer = setInterval(async () => {
        try {
          const prog = await api.getIngestionProgress(taskId);
          if (prog?.progress_pct) setUploadProgress(prog.progress_pct);
        } catch {}
      }, 500);

      try {
        const uploadTarget = selectedCourseId === 'all' ? (activeCourseId || (courses[0]?.id || '')) : selectedCourseId;
        if (!uploadTarget) {
          alert('Please create or select an active course before uploading files.');
          clearInterval(pollTimer);
          setUploadProgress(null);
          return;
        }
        await api.uploadMaterial(uploadTarget, selectedFiles, taskId);
        clearInterval(pollTimer);
        setUploadProgress(100);
        setTimeout(async () => {
          setUploadProgress(null);
          await loadDocuments();
        }, 600);
      } catch (err) {
        clearInterval(pollTimer);
        setUploadProgress(null);
        alert('Upload failed. Please try a valid PDF, PPTX, or Video file.');
      }
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === files.length) setSelectedIds([]);
    else setSelectedIds(files.map((f) => f.id));
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this document from the course?')) return;
    try {
      await api.deleteUserDocument(id);
      setFiles((prev) => prev.filter((f) => f.id !== id));
      setSelectedIds((prev) => prev.filter((i) => i !== id));
    } catch (err) {
      alert('Failed to delete document');
    }
  };

  const filteredFiles = files.filter((f) => {
    const q = searchQuery.toLowerCase();
    const matchesSearch = (f.name || '').toLowerCase().includes(q) ||
      (Array.isArray(f.topics) && f.topics.some((t) => String(t || '').toLowerCase().includes(q)));
    const matchesCourse = selectedCourseId === 'all' || !f.course_id || f.course_id === selectedCourseId;
    return matchesSearch && matchesCourse;
  });

  return (
    <div className="flex-1 flex flex-col bg-[#FAF8F5] overflow-hidden min-h-screen">
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6 max-w-6xl w-full mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#EAE6DF] pb-5">
          <div>
            <div className="flex items-center space-x-2">
              <Pill variant="neutral" size="sm">SOURCE CORPUS</Pill>
              <span className="text-xs font-mono text-[#7B766C]">· {files.length} Ingested Works</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-serif font-bold text-[#16130F] tracking-tight mt-1">
              Document Archive & Manuscripts
            </h1>
            <p className="text-sm text-[#5E5A52] mt-1">
              Course textbooks, lecture slide decks, syllabus outlines, and problem sets indexed for grounded citation.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <button
              onClick={handleReanalyzeCourse}
              disabled={reanalyzingCourse}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#FAF8F5] hover:bg-[#F3EFE8] text-[#16130F] font-mono text-xs font-semibold border border-[#EAE6DF] shadow-2xs transition disabled:opacity-50 cursor-pointer"
              title="Re-run concept extraction and chunk tagging for all documents in this course"
            >
              <RefreshCw className={`h-3.5 w-3.5 text-[#1D4ED8] ${reanalyzingCourse ? 'animate-spin' : ''}`} />
              <span>{reanalyzingCourse ? 'Re-analyzing Course...' : 'Re-run Course Analysis'}</span>
            </button>

            <label className="cursor-pointer">
              <span className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#1D4ED8] hover:bg-[#1e40af] text-white font-sans font-medium text-xs shadow-sm hover:shadow transition-all active:scale-98">
                <UploadCloud className="h-4 w-4" />
                <span>Upload Manuscripts</span>
              </span>
              <input
                type="file"
                multiple
                className="hidden"
                accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg,.pptx"
                onChange={handleFileUpload}
              />
            </label>
          </div>
        </div>

        {/* Upload Progress Bar if active */}
        {uploadProgress !== null && (
          <Card className="p-4 border-[#FFE45C] bg-[#FFFBEA]">
            <div className="flex justify-between text-xs font-semibold text-[#16130F] mb-2">
              <span className="flex items-center space-x-2">
                <Sparkles className="h-4 w-4 text-[#1D4ED8] animate-spin" />
                <span>Parsing manuscript & indexing multimodal chunks...</span>
              </span>
              <span className="font-mono text-[#1D4ED8]">{uploadProgress}%</span>
            </div>
            <div className="w-full bg-[#FAF8F5] h-2 rounded-full overflow-hidden border border-[#EAE6DF]">
              <div
                className="bg-[#FFE45C] h-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </Card>
        )}

        {/* Tab Navigation: Materials vs Source Conflicts vs Syllabus Coverage */}
        <div className="flex items-center space-x-2 border-b border-[#EAE6DF] pb-2">
          <button
            onClick={() => setActiveTab('materials')}
            className={`px-4 py-2 text-xs font-mono font-bold rounded-lg transition ${
              activeTab === 'materials'
                ? 'bg-[#1D4ED8] text-white shadow-xs'
                : 'bg-white text-[#7B766C] hover:text-[#16130F] border border-[#EAE6DF]'
            }`}
          >
            Course Manuscripts ({files.length})
          </button>
          <button
            onClick={() => setActiveTab('conflicts')}
            className={`px-4 py-2 text-xs font-mono font-bold rounded-lg transition flex items-center space-x-1.5 ${
              activeTab === 'conflicts'
                ? 'bg-[#1D4ED8] text-white shadow-xs'
                : 'bg-white text-[#7B766C] hover:text-[#16130F] border border-[#EAE6DF]'
            }`}
          >
            <AlertCircle className="h-3.5 w-3.5 text-amber-500" />
            <span>Source Conflicts ({conflicts.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('syllabus')}
            className={`px-4 py-2 text-xs font-mono font-bold rounded-lg transition flex items-center space-x-1.5 ${
              activeTab === 'syllabus'
                ? 'bg-[#1D4ED8] text-white shadow-xs'
                : 'bg-white text-[#7B766C] hover:text-[#16130F] border border-[#EAE6DF]'
            }`}
          >
            <BookOpen className="h-3.5 w-3.5 text-indigo-500" />
            <span>Syllabus Coverage</span>
          </button>
          <button
            onClick={() => setActiveTab('alignments')}
            className={`px-4 py-2 text-xs font-mono font-bold rounded-lg transition flex items-center space-x-1.5 ${
              activeTab === 'alignments'
                ? 'bg-[#1D4ED8] text-white shadow-xs'
                : 'bg-white text-[#7B766C] hover:text-[#16130F] border border-[#EAE6DF]'
            }`}
          >
            <Video className="h-3.5 w-3.5 text-rose-500" />
            <span>Lecture Alignment ({alignments.length})</span>
          </button>
        </div>

        {activeTab === 'syllabus' ? (
          <div className="space-y-4">
            {loadingSyllabus ? (
              <div className="py-16 text-center text-xs font-mono text-[#7B766C] flex items-center justify-center space-x-2">
                <RefreshCw className="h-4 w-4 animate-spin text-[#1D4ED8]" />
                <span>Auditing syllabus coverage against uploaded manuscripts...</span>
              </div>
            ) : !syllabusReport || !syllabusReport.has_syllabus ? (
              <Card className="p-8 text-center space-y-3">
                <BookOpen className="h-8 w-8 text-slate-400 mx-auto" />
                <h3 className="font-serif text-base font-bold text-[#16130F]">No Syllabus Document Found</h3>
                <p className="font-serif text-xs text-[#7B766C] max-w-md mx-auto">
                  Upload a PDF with "syllabus" in the filename to automatically audit course coverage and detect missing units.
                </p>
              </Card>
            ) : (
              <div className="space-y-4">
                {/* Syllabus Coverage Summary Banner */}
                <Card className="p-5 border-indigo-200 bg-gradient-to-r from-indigo-50/50 via-white to-indigo-50/20">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded font-mono text-[10px] font-bold uppercase bg-indigo-100 text-indigo-800 border border-indigo-200">
                          Curriculum Audit
                        </span>
                        <span className="text-xs text-slate-500 font-medium">
                          Source: <strong className="text-slate-800">{syllabusReport.syllabus_document?.name}</strong>
                        </span>
                      </div>
                      <h3 className="font-serif text-lg font-bold text-[#16130F]">
                        Syllabus Topic Coverage: {syllabusReport.overall_coverage_pct}%
                      </h3>
                      <p className="font-serif text-xs text-[#5E5A52]">
                        {syllabusReport.summary}
                      </p>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="text-center px-3 py-2 rounded-xl bg-white border border-[#EAE6DF] shadow-xs">
                        <div className="font-mono text-base font-bold text-emerald-600">{syllabusReport.counts?.covered || 0}</div>
                        <div className="text-[10px] uppercase font-bold text-slate-400">Covered</div>
                      </div>
                      <div className="text-center px-3 py-2 rounded-xl bg-white border border-[#EAE6DF] shadow-xs">
                        <div className="font-mono text-base font-bold text-amber-600">{syllabusReport.counts?.thin || 0}</div>
                        <div className="text-[10px] uppercase font-bold text-slate-400">Thin</div>
                      </div>
                      <div className="text-center px-3 py-2 rounded-xl bg-white border border-[#EAE6DF] shadow-xs">
                        <div className="font-mono text-base font-bold text-rose-600">{syllabusReport.counts?.missing || 0}</div>
                        <div className="text-[10px] uppercase font-bold text-slate-400">Missing</div>
                      </div>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden border border-slate-200 mt-4">
                    <div 
                      className="bg-indigo-600 h-full transition-all duration-500 rounded-full"
                      style={{ width: `${syllabusReport.overall_coverage_pct}%` }}
                    />
                  </div>
                </Card>

                {/* Items List */}
                <div className="space-y-3">
                  {syllabusReport.items?.map((item: any) => (
                    <Card key={item.id} className="p-4 transition hover:border-slate-300">
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[10px] font-bold text-slate-500 uppercase">
                              Unit {item.unit_number}: {item.unit_title}
                            </span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase ${
                              item.status === 'covered'
                                ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                                : item.status === 'thin'
                                ? 'bg-amber-100 text-amber-800 border border-amber-200'
                                : 'bg-rose-100 text-rose-800 border border-rose-200'
                            }`}>
                              {item.status}
                            </span>
                          </div>
                          <h4 className="font-serif text-sm font-bold text-[#16130F]">
                            {item.topic_name}
                          </h4>
                          <p className="font-serif text-xs text-[#5E5A52]">
                            {item.description}
                          </p>
                        </div>

                        <div className="shrink-0 text-right">
                          <div className="text-xs font-mono font-semibold text-slate-600">
                            {item.supporting_chunk_count} supporting chunk{item.supporting_chunk_count !== 1 ? 's' : ''}
                          </div>
                        </div>
                      </div>

                      {/* Supporting Chunks / Recommendation */}
                      <div className="mt-3 pt-3 border-t border-[#EAE6DF] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs">
                        <span className="text-slate-500 italic">
                          {item.recommendation}
                        </span>

                        {item.status === 'missing' && (
                          <label className="cursor-pointer inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 font-semibold text-xs transition">
                            <UploadCloud className="h-3.5 w-3.5" />
                            <span>Upload material for {item.topic_name}</span>
                            <input
                              type="file"
                              className="hidden"
                              accept=".pdf,.docx,.doc,.txt,.pptx"
                              onChange={handleFileUpload}
                            />
                          </label>
                        )}
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : activeTab === 'conflicts' ? (

          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-950 text-xs flex items-start space-x-2.5">
              <AlertCircle className="h-4 w-4 text-amber-700 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Cross-Document Disagreement Detector:</span>
                <p className="mt-0.5 text-amber-900 leading-relaxed">
                  StudyMind scans all uploaded documents for conflicting parameters, differing numbers, or contradictory architectural definitions. Mark which source to trust to calibrate your personal tutor.
                </p>
              </div>
            </div>

            {loadingConflicts ? (
              <div className="py-12 text-center text-xs font-mono text-[#7B766C] flex items-center justify-center space-x-2">
                <RefreshCw className="h-4 w-4 animate-spin text-[#1D4ED8]" />
                <span>Scanning cross-document claims for factual contradictions...</span>
              </div>
            ) : conflicts.length === 0 ? (
              <Card className="p-8 text-center space-y-2">
                <Check className="h-8 w-8 text-emerald-600 mx-auto" />
                <h3 className="font-serif font-bold text-sm text-[#16130F]">No Source Conflicts Detected</h3>
                <p className="text-xs font-serif text-[#7B766C] max-w-md mx-auto">
                  All uploaded documents in this course are factually aligned. No contradictory formulas, numbers, or parameters were found.
                </p>
              </Card>
            ) : (
              <div className="space-y-4">
                {conflicts.map((c: any) => (
                  <Card key={c.id} className="p-5 space-y-3.5 border-amber-200 bg-white">
                    <div className="flex items-center justify-between border-b border-[#EAE6DF] pb-2">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
                          {c.type?.replace(/_/g, ' ') || 'Conflict'}
                        </span>
                        <span className="font-serif font-bold text-sm text-[#16130F]">
                          Discrepancy on: {c.attribute}
                        </span>
                      </div>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${c.status === 'resolved' ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'}`}>
                        {c.status === 'resolved' ? `Resolved (Trusted: ${c.trusted_source})` : 'Active Disagreement'}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      {/* Claim A */}
                      <div className="p-3.5 rounded-xl border border-[#EAE6DF] bg-[#FAF8F5] space-y-2">
                        <div className="flex items-center justify-between font-mono text-[11px] text-[#1D4ED8] font-bold">
                          <span>{c.claim_a?.document_name}</span>
                          <span>Page {c.claim_a?.page_number}</span>
                        </div>
                        <p className="font-serif text-[#16130F] font-semibold">
                          Claim: "{c.claim_a?.statement}"
                        </p>
                        <p className="font-serif text-[11px] text-[#5E5A52] italic line-clamp-2">
                          "{c.claim_a?.snippet}"
                        </p>
                        <button
                          type="button"
                          onClick={() => handleResolveConflict(c.id, c.claim_a?.document_name)}
                          className={`w-full mt-2 py-1.5 px-3 rounded-lg text-[11px] font-mono font-bold transition ${
                            c.trusted_source === c.claim_a?.document_name 
                              ? 'bg-emerald-600 text-white' 
                              : 'bg-white border border-[#EAE6DF] text-[#16130F] hover:bg-emerald-50 hover:border-emerald-300'
                          }`}
                        >
                          {c.trusted_source === c.claim_a?.document_name ? '✓ Trusted Source' : `Trust ${c.claim_a?.document_name}`}
                        </button>
                      </div>

                      {/* Claim B */}
                      <div className="p-3.5 rounded-xl border border-[#EAE6DF] bg-[#FAF8F5] space-y-2">
                        <div className="flex items-center justify-between font-mono text-[11px] text-[#1D4ED8] font-bold">
                          <span>{c.claim_b?.document_name}</span>
                          <span>Page {c.claim_b?.page_number}</span>
                        </div>
                        <p className="font-serif text-[#16130F] font-semibold">
                          Claim: "{c.claim_b?.statement}"
                        </p>
                        <p className="font-serif text-[11px] text-[#5E5A52] italic line-clamp-2">
                          "{c.claim_b?.snippet}"
                        </p>
                        <button
                          type="button"
                          onClick={() => handleResolveConflict(c.id, c.claim_b?.document_name)}
                          className={`w-full mt-2 py-1.5 px-3 rounded-lg text-[11px] font-mono font-bold transition ${
                            c.trusted_source === c.claim_b?.document_name 
                              ? 'bg-emerald-600 text-white' 
                              : 'bg-white border border-[#EAE6DF] text-[#16130F] hover:bg-emerald-50 hover:border-emerald-300'
                          }`}
                        >
                          {c.trusted_source === c.claim_b?.document_name ? '✓ Trusted Source' : `Trust ${c.claim_b?.document_name}`}
                        </button>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        ) : activeTab === 'alignments' ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-serif font-bold text-base text-[#16130F]">
                  Lecture-to-Slide Multimodal Alignment
                </h3>
                <p className="font-serif text-xs text-[#5E5A52]">
                  Dynamic programming alignment linking lecture video timecodes to corresponding slide deck pages with monotonic progression constraint.
                </p>
              </div>
              <button
                type="button"
                onClick={loadAlignments}
                disabled={loadingAlignments}
                className="px-3 py-1.5 rounded-lg border border-[#EAE6DF] bg-white text-xs font-mono font-bold text-[#16130F] hover:bg-[#FAF8F5] transition flex items-center space-x-1.5 cursor-pointer"
              >
                <RefreshCw className={`h-3 w-3 text-[#1D4ED8] ${loadingAlignments ? 'animate-spin' : ''}`} />
                <span>Re-align</span>
              </button>
            </div>

            {loadingAlignments ? (
              <div className="py-16 text-center text-xs font-mono text-[#7B766C] flex items-center justify-center space-x-2">
                <RefreshCw className="h-4 w-4 animate-spin text-[#1D4ED8]" />
                <span>Computing monotonic dynamic programming alignment across video windows and presentation slides...</span>
              </div>
            ) : alignments.length === 0 ? (
              <Card className="p-8 text-center space-y-3">
                <Video className="h-8 w-8 text-slate-400 mx-auto" />
                <h3 className="font-serif text-base font-bold text-[#16130F]">No Video or Slide Decks Found</h3>
                <p className="font-serif text-xs text-[#7B766C] max-w-md mx-auto">
                  Upload lecture video transcripts (or YouTube links) and presentation slides (.pptx/.pdf) to align timestamps to slide pages.
                </p>
              </Card>
            ) : (
              <div className="grid grid-cols-1 gap-3.5">
                {alignments.map((a: any, aIdx: number) => (
                  <Card key={a.id || aIdx} className="p-4 border-[#EAE6DF] bg-white hover:border-[#1D4ED8]/40 transition space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#EAE6DF] pb-2.5">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-rose-50 text-rose-800 border border-rose-200 flex items-center space-x-1">
                          <Clock className="h-3 w-3" />
                          <span>{a.timestamp_label || '00:00'}</span>
                        </span>
                        <span className="font-serif font-bold text-xs text-[#16130F] truncate max-w-xs sm:max-w-md">
                          {a.video_title}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200 flex items-center space-x-1">
                          <Layers className="h-3 w-3" />
                          <span>Slide {a.slide_number} ({a.slide_document})</span>
                        </span>
                        <span className="font-mono text-[10px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                          Match: {Math.round((a.similarity_score || 0.8) * 100)}%
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      <div className="p-2.5 rounded-lg bg-[#FAF8F5] border border-[#EAE6DF] space-y-1">
                        <span className="font-mono text-[10px] text-[#7B766C] uppercase font-bold block">Spoken Lecture Transcript:</span>
                        <p className="font-serif text-[#16130F] italic text-[11px] line-clamp-2">
                          "{a.transcript_snippet}"
                        </p>
                      </div>
                      <div className="p-2.5 rounded-lg bg-[#FAF8F5] border border-[#EAE6DF] space-y-1">
                        <span className="font-mono text-[10px] text-[#7B766C] uppercase font-bold block">Presentation Slide Content:</span>
                        <p className="font-serif text-[#16130F] text-[11px] line-clamp-2">
                          {a.slide_snippet}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-1">
                      <span className="text-xs font-mono font-bold text-[#1D4ED8] flex items-center space-x-1 cursor-pointer hover:underline">
                        <Video className="h-3.5 w-3.5" />
                        <span>Watch this part of the lecture ({a.timestamp_label})</span>
                      </span>

                      <span className="text-xs font-mono font-bold text-[#7B766C] flex items-center space-x-1 cursor-pointer hover:text-[#16130F]">
                        <Layers className="h-3.5 w-3.5" />
                        <span>Slides for this moment (Slide {a.slide_number})</span>
                      </span>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        ) : (
        <>
        {/* Search & Filter Bar */}
        <Card className="p-3 shadow-none">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto flex-1">
              <div className="relative w-full sm:w-80">
                <Search className="h-3.5 w-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#7B766C]" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search titles, authors, or extracted concepts..."
                  className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg bg-[#FAF8F5] border border-[#EAE6DF] text-[#16130F] placeholder-[#7B766C] focus:outline-none focus:ring-2 focus:ring-[#1D4ED8]/20 focus:border-[#1D4ED8]"
                />
              </div>

              {courses && courses.length > 0 && (
                <div className="flex items-center space-x-2 text-xs">
                  <span className="text-[#7B766C] font-mono text-[11px] uppercase">Course:</span>
                  <select
                    value={selectedCourseId}
                    onChange={(e) => setSelectedCourseId(e.target.value)}
                    className="py-1 px-3 rounded-lg bg-[#FAF8F5] border border-[#EAE6DF] text-[#16130F] text-xs font-medium focus:outline-none focus:ring-1 focus:ring-[#1D4ED8]"
                  >
                    <option value="all">All Registered Courses</option>
                    {courses.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name || c.title}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <div className="flex items-center space-x-3 w-full sm:w-auto justify-between sm:justify-end text-xs text-[#5E5A52]">
              <span className="font-mono text-[11px]">{filteredFiles.length} manuscripts</span>
              {selectedIds.length > 0 && (
                <div className="flex items-center space-x-2">
                  <span className="font-mono font-semibold text-[#1D4ED8]">
                    ({selectedIds.length} selected)
                  </span>
                  <button
                    onClick={async () => {
                      for (const id of selectedIds) {
                        const link = document.createElement('a');
                        link.href = api.getDocumentDownloadUrl(id);
                        link.download = '';
                        link.target = '_blank';
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                      }
                    }}
                    className="px-2.5 py-1 rounded-lg bg-[#FAF8F5] text-[#16130F] hover:bg-[#F3EFE8] border border-[#EAE6DF] text-xs font-medium flex items-center space-x-1 transition"
                    title="Download Selected Files"
                  >
                    <Download className="h-3 w-3 text-[#5E5A52]" />
                    <span>Download</span>
                  </button>
                  <button
                    onClick={async () => {
                      if (!window.confirm(`Delete ${selectedIds.length} selected document(s)?`)) return;
                      for (const id of selectedIds) {
                        await api.deleteUserDocument(id).catch(() => {});
                      }
                      setFiles((prev) => prev.filter((f) => !selectedIds.includes(f.id)));
                      setSelectedIds([]);
                    }}
                    className="px-2.5 py-1 rounded-lg bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 text-xs font-medium flex items-center space-x-1 transition"
                    title="Delete Selected Files"
                  >
                    <Trash2 className="h-3 w-3" />
                    <span>Delete</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* Files Table */}
        <Card className="p-0 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#FAF8F5] border-b border-[#EAE6DF] text-[10px] font-mono uppercase tracking-wider text-[#7B766C]">
                  <th className="p-3.5 w-10 text-center">
                    <button onClick={toggleSelectAll} className="text-[#7B766C] hover:text-[#16130F] transition">
                      {selectedIds.length === files.length && files.length > 0 ? (
                        <CheckSquare className="h-4 w-4 text-[#1D4ED8]" />
                      ) : (
                        <Square className="h-4 w-4" />
                      )}
                    </button>
                  </th>
                  <th className="p-3.5 font-medium">Source Document</th>
                  <th className="p-3.5 w-16 font-medium text-center">Type</th>
                  <th className="p-3.5 w-20 font-medium text-center">Chunks</th>
                  <th className="p-3.5 w-20 font-medium text-center">Concepts</th>
                  <th className="p-3.5 w-36 font-medium">Status & Health</th>
                  <th className="p-3.5 text-right w-80 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EAE6DF] text-xs">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-[#7B766C] font-mono text-xs">
                      Indexing files...
                    </td>
                  </tr>
                ) : filteredFiles.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="p-12 text-center text-[#7B766C]">
                      <File className="h-8 w-8 mx-auto mb-2 text-[#7B766C]/40" />
                      <p className="font-serif text-sm text-[#16130F]">No manuscripts matched "{searchQuery}"</p>
                      <p className="text-xs text-[#5E5A52] mt-1">Upload a PDF, slide deck, or problem set to begin.</p>
                    </td>
                  </tr>
                ) : (
                  filteredFiles.map((file) => {
                    const isSelected = selectedIds.includes(file.id);
                    const isReanalyzing = reanalyzingDocId === file.id;
                    const statusNormalized = (file.status || 'processed').toLowerCase();

                    return (
                      <tr
                        key={file.id}
                        className={`hover:bg-[#FAF8F5]/80 transition ${
                          isSelected ? 'bg-[#FFE45C]/10' : ''
                        }`}
                      >
                        <td className="p-3.5 text-center">
                          <button
                            onClick={() => toggleSelect(file.id)}
                            className="text-[#7B766C] hover:text-[#16130F]"
                          >
                            {isSelected ? (
                              <CheckSquare className="h-4 w-4 text-[#1D4ED8]" />
                            ) : (
                              <Square className="h-4 w-4" />
                            )}
                          </button>
                        </td>

                        <td className="p-3.5">
                          <div className="flex items-start space-x-3">
                            <div className="p-2 rounded-lg bg-[#FAF8F5] text-[#1D4ED8] border border-[#EAE6DF] shrink-0 mt-0.5">
                              <FileText className="h-4 w-4" />
                            </div>
                            <div className="space-y-1">
                              <div className="font-serif font-semibold text-sm text-[#16130F] hover:text-[#1D4ED8] transition cursor-pointer">
                                {file.name}
                              </div>
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span className="font-mono text-[#7B766C] text-[10px]">
                                  {file.size} • {file.uploadDate}
                                </span>
                                {file.topics.slice(0, 2).map((t, idx) => (
                                  <span
                                    key={idx}
                                    className="px-1.5 py-0.5 rounded text-[10px] bg-[#FAF8F5] text-[#5E5A52] border border-[#EAE6DF] font-mono"
                                  >
                                    {t}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>
                        </td>

                        {/* File Type */}
                        <td className="p-3.5 text-center whitespace-nowrap">
                          <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-[#F3EFE8] text-[#16130F] border border-[#EAE6DF]">
                            {file.type}
                          </span>
                        </td>

                        {/* Chunk Count */}
                        <td className="p-3.5 text-center font-mono font-bold text-xs text-[#16130F] whitespace-nowrap">
                          {file.chunk_count}
                        </td>

                        {/* Concept Count */}
                        <td className="p-3.5 text-center font-mono font-bold text-xs text-[#1D4ED8] whitespace-nowrap">
                          {file.concept_count}
                        </td>

                        {/* Status & Health */}
                        <td className="p-3.5 whitespace-nowrap">
                          <div className="space-y-1">
                            {statusNormalized === 'processed' ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]">
                                <Check className="h-3 w-3" />
                                <span>processed</span>
                              </span>
                            ) : statusNormalized === 'needs analysis' ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-[#FFFBEB] text-[#D97706] border border-[#FDE68A]">
                                <AlertCircle className="h-3 w-3" />
                                <span>needs analysis</span>
                              </span>
                            ) : statusNormalized === 'processing' ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-[#EFF6FF] text-[#1D4ED8] border border-[#BFDBFE]">
                                <RefreshCw className="h-3 w-3 animate-spin" />
                                <span>processing</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-[#FEF2F2] text-[#DC2626] border border-[#FECACA]">
                                <AlertCircle className="h-3 w-3" />
                                <span>failed</span>
                              </span>
                            )}
                            {file.last_error && (
                              <p className="text-[10px] font-mono text-red-600 truncate max-w-[140px]" title={file.last_error}>
                                {file.last_error}
                              </p>
                            )}
                          </div>
                        </td>

                        {/* Actions */}
                        <td className="p-3.5 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end space-x-1.5">
                            <button
                              onClick={() => handleReanalyzeDoc(file.id)}
                              disabled={isReanalyzing}
                              title="Re-run analysis for this document"
                              className="px-2 py-1 rounded-md bg-[#FAF8F5] hover:bg-[#EFF6FF] hover:text-[#1D4ED8] text-[#16130F] text-[11px] font-mono border border-[#EAE6DF] transition flex items-center gap-1 cursor-pointer disabled:opacity-50"
                            >
                              <RefreshCw className={`h-3 w-3 text-[#1D4ED8] ${isReanalyzing ? 'animate-spin' : ''}`} />
                              <span>{isReanalyzing ? 'Running...' : 'Re-run analysis'}</span>
                            </button>
                            <a
                              href={api.getDocumentDownloadUrl(file.id)}
                              download={file.name}
                              target="_blank"
                              rel="noreferrer"
                              title="Download File"
                              className="p-1 rounded-md text-[#7B766C] hover:text-[#1D4ED8] hover:bg-[#FAF8F5] transition"
                            >
                              <Download className="h-3.5 w-3.5" />
                            </a>
                            <button
                              onClick={() => handleDelete(file.id)}
                              title="Delete File"
                              className="p-1 rounded-md text-[#7B766C] hover:text-red-600 hover:bg-red-50 transition"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Table Bottom / Go1 Navigation */}
          <div className="p-4 bg-[#FAF8F5] border-t border-[#EAE6DF] flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
            <span className="text-[#5E5A52] font-mono text-[11px]">
              Displaying 1 to {filteredFiles.length} of {filteredFiles.length} manuscripts
            </span>
            <div className="flex items-center space-x-2">
              <span className="px-2.5 py-1 rounded-md border border-[#EAE6DF] bg-white text-[#16130F] font-mono text-[11px]">
                Page 1 of 1
              </span>
              <button disabled className="px-3 py-1 rounded-md border border-[#EAE6DF] bg-white text-[#7B766C] opacity-50 cursor-not-allowed text-xs">
                Previous
              </button>
              <button disabled className="px-3 py-1 rounded-md border border-[#EAE6DF] bg-white text-[#7B766C] opacity-50 cursor-not-allowed text-xs">
                Next
              </button>
            </div>
          </div>
        </Card>
        </>
        )}
      </div>
    </div>
  );
};

