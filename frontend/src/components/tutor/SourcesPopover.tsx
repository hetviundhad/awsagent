import React, { useState, useRef, useEffect } from 'react';
import { Filter, CheckSquare, Square, ChevronDown, BookOpen } from 'lucide-react';

export interface SourceDoc {
  id: string;
  name: string;
  size?: string;
  type?: string;
}

interface SourcesPopoverProps {
  documents: SourceDoc[];
  selectedDocIds: string[];
  onChangeSelectedDocIds: (ids: string[]) => void;
}

export const SourcesPopover: React.FC<SourcesPopoverProps> = ({
  documents,
  selectedDocIds,
  onChangeSelectedDocIds,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const isAllSelected = documents.length > 0 && selectedDocIds.length === documents.length;

  const handleToggleDoc = (docId: string) => {
    if (selectedDocIds.includes(docId)) {
      if (selectedDocIds.length === 1) return; // keep at least one
      onChangeSelectedDocIds(selectedDocIds.filter(id => id !== docId));
    } else {
      onChangeSelectedDocIds([...selectedDocIds, docId]);
    }
  };

  const handleToggleAll = () => {
    if (isAllSelected) {
      // Keep only first
      onChangeSelectedDocIds(documents.length > 0 ? [documents[0].id] : []);
    } else {
      onChangeSelectedDocIds(documents.map(d => d.id));
    }
  };

  const labelText = isAllSelected 
    ? 'All Sources' 
    : `${selectedDocIds.length} of ${documents.length} Sources`;

  return (
    <div className="relative inline-block" ref={containerRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 transition cursor-pointer shadow-xs"
      >
        <Filter className="h-3.5 w-3.5 text-blue-600" />
        <span>{labelText}</span>
        <ChevronDown className="h-3 w-3 text-slate-400" />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-1.5 z-40 w-72 bg-white rounded-2xl border border-slate-200 shadow-xl p-3 space-y-2 animate-in fade-in">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-100">
            <span className="text-xs font-bold text-slate-800">Filter Knowledge Retrieval</span>
            <button
              type="button"
              onClick={handleToggleAll}
              className="text-[11px] font-mono text-blue-600 hover:text-blue-800 font-bold cursor-pointer"
            >
              {isAllSelected ? 'Reset' : 'Select All'}
            </button>
          </div>

          <div className="max-h-48 overflow-y-auto divide-y divide-slate-100 text-xs">
            {documents.length === 0 ? (
              <div className="p-3 text-center text-slate-400 text-xs">
                No course documents uploaded yet.
              </div>
            ) : (
              documents.map(doc => {
                const checked = selectedDocIds.includes(doc.id);
                return (
                  <div
                    key={doc.id}
                    onClick={() => handleToggleDoc(doc.id)}
                    className="p-2 flex items-center justify-between hover:bg-slate-50 cursor-pointer rounded-lg transition"
                  >
                    <div className="flex items-center gap-2 min-w-0 pr-2">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {}}
                        className="rounded text-blue-600 focus:ring-blue-500 accent-blue-600 cursor-pointer"
                      />
                      <span className="truncate font-medium text-slate-700">{doc.name}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
          <div className="text-[10px] text-slate-400 pt-1 border-t border-slate-100">
            Tutor will strictly restrict grounding and citations to ticked sources.
          </div>
        </div>
      )}
    </div>
  );
};
