import React, { useState, useEffect } from 'react';
import { 
  Flame, Trophy, Sparkles, Volume2, RefreshCw, 
  Play, Pause, RotateCcw, CheckCircle2, Target, Award, Zap
} from 'lucide-react';

interface StudentMotivationHubProps {
  onStartQuiz?: () => void;
  compact?: boolean;
}

const MOTIVATIONAL_QUOTES = [
  {
    quote: "Consistency beats genius every single day. Master your fundamentals and you cannot be stopped.",
    author: "Academic Wisdom"
  },
  {
    quote: "Every complex problem was once considered impossible until broken down step-by-step.",
    author: "Alan Turing"
  },
  {
    quote: "Small daily improvements over time lead to stunning exam results. Keep showing up.",
    author: "Robin Sharma"
  },
  {
    quote: "You don't have to be great to start, but you have to start to be great.",
    author: "Zig Ziglar"
  },
  {
    quote: "Doubt kills more dreams than failure ever will. Believe in your preparation.",
    author: "Suzy Kassem"
  },
  {
    quote: "Mistakes are proof that you are trying and your brain is forming new neural connections.",
    author: "Mindset Science"
  }
];

export const StudentMotivationHub: React.FC<StudentMotivationHubProps> = ({ onStartQuiz, compact = false }) => {
  const [quoteIndex, setQuoteIndex] = useState(0);
  const [streakDays, setStreakDays] = useState(0);
  const [xp, setXp] = useState(0);
  const [level, setLevel] = useState(1);
  const xpNeeded = 500;

  // Pomodoro Focus Timer
  const [focusSeconds, setFocusSeconds] = useState(25 * 60);
  const [isTimerRunning, setIsTimerRunning] = useState(false);
  const [timerMode, setTimerMode] = useState<'study' | 'break'>('study');

  useEffect(() => {
    let interval: any = null;
    if (isTimerRunning && focusSeconds > 0) {
      interval = setInterval(() => {
        setFocusSeconds((prev) => prev - 1);
      }, 1000);
    } else if (focusSeconds === 0) {
      setIsTimerRunning(false);
      if (timerMode === 'study') {
        alert("🎉 Awesome 25-minute focus session completed! You earned +50 Focus XP! Take a 5-minute break.");
        setXp((prev) => prev + 50);
        setTimerMode('break');
        setFocusSeconds(5 * 60);
      } else {
        alert("Break is over! Ready to resume deep study?");
        setTimerMode('study');
        setFocusSeconds(25 * 60);
      }
    }
    return () => clearInterval(interval);
  }, [isTimerRunning, focusSeconds, timerMode]);

  const formatTimer = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const nextQuote = () => {
    setQuoteIndex((prev) => (prev + 1) % MOTIVATIONAL_QUOTES.length);
  };

  const speakQuote = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  };

  const currentQuote = MOTIVATIONAL_QUOTES[quoteIndex];

  if (compact) {
    return (
      <div className="rounded-xl p-3 bg-white border border-[#EAE6DF] shadow-xs flex items-center justify-between text-xs text-slate-700">
        <div className="flex items-center space-x-2">
          <Sparkles className="h-4 w-4 text-amber-500 shrink-0" />
          <span className="italic line-clamp-1">"{currentQuote.quote}"</span>
        </div>
        <div className="flex items-center space-x-1 shrink-0 ml-2">
          <button
            onClick={() => speakQuote(currentQuote.quote)}
            className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-stone-100 transition"
            title="Read aloud"
          >
            <Volume2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl p-5 bg-white border border-[#EAE6DF] shadow-xs relative overflow-hidden space-y-5">
      {/* Header with Streak and Level */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#F0ECE1] pb-4">
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-700 shadow-xs">
            <Flame className="h-5 w-5 fill-amber-500 text-amber-500" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-bold text-slate-900 tracking-tight">
                Daily Study Momentum
              </h2>
              <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200 text-[10px] font-semibold">
                {streakDays} Days on Fire 🔥
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Consistency is your superpower. Every session moves your mastery forward.
            </p>
          </div>
        </div>

        {/* Level and XP progress */}
        <div className="bg-[#FAF8F5] border border-[#EAE6DF] rounded-xl p-3 min-w-[200px] space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-800 flex items-center space-x-1">
              <Award className="h-3.5 w-3.5 text-amber-600" />
              <span>Level {level} Scholar</span>
            </span>
            <span className="text-[11px] text-slate-500 font-mono">{xp} / {xpNeeded} XP</span>
          </div>
          <div className="w-full bg-[#EAE6DF] rounded-full h-2 overflow-hidden">
            <div 
              className="bg-emerald-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min((xp / xpNeeded) * 100, 100)}%` }}
            />
          </div>
          <div className="text-[10px] text-slate-500 flex justify-between">
            <span>Rank: Algorithm Apprentice</span>
            <span className="text-emerald-700 font-medium">+{xpNeeded - xp} XP to Lvl {level + 1}</span>
          </div>
        </div>
      </div>

      {/* Main Motivation Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Left: Daily Inspiring Quote Card */}
        <div className="p-4 rounded-xl bg-[#FAF8F5] border border-[#EAE6DF] flex flex-col justify-between space-y-3">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
                <Sparkles className="h-3.5 w-3.5 text-amber-500" />
                <span>Daily Motivation Boost</span>
              </span>
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => speakQuote(currentQuote.quote)}
                  className="p-1 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-stone-200/60 transition"
                  title="Read aloud"
                >
                  <Volume2 className="h-3.5 w-3.5" />
                </button>
                <button
                  onClick={nextQuote}
                  className="p-1 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-stone-200/60 transition"
                  title="Get another quote"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            <blockquote className="text-xs font-medium text-slate-800 italic leading-relaxed">
              "{currentQuote.quote}"
            </blockquote>
          </div>

          <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-[#EAE6DF]">
            <span className="font-semibold text-slate-700">— {currentQuote.author}</span>
            <span className="text-[10px] text-slate-400">Daily Mindset</span>
          </div>
        </div>

        {/* Right: Pomodoro Deep Focus Study Timer */}
        <div className="p-4 rounded-xl bg-[#FAF8F5] border border-[#EAE6DF] flex flex-col justify-between space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5">
              <Target className="h-3.5 w-3.5 text-emerald-600" />
              <span>Deep Focus Session ({timerMode === 'study' ? '25m Study' : '5m Break'})</span>
            </span>
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-bold ${
              isTimerRunning ? 'bg-emerald-100 text-emerald-800' : 'bg-stone-200/70 text-slate-600'
            }`}>
              {isTimerRunning ? 'ACTIVE' : 'READY'}
            </span>
          </div>

          {/* Timer Display */}
          <div className="flex items-center justify-between">
            <div className="text-2xl sm:text-3xl font-bold font-mono tracking-tight text-slate-900">
              {formatTimer(focusSeconds)}
            </div>

            {/* Timer Controls */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setIsTimerRunning(!isTimerRunning)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition shadow-xs ${
                  isTimerRunning
                    ? 'bg-amber-500 hover:bg-amber-600 text-white'
                    : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                }`}
              >
                {isTimerRunning ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                <span>{isTimerRunning ? 'Pause' : 'Start Focus'}</span>
              </button>
              <button
                onClick={() => {
                  setIsTimerRunning(false);
                  setFocusSeconds(timerMode === 'study' ? 25 * 60 : 5 * 60);
                }}
                className="p-1.5 rounded-xl bg-white text-slate-500 hover:text-slate-800 border border-[#EAE6DF] hover:bg-stone-100 transition"
                title="Reset timer"
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          <div className="text-[11px] text-slate-500 flex items-center justify-between">
            <span>Zero distractions. Earn +50 XP upon session completion.</span>
            <span className="text-emerald-700 font-semibold">+50 XP</span>
          </div>
        </div>
      </div>

      {/* Motivational Quick Checklist & Badges */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1 text-xs text-slate-600">
        <div className="flex items-center space-x-4 flex-wrap gap-y-2">
          <div className="flex items-center space-x-1.5 text-emerald-700 font-medium">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>3 / 5 Daily Questions Asked</span>
          </div>
          <div className="flex items-center space-x-1.5 text-slate-600">
            <Zap className="h-3.5 w-3.5 text-amber-500" />
            <span>1 Study Link Explored</span>
          </div>
          <div className="flex items-center space-x-1.5 text-slate-700">
            <Trophy className="h-3.5 w-3.5 text-amber-500" />
            <span>Safe Mode Ace 🛡️</span>
          </div>
        </div>

        {onStartQuiz && (
          <button
            onClick={onStartQuiz}
            className="px-3 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-medium text-xs flex items-center space-x-1.5 transition shadow-xs"
          >
            <Trophy className="h-3.5 w-3.5 text-amber-400" />
            <span>Quick Practice Quiz</span>
          </button>
        )}
      </div>
    </div>
  );
};
