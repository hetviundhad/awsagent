import React, { useState } from 'react';
import { Send, Mic, Sparkles, Loader2 } from 'lucide-react';

interface ComposerProps {
  onSendMessage: (query: string, style: string, language: string) => void;
  isProcessing: boolean;
  activeCourseName: string;
}

export const Composer: React.FC<ComposerProps> = ({
  onSendMessage,
  isProcessing,
  activeCourseName,
}) => {
  const [queryInput, setQueryInput] = useState('');
  // 2 CONTROLS: Style and Language
  const [style, setStyle] = useState<'Simple' | 'Detailed' | 'Quiz me'>('Simple');
  const [language, setLanguage] = useState<'English' | 'Hindi' | 'Hinglish'>('English');

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!queryInput.trim() || isProcessing) return;

    onSendMessage(queryInput.trim(), style, language);
    setQueryInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-slate-200 bg-white p-3 sm:p-4 space-y-3">
      {/* 2 Streamlined Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        {/* Control 1: Style */}
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-mono">
            Style:
          </span>
          <div className="inline-flex bg-slate-100 p-0.5 rounded-xl border border-slate-200">
            {(['Simple', 'Detailed', 'Quiz me'] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setStyle(s)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition cursor-pointer ${
                  style === s
                    ? 'bg-white text-blue-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Control 2: Language */}
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider font-mono">
            Language:
          </span>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as any)}
            className="px-2.5 py-1 text-xs rounded-xl border border-slate-200 bg-slate-50 font-medium text-slate-800 focus:outline-none focus:border-blue-500"
          >
            <option value="English">English</option>
            <option value="Hindi">Hindi (हिंदी)</option>
            <option value="Hinglish">Hinglish</option>
          </select>
        </div>
      </div>

      {/* Input box */}
      <form onSubmit={handleSubmit} className="relative flex items-center">
        <textarea
          rows={2}
          value={queryInput}
          onChange={(e) => setQueryInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Ask anything about ${activeCourseName || 'your course material'}... (Enter to send)`}
          className="w-full pl-4 pr-24 py-2.5 text-xs sm:text-sm rounded-2xl border border-slate-200 bg-slate-50/60 focus:bg-white focus:border-blue-500 focus:outline-none resize-none placeholder-slate-400 text-slate-800 transition"
        />

        <div className="absolute right-2.5 flex items-center gap-1.5">
          <button
            type="submit"
            disabled={!queryInput.trim() || isProcessing}
            className="p-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white font-bold transition shadow-xs cursor-pointer"
            title="Send query"
          >
            {isProcessing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
