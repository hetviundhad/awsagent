import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, Lock, Eye, EyeOff, ArrowRight, Sparkles, FileText, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui';

export const LoginPage: React.FC = () => {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) return;
    setLoading(true);
    setError('');
    const err = await signIn(email.trim(), password);
    if (err) {
      setError(err);
      setLoading(false);
    } else {
      navigate('/dashboard', { replace: true });
    }
  };

  const handleDemoLogin = async () => {
    setLoading(true);
    setError('');
    const err = await signIn('demo@studymind.ai', 'demo1234');
    if (err) {
      setError(err);
      setLoading(false);
    } else {
      navigate('/dashboard', { replace: true });
    }
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] flex flex-col lg:flex-row text-[#16130F]">
      {/* LEFT: Editorial Sign In Form */}
      <div className="w-full lg:w-1/2 flex flex-col justify-between p-6 sm:p-10 lg:p-14 max-w-xl mx-auto lg:max-w-none">
        <div>
          {/* Brand */}
          <Link to="/" className="inline-flex items-center gap-2.5 group">
            <div className="h-9 w-9 rounded-xl bg-white border border-[#EAE6DF] flex items-center justify-center text-[#1D4ED8] shadow-xs group-hover:border-[#FFE45C] group-hover:bg-[#FFFBEB] transition-colors">
              <Sparkles className="h-4.5 w-4.5 text-[#1D4ED8]" />
            </div>
            <div className="flex items-center gap-1.5">
              <span className="font-display font-bold text-lg tracking-tight text-[#16130F]">
                StudyMind
              </span>
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-[#FFE45C] text-[#16130F] border border-[#E5C936]">
                AI
              </span>
            </div>
          </Link>
        </div>

        {/* Center Form Container */}
        <div className="my-auto py-8 max-w-md w-full mx-auto space-y-6">
          <div className="space-y-1.5">
            <span className="font-mono text-xs uppercase tracking-wider text-[#7B766C]">
              STUDENT DESK ACCESS
            </span>
            <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-[#16130F]">
              Welcome back to your study desk.
            </h1>
            <p className="text-xs sm:text-sm text-[#5E5A52] leading-relaxed">
              Sign in to resume grounded tutoring, review forgetting curve decks, and practice verified assessments.
            </p>
          </div>

          {/* 1-Click Instant Demo Access */}
          <div className="bg-white rounded-2xl border border-[#E5C936] p-4 shadow-paper space-y-2.5 relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] font-bold text-[#16130F] bg-[#FFE45C] px-2 py-0.5 rounded border border-[#E5C936]">
                INSTANT EVALUATION
              </span>
              <span className="font-mono text-xs text-[#059669] font-medium flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Zero Credentials Needed
              </span>
            </div>
            <div>
              <h4 className="font-display text-sm font-bold text-[#16130F]">
                Multimodal Hackathon Evaluator Account
              </h4>
              <p className="text-[11px] text-[#5E5A52] mt-0.5">
                Pre-seeded with algorithms course, textbook PDFs, lecture slides, and Whisper video transcripts.
              </p>
            </div>
            <Button
              variant="highlighter"
              size="md"
              onClick={handleDemoLogin}
              isLoading={loading}
              icon={<ArrowRight className="h-4 w-4" />}
              iconPosition="right"
              className="w-full font-bold"
            >
              Continue as Demo Student
            </Button>
          </div>

          {/* Divider */}
          <div className="relative flex items-center py-1">
            <div className="flex-grow border-t border-[#EAE6DF]" />
            <span className="flex-shrink mx-3 text-[10px] font-mono uppercase text-[#7B766C]">
              or sign in with university email
            </span>
            <div className="flex-grow border-t border-[#EAE6DF]" />
          </div>

          {error && (
            <div className="p-3.5 rounded-xl bg-[#FEF2F2] border border-[#FECACA] text-[#DC2626] text-xs font-mono">
              {error}
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <label className="block text-xs font-semibold text-[#16130F]">University Email</label>
              <div className="relative">
                <Mail className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#7B766C] pointer-events-none" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="student@university.edu"
                  className="w-full pl-9 pr-3 py-2.5 text-xs rounded-xl bg-white border border-[#EAE6DF] text-[#16130F] placeholder-[#7B766C] focus:outline-none focus:border-[#1D4ED8] focus:ring-1 focus:ring-[#1D4ED8] transition min-h-[44px]"
                />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold text-[#16130F]">Password</label>
              </div>
              <div className="relative">
                <Lock className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#7B766C] pointer-events-none" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-10 py-2.5 text-xs rounded-xl bg-white border border-[#EAE6DF] text-[#16130F] placeholder-[#7B766C] focus:outline-none focus:border-[#1D4ED8] focus:ring-1 focus:ring-[#1D4ED8] transition min-h-[44px]"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#7B766C] hover:text-[#16130F] transition"
                  aria-label="Toggle password visibility"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={loading}
              className="w-full font-semibold"
            >
              Sign In to Study Desk
            </Button>
          </form>

          <p className="text-center text-xs text-[#5E5A52] pt-2">
            Don't have an account yet?{' '}
            <Link to="/register" className="font-semibold text-[#1D4ED8] hover:underline">
              Create an account
            </Link>
          </p>
        </div>

        {/* Footer */}
        <div className="text-center text-[11px] font-mono text-[#7B766C]">
          Track D: Personalized Tutoring & Adaptive Learning • 2026
        </div>
      </div>

      {/* RIGHT: Calm animated illustration of citations floating over annotated paper */}
      <div className="hidden lg:flex w-1/2 bg-[#F3EFE8] border-l border-[#EAE6DF] p-12 flex-col justify-between relative overflow-hidden bg-paper-dots">
        {/* Subtle decorative glow */}
        <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-[#FFE45C]/20 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex justify-end">
          <span className="font-mono text-xs text-[#7B766C] bg-white/80 px-3 py-1 rounded-full border border-[#EAE6DF]">
            Editorial Study Desk Architecture
          </span>
        </div>

        {/* Center Paper & Floating Citation Pills Illustration */}
        <div className="relative z-10 max-w-md mx-auto my-auto space-y-6">
          {/* Main Paper Sheet Card */}
          <motion.div
            initial={{ y: 15, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, ease: [0.2, 0.8, 0.2, 1] }}
            className="bg-white rounded-2xl p-6 border border-[#EAE6DF] shadow-paper-lg space-y-4 relative"
          >
            {/* Header of paper */}
            <div className="flex items-center justify-between border-b border-[#EAE6DF] pb-3 text-xs font-mono">
              <span className="font-bold text-[#16130F] flex items-center gap-1.5">
                <FileText className="h-4 w-4 text-[#1D4ED8]" />
                <span>Lecture Invariant Notes #15</span>
              </span>
              <span className="text-[#059669] bg-[#ECFDF5] px-2 py-0.5 rounded border border-[#A7F3D0]">
                Verified Source
              </span>
            </div>

            <p className="text-xs text-[#5E5A52] leading-relaxed">
              "In dynamic programming, memoization caches the answers to subproblems so they are evaluated at most once{' '}
              <span className="inline-block bg-[#FFE45C] text-[#16130F] font-mono px-1 rounded font-semibold">
                [1] p.14
              </span>
              . The dependency graph must form a directed acyclic graph (DAG)..."
            </p>

            <div className="p-3 bg-[#FAF8F5] rounded-xl border border-[#EAE6DF] text-[11px] font-mono text-[#5E5A52] space-y-1">
              <div>&bull; BKT Prior: <span className="text-[#059669] font-bold">P(L0) = 0.65</span></div>
              <div>&bull; Grounding Threshold: <span className="text-[#1D4ED8] font-bold">&tau; &ge; 0.20</span></div>
            </div>
          </motion.div>

          {/* Floating Margin Note Pill 1 */}
          <motion.div
            animate={{ y: [-4, 4, -4] }}
            transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
            className="inline-flex items-center gap-2 bg-white px-3.5 py-2 rounded-xl border border-[#EAE6DF] shadow-paper text-xs font-mono absolute -top-4 -right-4"
          >
            <span className="font-bold text-[#1D4ED8]">[1]</span>
            <span className="text-[#16130F]">p.14 algorithms.pdf</span>
            <span className="h-2 w-2 rounded-full bg-[#059669]" />
          </motion.div>

          {/* Floating Margin Note Pill 2 */}
          <motion.div
            animate={{ y: [4, -4, 4] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }}
            className="inline-flex items-center gap-2 bg-white px-3.5 py-2 rounded-xl border border-[#EAE6DF] shadow-paper text-xs font-mono absolute -bottom-6 -left-4"
          >
            <span className="font-bold text-[#1D4ED8]">[2]</span>
            <span className="text-[#16130F]">14:20 video lecture clip</span>
            <span className="h-2 w-2 rounded-full bg-[#FFE45C] border border-[#E5C936]" />
          </motion.div>
        </div>

        {/* Footer quote */}
        <div className="relative z-10 text-center font-serif text-sm text-[#5E5A52] italic">
          "Every statement is anchored to a textbook page or lecture video timestamp."
        </div>
      </div>
    </div>
  );
};
