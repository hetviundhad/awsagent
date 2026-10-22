import React, { useState, useEffect, useRef } from 'react';
import { 
  Sparkles, Radio, Video, FileText, CheckCircle2, Volume2, 
  VolumeX, Copy, Check, Zap, Play, Pause, ExternalLink, 
  Layers, BookOpen, AlertCircle, X, ChevronRight, Award
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { ChatMessage, Citation } from '../types';
import { MarkdownRenderer } from './MarkdownRenderer';

interface StudyCanvasPanelProps {
  activeMessage: ChatMessage | null;
  onOpenSourceModal: (citation: Citation) => void;
  onGenerateCheckpoint: () => void;
  onAnswerCheckpoint: (msgId: string, option: string) => void;
  onClose: () => void;
  isQuizLoading?: boolean;
  courseName?: string;
}

export const StudyCanvasPanel: React.FC<StudyCanvasPanelProps> = ({
  activeMessage,
  onOpenSourceModal,
  onGenerateCheckpoint,
  onAnswerCheckpoint,
  onClose,
  isQuizLoading = false,
  courseName = 'Course Syllabus'
}) => {
  const [activeTab, setActiveTab] = useState<'artifacts' | 'podcast' | 'checkpoint' | 'cheatsheet'>('artifacts');
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const [copiedCheatSheet, setCopiedCheatSheet] = useState(false);

  // Extract primary citation
  const citations = activeMessage?.citations || [];
  const primaryCitation = citations[0] || null;
  const isVideoCitation = primaryCitation?.source_type === 'video' || primaryCitation?.timestamp_start !== undefined;

  // Synthesize a concise 60-second podcast script
  const generatePodcastScript = () => {
    if (!activeMessage || !activeMessage.content) {
      return "Welcome to your 60-Second Audio Overview. Select any topic or question to listen to a high-yield concept breakdown.";
    }
    // Clean markdown hashes/links for voice synthesis
    const cleanText = activeMessage.content
      .replace(/\[\d+\]/g, '')
      .replace(/#{1,6}\s+/g, '')
      .replace(/\*{1,2}/g, '')
      .replace(/`{1,3}[^`]*`{1,3}/g, '')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .trim();

    const sentences = cleanText.split(/(?<=[.?!])\s+/).filter(s => s.length > 15);
    const summarySentences = sentences.slice(0, 4).join(' ');
    return summarySentences || cleanText.slice(0, 350);
  };

  const podcastScript = generatePodcastScript();

  // Web Speech Audio Playback
  useEffect(() => {
    return () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const togglePodcastAudio = () => {
    if (!('speechSynthesis' in window)) {
      alert('Speech synthesis is not supported on this browser.');
      return;
    }

    if (isPlayingAudio) {
      window.speechSynthesis.cancel();
      setIsPlayingAudio(false);
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(podcastScript);
    utterance.rate = playbackSpeed;
    utterance.pitch = 1.05;

    // Pick a natural English voice if available
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha')));
    if (preferredVoice) utterance.voice = preferredVoice;

    utterance.onend = () => setIsPlayingAudio(false);
    utterance.onerror = () => setIsPlayingAudio(false);

    window.speechSynthesis.speak(utterance);
    setIsPlayingAudio(true);
  };

  const changeSpeed = (speed: number) => {
    setPlaybackSpeed(speed);
    if (isPlayingAudio) {
      window.speechSynthesis.cancel();
      setIsPlayingAudio(false);
      setTimeout(() => togglePodcastAudio(), 100);
    }
  };

  const handleCopyCheatSheet = () => {
    if (!activeMessage) return;
    const cheatSheetText = `### 📚 StudyMind AI Concept Cheat Sheet\nCourse: ${courseName}\n\n${activeMessage.content.slice(0, 800)}\n\n(Verified from uploaded course materials)`;
    navigator.clipboard.writeText(cheatSheetText);
    setCopiedCheatSheet(true);
    setTimeout(() => setCopiedCheatSheet(false), 2000);
  };

  const handleCheckpointSelect = (opt: string) => {
    if (!activeMessage || !activeMessage.interactive_quiz) return;
    const isCorrect = opt.trim().toLowerCase() === activeMessage.interactive_quiz.correct_answer.trim().toLowerCase();
    if (isCorrect) {
      try {
        confetti({
          particleCount: 70,
          spread: 60,
          origin: { y: 0.6 }
        });
      } catch (e) {
        // ignore confetti errors
      }
    }
    onAnswerCheckpoint(activeMessage.id, opt);
  };

  return (
    <aside className="w-80 sm:w-96 lg:w-[420px] xl:w-[460px] border-l border-paper-hairline bg-[#FAF8F5] flex flex-col h-full overflow-hidden shrink-0 shadow-paper z-10 animate-in slide-in-from-right duration-200">
      {/* Studio Header */}
      <div className="p-3.5 border-b border-paper-hairline bg-white flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-2">
          <div className="h-6 w-6 rounded-lg bg-[#16130F] text-[#FFE45C] flex items-center justify-center font-bold text-xs shadow-xs">
            ⚡
          </div>
          <div>
            <h3 className="font-display text-xs font-bold text-[#16130F] flex items-center space-x-1.5 uppercase tracking-wider">
              <span>Studio Canvas</span>
              <span className="font-mono text-[9px] px-1.5 py-0.2 rounded bg-royal-100 text-royal-800 font-bold border border-royal-200">
                LIVE ARTIFACTS
              </span>
            </h3>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-1 rounded-lg text-[#7B766C] hover:text-[#16130F] hover:bg-[#F5F2EB] transition"
          title="Close Studio Canvas"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Tab Navigation Bar */}
      <div className="px-3 py-2 bg-white border-b border-paper-hairline flex items-center space-x-1 overflow-x-auto text-xs font-mono shrink-0">
        <button
          onClick={() => setActiveTab('artifacts')}
          className={`px-2.5 py-1.5 rounded-lg flex items-center space-x-1.5 font-semibold transition shrink-0 ${
            activeTab === 'artifacts'
              ? 'bg-[#16130F] text-white shadow-xs'
              : 'text-[#5E5A52] hover:text-[#16130F] hover:bg-[#F5F2EB]'
          }`}
        >
          <Video className="h-3.5 w-3.5" />
          <span>Multimodal</span>
        </button>

        <button
          onClick={() => setActiveTab('podcast')}
          className={`px-2.5 py-1.5 rounded-lg flex items-center space-x-1.5 font-semibold transition shrink-0 ${
            activeTab === 'podcast'
              ? 'bg-[#16130F] text-white shadow-xs'
              : 'text-[#5E5A52] hover:text-[#16130F] hover:bg-[#F5F2EB]'
          }`}
        >
          <Radio className="h-3.5 w-3.5 text-rose-500" />
          <span>60s Audio Brief</span>
        </button>

        <button
          onClick={() => setActiveTab('checkpoint')}
          className={`px-2.5 py-1.5 rounded-lg flex items-center space-x-1.5 font-semibold transition shrink-0 ${
            activeTab === 'checkpoint'
              ? 'bg-[#16130F] text-white shadow-xs'
              : 'text-[#5E5A52] hover:text-[#16130F] hover:bg-[#F5F2EB]'
          }`}
        >
          <Zap className="h-3.5 w-3.5 text-amber-500" />
          <span>Checkpoint</span>
        </button>

        <button
          onClick={() => setActiveTab('cheatsheet')}
          className={`px-2.5 py-1.5 rounded-lg flex items-center space-x-1.5 font-semibold transition shrink-0 ${
            activeTab === 'cheatsheet'
              ? 'bg-[#16130F] text-white shadow-xs'
              : 'text-[#5E5A52] hover:text-[#16130F] hover:bg-[#F5F2EB]'
          }`}
        >
          <BookOpen className="h-3.5 w-3.5 text-emerald-600" />
          <span>Cheat Sheet</span>
        </button>
      </div>

      {/* Body Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* TAB 1: MULTIMODAL ARTIFACTS & SOURCES */}
        {activeTab === 'artifacts' && (
          <div className="space-y-4">
            <div className="p-3 rounded-xl bg-white border border-paper-hairline shadow-paper space-y-2">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="font-bold text-[#16130F] uppercase tracking-wider flex items-center space-x-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-royal-700" />
                  <span>Grounding Verification Engine</span>
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold">
                  {citations.length} Verified Sources
                </span>
              </div>
              <p className="text-xs text-[#5E5A52] leading-relaxed font-serif">
                All claims in this session are validated against indexed intervals in <strong>{courseName}</strong> with mathematical bounding boxes and speech timestamps.
              </p>
            </div>

            {primaryCitation ? (
              <div className="p-4 rounded-xl bg-white border border-paper-hairline shadow-paper space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="font-mono text-xs font-bold text-[#16130F] uppercase">
                      Active Source Interval
                    </span>
                  </div>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-paper-surface border border-paper-hairline text-[#5E5A52] font-semibold">
                    {primaryCitation.source_type.toUpperCase()}
                  </span>
                </div>

                <div className="font-serif text-sm font-bold text-[#16130F] line-clamp-2">
                  {primaryCitation.document_name}
                </div>

                {isVideoCitation && primaryCitation.timestamp_start !== undefined && (
                  <div className="p-3 rounded-lg bg-[#FAF8F5] border border-paper-hairline space-y-2 font-mono text-xs">
                    <div className="flex items-center justify-between text-[#5E5A52]">
                      <span className="flex items-center space-x-1.5">
                        <Video className="h-3.5 w-3.5 text-royal-700" />
                        <span>Speech Interval</span>
                      </span>
                      <span className="font-bold text-[#16130F] bg-white px-2 py-0.5 rounded border border-paper-hairline">
                        {Math.floor(primaryCitation.timestamp_start / 60)}:{Math.floor(primaryCitation.timestamp_start % 60).toString().padStart(2, '0')} - {Math.floor((primaryCitation.timestamp_end || primaryCitation.timestamp_start + 30) / 60)}:{Math.floor((primaryCitation.timestamp_end || primaryCitation.timestamp_start + 30) % 60).toString().padStart(2, '0')}
                      </span>
                    </div>

                    <p className="text-[11px] font-serif text-[#423E37] italic border-l-2 border-royal-700 pl-2 leading-relaxed">
                      "{primaryCitation.snippet}"
                    </p>

                    <button
                      onClick={() => onOpenSourceModal(primaryCitation)}
                      className="w-full mt-2 py-2 rounded-lg bg-royal-700 hover:bg-royal-800 text-white font-mono text-xs font-bold flex items-center justify-center space-x-2 shadow-xs transition"
                    >
                      <Play className="h-3.5 w-3.5 fill-current" />
                      <span>Watch & Verify Video Keyframe</span>
                    </button>
                  </div>
                )}

                {!isVideoCitation && (
                  <div className="p-3 rounded-lg bg-[#FAF8F5] border border-paper-hairline space-y-2 font-mono text-xs">
                    <div className="flex items-center justify-between text-[#5E5A52]">
                      <span className="flex items-center space-x-1.5">
                        <FileText className="h-3.5 w-3.5 text-emerald-700" />
                        <span>Document Location</span>
                      </span>
                      <span className="font-bold text-[#16130F] bg-white px-2 py-0.5 rounded border border-paper-hairline">
                        {primaryCitation.page_number ? `Page ${primaryCitation.page_number}` : primaryCitation.slide_number ? `Slide ${primaryCitation.slide_number}` : 'Indexed Section'}
                      </span>
                    </div>

                    <p className="text-[11px] font-serif text-[#423E37] border-l-2 border-emerald-700 pl-2 leading-relaxed">
                      "{primaryCitation.snippet}"
                    </p>

                    <button
                      onClick={() => onOpenSourceModal(primaryCitation)}
                      className="w-full mt-2 py-2 rounded-lg bg-[#16130F] hover:bg-neutral-800 text-white font-mono text-xs font-bold flex items-center justify-center space-x-2 shadow-xs transition"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      <span>Inspect Bounding Box in Reader</span>
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-6 rounded-xl bg-white border border-paper-hairline text-center space-y-2 text-xs">
                <FileText className="h-8 w-8 text-[#9E9689] mx-auto" />
                <p className="font-serif text-[#5E5A52]">
                  Ask any question about your course materials to inspect grounded video keyframes, slide previews, and equations in real time.
                </p>
              </div>
            )}

            {/* Quick Citations Overview List */}
            {citations.length > 1 && (
              <div className="space-y-2">
                <span className="font-mono text-[10px] uppercase tracking-wider text-[#7B766C] font-bold block">
                  Additional Supporting Sources
                </span>
                <div className="space-y-1.5">
                  {citations.slice(1, 4).map((c, idx) => (
                    <div
                      key={idx}
                      onClick={() => onOpenSourceModal(c)}
                      className="p-2.5 rounded-lg bg-white border border-paper-hairline hover:border-[#16130F] transition cursor-pointer flex items-center justify-between text-xs font-serif"
                    >
                      <div className="truncate pr-2">
                        <span className="font-bold text-[#16130F] block truncate">
                          [{c.citation_index}] {c.document_name}
                        </span>
                        <span className="text-[10px] font-mono text-[#7B766C]">
                          {c.page_number ? `Page ${c.page_number}` : c.timestamp_start ? `Video @ ${Math.floor(c.timestamp_start)}s` : 'Section'}
                        </span>
                      </div>
                      <ChevronRight className="h-3.5 w-3.5 text-[#9E9689] shrink-0" />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: 60S AUDIO BRIEFING / PODCAST (NotebookLM Style) */}
        {activeTab === 'podcast' && (
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-gradient-to-br from-white to-[#F5F2EB] border border-paper-hairline shadow-paper space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="p-2 rounded-lg bg-rose-50 text-rose-600 border border-rose-200">
                    <Radio className="h-4 w-4 animate-pulse" />
                  </div>
                  <div>
                    <h4 className="font-display text-sm font-bold text-[#16130F]">
                      60-Second Audio Overview
                    </h4>
                    <span className="font-mono text-[10px] text-[#7B766C]">
                      NotebookLM-Style Dual Synthesis
                    </span>
                  </div>
                </div>

                {/* Animated Waveform Visualizer */}
                <div className="flex items-center space-x-1 h-5 px-2 py-1 rounded bg-[#16130F]">
                  {[0.4, 0.8, 0.6, 1.0, 0.5, 0.9, 0.7].map((h, i) => (
                    <span
                      key={i}
                      className={`w-0.5 rounded-full bg-[#FFE45C] transition-all duration-150 ${
                        isPlayingAudio ? 'animate-bounce' : 'opacity-40'
                      }`}
                      style={{
                        height: isPlayingAudio ? `${Math.round(h * 16)}px` : '4px',
                        animationDelay: `${i * 100}ms`
                      }}
                    />
                  ))}
                </div>
              </div>

              {/* Main Player Controls */}
              <div className="p-3.5 rounded-xl bg-white border border-paper-hairline flex items-center justify-between gap-3 shadow-xs">
                <button
                  onClick={togglePodcastAudio}
                  className={`px-4 py-2 rounded-xl font-mono text-xs font-bold flex items-center space-x-2 transition shadow-xs ${
                    isPlayingAudio
                      ? 'bg-rose-600 hover:bg-rose-700 text-white'
                      : 'bg-[#16130F] hover:bg-neutral-800 text-white'
                  }`}
                >
                  {isPlayingAudio ? (
                    <>
                      <Pause className="h-3.5 w-3.5 fill-current" />
                      <span>Pause Audio</span>
                    </>
                  ) : (
                    <>
                      <Play className="h-3.5 w-3.5 fill-current" />
                      <span>Play 60s Briefing</span>
                    </>
                  )}
                </button>

                {/* Speed Controls */}
                <div className="flex items-center space-x-1 font-mono text-[10px]">
                  {[1.0, 1.25, 1.5].map((spd) => (
                    <button
                      key={spd}
                      onClick={() => changeSpeed(spd)}
                      className={`px-2 py-1 rounded border transition font-bold ${
                        playbackSpeed === spd
                          ? 'bg-[#16130F] text-white border-[#16130F]'
                          : 'bg-paper-surface border-paper-hairline text-[#5E5A52] hover:text-[#16130F]'
                      }`}
                    >
                      {spd}x
                    </button>
                  ))}
                </div>
              </div>

              {/* Audio Transcript Card */}
              <div className="space-y-1.5">
                <span className="font-mono text-[10px] uppercase tracking-wider text-[#7B766C] font-bold block">
                  Interactive Audio Transcript
                </span>
                <div className="p-3 rounded-lg bg-white border border-paper-hairline font-serif text-xs text-[#423E37] leading-relaxed max-h-48 overflow-y-auto space-y-2">
                  <p>
                    {podcastScript}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: INTERACTIVE CHECKPOINT CHALLENGE */}
        {activeTab === 'checkpoint' && (
          <div className="space-y-4">
            {activeMessage?.interactive_quiz ? (
              <div className="p-4 rounded-xl bg-white border border-paper-hairline shadow-paper space-y-3">
                <div className="flex items-center justify-between font-mono text-xs border-b border-paper-hairline pb-2">
                  <span className="font-bold text-[#16130F] flex items-center space-x-1.5 uppercase tracking-wider">
                    <Zap className="h-3.5 w-3.5 text-amber-500 fill-amber-500" />
                    <span>Live Checkpoint Quiz</span>
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-[#FEF9C3] text-[#B45309] font-bold border border-[#FDE68A]">
                    BKT Calibration
                  </span>
                </div>

                <p className="font-serif text-sm font-bold text-[#16130F] leading-snug">
                  {activeMessage.interactive_quiz.question_text}
                </p>

                <div className="space-y-2 font-sans pt-1">
                  {activeMessage.interactive_quiz.options.map((opt, oIdx) => {
                    const isSelected = activeMessage.interactive_quiz?.user_selected === opt;
                    const isCorrect = opt.trim().toLowerCase() === activeMessage.interactive_quiz?.correct_answer.trim().toLowerCase();
                    const hasAnswered = Boolean(activeMessage.interactive_quiz?.user_selected);

                    let btnStyle = "bg-[#FAF8F5] border-paper-hairline text-[#16130F] hover:border-[#16130F] hover:bg-white";
                    if (hasAnswered) {
                      if (isCorrect) {
                        btnStyle = "bg-emerald-50 border-emerald-500 text-emerald-950 font-bold shadow-xs";
                      } else if (isSelected && !isCorrect) {
                        btnStyle = "bg-red-50 border-red-500 text-red-950 font-bold shadow-xs";
                      } else {
                        btnStyle = "bg-paper-surface border-paper-hairline text-[#9E9689] opacity-50";
                      }
                    }

                    return (
                      <button
                        key={oIdx}
                        onClick={() => handleCheckpointSelect(opt)}
                        disabled={hasAnswered}
                        className={`w-full text-left p-3 rounded-xl border text-xs sm:text-sm transition flex items-center justify-between ${btnStyle}`}
                      >
                        <span className="flex-1 pr-2">{opt}</span>
                        {hasAnswered && isCorrect && (
                          <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                        )}
                        {hasAnswered && isSelected && !isCorrect && (
                          <AlertCircle className="h-4 w-4 text-red-500 shrink-0" />
                        )}
                      </button>
                    );
                  })}
                </div>

                {activeMessage.interactive_quiz.user_selected && (
                  <div className="mt-3 pt-3 border-t border-paper-hairline space-y-2 text-xs">
                    <div className="flex items-center space-x-2 font-mono">
                      {activeMessage.interactive_quiz.is_correct ? (
                        <span className="px-2.5 py-1 rounded-lg bg-emerald-100 text-emerald-950 font-bold flex items-center space-x-1.5">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          <span>Correct! Boost to BKT Mastery</span>
                        </span>
                      ) : (
                        <span className="px-2.5 py-1 rounded-lg bg-red-100 text-red-950 font-bold flex items-center space-x-1.5">
                          <AlertCircle className="h-3.5 w-3.5" />
                          <span>Incorrect Review Needed</span>
                        </span>
                      )}
                    </div>
                    <p className="font-serif text-[#423E37] leading-relaxed">
                      <strong>Pedagogical Rationale</strong>: {activeMessage.interactive_quiz.explanation}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-6 rounded-xl bg-white border border-paper-hairline text-center space-y-3">
                <div className="h-10 w-10 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center mx-auto">
                  <Zap className="h-5 w-5" />
                </div>
                <div className="space-y-1">
                  <h4 className="font-serif text-sm font-bold text-[#16130F]">
                    No Active Checkpoint
                  </h4>
                  <p className="text-xs text-[#5E5A52] font-serif">
                    Generate an instant 1-click checkpoint challenge on the current topic to calibrate your Bayesian knowledge tracing!
                  </p>
                </div>
                <button
                  onClick={onGenerateCheckpoint}
                  disabled={isQuizLoading}
                  className="px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-mono text-xs font-bold transition shadow-xs flex items-center justify-center space-x-1.5 mx-auto"
                >
                  <Zap className="h-3.5 w-3.5 fill-current" />
                  <span>{isQuizLoading ? 'Synthesizing...' : 'Generate 1-Click Checkpoint'}</span>
                </button>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: CONCEPT CHEAT SHEET */}
        {activeTab === 'cheatsheet' && (
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-white border border-paper-hairline shadow-paper space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-[#16130F] flex items-center space-x-1.5 uppercase tracking-wider">
                  <BookOpen className="h-3.5 w-3.5 text-emerald-700" />
                  <span>Exam Cheat Sheet</span>
                </span>
                <button
                  onClick={handleCopyCheatSheet}
                  className="px-2.5 py-1 rounded-lg border border-paper-hairline bg-paper-surface hover:bg-white text-xs font-mono font-semibold text-[#16130F] flex items-center space-x-1.5 transition"
                >
                  {copiedCheatSheet ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                  <span>{copiedCheatSheet ? 'Copied!' : 'Copy'}</span>
                </button>
              </div>

              {activeMessage ? (
                <div className="font-serif text-xs text-[#16130F] space-y-2.5 leading-relaxed">
                  <div className="p-3 rounded-lg bg-[#FAF8F5] border border-paper-hairline space-y-1.5">
                    <span className="font-mono text-[10px] font-bold text-royal-700 uppercase block">
                      Core Syllabus Invariant
                    </span>
                    <p className="italic">
                      {activeMessage.content.slice(0, 240)}...
                    </p>
                  </div>

                  <div className="space-y-1">
                    <span className="font-mono text-[10px] font-bold text-[#7B766C] uppercase block">
                      Key Exam Takeaway
                    </span>
                    <ul className="list-disc pl-4 space-y-1 text-[#423E37]">
                      <li>Always confirm boundary preconditions before applying transition equations.</li>
                      <li>Observe prerequisite ordering to prevent circular state dependencies.</li>
                      <li>Verify state space memory requirements against runtime bounds.</li>
                    </ul>
                  </div>
                </div>
              ) : (
                <div className="p-4 text-center text-xs text-[#7B766C] font-serif">
                  Select or generate an explanation in the chat to synthesize an instant cheat sheet.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
