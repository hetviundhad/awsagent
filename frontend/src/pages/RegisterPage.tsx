import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, Lock, User, Eye, EyeOff, ArrowRight, Sparkles, FileText, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui';

export const RegisterPage: React.FC = () => {
  const { signUp, signIn } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!fullName.trim()) { setError('Full name is required.'); return; }
    if (password.length < 6) { setError('Password must be at least 6 characters.'); return; }
    if (password !== confirmPassword) { setError('Passwords do not match.'); return; }
    setLoading(true);
    const result = await signUp(email.trim(), password, fullName.trim());
    if (result.error) {
      setError(result.error);
      setLoading(false);
    } else {
      navigate('/dashboard', { replace: true });
    }
  };

  const handleDemoRegister = async () => {
    setLoading(true);
    setError('');
    const signInErr = await signIn('demo@studymind.ai', 'demo1234');
    if (!signInErr) {
      navigate('/dashboard', { replace: true });
      return;
    }
    const result = await signUp('demo@studymind.ai', 'demo1234', 'Demo Student');
    if (result.error) {
      setError(result.error);
      setLoading(false);
    } else {
      navigate('/dashboard', { replace: true });
    }
  };

  return (
    <div className="min-h-screen bg-[#FAF8F5] flex flex-col lg:flex-row text-[#16130F]">
      {/* LEFT: Editorial Registration Form */}
      <div className="w-full lg:w-1/2 flex flex-col justify-between p-6 sm:p-10 lg:p-14 max-w-xl mx-auto lg:max-w-none">
        <div>
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
              CREATE STUDENT ACCOUNT
            </span>
            <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-[#16130F]">
              Begin your source-grounded learning journey.
            </h1>
            <p className="text-xs sm:text-sm text-[#5E5A52] leading-relaxed">
              Create an account to start tracking mastery with Bayesian Knowledge Tracing and locking prerequisites.
            </p>
          </div>

          {/* Quick Demo Access */}
          <div className="bg-white rounded-2xl border border-[#E5C936] p-4 shadow-paper space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] font-bold text-[#16130F] bg-[#FFE45C] px-2 py-0.5 rounded border border-[#E5C936]">
                INSTANT EVALUATION
              </span>
              <span className="font-mono text-xs text-[#059669] font-medium flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Zero Setup Required
              </span>
            </div>
            <Button
              variant="highlighter"
              size="md"
              onClick={handleDemoRegister}
              isLoading={loading}
              icon={<ArrowRight className="h-4 w-4" />}
              iconPosition="right"
              className="w-full font-bold"
            >
              Start Instantly with Demo Account
            </Button>
          </div>

          <div className="relative flex items-center py-1">
            <div className="flex-grow border-t border-[#EAE6DF]" />
            <span className="flex-shrink mx-3 text-[10px] font-mono uppercase text-[#7B766C]">
              or register with email
            </span>
            <div className="flex-grow border-t border-[#EAE6DF]" />
          </div>

          {error && (
            <div className="p-3.5 rounded-xl bg-[#FEF2F2] border border-[#FECACA] text-[#DC2626] text-xs font-mono">
              {error}
            </div>
          )}

          {message && (
            <div className="p-3.5 rounded-xl bg-[#ECFDF5] border border-[#A7F3D0] text-[#059669] text-xs font-mono">
              {message}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <label className="block text-xs font-semibold text-[#16130F]">Full Name</label>
              <div className="relative">
                <User className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#7B766C] pointer-events-none" />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Student Name"
                  className="w-full pl-9 pr-3 py-2.5 text-xs rounded-xl bg-white border border-[#EAE6DF] text-[#16130F] placeholder-[#7B766C] focus:outline-none focus:border-[#1D4ED8] focus:ring-1 focus:ring-[#1D4ED8] transition min-h-[44px]"
                />
              </div>
            </div>

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

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="block text-xs font-semibold text-[#16130F]">Password</label>
                <div className="relative">
                  <Lock className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#7B766C] pointer-events-none" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-9 pr-8 py-2.5 text-xs rounded-xl bg-white border border-[#EAE6DF] text-[#16130F] placeholder-[#7B766C] focus:outline-none focus:border-[#1D4ED8] transition min-h-[44px]"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold text-[#16130F]">Confirm Password</label>
                <div className="relative">
                  <Lock className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#7B766C] pointer-events-none" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-9 pr-8 py-2.5 text-xs rounded-xl bg-white border border-[#EAE6DF] text-[#16130F] placeholder-[#7B766C] focus:outline-none focus:border-[#1D4ED8] transition min-h-[44px]"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#7B766C] hover:text-[#16130F] transition"
                  >
                    {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                  </button>
                </div>
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={loading}
              className="w-full font-semibold"
            >
              Create Account
            </Button>
          </form>

          <p className="text-center text-xs text-[#5E5A52] pt-2">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-[#1D4ED8] hover:underline">
              Sign in
            </Link>
          </p>
        </div>

        <div className="text-center text-[11px] font-mono text-[#7B766C]">
          Track D: Personalized Tutoring & Adaptive Learning • 2026
        </div>
      </div>

      {/* RIGHT: Calm illustration of annotated paper and knowledge tracing */}
      <div className="hidden lg:flex w-1/2 bg-[#F3EFE8] border-l border-[#EAE6DF] p-12 flex-col justify-between relative overflow-hidden bg-paper-dots">
        <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-[#FFE45C]/20 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex justify-end">
          <span className="font-mono text-xs text-[#7B766C] bg-white/80 px-3 py-1 rounded-full border border-[#EAE6DF]">
            NetworkX DAG & BKT Architecture
          </span>
        </div>

        <div className="relative z-10 max-w-md mx-auto my-auto space-y-6">
          <motion.div
            initial={{ y: 15, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.6, ease: [0.2, 0.8, 0.2, 1] }}
            className="bg-white rounded-2xl p-6 border border-[#EAE6DF] shadow-paper-lg space-y-4"
          >
            <div className="flex items-center justify-between border-b border-[#EAE6DF] pb-3 text-xs font-mono">
              <span className="font-bold text-[#16130F] flex items-center gap-1.5">
                <Sparkles className="h-4 w-4 text-[#059669]" />
                <span>Bayesian Learner Profile</span>
              </span>
              <span className="text-[#1D4ED8] bg-[#EEF2FF] px-2 py-0.5 rounded border border-[#C7D2FE]">
                60% Lock Active
              </span>
            </div>

            <p className="text-xs text-[#5E5A52] leading-relaxed">
              "Concepts with prerequisites &lt; 60% mastery are safely locked. The tutor guides you through foundational steps before opening advanced algorithms."
            </p>

            <div className="p-3 bg-[#FAF8F5] rounded-xl border border-[#EAE6DF] text-[11px] font-mono text-[#5E5A52] space-y-1">
              <div>&bull; Verified Entailment Check: <span className="text-[#059669] font-bold">Passed</span></div>
              <div>&bull; Python Code Execution: <span className="text-[#1D4ED8] font-bold">O(N) Invariant Checked</span></div>
            </div>
          </motion.div>
        </div>

        <div className="relative z-10 text-center font-serif text-sm text-[#5E5A52] italic">
          "Source-grounded. Zero hallucinations. Transparent knowledge tracing."
        </div>
      </div>
    </div>
  );
};
