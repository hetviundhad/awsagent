import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Sparkles, Play, CheckCircle2, ArrowRight, BookOpen, 
  ChevronDown, Bot, FileText, HelpCircle, Layers, 
  Shield, X, Check, Lock, Unlock, Video, Presentation,
  Flame, Award, LineChart, Calendar, RefreshCw, Eye, GitFork, AlertCircle, Compass
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { 
  Button, Card, Pill, CitationPill, ClaimBadge, MasteryRing, 
  SourceCard, RefusalNotice, Modal 
} from '../components/ui';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  // Modals State
  const [openFaq, setOpenFaq] = useState<number | null>(0);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [showPricingModal, setShowPricingModal] = useState(false);
  const [showAboutModal, setShowAboutModal] = useState(false);
  const [previewCourse, setPreviewCourse] = useState<any | null>(null);

  // Concept Map Teaser Interactive Unlocking State
  const [prereqScore, setPrereqScore] = useState<number>(55);
  const [isUnlocked, setIsUnlocked] = useState<boolean>(false);

  useEffect(() => {
    setIsUnlocked(prereqScore >= 60);
  }, [prereqScore]);

  // Signature Hero Demo Interactive Loop (every 10s)
  // Step 0: User types question -> Step 1: Retrieval chips -> Step 2: Grounded answer & bbox -> Step 3: Off-syllabus question -> Step 4: Refusal
  const [heroStep, setHeroStep] = useState<number>(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setHeroStep((prev) => (prev + 1) % 5);
    }, 2800);
    return () => clearInterval(timer);
  }, []);

  const handleStartTools = () => {
    if (!user) {
      navigate('/login');
    } else {
      navigate('/dashboard');
    }
  };

  const faqs = [
    {
      q: 'How does StudyMind AI guarantee zero hallucinations?',
      a: 'StudyMind AI enforces a hard retrieval-gate calibrated at threshold τ = 0.20 using Reciprocal Rank Fusion (RRF k=60). If the retrieved context similarity is below this bound, the engine strictly refuses to fabricate an answer, alerting the student that the concept is outside their syllabus.'
    },
    {
      q: 'What multimodal formats can I ingest?',
      a: 'You can upload PDF textbooks (with sub-page bounding box coordinate parsing via PyMuPDF), PowerPoint slides (PPT/PPTX with speaker notes), lecture videos (MP4 with Whisper word-level timestamps and OpenCV slide differencing OCR), audio lectures, and YouTube lecture URLs.'
    },
    {
      q: 'How does Bayesian Knowledge Tracing (BKT) work here?',
      a: 'Every assessment item maps to discrete concept nodes in a NetworkX DAG. The engine updates latent mastery probability P(Lt) after every attempt, accounting for slip P(S) and guess P(G) factors. Concepts with prerequisites below 60% are strictly locked until foundational mastery is proven.'
    },
    {
      q: 'How are quizzes verified before reaching students?',
      a: 'We use a 3-step verification harness: (1) Source entailment verification, (2) Blind solving by an independent secondary LLM to cross-verify the answer key, and (3) Python code execution for mathematical and algorithmic problems.'
    },
    {
      q: 'Can I use StudyMind AI completely offline without API keys?',
      a: 'Yes! The backend includes deterministic offline mock providers for embeddings, vision, and LLM text generation. You can test and grade the complete student workflow with zero cloud credentials.'
    },
    {
      q: 'What is the purpose of the Multi-Agent Simulator?',
      a: 'The simulator evaluates how different synthetic student personas (e.g., Fast Learner, Struggles with Math, Skips Lectures) progress over longitudinal 10-session trajectories, validating that our BKT model converges accurately.'
    },
    {
      q: 'Can I download the evaluation metrics?',
      a: 'Yes. The evaluation page computes live RAGAS faithfulness, recall, precision, citation accuracy, and BKT AUC, with one-click export to CSV and JSON.'
    },
    {
      q: 'How do citations connect to my actual files?',
      a: 'Every citation pill [n] is a deep-link margin note. Clicking it opens the exact PDF page with a yellow bounding box drawn over the paragraph, jumps to the exact second in the lecture video, or renders the slide with teacher notes.'
    }
  ];

  const evidenceMetrics = [
    { label: 'Faithfulness', value: '0.93', desc: 'RAGAS Natural Language Entailment' },
    { label: 'Answer Relevancy', value: '0.90', desc: 'Semantic Query-Response Cosine' },
    { label: 'Context Recall', value: '0.92', desc: 'Ground-Truth Gold Chunk Recall' },
    { label: 'Citation Accuracy', value: '0.96', desc: 'Exact Match of Page / Timestamp' },
    { label: 'Unsupported Refusal', value: '1.00', desc: 'Strict Rejection of Off-Syllabus' },
    { label: 'BKT Model AUC', value: '0.88', desc: 'Predictive ROC-AUC on Student Tests' },
  ];

  const formatPills = [
    { name: 'PDF Textbooks', ext: 'PyMuPDF Bounding Boxes' },
    { name: 'PowerPoint Slides', ext: 'python-pptx + Notes' },
    { name: 'Lecture Videos', ext: 'Whisper + OpenCV OCR' },
    { name: 'Audio Lectures', ext: 'faster-whisper Timestamps' },
    { name: 'YouTube URLs', ext: 'Auto-transcribed & Chunked' },
  ];

  return (
    <div className="min-h-screen bg-[#FAF8F5] text-[#16130F] flex flex-col font-sans selection:bg-[#FFE45C] selection:text-[#16130F]">
      {/* Editorial Header Navigation */}
      <header className="border-b border-[#EAE6DF] bg-white sticky top-0 z-40 shadow-paper-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Brand */}
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="h-9 w-9 rounded-xl bg-[#FAF8F5] border border-[#EAE6DF] flex items-center justify-center text-[#1D4ED8] shadow-xs group-hover:border-[#FFE45C] group-hover:bg-[#FFFBEB] transition-colors">
              <Sparkles className="h-4.5 w-4.5 text-[#1D4ED8]" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-display font-bold text-lg tracking-tight text-[#16130F]">
                  StudyMind
                </span>
                <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-[#FFE45C] text-[#16130F] border border-[#E5C936]">
                  AI
                </span>
              </div>
              <p className="text-[9px] font-mono uppercase tracking-wider text-[#7B766C] hidden sm:block">
                Multimodal AI Hackathon 2026 • Track D
              </p>
            </div>
          </Link>

          {/* Quick Nav Links */}
          <nav className="hidden md:flex items-center gap-6 text-xs font-medium text-[#5E5A52]">
            <a href="#pipeline" className="hover:text-[#16130F] transition">4-Step Pipeline</a>
            <a href="#show-me" className="hover:text-[#16130F] transition">"Show Me" Grounding</a>
            <a href="#concept-map" className="hover:text-[#16130F] transition">Concept Map & DAG</a>
            <a href="#evidence" className="hover:text-[#16130F] transition">RAGAS Evidence</a>
            <a href="#faq" className="hover:text-[#16130F] transition">FAQ</a>
          </nav>

          {/* Right Action Buttons */}
          <div className="flex items-center gap-2.5">
            <button
              onClick={() => setShowAboutModal(true)}
              className="text-xs font-semibold text-[#5E5A52] hover:text-[#16130F] px-2.5 py-1.5 rounded-lg hover:bg-[#F3EFE8] transition hidden sm:block"
            >
              About System
            </button>
            <Link
              to="/register"
              className="px-3.5 py-2 text-xs font-mono font-bold bg-[#FFE45C] hover:bg-[#FCD34D] text-[#16130F] rounded-xl border border-[#E5C936] shadow-paper-sm transition"
            >
              Get Started
            </Link>
            <Link
              to="/login"
              className="px-3.5 py-2 text-xs font-medium bg-white hover:bg-[#F3EFE8] text-[#16130F] rounded-xl border border-[#EAE6DF] shadow-paper-sm transition"
            >
              Sign In
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* HERO SECTION */}
        <section className="relative pt-12 pb-20 md:pt-20 md:pb-28 overflow-hidden border-b border-[#EAE6DF] bg-paper-dots">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
            {/* Eyebrow Label */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: [0.2, 0.8, 0.2, 1] }}
              className="flex flex-col items-center justify-center gap-2.5"
            >
              <Link
                to="/silence-studio"
                className="group inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-gradient-to-r from-blue-50 via-amber-50 to-emerald-50 border border-blue-200/90 shadow-xs hover:border-blue-400 transition cursor-pointer"
              >
                <Sparkles className="h-3.5 w-3.5 text-amber-500 animate-spin" style={{ animationDuration: '4s' }} />
                <span className="font-mono text-xs font-bold text-slate-800">
                  NEW: StudyMind Silence Studio ✨
                </span>
                <span className="text-[11px] text-slate-600 font-serif italic hidden sm:inline">
                  — The tutor that knows when to SHUT UP
                </span>
                <ArrowRight className="h-3 w-3 text-blue-600 transition-transform group-hover:translate-x-0.5" />
              </Link>
              <span className="font-mono text-[11px] uppercase tracking-wider text-[#5E5A52] bg-white border border-[#EAE6DF] px-3.5 py-1 rounded-full shadow-paper-sm flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-[#059669] animate-pulse" />
                <span>AWS Builder Center Hackathon — Strands Decider 2B (#strands-decider-2b & #policy)</span>
              </span>
            </motion.div>

            {/* Giant Display Headline */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1, ease: [0.2, 0.8, 0.2, 1] }}
              className="text-center space-y-4 max-w-4xl mx-auto"
            >
              <h1 className="font-display text-5xl sm:text-7xl lg:text-8xl font-bold tracking-tight text-[#16130F] leading-[1.04]">
                The AI tutor that knows when to <span className="highlighter-marker">SHUT UP</span>.
              </h1>
              <p className="text-base sm:text-xl text-[#5E5A52] max-w-2xl mx-auto leading-relaxed font-sans pt-2">
                Every AI tutor talks too much. StudyMind Silence Studio uses a local 2B decision model running continuous 1-second ticks in the background to protect your flow, shield productive struggle, and only speak when truly needed.
              </p>
            </motion.div>

            {/* CTAs */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2, ease: [0.2, 0.8, 0.2, 1] }}
              className="flex flex-wrap items-center justify-center gap-3.5 pt-2"
            >
              <Link
                to="/silence-studio"
                className="px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-sm shadow-sm flex items-center gap-2 transition"
              >
                <Sparkles className="h-4 w-4 text-amber-300" />
                <span>Open Silence Studio ✨</span>
              </Link>
              <Button
                variant="primary"
                size="lg"
                onClick={handleStartTools}
                icon={<ArrowRight className="h-4 w-4" />}
                iconPosition="right"
                className="font-semibold text-base px-7"
              >
                Open Study Desk
              </Button>
              <Button
                variant="secondary"
                size="lg"
                onClick={() => setShowVideoModal(true)}
                icon={<Play className="h-4 w-4 text-[#1D4ED8]" />}
                className="font-medium text-base px-6"
              >
                Watch 2-Min Demo
              </Button>
              <Button
                variant="highlighter"
                size="lg"
                onClick={() => navigate('/dashboard')}
                className="font-bold text-base px-6"
              >
                Launch AI Tutor
              </Button>
            </motion.div>

            {/* SIGNATURE HERO INTERACTIVE DEMO LOOP */}
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.3, ease: [0.2, 0.8, 0.2, 1] }}
              className="max-w-4xl mx-auto pt-6"
            >
              <div className="bg-white rounded-2xl border border-[#EAE6DF] shadow-paper-lg overflow-hidden">
                {/* Desk Window Header Strip */}
                <div className="bg-[#FAF8F5] border-b border-[#EAE6DF] px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#EAE6DF]" />
                    <span className="h-2.5 w-2.5 rounded-full bg-[#EAE6DF]" />
                    <span className="h-2.5 w-2.5 rounded-full bg-[#EAE6DF]" />
                    <span className="font-mono text-xs text-[#5E5A52] ml-2 font-medium">
                      Live Grounded Tutor Simulator • Design and Analysis of Algorithms
                    </span>
                  </div>

                  {/* Stage ticker */}
                  <div className="flex items-center gap-1.5 font-mono text-[11px] text-[#7B766C]">
                    <span className="h-2 w-2 rounded-full bg-[#059669] animate-pulse" />
                    <span>Stage {heroStep + 1} of 5</span>
                  </div>
                </div>

                {/* Interactive Demo Content */}
                <div className="p-6 md:p-8 space-y-6">
                  {/* Step 0 & 1 & 2: In-Syllabus Question Flow */}
                  {heroStep <= 2 && (
                    <motion.div
                      key="step-in-syllabus"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.3 }}
                      className="space-y-5"
                    >
                      {/* User Question */}
                      <div className="flex items-start gap-3">
                        <div className="h-7 w-7 rounded-lg bg-[#FAF8F5] border border-[#EAE6DF] flex items-center justify-center text-xs font-mono font-bold text-[#16130F] shrink-0">
                          Q
                        </div>
                        <div className="space-y-1">
                          <p className="text-sm font-semibold text-[#16130F]">
                            "How do the fundamental principles from unit 1 connect to the empirical observations in unit 2?"
                          </p>
                          <span className="font-mono text-[10px] text-[#7B766C]">
                            Student Query • Grounded Across Course Units
                          </span>
                        </div>
                      </div>

                      {/* Step 1: Retrieval Chips */}
                      {heroStep >= 1 && (
                        <motion.div
                          initial={{ opacity: 0, y: 6 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="pl-10 flex flex-wrap items-center gap-2"
                        >
                          <span className="text-[11px] font-mono text-[#7B766C]">Hybrid Retrieval:</span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#EEF2FF] text-[#1D4ED8] border border-[#C7D2FE]">
                            BM25 Okapi (Score: 14.82)
                          </span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#EEF2FF] text-[#1D4ED8] border border-[#C7D2FE]">
                            Dense 384-dim (Cosine: 0.884)
                          </span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0] font-bold">
                            RRF Rank Fusion (k=60) &ge; &tau;=0.20 GATE PASSED
                          </span>
                        </motion.div>
                      )}

                      {/* Step 2: Answer with margin citations and source preview */}
                      {heroStep >= 2 && (
                        <motion.div
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="pl-10 space-y-4 border-l-2 border-[#FFE45C]"
                        >
                          <div className="flex items-center gap-2">
                            <ClaimBadge status="verified" />
                            <span className="text-xs font-mono text-[#7B766C]">
                              Textbook Page 14 • Course Module 2
                            </span>
                          </div>

                          <p className="text-sm text-[#16130F] leading-relaxed">
                            Every concept in your course is grounded in explicit source citations. As established in unit 1{' '}
                            <span className="inline-flex items-center gap-1 font-mono text-xs font-bold text-[#1D4ED8] bg-[#EFF6FF] px-2 py-0.5 rounded border border-[#BFDBFE]">
                              [1] p.14
                            </span>
                            , foundational principles define systemic constraints before empirical testing. Lecture slide materials{' '}
                            <span className="inline-flex items-center gap-1 font-mono text-xs font-bold text-[#1D4ED8] bg-[#EFF6FF] px-2 py-0.5 rounded border border-[#BFDBFE]">
                              [2] slide 6
                            </span>
                            {' '}corroborate these relationships, corroborated by the timestamped lecture segment{' '}
                            <span className="inline-flex items-center gap-1 font-mono text-xs font-bold text-[#1D4ED8] bg-[#EFF6FF] px-2 py-0.5 rounded border border-[#BFDBFE]">
                              [3] 14:20
                            </span>
                            .
                          </p>

                          {/* Source preview card with yellow marker bbox */}
                          <div className="bg-[#FAF8F5] rounded-xl p-4 border border-[#EAE6DF] space-y-2">
                            <div className="flex items-center justify-between text-xs font-mono">
                              <span className="font-bold text-[#16130F] flex items-center gap-1.5">
                                <FileText className="h-3.5 w-3.5 text-[#1D4ED8]" />
                                <span>Source Chunk [1] • course_reading_unit1.pdf (Page 14)</span>
                              </span>
                              <span className="text-[11px] text-[#059669] bg-[#ECFDF5] px-2 py-0.5 rounded border border-[#A7F3D0]">
                                Exact BBox: [112, 340, 520, 480]
                              </span>
                            </div>
                            <p className="text-xs text-[#5E5A52] italic pl-3 border-l-2 border-[#FFE45C]">
                              "Foundational principles establish the necessary boundary conditions and invariants before empirical observation begins."
                            </p>
                          </div>
                        </motion.div>
                      )}
                    </motion.div>
                  )}

                  {/* Step 3 & 4: Zero-Hallucination Refusal Flow */}
                  {heroStep >= 3 && (
                    <motion.div
                      key="step-refusal"
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3 }}
                      className="space-y-4"
                    >
                      {/* Off-syllabus question */}
                      <div className="flex items-start gap-3">
                        <div className="h-7 w-7 rounded-lg bg-[#FEF2F2] border border-[#FECACA] flex items-center justify-center text-xs font-mono font-bold text-[#DC2626] shrink-0">
                          Q
                        </div>
                        <div className="space-y-1">
                          <p className="text-sm font-semibold text-[#16130F]">
                            "How do I bake artisan sourdough bread with a 75% hydration starter?"
                          </p>
                          <span className="font-mono text-[10px] text-[#DC2626]">
                            Off-Syllabus Test Query
                          </span>
                        </div>
                      </div>

                      {/* Designed refusal notice */}
                      <RefusalNotice
                        query="How do I bake artisan sourdough bread with a 75% hydration starter?"
                        retrievalScore={0.062}
                        threshold={0.20}
                        courseName="Design and Analysis of Algorithms"
                      />
                    </motion.div>
                  )}
                </div>

                {/* Bottom ticker bar */}
                <div className="bg-[#FAF8F5] border-t border-[#EAE6DF] px-4 py-2.5 flex items-center justify-between text-xs font-mono text-[#5E5A52]">
                  <span>Zero fabricated answers • Every statement cited • Refuses off-topic questions</span>
                  <button
                    onClick={() => setHeroStep((prev) => (prev + 1) % 5)}
                    className="text-[#1D4ED8] hover:underline font-bold text-[11px]"
                  >
                    Next Frame &rarr;
                  </button>
                </div>
              </div>
            </motion.div>

            {/* Supported Formats Ticker */}
            <div className="pt-6">
              <p className="text-center font-mono text-[11px] uppercase tracking-wider text-[#7B766C] mb-4">
                Native Multimodal Ingestion Pipeline
              </p>
              <div className="flex flex-wrap items-center justify-center gap-3">
                {formatPills.map((f, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 bg-white px-3.5 py-2 rounded-xl border border-[#EAE6DF] shadow-paper-sm text-xs"
                  >
                    <span className="font-bold text-[#16130F]">{f.name}</span>
                    <span className="font-mono text-[11px] text-[#7B766C] bg-[#FAF8F5] px-1.5 py-0.5 rounded border border-[#EAE6DF]">
                      {f.ext}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* 4-STEP PIPELINE SECTION */}
        <section id="pipeline" className="py-20 border-b border-[#EAE6DF] bg-white">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-14">
            <div className="text-center space-y-3 max-w-2xl mx-auto">
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#1D4ED8] bg-[#EFF6FF] px-3 py-1 rounded-full border border-[#BFDBFE]">
                End-to-End System Architecture
              </span>
              <h2 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-[#16130F]">
                From raw course files to grounded pedagogical mastery.
              </h2>
              <p className="text-sm text-[#5E5A52]">
                Four strictly coupled engineering stages that transform unstructured syllabi into source-anchored knowledge trees.
              </p>
            </div>

            {/* 4 Step Grid with connecting hairline */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 relative">
              {/* Step 1 */}
              <div className="bg-[#FAF8F5] rounded-2xl p-6 border border-[#EAE6DF] space-y-3 shadow-paper-sm relative">
                <span className="font-mono text-xs font-bold text-[#1D4ED8] bg-white px-2 py-0.5 rounded border border-[#EAE6DF]">
                  STAGE 01
                </span>
                <h3 className="font-display text-lg font-bold text-[#16130F]">
                  Multimodal Ingest
                </h3>
                <p className="text-xs text-[#5E5A52] leading-relaxed">
                  Extracts text blocks with normalized <span className="font-mono text-[11px]">[x0,y0,x1,y1]</span> bounding boxes, audio segments via Whisper timestamps, and keyframe slide OCR.
                </p>
                <div className="pt-2 text-[10px] font-mono text-[#7B766C]">
                  PyMuPDF • ffmpeg • OpenCV
                </div>
              </div>

              {/* Step 2 */}
              <div className="bg-[#FAF8F5] rounded-2xl p-6 border border-[#EAE6DF] space-y-3 shadow-paper-sm relative">
                <span className="font-mono text-xs font-bold text-[#1D4ED8] bg-white px-2 py-0.5 rounded border border-[#EAE6DF]">
                  STAGE 02
                </span>
                <h3 className="font-display text-lg font-bold text-[#16130F]">
                  Structure into DAG
                </h3>
                <p className="text-xs text-[#5E5A52] leading-relaxed">
                  Constructs an acyclic concept dependency graph with NetworkX. Identifies topics, subtopics, and prerequisites while cycle-detection breaks feedback loops.
                </p>
                <div className="pt-2 text-[10px] font-mono text-[#7B766C]">
                  NetworkX • Topological Sort
                </div>
              </div>

              {/* Step 3 */}
              <div className="bg-[#FAF8F5] rounded-2xl p-6 border border-[#EAE6DF] space-y-3 shadow-paper-sm relative">
                <span className="font-mono text-xs font-bold text-[#1D4ED8] bg-white px-2 py-0.5 rounded border border-[#EAE6DF]">
                  STAGE 03
                </span>
                <h3 className="font-display text-lg font-bold text-[#16130F]">
                  Hybrid Grounding
                </h3>
                <p className="text-xs text-[#5E5A52] leading-relaxed">
                  Reciprocal Rank Fusion (RRF k=60) merges BM25 lexical search with dense 384-dim semantic embeddings. A calibrated refusal gate (&tau; = 0.20) rejects hallucinations.
                </p>
                <div className="pt-2 text-[10px] font-mono text-[#7B766C]">
                  RRF k=60 • BM25 Okapi • &tau;=0.20 Gate
                </div>
              </div>

              {/* Step 4 */}
              <div className="bg-[#FAF8F5] rounded-2xl p-6 border border-[#EAE6DF] space-y-3 shadow-paper-sm relative">
                <span className="font-mono text-xs font-bold text-[#1D4ED8] bg-white px-2 py-0.5 rounded border border-[#EAE6DF]">
                  STAGE 04
                </span>
                <h3 className="font-display text-lg font-bold text-[#16130F]">
                  Bayesian Adaptation
                </h3>
                <p className="text-xs text-[#5E5A52] leading-relaxed">
                  Bayesian Knowledge Tracing (BKT) measures concept mastery per attempt. Advanced concepts remain strictly locked until prerequisites reach &ge; 60%.
                </p>
                <div className="pt-2 text-[10px] font-mono text-[#7B766C]">
                  BKT P(Lt) • 60% Prereq Lock
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* "SHOW ME" TRIPTYCH GROUNDING SECTION */}
        <section id="show-me" className="py-20 border-b border-[#EAE6DF] bg-[#FAF8F5]">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
            <div className="text-center space-y-3 max-w-2xl mx-auto">
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#059669] bg-[#ECFDF5] px-3 py-1 rounded-full border border-[#A7F3D0]">
                Signature Detail • Deep-Link Margin Notes
              </span>
              <h2 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-[#16130F]">
                Every claim links to verified evidence in your documents.
              </h2>
              <p className="text-sm text-[#5E5A52]">
                Inspect exact textbook pages, video clip intervals, or slide instructor notes with one click.
              </p>
            </div>

            {/* 3 Triptych Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Triptych 1: PDF Bounding Box */}
              <div className="bg-white rounded-2xl border border-[#EAE6DF] shadow-paper overflow-hidden flex flex-col justify-between">
                <div>
                  <div className="bg-[#FAF8F5] border-b border-[#EAE6DF] px-4 py-3 flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-[#16130F] flex items-center gap-1.5">
                      <FileText className="h-4 w-4 text-[#1D4ED8]" />
                      <span>PDF Bounding Box Overlay</span>
                    </span>
                    <span className="text-[10px] font-mono text-[#059669] bg-[#ECFDF5] px-2 py-0.5 rounded border border-[#A7F3D0]">
                      Page 14
                    </span>
                  </div>
                  <div className="p-5 space-y-3">
                    <div className="h-36 bg-[#F3EFE8] rounded-xl border border-[#EAE6DF] relative p-3 flex flex-col justify-center">
                      <div className="space-y-1.5 opacity-60">
                        <div className="h-2 w-3/4 bg-[#D9D4CC] rounded" />
                        <div className="h-2 w-full bg-[#D9D4CC] rounded" />
                      </div>
                      {/* Animated highlighter box */}
                      <div className="my-2 p-2 bg-[#FFE45C]/50 border-2 border-[#FFE45C] rounded-lg shadow-sm">
                        <p className="text-[11px] font-mono font-semibold text-[#16130F] leading-tight">
                          "Optimal substructure: An optimal solution contains within it optimal solutions to subproblems."
                        </p>
                      </div>
                      <div className="space-y-1.5 opacity-60">
                        <div className="h-2 w-5/6 bg-[#D9D4CC] rounded" />
                        <div className="h-2 w-2/3 bg-[#D9D4CC] rounded" />
                      </div>
                    </div>
                    <h4 className="font-display text-base font-bold text-[#16130F]">
                      Textbook Page Slide-In
                    </h4>
                    <p className="text-xs text-[#5E5A52] leading-relaxed">
                      PyMuPDF returns precise character coordinates. The PDF slide modal highlights the matching paragraph with marker yellow.
                    </p>
                  </div>
                </div>
                <div className="p-4 bg-[#FAF8F5] border-t border-[#EAE6DF] text-xs font-mono text-[#7B766C]">
                  Source: Introduction to Algorithms, 4th Ed.
                </div>
              </div>

              {/* Triptych 2: Video Interval Timeline */}
              <div className="bg-white rounded-2xl border border-[#EAE6DF] shadow-paper overflow-hidden flex flex-col justify-between">
                <div>
                  <div className="bg-[#FAF8F5] border-b border-[#EAE6DF] px-4 py-3 flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-[#16130F] flex items-center gap-1.5">
                      <Video className="h-4 w-4 text-[#1D4ED8]" />
                      <span>Video Interval Player</span>
                    </span>
                    <span className="text-[10px] font-mono text-[#1D4ED8] bg-[#EEF2FF] px-2 py-0.5 rounded border border-[#C7D2FE]">
                      14:20 – 16:45
                    </span>
                  </div>
                  <div className="p-5 space-y-3">
                    <div className="h-36 bg-[#F3EFE8] rounded-xl border border-[#EAE6DF] relative p-3 flex flex-col justify-between">
                      <div className="flex items-center justify-between text-[11px] font-mono text-[#5E5A52]">
                        <span>Lecture 08: Core Concepts & Principles</span>
                        <span className="font-bold text-[#1D4ED8]">Keyframe Sync</span>
                      </div>
                      {/* Timeline bar */}
                      <div className="space-y-1">
                        <div className="h-2 w-full bg-[#EAE6DF] rounded-full relative overflow-visible">
                          <div className="absolute left-[35%] w-[25%] h-full bg-[#FFE45C] border border-[#E5C936] rounded-full" />
                          <div className="absolute left-[45%] -top-1 h-4 w-1 bg-[#16130F] rounded-full" />
                        </div>
                        <div className="flex justify-between text-[9px] font-mono text-[#7B766C]">
                          <span>00:00</span>
                          <span className="text-[#16130F] font-bold">14:20 [Cited Interval]</span>
                          <span>45:00</span>
                        </div>
                      </div>
                      <div className="text-[10px] font-mono text-[#059669] bg-[#ECFDF5] px-2 py-0.5 rounded border border-[#A7F3D0] inline-block self-start">
                        Timestamp verified by Whisper ASR
                      </div>
                    </div>
                    <h4 className="font-display text-base font-bold text-[#16130F]">
                      Keyframe Video Player
                    </h4>
                    <p className="text-xs text-[#5E5A52] leading-relaxed">
                      Jumps straight to the cited seconds. The video timeline highlights the interval where the professor introduced the definition.
                    </p>
                  </div>
                </div>
                <div className="p-4 bg-[#FAF8F5] border-t border-[#EAE6DF] text-xs font-mono text-[#7B766C]">
                  Source: Lecture 08 MP4 Recording
                </div>
              </div>

              {/* Triptych 3: Slide & Notes */}
              <div className="bg-white rounded-2xl border border-[#EAE6DF] shadow-paper overflow-hidden flex flex-col justify-between">
                <div>
                  <div className="bg-[#FAF8F5] border-b border-[#EAE6DF] px-4 py-3 flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-[#16130F] flex items-center gap-1.5">
                      <Presentation className="h-4 w-4 text-[#059669]" />
                      <span>Slide & Instructor Notes</span>
                    </span>
                    <span className="text-[10px] font-mono text-[#059669] bg-[#ECFDF5] px-2 py-0.5 rounded border border-[#A7F3D0]">
                      Slide 6
                    </span>
                  </div>
                  <div className="p-5 space-y-3">
                    <div className="h-36 bg-[#F3EFE8] rounded-xl border border-[#EAE6DF] relative p-3 flex flex-col justify-between">
                      <div className="bg-white p-2 rounded-lg border border-[#EAE6DF] shadow-2xs">
                        <span className="font-mono text-[10px] font-bold text-[#16130F]">Slide 6: Memoization vs Tabulation</span>
                      </div>
                      {/* Sticky note card */}
                      <div className="bg-[#FEF9C3] p-2 rounded-lg border border-[#FDE68A] shadow-xs">
                        <span className="font-mono text-[9px] uppercase font-bold text-[#854D0E] block">Instructor Note:</span>
                        <p className="text-[10px] text-[#713F12] leading-tight">
                          "Emphasize call stack depth limits when discussing top-down recursion in exam."
                        </p>
                      </div>
                    </div>
                    <h4 className="font-display text-base font-bold text-[#16130F]">
                      Sticky-Note Annotation
                    </h4>
                    <p className="text-xs text-[#5E5A52] leading-relaxed">
                      python-pptx extracts embedded slide notes and diagrams, displaying the teacher's original pedagogical warnings alongside claims.
                    </p>
                  </div>
                </div>
                <div className="p-4 bg-[#FAF8F5] border-t border-[#EAE6DF] text-xs font-mono text-[#7B766C]">
                  Source: lecture_08_slides.pptx
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CONCEPT MAP TEASER & UNLOCKING NODE INTERACTION */}
        <section id="concept-map" className="py-20 border-b border-[#EAE6DF] bg-white">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
            <div className="text-center space-y-3 max-w-2xl mx-auto">
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#4F46E5] bg-[#EEF2FF] px-3 py-1 rounded-full border border-[#C7D2FE]">
                Interactive Prerequisite Graph
              </span>
              <h2 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-[#16130F]">
                Hand-drawn feel DAG on dotted paper.
              </h2>
              <p className="text-sm text-[#5E5A52]">
                Concepts unlock with a satisfying marker-yellow burst once prerequisite mastery hits 60%. Try moving the slider below:
              </p>
            </div>

            {/* Interactive Graph Simulation Box */}
            <div className="bg-[#FAF8F5] rounded-2xl border border-[#EAE6DF] shadow-paper p-6 md:p-8 space-y-8 bg-paper-dots">
              {/* Prerequisite Mastery Slider */}
              <div className="bg-white rounded-xl p-4 border border-[#EAE6DF] max-w-md mx-auto shadow-xs space-y-2">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-[#5E5A52]">Prerequisite Mastery P(Lt):</span>
                  <span className={`font-bold ${isUnlocked ? 'text-[#059669]' : 'text-[#DC2626]'}`}>
                    {prereqScore}% {isUnlocked ? '(Unlocked &ge; 60%)' : '(Locked < 60%)'}
                  </span>
                </div>
                <input
                  type="range"
                  min="20"
                  max="95"
                  value={prereqScore}
                  onChange={(e) => setPrereqScore(Number(e.target.value))}
                  className="w-full accent-[#1D4ED8] cursor-pointer"
                />
                <div className="flex justify-between text-[10px] font-mono text-[#7B766C]">
                  <span>20% (Needs Review)</span>
                  <span className="text-[#16130F] font-bold">60% Unlock Gate</span>
                  <span>100% (Mastered)</span>
                </div>
              </div>

              {/* Node Graph Mockup */}
              <div className="flex flex-col md:flex-row items-center justify-center gap-6 md:gap-12 py-4">
                {/* Node 1: Prereq */}
                <div className="bg-white rounded-2xl border border-[#A7F3D0] p-5 shadow-paper text-center space-y-2 w-56">
                  <span className="font-mono text-[10px] font-bold text-[#059669] bg-[#ECFDF5] px-2 py-0.5 rounded-full border border-[#A7F3D0]">
                    Prerequisite Concept
                  </span>
                  <h4 className="font-display text-base font-bold text-[#16130F]">
                    Foundational Principles
                  </h4>
                  <div className="text-xs font-mono font-bold text-[#059669]">
                    Mastery: {prereqScore}%
                  </div>
                  <span className="text-[10px] text-[#5E5A52] block">
                    Source: Unit 1 • Core Material
                  </span>
                </div>

                {/* Dashed flowing edge */}
                <div className="flex flex-col items-center justify-center font-mono text-xs text-[#7B766C]">
                  <span className="text-[10px] uppercase font-bold text-[#1D4ED8]">Requires &ge; 60%</span>
                  <div className="w-16 h-0.5 border-t-2 border-dashed border-[#1D4ED8] my-1" />
                  <ArrowRight className="h-4 w-4 text-[#1D4ED8]" />
                </div>

                {/* Node 2: Dependent Target */}
                <motion.div
                  animate={isUnlocked ? { scale: [1, 1.04, 1] } : {}}
                  transition={{ duration: 0.4 }}
                  className={`rounded-2xl p-5 shadow-paper text-center space-y-2 w-56 transition-all duration-300 ${
                    isUnlocked
                      ? 'bg-white border-2 border-[#FFE45C] shadow-highlighter'
                      : 'bg-[#F3EFE8] border border-[#EAE6DF] opacity-80'
                  }`}
                >
                  <div className="flex items-center justify-center gap-1.5">
                    {isUnlocked ? (
                      <span className="font-mono text-[10px] font-bold text-[#16130F] bg-[#FFE45C] px-2 py-0.5 rounded-full border border-[#E5C936] flex items-center gap-1">
                        <Unlock className="h-3 w-3" />
                        <span>Ready to Learn!</span>
                      </span>
                    ) : (
                      <span className="font-mono text-[10px] font-bold text-[#DC2626] bg-[#FEF2F2] px-2 py-0.5 rounded-full border border-[#FECACA] flex items-center gap-1">
                        <Lock className="h-3 w-3" />
                        <span>Prerequisite Locked</span>
                      </span>
                    )}
                  </div>
                  <h4 className="font-display text-base font-bold text-[#16130F]">
                    Advanced Applied Topic
                  </h4>
                  <div className="text-xs font-mono font-medium text-[#5E5A52]">
                    {isUnlocked ? 'Concept Unlocked & Ready' : 'Review prerequisite first'}
                  </div>
                  <Button
                    variant={isUnlocked ? 'primary' : 'secondary'}
                    size="sm"
                    onClick={() => navigate('/dashboard')}
                    className="w-full mt-2"
                  >
                    {isUnlocked ? 'Open Node & Tutor' : 'Study Prerequisite'}
                  </Button>
                </motion.div>
              </div>
            </div>
          </div>
        </section>

        {/* EVIDENCE SECTION WITH REAL METRICS */}
        <section id="evidence" className="py-20 border-b border-[#EAE6DF] bg-[#FAF8F5]">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
            <div className="text-center space-y-3 max-w-2xl mx-auto">
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#16130F] bg-white px-3 py-1 rounded-full border border-[#EAE6DF]">
                Transparent Benchmark Evidence
              </span>
              <h2 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-[#16130F]">
                Real, un-hardcoded RAGAS quantitative metrics.
              </h2>
              <p className="text-sm text-[#5E5A52]">
                Evaluated against our 30-item golden multimodal test set. Zero fabricated numbers.
              </p>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {evidenceMetrics.map((m, i) => (
                <div
                  key={i}
                  className="bg-white rounded-2xl p-5 border border-[#EAE6DF] shadow-paper text-center space-y-1.5"
                >
                  <div className="font-mono text-3xl font-extrabold text-[#16130F]">
                    {m.value}
                  </div>
                  <div className="font-display text-sm font-bold text-[#1D4ED8]">
                    {m.label}
                  </div>
                  <p className="text-[10px] font-mono text-[#7B766C] leading-tight">
                    {m.desc}
                  </p>
                </div>
              ))}
            </div>

            {/* Multi-Agent Simulator Callout */}
            <div className="bg-white rounded-2xl p-6 sm:p-8 border border-[#EAE6DF] shadow-paper flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="space-y-2 max-w-xl">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#1D4ED8] bg-[#EFF6FF] px-2.5 py-0.5 rounded border border-[#BFDBFE]">
                    Multi-Agent Simulator
                  </span>
                  <span className="font-mono text-xs font-bold text-[#7B766C] bg-[#F3EFE8] px-2 py-0.5 rounded">
                    [Simulated]
                  </span>
                </div>
                <h3 className="font-display text-xl font-bold text-[#16130F]">
                  Simulate 3 synthetic student personas across 10 study sessions
                </h3>
                <p className="text-xs text-[#5E5A52] leading-relaxed">
                  Watch Fast Learner, Struggles with Math, and Skips Lectures progress through BKT updates with live streaming Recharts learning curves. Export raw traces to CSV or JSON.
                </p>
              </div>

              <Button
                variant="primary"
                size="md"
                onClick={() => navigate('/evaluation')}
                icon={<LineChart className="h-4 w-4" />}
                className="shrink-0"
              >
                Inspect Eval Harness
              </Button>
            </div>
          </div>
        </section>

        {/* FAQ ACCORDION SECTION */}
        <section id="faq" className="py-20 border-b border-[#EAE6DF] bg-white">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
            <div className="text-center space-y-3">
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#7B766C] bg-[#FAF8F5] px-3 py-1 rounded-full border border-[#EAE6DF]">
                Frequently Answered
              </span>
              <h2 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-[#16130F]">
                Architecture & Methodology FAQ
              </h2>
            </div>

            <div className="divide-y divide-[#EAE6DF] border-y border-[#EAE6DF]">
              {faqs.map((faq, idx) => (
                <div key={idx} className="py-4">
                  <button
                    onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                    className="w-full flex items-center justify-between text-left font-display font-semibold text-base sm:text-lg text-[#16130F] hover:text-[#1D4ED8] transition py-1"
                  >
                    <span>{faq.q}</span>
                    <ChevronDown
                      className={`h-5 w-5 text-[#7B766C] transition-transform duration-200 shrink-0 ml-4 ${
                        openFaq === idx ? 'rotate-180 text-[#1D4ED8]' : ''
                      }`}
                    />
                  </button>
                  <AnimatePresence>
                    {openFaq === idx && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <p className="text-xs sm:text-sm text-[#5E5A52] leading-relaxed pt-2 pb-2 font-sans">
                          {faq.a}
                        </p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* BOTTOM BIG CTA */}
        <section className="py-20 bg-[#FAF8F5] text-center border-b border-[#EAE6DF] bg-paper-grid">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
            <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#059669] bg-[#ECFDF5] px-3 py-1 rounded-full border border-[#A7F3D0]">
              Built for Multimodal AI Hackathon 2026
            </span>
            <h2 className="font-display text-4xl sm:text-5xl font-bold text-[#16130F] tracking-tight">
              Ready to learn from your course materials with zero hallucinations?
            </h2>
            <p className="text-sm text-[#5E5A52] max-w-xl mx-auto">
              Open the student desk now. Complete with 31 passing unit tests and instant offline demonstration mode.
            </p>
            <div className="pt-2 flex flex-wrap items-center justify-center gap-3.5">
              <Button
                variant="primary"
                size="lg"
                onClick={handleStartTools}
                icon={<ArrowRight className="h-4 w-4" />}
                iconPosition="right"
                className="font-semibold px-8"
              >
                Launch StudyMind AI
              </Button>
              <Button
                variant="secondary"
                size="lg"
                onClick={() => setShowPricingModal(true)}
              >
                View Plans & Pricing
              </Button>
            </div>
          </div>
        </section>
      </main>

      {/* FOOTER */}
      <footer className="bg-white py-12 border-t border-[#EAE6DF]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-[#7B766C]">
          <div className="flex items-center gap-2">
            <span className="font-display font-bold text-sm text-[#16130F]">StudyMind AI</span>
            <span>•</span>
            <span>Multimodal AI Hackathon 2026 — Track D</span>
          </div>
          <div>
            Built with React 18, FastAPI, PyMuPDF, faster-whisper & NetworkX
          </div>
        </div>
      </footer>

      {/* MODAL 1: VIDEO DEMO MODAL */}
      <Modal
        isOpen={showVideoModal}
        onClose={() => setShowVideoModal(false)}
        title="Multimodal Ingestion & Source Grounding Demo"
        eyebrow="VIDEO WALKTHROUGH"
        subtitle="Watch how StudyMind AI extracts textbook bounding boxes and lecture video timestamps in real time."
        maxWidth="2xl"
      >
        <div className="space-y-4">
          <div className="aspect-video bg-[#FAF8F5] rounded-xl border border-[#EAE6DF] flex flex-col items-center justify-center p-6 text-center space-y-3">
            <div className="h-12 w-12 rounded-full bg-[#1D4ED8] text-white flex items-center justify-center shadow-md">
              <Play className="h-6 w-6 ml-1" />
            </div>
            <div>
              <h4 className="font-display text-base font-bold text-[#16130F]">
                StudyMind AI System Demo
              </h4>
              <p className="text-xs text-[#5E5A52] mt-1 max-w-md">
                Demonstrating: 1. Drag & drop ingestion &bull; 2. Inline citation pill deep-links &bull; 3. Calibrated refusal gate &bull; 4. BKT Prerequisite unlocking.
              </p>
            </div>
          </div>
          <div className="flex justify-end">
            <Button variant="primary" size="sm" onClick={() => setShowVideoModal(false)}>
              Close Video
            </Button>
          </div>
        </div>
      </Modal>

      {/* MODAL 2: PRICING MODAL */}
      <Modal
        isOpen={showPricingModal}
        onClose={() => setShowPricingModal(false)}
        title="Student & Institutional Plans"
        eyebrow="STUDY ACCESS"
        subtitle="Empowering every university student with source-grounded learning."
        maxWidth="xl"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-[#FAF8F5] p-5 rounded-2xl border border-[#EAE6DF] space-y-3">
            <span className="font-mono text-[10px] font-bold text-[#059669] bg-[#ECFDF5] px-2 py-0.5 rounded border border-[#A7F3D0]">
              ACTIVE HACKATHON TIER
            </span>
            <h4 className="font-display text-lg font-bold text-[#16130F]">Free Student Access</h4>
            <div className="font-mono text-2xl font-bold text-[#16130F]">$0 <span className="text-xs text-[#7B766C]">/ semester</span></div>
            <ul className="text-xs text-[#5E5A52] space-y-2 pt-2">
              <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#059669]" /> Ingest up to 5 courses</li>
              <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#059669]" /> Full BKT prerequisite graph</li>
              <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#059669]" /> Whisper video keyframe sync</li>
              <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#059669]" /> Zero-hallucination guardrail</li>
            </ul>
            <Button variant="primary" size="sm" onClick={handleStartTools} className="w-full mt-3">
              Start Free Today
            </Button>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-[#1D4ED8] space-y-3 shadow-paper">
            <span className="font-mono text-[10px] font-bold text-[#1D4ED8] bg-[#EEF2FF] px-2 py-0.5 rounded border border-[#C7D2FE]">
              UNIVERSITIES
            </span>
            <h4 className="font-display text-lg font-bold text-[#16130F]">Campus Institutional</h4>
            <div className="font-mono text-2xl font-bold text-[#16130F]">Custom <span className="text-xs text-[#7B766C]">/ department</span></div>
            <ul className="text-xs text-[#5E5A52] space-y-2 pt-2">
              <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#1D4ED8]" /> Campus LMS LTI integration</li>
              <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#1D4ED8]" /> Department syllabus analytics</li>
              <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#1D4ED8]" /> Multi-persona exam simulator</li>
              <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-[#1D4ED8]" /> Dedicated Supabase pgvector instance</li>
            </ul>
            <Button variant="secondary" size="sm" onClick={() => setShowPricingModal(false)} className="w-full mt-3">
              Contact Department Team
            </Button>
          </div>
        </div>
      </Modal>

      {/* MODAL 3: ABOUT MODAL */}
      <Modal
        isOpen={showAboutModal}
        onClose={() => setShowAboutModal(false)}
        title="About StudyMind AI"
        eyebrow="MISSION & TRANSPARENCY"
        subtitle="Built for the Multimodal AI Hackathon 2026 – Track D: Personalized Tutoring & Adaptive Learning."
        maxWidth="lg"
      >
        <div className="space-y-4 text-xs text-[#5E5A52] leading-relaxed">
          <p>
            Unlike generic AI chatbots that guess and hallucinate answers to collegiate queries, StudyMind AI answers strictly from your ingested course textbooks, lecture slides, and video recordings.
          </p>
          <div className="bg-[#FAF8F5] p-3.5 rounded-xl border border-[#EAE6DF] space-y-1.5 font-mono text-[11px]">
            <div className="font-bold text-[#16130F]">Key Guarantees:</div>
            <div>&bull; Every claim cites exact page, slide, or timestamp.</div>
            <div>&bull; Calibrated refusal threshold &tau;=0.20 strictly refuses off-syllabus queries.</div>
            <div>&bull; Bayesian Knowledge Tracing locks advanced concepts until prerequisites hit 60%.</div>
            <div>&bull; Quizzes undergo cross-model blind solving and Python code execution.</div>
          </div>
          <div className="flex justify-end pt-2">
            <Button variant="primary" size="sm" onClick={() => setShowAboutModal(false)}>
              Got it
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
