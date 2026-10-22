import React, { useState } from 'react';
import { Bot, User, AlertCircle, HelpCircle, Sparkles, BookOpen, CheckCircle2, XCircle, Zap } from 'lucide-react';
import { ChatMessage, Citation } from '../../types';
import { CitationChips } from './CitationChips';
import { MarkdownRenderer } from '../MarkdownRenderer';
import { DecisionTraceChip } from '../DecisionTraceChip';

interface MessageListProps {
  messages: ChatMessage[];
  onSelectCitation: (citation: Citation) => void;
  onFollowupClick: (promptText: string) => void;
  isProcessing: boolean;
}

const InteractiveQuizCard: React.FC<{
  quiz: NonNullable<ChatMessage['interactive_quiz']>;
  onFollowupClick: (promptText: string) => void;
}> = ({ quiz, onFollowupClick }) => {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [isAnswered, setIsAnswered] = useState<boolean>(false);

  const cleanCorrect = (quiz.correct_answer || '').trim().toLowerCase();

  const handleSelect = (opt: string) => {
    if (isAnswered) return;
    setSelectedOption(opt);
    setIsAnswered(true);
  };

  const isCorrect = selectedOption
    ? selectedOption.trim().toLowerCase() === cleanCorrect ||
      selectedOption.trim().toLowerCase().startsWith(cleanCorrect) ||
      cleanCorrect.startsWith(selectedOption.trim().toLowerCase())
    : false;

  return (
    <div className="mt-4 p-4 sm:p-5 rounded-2xl bg-gradient-to-br from-blue-50/80 via-indigo-50/30 to-white border border-blue-200 shadow-xs space-y-4">
      {/* Header Badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="p-1 rounded-md bg-blue-600 text-white shadow-2xs">
            <Zap className="h-3.5 w-3.5" />
          </span>
          <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-blue-900">
            Interactive Checkpoint Quiz
          </span>
        </div>
        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
          +25 Mastery XP
        </span>
      </div>

      {/* Question Text */}
      <div className="text-xs sm:text-sm font-semibold text-slate-900 leading-snug">
        {quiz.question_text}
      </div>

      {/* Options List */}
      <div className="space-y-2">
        {quiz.options && quiz.options.map((option, idx) => {
          const letter = String.fromCharCode(65 + idx);
          const isSelected = selectedOption === option;
          const isThisCorrect =
            option.trim().toLowerCase() === cleanCorrect ||
            option.trim().toLowerCase().startsWith(cleanCorrect) ||
            cleanCorrect.startsWith(option.trim().toLowerCase());

          let btnClass = "border-slate-200 bg-white text-slate-800 hover:border-blue-300 hover:bg-blue-50/40";
          let badgeClass = "bg-slate-100 text-slate-600";

          if (isAnswered) {
            if (isThisCorrect) {
              btnClass = "border-emerald-500 bg-emerald-50/90 text-emerald-950 font-medium shadow-xs";
              badgeClass = "bg-emerald-600 text-white";
            } else if (isSelected && !isThisCorrect) {
              btnClass = "border-rose-400 bg-rose-50/90 text-rose-950 font-medium";
              badgeClass = "bg-rose-500 text-white";
            } else {
              btnClass = "border-slate-200 bg-white/60 text-slate-400 opacity-60";
            }
          }

          return (
            <button
              key={idx}
              type="button"
              disabled={isAnswered}
              onClick={() => handleSelect(option)}
              className={`w-full p-3 rounded-xl border text-left text-xs sm:text-sm flex items-start gap-3 transition cursor-pointer ${btnClass}`}
            >
              <span className={`h-6 w-6 rounded-lg font-mono text-xs font-bold flex items-center justify-center shrink-0 transition-colors ${badgeClass}`}>
                {letter}
              </span>
              <span className="pt-0.5 leading-relaxed">{option}</span>
            </button>
          );
        })}
      </div>

      {/* Answer Feedback & Explanation */}
      {isAnswered && (
        <div className={`p-3.5 rounded-xl border space-y-2 text-xs transition-all ${
          isCorrect ? 'bg-emerald-50/90 border-emerald-200 text-emerald-900' : 'bg-amber-50/90 border-amber-200 text-amber-900'
        }`}>
          <div className="flex items-center gap-2 font-bold text-xs">
            {isCorrect ? (
              <>
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                <span>Excellent! Correct Answer</span>
              </>
            ) : (
              <>
                <XCircle className="h-4 w-4 text-rose-600" />
                <span>Incorrect Answer</span>
              </>
            )}
          </div>
          {quiz.explanation && (
            <div className="text-[11px] leading-relaxed pt-1.5 border-t border-slate-200/50">
              <span className="font-semibold block mb-0.5 text-slate-800">Explanation:</span>
              <p className="text-slate-700">{quiz.explanation}</p>
            </div>
          )}
          <div className="pt-2 flex items-center justify-end">
            <button
              type="button"
              onClick={() => onFollowupClick("Give me another practice question on this topic.")}
              className="text-[11px] font-medium text-blue-700 hover:text-blue-900 hover:underline cursor-pointer"
            >
              Ask another quiz question &rarr;
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  onSelectCitation,
  onFollowupClick,
  isProcessing,
}) => {
  return (
    <div className="space-y-5 p-4 sm:p-6">
      {messages.map((msg) => {
        const isUser = msg.role === 'user';
        const isRefused = msg.refusal === true || msg.refusal_category !== undefined;
        const isOutside = msg.is_outside_knowledge === true;

        if (isUser) {
          return (
            <div key={msg.id} className="flex justify-end items-start gap-2.5">
              <div className="max-w-xl bg-blue-600 text-white p-3.5 rounded-2xl rounded-tr-xs text-xs sm:text-sm leading-relaxed shadow-xs">
                {msg.content}
              </div>
              <div className="h-7 w-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center shrink-0 text-xs font-bold">
                <User className="h-4 w-4" />
              </div>
            </div>
          );
        }

        return (
          <div key={msg.id} className="flex justify-start items-start gap-3">
            <div className="h-8 w-8 rounded-full bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
              <Bot className="h-4 w-4" />
            </div>

            <div className="max-w-2xl w-full space-y-3 bg-white p-4 sm:p-5 rounded-2xl rounded-tl-xs border border-slate-200 shadow-xs">
              
              {/* Refusal notification */}
              {isRefused && (
                <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs space-y-1">
                  <div className="flex items-center gap-1.5 font-bold">
                    <AlertCircle className="h-3.5 w-3.5 text-amber-600 shrink-0" />
                    <span>Outside Active Course Scope</span>
                  </div>
                  <p className="text-[11px] text-amber-800">
                    This question falls outside the uploaded syllabus and lecture units.
                  </p>
                </div>
              )}

              {/* Outside knowledge badge */}
              {isOutside && !isRefused && (
                <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-[10px] font-mono font-bold">
                  <AlertCircle className="h-3 w-3 text-amber-600" />
                  <span>Outside Knowledge Supplement</span>
                </div>
              )}

              {/* Message Content */}
              <div className="text-xs sm:text-sm text-slate-800 leading-relaxed font-sans">
                <MarkdownRenderer content={msg.content} />
              </div>

              {/* Strands Decider 2B decision trace */}
              {msg.decision_trace && <DecisionTraceChip trace={msg.decision_trace} />}

              {/* Citations Chips */}
              {msg.citations && msg.citations.length > 0 && (
                <CitationChips 
                  citations={msg.citations} 
                  onSelectCitation={onSelectCitation} 
                />
              )}

              {/* Interactive MCQ Quiz Card if present */}
              {msg.interactive_quiz && (
                <InteractiveQuizCard 
                  quiz={msg.interactive_quiz}
                  onFollowupClick={onFollowupClick}
                />
              )}

              {/* Check yourself tiny quiz item */}
              {msg.check_yourself_question && !msg.interactive_quiz && (
                <div className="mt-3 p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-2">
                  <div className="font-bold text-slate-800 flex items-center gap-1.5">
                    <HelpCircle className="h-3.5 w-3.5 text-blue-600" />
                    <span>Check Yourself:</span>
                  </div>
                  <p className="text-slate-700">{msg.check_yourself_question}</p>
                </div>
              )}

              {/* Follow-up Quick Action Chips: Want more detail? */}
              <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-1.5">
                <span className="text-[10px] font-mono font-bold text-slate-400 uppercase mr-1">
                  Want more detail?
                </span>
                <button
                  type="button"
                  onClick={() => onFollowupClick("Can you give a concrete real-world example from the course notes?")}
                  className="px-2.5 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-medium transition cursor-pointer"
                >
                  Show example
                </button>
                <button
                  type="button"
                  onClick={() => onFollowupClick("Explain this more deeply step-by-step.")}
                  className="px-2.5 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-medium transition cursor-pointer"
                >
                  Go deeper
                </button>
                <button
                  type="button"
                  onClick={() => onFollowupClick("Quiz me on this concept with a quick diagnostic question.")}
                  className="px-2.5 py-1 rounded-full bg-blue-50 hover:bg-blue-100 text-blue-700 text-[11px] font-medium border border-blue-200 transition cursor-pointer"
                >
                  Quiz me
                </button>
              </div>

            </div>
          </div>
        );
      })}

      {isProcessing && (
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center shrink-0">
            <Bot className="h-4 w-4" />
          </div>
          <div className="p-3.5 rounded-2xl bg-white border border-slate-200 text-xs text-slate-500 flex items-center gap-2 shadow-xs">
            <div className="w-2 h-2 rounded-full bg-blue-600 animate-ping" />
            <span>Consulting course lecture notes and synthesizing verified answer...</span>
          </div>
        </div>
      )}
    </div>
  );
};
