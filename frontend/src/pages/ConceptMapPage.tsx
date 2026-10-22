import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  GitFork, Brain, Zap, ArrowRight, ShieldCheck, Layers, BookOpen, X, Lock, Unlock,
  CheckCircle2, AlertTriangle, AlertCircle, FileText, Presentation, Video, 
  ExternalLink, Globe, Sparkles 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../services/api';
import { SourceViewerModal } from '../components/SourceViewerModal';
import { WhyAmIStuckModal } from '../components/WhyAmIStuckModal';
import { TeachBackModal } from '../components/TeachBackModal';
import { Citation } from '../types';
import { Button, Card, Pill, Modal } from '../components/ui';

interface ConceptMapPageProps {
  activeCourseId: string;
  studentId?: string;
}

export const ConceptMapPage: React.FC<ConceptMapPageProps> = ({ 
  activeCourseId, 
  studentId = 'default_student' 
}) => {
  const navigate = useNavigate();
  const [mapData, setMapData] = useState<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [loading, setLoading] = useState(true);
  const [generatingQuiz, setGeneratingQuiz] = useState(false);
  const [isStuckModalOpen, setIsStuckModalOpen] = useState(false);
  const [isTeachBackOpen, setIsTeachBackOpen] = useState(false);

  
  // Interactive 60% threshold calibration slider for testing unlock moment
  const [calibrationBoost, setCalibrationBoost] = useState(0);
  const [justUnlockedNodeId, setJustUnlockedNodeId] = useState<string | null>(null);

  const effectiveCourseId = activeCourseId || localStorage.getItem('studymind_active_course') || '';

  useEffect(() => {
    loadMap();
  }, [effectiveCourseId]);

  const loadMap = async () => {
    setLoading(true);
    try {
      let targetId = effectiveCourseId;
      if (!targetId) {
        const cList = await api.getCourses().catch(() => []);
        if (cList && cList.length > 0) {
          targetId = cList[0].id;
          localStorage.setItem('studymind_active_course', targetId);
        }
      }
      if (targetId) {
        const data = await api.getConceptMap(targetId);
        setMapData(data || { nodes: [], edges: [] });
        if (data?.nodes?.length > 0) {
          const lockedNode = data.nodes.find((n: any) => n.is_locked);
          setSelectedNode(lockedNode || data.nodes[2] || data.nodes[0]);
        }
      } else {
        setMapData({ nodes: [], edges: [] });
      }
    } catch (e) {
      console.error(e);
      setMapData({ nodes: [], edges: [] });
    } finally {
      setLoading(false);
    }
  };

  const handleStudyPrerequisite = (node: any) => {
    const prereq = node.blocking_prerequisite;
    const prereqName = prereq?.name || 'the foundational prerequisite';
    const prefilledMsg = `I want to strengthen my understanding of ${prereqName} as a foundation for ${node.name}. Can you explain ${prereqName} and its core principles step-by-step?`;
    navigate(`/tutor?concept=${encodeURIComponent(prereqName)}&message=${encodeURIComponent(prefilledMsg)}&mode=Guided%20Practice`);
  };

  const handlePracticeConcept = (node: any) => {
    navigate(`/tutor?concept=${encodeURIComponent(node.name)}&mode=Practice%20Mode`);
  };

  const handleGenerateConceptAssessment = async (node: any) => {
    setGeneratingQuiz(true);
    try {
      const targetId = effectiveCourseId || activeCourseId;
      const newAssessment = await api.generateAssessment({
        course_id: targetId,
        concept_id: node.id,
        concept_name: node.name,
        question_count: 5,
        difficulty: 'Adaptive',
      });
      navigate(`/assessments/${newAssessment.id}`);
    } catch (err: any) {
      alert(`Could not generate assessment for ${node.name}: ${err.message || 'Error'}`);
    } finally {
      setGeneratingQuiz(false);
    }
  };

  // Trigger marker-yellow unlock moment
  const handleSimulateUnlock = (nodeId: string) => {
    setJustUnlockedNodeId(nodeId);
    setTimeout(() => {
      setJustUnlockedNodeId(null);
    }, 2500);
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-paper-canvas text-ink-500 font-serif text-xs">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 border-2 border-royal-700 border-t-transparent rounded-full animate-spin" />
          <span>Generating Bayesian prerequisite graph and evaluating knowledge state...</span>
        </div>
      </div>
    );
  }

  if (mapData.nodes.length === 0 && !loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-paper-canvas p-6 text-center space-y-4">
        <div className="p-4 rounded-2xl bg-amber-50 text-amber-700 border border-amber-200">
          <GitFork className="h-8 w-8" />
        </div>
        <div className="max-w-md space-y-2">
          <h2 className="font-serif text-xl font-bold text-ink-900">No Course Material Processed Yet</h2>
          <p className="text-xs text-ink-600 leading-relaxed">
            Concept Maps & Prerequisite DAGs are generated directly from your uploaded course documents. Upload a syllabus or lecture PDF to build this knowledge graph.
          </p>
        </div>
        <button
          onClick={() => navigate('/dashboard', { state: { openCreateCourse: true } })}
          className="px-4 py-2.5 rounded-xl bg-ink-900 text-white font-mono text-xs font-bold shadow-paper transition hover:bg-ink-800 cursor-pointer"
        >
          Create Course with Document &rarr;
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-paper-canvas overflow-hidden">
      {/* Top Header */}
      <div className="px-6 py-4 border-b border-paper-hairline bg-white flex flex-col md:flex-row md:items-center justify-between gap-4 shrink-0 shadow-paper-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-royal-700 bg-royal-50 px-2 py-0.5 rounded border border-royal-200">
              PREREQUISITE KNOWLEDGE DAG
            </span>
            <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-highlighter-base text-ink-900 font-bold border border-ink-900/10">
              &tau; &ge; 0.60 GATE
            </span>
          </div>
          <h1 className="font-serif text-2xl font-bold text-ink-900 tracking-tight mt-1">
            Course Concept Map
          </h1>
          <p className="font-serif text-xs text-ink-600 mt-0.5">
            Hand-drawn dependency graph on dotted paper. Concepts with prerequisite mastery &lt;60% are locked until foundational mastery is established.
          </p>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-paper-surface border border-paper-hairline text-emerald-800">
            <span className="h-2 w-2 rounded-full bg-emerald-600" />
            <span>Mastered (&ge;75%)</span>
          </div>
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-paper-surface border border-paper-hairline text-amber-800">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            <span>Developing (45-74%)</span>
          </div>
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-paper-surface border border-paper-hairline text-red-800">
            <span className="h-2 w-2 rounded-full bg-red-500" />
            <span>Needs Review (&lt;45%)</span>
          </div>
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-paper-surface border border-paper-hairline text-ink-800 font-semibold">
            <Lock className="h-3 w-3 text-amber-600" />
            <span>Locked (&lt;60% Prereq)</span>
          </div>
        </div>
      </div>

      {/* Main Canvas Area + Detail Drawer */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden relative">
        {/* Dotted Paper Canvas with Hand-Drawn Connected Graph */}
        <div className="flex-1 p-6 md:p-10 overflow-auto flex items-center justify-center bg-[radial-gradient(#D5CFC5_1px,transparent_1px)] [background-size:24px_24px] relative">
          
          <div className="relative w-full max-w-4xl min-h-[520px] flex flex-col justify-center py-6">
            
            {/* SVG Connecting Dashed Flow Lines */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none z-0 hidden sm:block">
              <defs>
                <marker
                  id="arrow"
                  viewBox="0 0 10 10"
                  refX="6"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 8 5 L 0 9 z" fill="#7B766C" />
                </marker>
              </defs>
              {/* Dashed flowing curved lines connecting column 1 to 2 to 3 */}
              <path
                d="M 220 180 C 320 180, 320 180, 420 180"
                fill="none"
                stroke="#A8A29E"
                strokeWidth="1.75"
                strokeDasharray="5 5"
                markerEnd="url(#arrow)"
              />
              <path
                d="M 220 180 C 320 180, 320 340, 420 340"
                fill="none"
                stroke="#A8A29E"
                strokeWidth="1.75"
                strokeDasharray="5 5"
                markerEnd="url(#arrow)"
              />
              <path
                d="M 460 180 C 560 180, 560 260, 660 260"
                fill="none"
                stroke="#A8A29E"
                strokeWidth="1.75"
                strokeDasharray="5 5"
                markerEnd="url(#arrow)"
              />
            </svg>

            {/* Nodes Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 relative z-10">
              {mapData.nodes.map((node) => {
                const isSelected = selectedNode?.id === node.id;
                const effectiveMastery = Math.min(100, node.mastery + calibrationBoost);
                const isLocked = node.is_locked && effectiveMastery < 60;
                const isUnlockingNow = justUnlockedNodeId === node.id;

                let cardBorder = 'border-paper-hairline';
                let cardBg = 'bg-white';
                let statusLabel = 'Mastered';

                if (isLocked) {
                  cardBorder = 'border-amber-300';
                  cardBg = 'bg-white';
                  statusLabel = 'Locked';
                } else if (effectiveMastery >= 75) {
                  cardBorder = 'border-emerald-300';
                  cardBg = 'bg-white';
                  statusLabel = 'Mastered';
                } else if (effectiveMastery >= 45) {
                  cardBorder = 'border-amber-300';
                  cardBg = 'bg-white';
                  statusLabel = 'Developing';
                } else {
                  cardBorder = 'border-red-300';
                  cardBg = 'bg-white';
                  statusLabel = 'Needs Review';
                }

                return (
                  <motion.div
                    key={node.id}
                    layout
                    whileHover={{ y: -4 }}
                    onClick={() => setSelectedNode(node)}
                    className={`relative p-5 rounded-2xl border-2 transition-all cursor-pointer shadow-paper ${cardBg} ${cardBorder} ${
                      isSelected ? 'ring-2 ring-royal-700 !border-royal-700 shadow-paper-md' : ''
                    } ${isUnlockingNow ? 'ring-4 ring-highlighter-base !border-highlighter-base' : ''}`}
                  >
                    {/* Marker Yellow Unlock Burst Overlay */}
                    <AnimatePresence>
                      {isUnlockingNow && (
                        <motion.div
                          initial={{ scale: 0.8, opacity: 0 }}
                          animate={{ scale: 1.05, opacity: 1 }}
                          exit={{ scale: 1, opacity: 0 }}
                          transition={{ duration: 0.4 }}
                          className="absolute -top-3 -right-3 z-20 px-3 py-1 rounded-full bg-highlighter-base border border-ink-900 text-ink-900 font-mono font-bold text-xs shadow-highlighter flex items-center gap-1"
                        >
                          <Unlock className="h-3 w-3" />
                          <span>Unlocked (60%)!</span>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {/* Top Row: Difficulty & Status Badge */}
                    <div className="flex items-center justify-between font-mono text-[11px] mb-2">
                      <span className="uppercase text-ink-500 font-medium tracking-wider">
                        {node.difficulty || 'CORE'}
                      </span>

                      {isLocked ? (
                        <span className="flex items-center space-x-1 text-[10px] px-2 py-0.5 rounded-full bg-amber-50 border border-amber-300 text-amber-900 font-bold">
                          <Lock className="h-3 w-3 text-amber-700" />
                          <span>Locked</span>
                        </span>
                      ) : effectiveMastery >= 75 ? (
                        <span className="flex items-center space-x-1 text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-300 text-emerald-900 font-bold">
                          <CheckCircle2 className="h-3 w-3 text-emerald-700" />
                          <span>Mastered</span>
                        </span>
                      ) : (
                        <span className="flex items-center space-x-1 text-[10px] px-2 py-0.5 rounded-full bg-paper-surface border border-paper-hairline text-ink-700 font-bold">
                          <span>{effectiveMastery}%</span>
                        </span>
                      )}
                    </div>

                    {/* Title */}
                    <div className="flex items-center space-x-2 mb-2">
                      {isLocked && <Lock className="h-4 w-4 text-amber-600 shrink-0" />}
                      <h3 className="font-serif text-sm font-bold text-ink-900 truncate">
                        {node.name}
                      </h3>
                    </div>

                    {/* Mastery Bar with 60% Marker */}
                    <div className="relative w-full bg-paper-hairline h-2 rounded-full overflow-hidden my-2">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          isLocked ? 'bg-amber-500' : effectiveMastery >= 75 ? 'bg-emerald-600' : 'bg-royal-700'
                        }`}
                        style={{ width: `${Math.max(effectiveMastery, 6)}%` }}
                      />
                      {/* 60% threshold tick */}
                      <div className="absolute top-0 bottom-0 left-[60%] w-[1.5px] bg-ink-900/40" title="60% Prerequisite Gate" />
                    </div>

                    <div className="flex items-center justify-between text-[11px] font-mono text-ink-500 pt-2 border-t border-paper-hairline">
                      <span>P(L): <strong className="text-ink-900">{effectiveMastery}%</strong></span>
                      <span>
                        {node.prerequisites?.length > 0
                          ? `${node.prerequisites.length} Prereqs`
                          : 'Root Concept'}
                      </span>
                    </div>

                    {/* What-if DAG unlock projection */}
                    {isLocked && (
                      <div className="mt-3 pt-2 border-t border-paper-hairline flex justify-end">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSimulateUnlock(node.id);
                          }}
                          className="text-[10px] font-mono font-bold text-royal-700 hover:text-royal-900 hover:underline flex items-center gap-1"
                          title="What-if projection: preview downstream unlocks when this prerequisite reaches 60% mastery"
                        >
                          <Sparkles className="h-3 w-3 text-amber-600" />
                          <span>What-if: Preview Unlock</span>
                        </button>
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Selected Concept Info Drawer */}
        {selectedNode && (
          <aside className="w-full lg:w-96 border-t lg:border-t-0 lg:border-l border-paper-hairline bg-white p-6 space-y-5 overflow-y-auto shrink-0 shadow-paper-lg">
            <div className="flex items-start justify-between border-b border-paper-hairline pb-3">
              <div>
                <span className="font-mono text-[10px] uppercase font-bold text-royal-700 tracking-wider">
                  NODE SPECIFICATION
                </span>
                <h3 className="font-serif text-lg font-bold text-ink-900 mt-0.5 flex items-center space-x-2">
                  {selectedNode.is_locked && <Lock className="h-4 w-4 text-amber-600" />}
                  <span>{selectedNode.name}</span>
                </h3>
              </div>
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-mono font-bold border flex items-center space-x-1 ${
                  selectedNode.is_locked
                    ? 'bg-amber-50 border-amber-300 text-amber-900'
                    : selectedNode.mastery >= 75
                    ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
                    : 'bg-paper-surface border-paper-hairline text-ink-800'
                }`}
              >
                {selectedNode.is_locked ? (
                  <>
                    <Lock className="h-3 w-3 text-amber-700" />
                    <span>Locked</span>
                  </>
                ) : (
                  <span>{selectedNode.mastery}% Mastered</span>
                )}
              </span>
            </div>

            {/* Locked Node Remediation Banner */}
            {selectedNode.is_locked && (
              <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-300 space-y-2">
                <div className="flex items-center space-x-2 text-xs font-mono font-bold text-amber-900 uppercase tracking-wide">
                  <Lock className="h-4 w-4 text-amber-700" />
                  <span>Prerequisite Threshold Gate</span>
                </div>
                <p className="font-serif text-xs text-amber-950 leading-relaxed">
                  In this course's dependency graph, foundational concept <strong>{selectedNode.blocking_prerequisite?.name || 'Prerequisite'}</strong> has mastery &lt;60%. We recommend mastering it first in AI Tutor.
                </p>
                {selectedNode.blocking_prerequisite && (
                  <div className="text-[11px] font-mono text-amber-950 bg-white p-2 rounded border border-amber-200 flex items-center justify-between">
                    <span>Prerequisite: <strong>{selectedNode.blocking_prerequisite.name}</strong></span>
                    <span>Current: <strong>{selectedNode.blocking_prerequisite.mastery}%</strong> (Target: 60%)</span>
                  </div>
                )}
              </div>
            )}

            <div className="space-y-3 text-xs">
              <div className="font-serif text-ink-700 leading-relaxed">
                Key objective: Master foundational theorems, invariants, and recurrence solutions for {selectedNode.name}.
              </div>

              {/* Prerequisites Breakdown */}
              <div className="p-3.5 rounded-xl bg-paper-surface border border-paper-hairline space-y-2">
                <div className="text-[11px] font-mono font-bold text-ink-800 flex items-center justify-between">
                  <span className="flex items-center space-x-1.5 uppercase tracking-wider">
                    <Layers className="h-3.5 w-3.5 text-royal-700" />
                    <span>Prerequisites:</span>
                  </span>
                  <span className="text-[10px] text-ink-500 font-normal">
                    {selectedNode.prerequisite_details?.length || selectedNode.prerequisites?.length || 0} mapped
                  </span>
                </div>
                {selectedNode.prerequisite_details && selectedNode.prerequisite_details.length > 0 ? (
                  <div className="space-y-1.5 pt-1">
                    {selectedNode.prerequisite_details.map((pr: any) => (
                      <div 
                        key={pr.id}
                        className={`p-2 rounded-lg border text-[11px] font-mono flex items-center justify-between transition ${
                          pr.is_met 
                            ? 'bg-emerald-50/70 border-emerald-300 text-emerald-950' 
                            : 'bg-amber-50/70 border-amber-300 text-amber-950'
                        }`}
                      >
                        <span className="font-semibold">{pr.name}</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-white border border-paper-hairline">
                          {pr.mastery}% {pr.is_met ? '✓ Met' : '⚠ <60%'}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="font-serif text-ink-500 text-[11px]">
                    Fundamental root concept with no prior prerequisites required.
                  </div>
                )}
              </div>

              {/* Exact Source Units & Citations */}
              <div className="p-3.5 rounded-xl bg-paper-surface border border-paper-hairline space-y-2.5">
                <div className="text-[11px] font-mono font-bold text-ink-800 flex items-center justify-between">
                  <span className="flex items-center space-x-1.5 uppercase tracking-wider">
                    <BookOpen className="h-3.5 w-3.5 text-royal-700" />
                    <span>Grounded Sources:</span>
                  </span>
                  <span className="text-[10px] text-ink-500 font-normal">
                    {selectedNode.source_units?.length || 0} units
                  </span>
                </div>

                {selectedNode.source_units && selectedNode.source_units.length > 0 ? (
                  <div className="space-y-2 pt-1 max-h-52 overflow-y-auto pr-1">
                    {selectedNode.source_units.map((unit: any, uIdx: number) => {
                      const isPdf = unit.source_type === 'pdf';
                      const isSlide = unit.source_type === 'slide';
                      const isVideo = unit.source_type === 'video';

                      const locationText = isPdf && unit.page_number
                        ? `Page ${unit.page_number}`
                        : isSlide && unit.slide_number
                        ? `Slide ${unit.slide_number}`
                        : isVideo && unit.timestamp_start !== undefined
                        ? `${Math.floor(unit.timestamp_start / 60)}:${Math.floor(unit.timestamp_start % 60).toString().padStart(2, '0')}`
                        : 'Source Doc';

                      return (
                        <div
                          key={uIdx}
                          className="p-2.5 rounded-lg bg-white border border-paper-hairline hover:border-ink-900/30 transition shadow-2xs space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-1.5 truncate pr-2">
                              {isPdf ? (
                                <FileText className="h-3.5 w-3.5 text-ink-800 shrink-0" />
                              ) : isSlide ? (
                                <Presentation className="h-3.5 w-3.5 text-royal-700 shrink-0" />
                              ) : isVideo ? (
                                <Video className="h-3.5 w-3.5 text-amber-700 shrink-0" />
                              ) : (
                                <Globe className="h-3.5 w-3.5 text-teal-700 shrink-0" />
                              )}
                              <span className="font-serif font-bold text-ink-900 text-[11px] truncate">
                                {unit.document_name}
                              </span>
                            </div>
                            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-paper-surface border border-paper-hairline text-ink-700 shrink-0">
                              {locationText}
                            </span>
                          </div>

                          <p className="font-serif text-[11px] text-ink-600 line-clamp-2 leading-relaxed pl-1.5 border-l border-highlighter-base">
                            "{unit.snippet}"
                          </p>

                          <div className="pt-1 flex justify-end">
                            <button
                              type="button"
                              onClick={() => setActiveCitation(unit)}
                              className="text-[10px] font-mono font-semibold text-royal-700 hover:text-royal-900 flex items-center space-x-1 hover:underline"
                            >
                              <span>Show me source</span>
                              <ExternalLink className="h-3 w-3" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="font-serif text-[11px] text-ink-500">
                    Source units mapped to course textbook, slides, and video lectures.
                  </div>
                )}
              </div>
            </div>

            <div className="pt-3 space-y-2 font-mono">
              <Button
                variant="primary"
                onClick={() => handleGenerateConceptAssessment(selectedNode)}
                disabled={generatingQuiz}
                className="w-full justify-center"
              >
                <Zap className="h-4 w-4" />
                <span>
                  {generatingQuiz
                    ? `Generating Quiz on ${selectedNode.name}...`
                    : `Generate Quiz for '${selectedNode.name}'`}
                </span>
              </Button>

              <Button
                variant="secondary"
                onClick={() => handlePracticeConcept(selectedNode)}
                className="w-full justify-center"
              >
                <Brain className="h-4 w-4 text-royal-700" />
                <span>Practice in AI Tutor</span>
              </Button>

              <Button
                variant="secondary"
                onClick={() => setIsStuckModalOpen(true)}
                className="w-full justify-center bg-amber-500/10 text-amber-900 border-amber-300 hover:bg-amber-500/20"
              >
                <AlertTriangle className="h-4 w-4 text-amber-700" />
                <span>Why am I stuck? (Root Cause)</span>
              </Button>

              <Button
                variant="secondary"
                onClick={() => setIsTeachBackOpen(true)}
                className="w-full justify-center bg-indigo-500/10 text-indigo-900 border-indigo-300 hover:bg-indigo-500/20"
              >
                <Sparkles className="h-4 w-4 text-indigo-700" />
                <span>Teach it back (Feynman Method)</span>
              </Button>

              {selectedNode.is_locked && selectedNode.blocking_prerequisite && (
                <Button
                  variant="secondary"
                  onClick={() => handleStudyPrerequisite(selectedNode)}
                  className="w-full justify-center bg-amber-50 text-amber-950 border-amber-300 hover:bg-amber-100"
                >
                  <Sparkles className="h-3.5 w-3.5 text-amber-700" />
                  <span>Study Prerequisite: {selectedNode.blocking_prerequisite.name}</span>
                </Button>
              )}

              <div className="pt-1 text-center">
                <button
                  type="button"
                  onClick={() => navigate(`/assessments?concept_id=${selectedNode.id}&concept_name=${encodeURIComponent(selectedNode.name)}`)}
                  className="text-[11px] text-royal-700 hover:text-royal-900 font-semibold hover:underline inline-flex items-center space-x-1 cursor-pointer"
                >
                  <span>Configure in Assessment Engine</span>
                  <ArrowRight className="h-3 w-3" />
                </button>
              </div>
            </div>
          </aside>
        )}
      </div>

      {/* Why Am I Stuck Root-Cause Modal */}
      <WhyAmIStuckModal
        isOpen={isStuckModalOpen}
        onClose={() => setIsStuckModalOpen(false)}
        courseId={effectiveCourseId}
        conceptId={selectedNode?.id}
        conceptName={selectedNode?.name}
      />

      {/* Teach-Back Mode Modal */}
      <TeachBackModal
        isOpen={isTeachBackOpen}
        onClose={() => setIsTeachBackOpen(false)}
        courseId={effectiveCourseId}
        conceptId={selectedNode?.id}
        conceptName={selectedNode?.name}
        onSuccess={() => loadMap()}
      />


      {/* Citation / Exact Source Viewer Modal */}
      {activeCitation && (
        <SourceViewerModal
          citation={activeCitation}
          onClose={() => setActiveCitation(null)}
        />
      )}
    </div>
  );
};
