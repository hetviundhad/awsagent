import React, { useState, useEffect, useMemo } from 'react';
import { 
  X, UploadCloud, Search, CheckSquare, Square, 
  HelpCircle, Sliders, ChevronDown, ChevronUp, AlertCircle, 
  Loader2, Sparkles, BookOpen, Layers, CheckCircle2 
} from 'lucide-react';
import { api } from '../services/api';
import { Course } from '../types';

export interface DocumentItem {
  id: string;
  name: string;
  size: string;
  date: string;
  topics?: string[];
  type?: string;
  chunks_count?: number;
}

interface QuizModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeCourse: Course | null;
  userDocuments: DocumentItem[];
  onQuizCreated: (quizData: any) => void;
  onDocumentUploaded?: () => void;
}

export const QuizModal: React.FC<QuizModalProps> = ({
  isOpen,
  onClose,
  activeCourse,
  userDocuments,
  onQuizCreated,
  onDocumentUploaded,
}) => {
  // Context source tab: 'course' or 'documents'
  const [contextSource, setContextSource] = useState<'course' | 'documents'>('course');

  // Selected document IDs (Checkboxes)
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  
  // Search & Type Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<'ALL' | 'PDF' | 'PPTX' | 'DOCX' | 'VIDEO'>('ALL');

  // Focus topics multi-select
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);

  // Generation options
  const [questionCount, setQuestionCount] = useState<number>(5);
  const [questionTypes, setQuestionTypes] = useState<string[]>(['mcq']);
  const [difficulty, setDifficulty] = useState<string>('Adaptive');
  const [language, setLanguage] = useState<string>('English');
  const [timeLimitMinutes, setTimeLimitMinutes] = useState<number | ''>('');
  const [practicalRatio, setPracticalRatio] = useState<number>(0.7);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Upload state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);

  // Quota state
  const [quota, setQuota] = useState<{ quota_limit: number | null; quizzes_used: number; remaining: number | null } | null>(null);

  // Generation progress & error
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStep, setGenerationStep] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch real quota on open
  useEffect(() => {
    if (isOpen) {
      setErrorMessage(null);
      api.getQuizQuota()
        .then((q) => setQuota(q))
        .catch(() => setQuota(null));
    }
  }, [isOpen]);

  // Default select all available documents when modal opens
  useEffect(() => {
    if (isOpen && userDocuments.length > 0 && selectedDocIds.length === 0) {
      setSelectedDocIds(userDocuments.map(d => d.id));
    }
  }, [isOpen, userDocuments]);

  // Filter documents by name and type
  const filteredDocuments = useMemo(() => {
    return userDocuments.filter((doc) => {
      const name = doc.name.toLowerCase();
      const matchesSearch = !searchQuery || name.includes(searchQuery.toLowerCase());
      
      if (!matchesSearch) return false;
      if (typeFilter === 'ALL') return true;
      if (typeFilter === 'PDF') return name.endsWith('.pdf');
      if (typeFilter === 'PPTX') return name.endsWith('.pptx') || name.endsWith('.ppt');
      if (typeFilter === 'DOCX') return name.endsWith('.docx') || name.endsWith('.doc');
      if (typeFilter === 'VIDEO') return name.includes('video') || name.includes('youtube') || name.endsWith('.mp4');
      return true;
    });
  }, [userDocuments, searchQuery, typeFilter]);

  // Aggregate real topics from selected documents
  const availableTopics = useMemo(() => {
    const topicSet = new Set<string>();
    const activeDocs = userDocuments.filter(d => selectedDocIds.includes(d.id));
    activeDocs.forEach(d => {
      if (Array.isArray(d.topics)) {
        d.topics.forEach(t => {
          if (t && t.trim()) topicSet.add(t.trim());
        });
      }
    });
    // Fallback to activeCourse topics if document topics are empty
    if (topicSet.size === 0 && (activeCourse as any)?.topics) {
      ((activeCourse as any).topics as any[]).forEach((t: any) => topicSet.add(typeof t === 'string' ? t : t?.name || ''));
    }
    return Array.from(topicSet);
  }, [userDocuments, selectedDocIds, activeCourse]);

  // Handlers for document selection
  const handleToggleDoc = (docId: string) => {
    setSelectedDocIds((prev) => 
      prev.includes(docId) ? prev.filter(id => id !== docId) : [...prev, docId]
    );
  };

  const handleSelectAll = () => {
    const allFilteredIds = filteredDocuments.map(d => d.id);
    const allSelected = allFilteredIds.every(id => selectedDocIds.includes(id));
    if (allSelected) {
      setSelectedDocIds(prev => prev.filter(id => !allFilteredIds.includes(id)));
    } else {
      setSelectedDocIds(prev => Array.from(new Set([...prev, ...allFilteredIds])));
    }
  };

  const handleToggleTopic = (topic: string) => {
    setSelectedTopics(prev => 
      prev.includes(topic) ? prev.filter(t => t !== topic) : [...prev, topic]
    );
  };

  const handleToggleQuestionType = (t: string) => {
    setQuestionTypes(prev => {
      if (prev.includes(t)) {
        if (prev.length === 1) return prev; // Keep at least one type
        return prev.filter(item => item !== t);
      }
      return [...prev, t];
    });
  };

  // Upload handler with indexing progress
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeCourse) return;

    try {
      setIsUploading(true);
      setUploadStatus(`Indexing ${file.name}...`);
      setErrorMessage(null);

      const taskId = `task_${Date.now()}`;
      await api.uploadDocument(activeCourse.id, file, taskId);
      
      setUploadStatus('Ready and indexed!');
      if (onDocumentUploaded) {
        await onDocumentUploaded();
      }
      setTimeout(() => {
        setIsUploading(false);
        setUploadStatus(null);
      }, 1200);
    } catch (err: any) {
      setIsUploading(false);
      setUploadStatus(null);
      setErrorMessage(err.message || 'File upload and indexing failed');
    }
  };

  // Quiz generation handler calling unified verified pipeline
  const handleGenerate = async () => {
    if (!activeCourse) {
      setErrorMessage('Please select or create an active course first');
      return;
    }

    try {
      setIsGenerating(true);
      setErrorMessage(null);
      setGenerationStep(`Sampling chunks across ${selectedDocIds.length || userDocuments.length} document(s)...`);

      const targetDocIds = selectedDocIds.length > 0 
        ? selectedDocIds 
        : userDocuments.map(d => d.id);

      // Call verified assessment pipeline
      setGenerationStep(`Synthesizing & verifying ${questionCount} questions at ${difficulty} level...`);
      const assessmentData = await api.generateAssessment({
        course_id: activeCourse.id,
        document_ids: targetDocIds,
        topic_ids: selectedTopics.length > 0 ? selectedTopics : undefined,
        question_count: questionCount,
        difficulty: difficulty,
        types: questionTypes,
        language: language,
        mode: difficulty === 'Adaptive' ? 'adaptive' : 'standard',
        practical_ratio: practicalRatio
      });

      setGenerationStep('Finalizing coverage report & verified questions...');
      setIsGenerating(false);
      onClose();
      onQuizCreated(assessmentData);
    } catch (err: any) {
      setIsGenerating(false);
      setErrorMessage(err.message || 'Failed to generate verified questions. Please try again.');
    }
  };

  if (!isOpen) return null;

  const isAllFilteredSelected = filteredDocuments.length > 0 && 
    filteredDocuments.every(d => selectedDocIds.includes(d.id));

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4 animate-in fade-in">
      <div className="bg-white rounded-3xl max-w-2xl w-full p-5 sm:p-7 space-y-5 shadow-2xl relative max-h-[92vh] flex flex-col border border-slate-200">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          disabled={isGenerating}
          className="absolute top-5 right-5 p-1.5 rounded-full text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition cursor-pointer"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Header */}
        <div className="shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
              Verified Assessment Pipeline
            </span>
            {activeCourse && (
              <span className="text-[10px] font-mono text-slate-500">
                Course: <strong>{activeCourse.name}</strong>
              </span>
            )}
          </div>
          <h2 className="text-xl font-bold text-slate-900 mt-1">Start a New Quiz</h2>
          <p className="text-xs text-slate-500">
            Select course documents to synthesize verified, grounded questions with balanced coverage.
          </p>
        </div>

        {/* Error Banner */}
        {errorMessage && (
          <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-start gap-2 shrink-0">
            <AlertCircle className="h-4 w-4 shrink-0 text-red-600 mt-0.5" />
            <div className="flex-1">{errorMessage}</div>
          </div>
        )}

        {/* Modal Scrollable Body */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-1">
          
          {/* Source Tabs */}
          <div className="grid grid-cols-2 gap-2.5">
            <button
              type="button"
              onClick={() => setContextSource('course')}
              className={`p-3 rounded-xl border text-left text-xs transition cursor-pointer ${
                contextSource === 'course'
                  ? 'border-blue-600 bg-blue-50/60 text-blue-900 font-semibold shadow-xs'
                  : 'border-slate-200 hover:bg-slate-50 text-slate-700'
              }`}
            >
              <div className="font-bold flex items-center gap-1.5">
                <BookOpen className="h-3.5 w-3.5 text-blue-600" />
                <span>From Course Documents</span>
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                Multi-select from {userDocuments.length} indexed documents
              </div>
            </button>

            <button
              type="button"
              onClick={() => setContextSource('documents')}
              className={`p-3 rounded-xl border text-left text-xs transition cursor-pointer ${
                contextSource === 'documents'
                  ? 'border-blue-600 bg-blue-50/60 text-blue-900 font-semibold shadow-xs'
                  : 'border-slate-200 hover:bg-slate-50 text-slate-700'
              }`}
            >
              <div className="font-bold flex items-center gap-1.5">
                <UploadCloud className="h-3.5 w-3.5 text-blue-600" />
                <span>Upload New Material</span>
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                Upload & index PDFs, PPTX, or DOCX files
              </div>
            </button>
          </div>

          {/* Document Upload Zone (if 'documents' tab or quick upload) */}
          {contextSource === 'documents' && (
            <div className="space-y-2">
              <label className="border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-2xl p-4 flex flex-col items-center justify-center text-center cursor-pointer bg-slate-50 hover:bg-blue-50/30 transition">
                <UploadCloud className="h-6 w-6 text-blue-600 mb-1" />
                <span className="text-xs font-semibold text-slate-700">
                  {isUploading ? uploadStatus : 'Click or drop files here to upload & index'}
                </span>
                <span className="text-[10px] text-slate-400 mt-0.5">
                  Supports PDF, PPTX, DOCX, TXT. Automatically extracts & tags concepts.
                </span>
                <input
                  type="file"
                  className="hidden"
                  accept=".pdf,.pptx,.docx,.txt"
                  disabled={isUploading}
                  onChange={handleFileUpload}
                />
              </label>
              {isUploading && (
                <div className="flex items-center justify-center gap-2 text-xs font-mono text-blue-700 bg-blue-50 py-2 rounded-xl border border-blue-200">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>{uploadStatus}</span>
                </div>
              )}
            </div>
          )}

          {/* Document Selection Section */}
          <div className="space-y-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <label className="text-xs font-bold text-slate-800">
                  Select Documents to Cover
                </label>
                <span className="text-[11px] font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200">
                  {selectedDocIds.length} of {userDocuments.length} selected
                </span>
              </div>

              {/* Type filter tabs */}
              <div className="flex items-center gap-1 text-[10px] font-mono bg-slate-100 p-0.5 rounded-lg">
                {(['ALL', 'PDF', 'PPTX', 'DOCX'] as const).map(tab => (
                  <button
                    key={tab}
                    type="button"
                    onClick={() => setTypeFilter(tab)}
                    className={`px-2 py-0.5 rounded font-bold transition cursor-pointer ${
                      typeFilter === tab ? 'bg-white text-blue-600 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>
            </div>

            {/* Search filter input + Select all bar */}
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="h-3.5 w-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Filter documents by title..."
                  className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <button
                type="button"
                onClick={handleSelectAll}
                className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 flex items-center gap-1.5 cursor-pointer shrink-0"
              >
                {isAllFilteredSelected ? (
                  <CheckSquare className="h-3.5 w-3.5 text-blue-600" />
                ) : (
                  <Square className="h-3.5 w-3.5 text-slate-400" />
                )}
                <span>{isAllFilteredSelected ? 'Deselect All' : 'Select All'}</span>
              </button>
            </div>

            {/* Document Checkbox Table */}
            <div className="border border-slate-200 rounded-2xl overflow-hidden max-h-48 overflow-y-auto divide-y divide-slate-100 text-xs bg-white">
              {filteredDocuments.length === 0 ? (
                <div className="p-4 text-center text-slate-400 text-xs">
                  No documents match your filter criteria.
                </div>
              ) : (
                filteredDocuments.map((doc) => {
                  const isChecked = selectedDocIds.includes(doc.id);
                  return (
                    <div
                      key={doc.id}
                      onClick={() => handleToggleDoc(doc.id)}
                      className={`p-2.5 flex items-center justify-between cursor-pointer transition select-none ${
                        isChecked ? 'bg-blue-50/40 text-blue-950 font-medium' : 'hover:bg-slate-50 text-slate-700'
                      }`}
                    >
                      <div className="flex items-center space-x-2.5 min-w-0 pr-2">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {}}
                          className="rounded text-blue-600 focus:ring-blue-500 h-4 w-4 accent-blue-600 cursor-pointer"
                        />
                        <div className="min-w-0">
                          <div className="truncate font-medium text-xs text-slate-800">{doc.name}</div>
                          {doc.topics && doc.topics.length > 0 && (
                            <div className="text-[10px] text-slate-400 truncate mt-0.5">
                              {doc.topics.slice(0, 3).join(' • ')}
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <span className="text-[10px] font-mono text-slate-400 block">{doc.size || 'Doc'}</span>
                        {doc.chunks_count ? (
                          <span className="text-[9px] font-mono text-emerald-600 block">{doc.chunks_count} chunks</span>
                        ) : null}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Focus Topics Multi-select (Optional) */}
          {availableTopics.length > 0 && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-700">
                  Focus Topics / Concepts (Optional)
                </label>
                <span className="text-[10px] text-slate-400 font-mono">
                  {selectedTopics.length > 0 ? `${selectedTopics.length} selected` : 'All topics covered'}
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto p-1.5 rounded-xl border border-slate-200 bg-slate-50/50">
                {availableTopics.map(topic => {
                  const isSel = selectedTopics.includes(topic);
                  return (
                    <button
                      key={topic}
                      type="button"
                      onClick={() => handleToggleTopic(topic)}
                      className={`px-2 py-0.5 rounded-full text-[11px] font-medium transition cursor-pointer border ${
                        isSel 
                          ? 'bg-blue-600 text-white border-blue-600' 
                          : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100'
                      }`}
                    >
                      {topic}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Core Configuration Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {/* Question Count */}
            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1">
                Question Count
              </label>
              <input
                type="number"
                min={3}
                max={25}
                value={questionCount}
                onChange={(e) => setQuestionCount(Math.min(25, Math.max(3, Number(e.target.value) || 5)))}
                className="w-full px-2.5 py-1.5 text-xs rounded-xl border border-slate-200 bg-white font-mono font-bold"
              />
            </div>

            {/* Difficulty */}
            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1">
                Difficulty
              </label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs rounded-xl border border-slate-200 bg-white font-medium"
              >
                <option value="Adaptive">Adaptive (BKT-Calibrated)</option>
                <option value="Beginner">Beginner (Foundational)</option>
                <option value="Intermediate">Intermediate (Application)</option>
                <option value="Advanced">Advanced (Critical Synthesis)</option>
              </select>
            </div>

            {/* Language */}
            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1">
                Language
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs rounded-xl border border-slate-200 bg-white font-medium"
              >
                <option value="English">English</option>
                <option value="Hindi">Hindi (हिंदी)</option>
                <option value="Hinglish">Hinglish</option>
              </select>
            </div>

            {/* Time limit (optional) */}
            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1">
                Time Limit (Mins)
              </label>
              <input
                type="number"
                min={1}
                max={60}
                placeholder="Untimed"
                value={timeLimitMinutes}
                onChange={(e) => setTimeLimitMinutes(e.target.value ? Number(e.target.value) : '')}
                className="w-full px-2.5 py-1.5 text-xs rounded-xl border border-slate-200 bg-white font-mono"
              />
            </div>
          </div>

          {/* Question Types (Checkboxes) */}
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-slate-700">Question Types</label>
            <div className="grid grid-cols-3 gap-2 text-xs">
              {[
                { id: 'mcq', label: 'Multiple Choice (MCQ)' },
                { id: 'short_answer', label: 'Short Answer' },
                { id: 'numerical', label: 'Numerical / SymPy' },
              ].map(t => {
                const checked = questionTypes.includes(t.id);
                return (
                  <label
                    key={t.id}
                    onClick={() => handleToggleQuestionType(t.id)}
                    className={`flex items-center gap-2 p-2 rounded-xl border cursor-pointer select-none transition ${
                      checked ? 'bg-blue-50/50 border-blue-400 text-blue-900 font-semibold' : 'border-slate-200 text-slate-600'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => {}}
                      className="rounded text-blue-600 focus:ring-blue-500 accent-blue-600"
                    />
                    <span>{t.label}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Advanced Options Accordion */}
          <div className="border border-slate-200 rounded-2xl overflow-hidden">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full p-2.5 flex items-center justify-between text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 transition cursor-pointer"
            >
              <div className="flex items-center gap-1.5">
                <Sliders className="h-3.5 w-3.5 text-slate-500" />
                <span>Pedagogy & Rigor Settings</span>
              </div>
              {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>

            {showAdvanced && (
              <div className="p-3.5 space-y-3 bg-white text-xs border-t border-slate-200">
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="font-semibold text-slate-700">
                      Practical Scenarios vs Pure Theory Ratio
                    </label>
                    <span className="font-mono text-[11px] text-blue-600 font-bold">
                      {Math.round(practicalRatio * 100)}% Practical / {Math.round((1 - practicalRatio) * 100)}% Theory
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={practicalRatio}
                    onChange={(e) => setPracticalRatio(Number(e.target.value))}
                    className="w-full accent-blue-600"
                  />
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    Controls Bloom cognitive level: higher favors concrete situational problems, lower favors factual definitions.
                  </p>
                </div>
              </div>
            )}
          </div>

        </div>

        {/* Footer with Real Quota & Action Button */}
        <div className="pt-3 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3 shrink-0">
          <div>
            {quota && typeof quota.quota_limit === 'number' && quota.quota_limit > 0 ? (
              <span className="text-xs text-slate-600 font-mono">
                {quota.quizzes_used ?? 0} of {quota.quota_limit} free quizzes used
              </span>
            ) : null}
          </div>

          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            <button
              type="button"
              onClick={onClose}
              disabled={isGenerating}
              className="flex-1 sm:flex-initial px-4 py-2 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 font-semibold text-xs transition cursor-pointer"
            >
              Cancel
            </button>

            <button
              type="button"
              onClick={handleGenerate}
              disabled={isGenerating || isUploading || (selectedDocIds.length === 0 && userDocuments.length === 0)}
              className="flex-1 sm:flex-initial px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold text-xs transition shadow-sm flex items-center justify-center gap-2 cursor-pointer"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>{generationStep || 'Generating...'}</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>Generate Verified Quiz</span>
                </>
              )}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
