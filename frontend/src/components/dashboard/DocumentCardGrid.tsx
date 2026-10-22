import React from 'react';
import { FileText, Award, Bot, ExternalLink, Plus, BookOpen } from 'lucide-react';
import { DocumentItem } from '../QuizModal';

interface DocumentCardGridProps {
  documents: DocumentItem[];
  onOpenQuizModalWithDoc: (docId: string) => void;
  onAskTutorWithDoc: (docName: string) => void;
  onOpenDocumentViewer: (docId: string) => void;
  onUploadClick: () => void;
}

export const DocumentCardGrid: React.FC<DocumentCardGridProps> = ({
  documents,
  onOpenQuizModalWithDoc,
  onAskTutorWithDoc,
  onOpenDocumentViewer,
  onUploadClick,
}) => {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 block mb-0.5">
            Verified Source Content
          </span>
          <h2 className="text-base font-bold text-slate-900">
            Course Materials ({documents.length})
          </h2>
        </div>
        <button
          onClick={onUploadClick}
          className="text-xs font-bold text-blue-600 hover:text-blue-800 flex items-center gap-1 cursor-pointer"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>Add Material</span>
        </button>
      </div>

      {documents.length === 0 ? (
        <div className="p-8 rounded-3xl bg-white border border-slate-200 text-center space-y-3">
          <BookOpen className="h-8 w-8 text-slate-400 mx-auto" />
          <h3 className="text-sm font-bold text-slate-800">No course documents uploaded yet</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Upload course slides, syllabus, or lecture PDFs to unlock question generation and AI tutoring.
          </p>
          <button
            onClick={onUploadClick}
            className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition shadow-xs cursor-pointer"
          >
            Upload Lecture Notes
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {documents.map((doc) => {
            // Get each document's OWN concepts (fixed bug where every card had identical fake tags)
            const docConcepts = Array.isArray(doc.topics) && doc.topics.length > 0
              ? doc.topics.slice(0, 3)
              : ['Course Syllabus'];

            return (
              <div
                key={doc.id}
                className="bg-white rounded-3xl p-5 border border-slate-200 shadow-xs hover:border-blue-300 transition flex flex-col justify-between space-y-4 group"
              >
                <div className="space-y-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <button
                      onClick={() => onOpenDocumentViewer(doc.id)}
                      className="text-xs font-bold text-slate-900 group-hover:text-blue-600 transition truncate text-left cursor-pointer flex-1"
                      title={doc.name}
                    >
                      {doc.name}
                    </button>
                    <span className="text-[10px] font-mono text-slate-400 shrink-0 bg-slate-100 px-2 py-0.5 rounded">
                      {doc.size || 'Doc'}
                    </span>
                  </div>

                  {/* Document's own top concepts tags */}
                  <div className="flex flex-wrap gap-1">
                    {docConcepts.map((tag, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md truncate max-w-[150px]"
                        title={tag}
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Footer with chunk count and actions */}
                <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-semibold">
                    {doc.chunks_count ? `${doc.chunks_count} chunks` : 'Indexed'}
                  </span>

                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => onOpenDocumentViewer(doc.id)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition cursor-pointer"
                      title="Open in Document Viewer (Page 1)"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => onAskTutorWithDoc(doc.name)}
                      className="px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100 transition cursor-pointer"
                      title="Ask Tutor about this document"
                    >
                      Tutor
                    </button>
                    <button
                      onClick={() => onOpenQuizModalWithDoc(doc.id)}
                      className="px-3 py-1 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-bold transition cursor-pointer"
                      title="Generate Quiz on this document"
                    >
                      Quiz
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
