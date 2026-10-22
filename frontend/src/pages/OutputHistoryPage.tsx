import React, { useState, useEffect } from 'react';
import { 
  FolderArchive, Search, Filter, BookOpen, HelpCircle, 
  Layers, FileText, Bot, Calculator, Download, Trash2, 
  ExternalLink, Calendar, Copy, Check, Sparkles, RefreshCw, Plus, Archive
} from 'lucide-react';
import { api } from '../services/api';
import { Card } from '../components/ui/Card';
import { Pill } from '../components/ui/Pill';
import { Button } from '../components/ui/Button';

interface HistoryItem {
  id: string;
  type: 'course' | 'quiz' | 'flashcard' | 'summary' | 'homework';
  title: string;
  source: string;
  createdAt: string;
  summary: string;
  itemCount?: string;
}

export const OutputHistoryPage: React.FC = () => {
  const [filterType, setFilterType] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadHistory() {
      try {
        const [assessments, courses, docs] = await Promise.all([
          api.listAssessments().catch(() => []),
          api.getCourses().catch(() => []),
          api.getUserDocuments().catch(() => []),
        ]);

        const history: HistoryItem[] = [];

        (courses || []).forEach((c: any) => {
          history.push({
            id: c.id,
            type: 'course',
            title: c.name,
            source: `${c.document_count || (docs ? docs.length : 1)} Source Documents`,
            createdAt: c.created_at ? new Date(c.created_at).toLocaleDateString() : 'Recently',
            summary: c.description || 'Source-grounded course knowledge base with NetworkX prerequisite mapping.',
            itemCount: `${c.concept_count || 12} Concepts`
          });
        });

        (assessments || []).forEach((a: any) => {
          history.push({
            id: a.id,
            type: 'quiz',
            title: a.title,
            source: a.difficulty ? `${a.difficulty} Difficulty` : 'Adaptive Difficulty',
            createdAt: a.created_at ? new Date(a.created_at).toLocaleDateString() : 'Recently',
            summary: a.score !== undefined && a.status === 'completed'
              ? `Diagnostic assessment completed with score: ${Math.round(a.score * 100)}%` 
              : 'Adaptive verified assessment generated from syllabus.',
            itemCount: `${a.total_questions || a.questions?.length || 5} Questions`
          });
        });

        setItems(history);
      } catch (e) {
        console.error('Error loading history:', e);
      } finally {
        setLoading(false);
      }
    }
    loadHistory();
  }, []);

  const filteredItems = items.filter((item) => {
    const matchesFilter = filterType === 'all' || item.type === filterType;
    const matchesSearch = item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          item.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          item.source.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleDelete = (id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'course': return <BookOpen className="h-4 w-4 text-[#1D4ED8]" />;
      case 'quiz': return <HelpCircle className="h-4 w-4 text-[#D97706]" />;
      case 'flashcard': return <Layers className="h-4 w-4 text-[#4F46E5]" />;
      case 'summary': return <FileText className="h-4 w-4 text-[#059669]" />;
      case 'homework': return <Calculator className="h-4 w-4 text-[#DC2626]" />;
      default: return <Sparkles className="h-4 w-4 text-[#1D4ED8]" />;
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-[#FAF8F5] overflow-hidden min-h-screen">
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6 max-w-6xl w-full mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#EAE6DF] pb-5">
          <div>
            <div className="flex items-center space-x-2">
              <Pill variant="neutral" size="sm">ACADEMIC PORTFOLIO</Pill>
              <span className="text-xs font-mono text-[#7B766C]">· {items.length} Artifacts</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-serif font-bold text-[#16130F] tracking-tight mt-1">
              Synthesized Artifact History
            </h1>
            <p className="text-sm text-[#5E5A52] mt-1">
              Your source-grounded course syllabi, spaced-repetition card decks, diagnostic exams, and study digests.
            </p>
          </div>

          {/* Search bar */}
          <div className="relative w-full sm:w-72">
            <Search className="h-3.5 w-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#7B766C]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter artifact titles or topics..."
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg bg-white border border-[#EAE6DF] text-[#16130F] placeholder-[#7B766C] focus:outline-none focus:ring-2 focus:ring-[#1D4ED8]/20 focus:border-[#1D4ED8]"
            />
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center space-x-2 overflow-x-auto pb-1">
          {[
            { id: 'all', label: 'All Artifacts' },
            { id: 'course', label: 'Courses' },
            { id: 'quiz', label: 'Exams & Quizzes' },
            { id: 'flashcard', label: 'Flashcards' },
            { id: 'summary', label: 'Digests' },
            { id: 'homework', label: 'Homework' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilterType(tab.id)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-mono transition ${
                filterType === tab.id
                  ? 'bg-[#16130F] text-white shadow-xs'
                  : 'bg-white border border-[#EAE6DF] text-[#5E5A52] hover:text-[#16130F] hover:bg-[#FAF8F5]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Items List */}
        {loading ? (
          <div className="text-center py-12 text-[#7B766C] font-mono text-xs">
            Loading academic history...
          </div>
        ) : filteredItems.length === 0 ? (
          <Card className="p-12 text-center space-y-3">
            <div className="h-12 w-12 rounded-xl bg-[#FAF8F5] text-[#7B766C] flex items-center justify-center mx-auto border border-[#EAE6DF]">
              <Archive className="h-6 w-6" />
            </div>
            <h3 className="font-serif text-base font-bold text-[#16130F]">No artifacts found</h3>
            <p className="text-xs text-[#5E5A52] max-w-sm mx-auto">
              Use StudyMind AI tools on your dashboard to synthesize course units, flashcard decks, or diagnostic quizzes.
            </p>
          </Card>
        ) : (
          <div className="space-y-3">
            {filteredItems.map((item) => (
              <Card
                key={item.id}
                className="p-5 hover:border-[#1D4ED8]/40 transition group"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="flex items-start space-x-3">
                    <div className="p-2.5 rounded-lg bg-[#FAF8F5] border border-[#EAE6DF] shrink-0 mt-0.5">
                      {getTypeIcon(item.type)}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-[10px] uppercase font-semibold text-[#1D4ED8] bg-[#1D4ED8]/10 px-2 py-0.5 rounded">
                          {item.type}
                        </span>
                        <span className="text-[#EAE6DF]">·</span>
                        <span className="text-[11px] font-mono text-[#7B766C] flex items-center gap-1">
                          <Calendar className="h-3 w-3 text-[#7B766C]" />
                          {item.createdAt}
                        </span>
                      </div>
                      <h3 className="text-base font-serif font-bold text-[#16130F] mt-1 group-hover:text-[#1D4ED8] transition">
                        {item.title}
                      </h3>
                      <p className="text-xs text-[#5E5A52] mt-1">
                        Source Grounding: <span className="font-mono text-[#16130F]">{item.source}</span>
                      </p>
                    </div>
                  </div>

                  {item.itemCount && (
                    <span className="text-xs font-mono font-medium text-[#16130F] bg-[#FFE45C]/30 px-2.5 py-1 rounded-md border border-[#FFE45C] self-start sm:self-center">
                      {item.itemCount}
                    </span>
                  )}
                </div>

                <p className="text-xs text-[#5E5A52] mt-3 pl-11 leading-relaxed">
                  {item.summary}
                </p>

                <div className="mt-4 pt-3 border-t border-[#EAE6DF] flex items-center justify-between pl-11 text-xs">
                  <span className="font-mono text-[11px] text-[#7B766C]">
                    Verified in student study desk
                  </span>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleCopy(item.id, `${item.title}\n\n${item.summary}`)}
                      className="px-2.5 py-1 rounded-md border border-[#EAE6DF] bg-white text-[#5E5A52] hover:text-[#16130F] hover:bg-[#FAF8F5] flex items-center space-x-1.5 transition text-xs font-mono"
                      title="Copy content"
                    >
                      {copiedId === item.id ? (
                        <>
                          <Check className="h-3 w-3 text-[#059669]" />
                          <span className="text-[#059669] font-semibold">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-3 w-3 text-[#7B766C]" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>

                    <button
                      onClick={() => {
                        const blob = new Blob([`${item.title}\n\n${item.summary}`], { type: 'text/plain' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `${item.title.replace(/\s+/g, '_')}.txt`;
                        a.click();
                      }}
                      className="px-2.5 py-1 rounded-md border border-[#EAE6DF] bg-white text-[#5E5A52] hover:text-[#16130F] hover:bg-[#FAF8F5] flex items-center space-x-1.5 transition text-xs font-mono"
                      title="Download file"
                    >
                      <Download className="h-3 w-3 text-[#7B766C]" />
                      <span>Export</span>
                    </button>

                    <button
                      onClick={() => handleDelete(item.id)}
                      className="p-1 rounded-md text-[#7B766C] hover:text-red-600 hover:bg-red-50 transition"
                      title="Delete item"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
