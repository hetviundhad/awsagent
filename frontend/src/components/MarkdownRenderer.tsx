import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '' }) => {
  return (
    <div className={`markdown-content space-y-3 leading-relaxed ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-lg sm:text-xl font-bold text-slate-900 border-b border-slate-200 pb-1.5 mt-3 mb-2">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mt-3 mb-1.5 flex items-center space-x-1.5">
              <span>{children}</span>
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm sm:text-base font-semibold text-emerald-900 mt-2.5 mb-1">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-xs sm:text-sm font-semibold text-slate-800 mt-2 mb-1">
              {children}
            </h4>
          ),
          p: ({ children }) => (
            <p className="text-xs sm:text-sm text-slate-800 my-1.5 leading-relaxed">
              {children}
            </p>
          ),
          ul: ({ children }) => (
            <ul className="list-disc pl-5 my-2 space-y-1 text-xs sm:text-sm text-slate-800">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal pl-5 my-2 space-y-1 text-xs sm:text-sm text-slate-800">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="leading-relaxed pl-0.5">
              {children}
            </li>
          ),
          strong: ({ children }) => (
            <strong className="font-bold text-slate-900">
              {children}
            </strong>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-emerald-500 bg-emerald-50/50 pl-3 py-1.5 my-2 rounded-r-lg text-slate-700 italic text-xs sm:text-sm">
              {children}
            </blockquote>
          ),
          code: ({ inline, className, children, ...props }: any) => {
            // react-markdown v10 doesn't supply inline prop; detect via language class or newline
            const match = /language-(\w+)/.exec(className || '');
            const contentStr = Array.isArray(children) ? children.join('') : String(children || '');
            const isBlock = Boolean(match) || contentStr.includes('\n');
            if (!isBlock) {
              return (
                <code
                  className="px-1.5 py-0.5 mx-0.5 rounded-md bg-stone-100 border border-stone-200 text-emerald-800 font-mono text-[11px] sm:text-xs font-medium"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            const language = match ? match[1].toUpperCase() : 'CODE';
            return (
              <div className="relative my-2.5 rounded-xl bg-slate-900 border border-slate-800 overflow-hidden text-slate-100 shadow-xs">
                <div className="px-3.5 py-1.5 bg-slate-800/80 text-[11px] text-slate-400 font-mono flex items-center justify-between border-b border-slate-700/50">
                  <span className="font-semibold text-slate-300 tracking-wide">{language}</span>
                  <button
                    onClick={() => {
                      if (typeof navigator !== 'undefined' && navigator.clipboard) {
                        navigator.clipboard.writeText(String(children).replace(/\n$/, ''));
                      }
                    }}
                    type="button"
                    className="text-[11px] hover:text-white transition px-2 py-0.5 rounded bg-slate-700/60 hover:bg-slate-700 flex items-center space-x-1"
                    title="Copy code to clipboard"
                  >
                    <span>Copy</span>
                  </button>
                </div>
                <pre className="p-3.5 text-xs sm:text-sm font-mono overflow-x-auto leading-relaxed text-emerald-300">
                  <code {...props}>{children}</code>
                </pre>
              </div>
            );
          },
          table: ({ children }) => (
            <div className="overflow-x-auto my-3 rounded-xl border border-slate-200 shadow-2xs">
              <table className="w-full text-left text-xs border-collapse">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-slate-100 border-b border-slate-200 text-slate-900 font-bold">
              {children}
            </thead>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2 border-r border-slate-200 last:border-r-0">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-1.5 border-b border-r border-slate-200 last:border-r-0 text-slate-700">
              {children}
            </td>
          ),
          hr: () => <hr className="my-3 border-t border-slate-200" />
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
