import React, { useState, useRef, useEffect } from 'react';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import { 
  Bot, Sparkles, BookOpen, Layers, AlertCircle, HelpCircle, ArrowLeft
} from 'lucide-react';
import { api } from '../services/api';
import { ChatMessage, Citation, Course } from '../types';
import { SourceViewerModal } from '../components/SourceViewerModal';
import { SourcesPopover, SourceDoc } from '../components/tutor/SourcesPopover';
import { PrerequisitePanel, PrereqConcept } from '../components/tutor/PrerequisitePanel';
import { Composer } from '../components/tutor/Composer';
import { MessageList } from '../components/tutor/MessageList';
import { TeachBackModal } from '../components/TeachBackModal';

interface TutorPageProps {
  courses: Course[];
  activeCourseId: string;
  studentId?: string;
  studentName?: string;
}

export const TutorPage: React.FC<TutorPageProps> = ({ 
  courses, 
  activeCourseId, 
  studentId = 'default_student', 
  studentName = 'Student' 
}) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const conceptParam = searchParams.get('concept');
  const promptParam = searchParams.get('prompt') || (location.state as any)?.initialPrompt;

  const selectedCourseId = activeCourseId || localStorage.getItem('studymind_active_course') || (courses[0]?.id || '');
  const currentCourse = courses.find(c => c.id === selectedCourseId) || courses[0];
  const courseName = currentCourse?.name || 'Academic Course';

  // State
  const [documents, setDocuments] = useState<SourceDoc[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [prereqConcepts, setPrereqConcepts] = useState<PrereqConcept[]>([]);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [isTeachBackOpen, setIsTeachBackOpen] = useState(false);


  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load course documents and concepts on mount or when active course changes
  useEffect(() => {
    if (!selectedCourseId) return;

    // Fetch documents
    api.getUserDocuments(selectedCourseId)
      .then((docs) => {
        const formatted: SourceDoc[] = docs.map((d: any) => ({
          id: d.id,
          name: d.name,
          size: d.size,
          type: d.type
        }));
        setDocuments(formatted);
        setSelectedDocIds(formatted.map(d => d.id));
      })
      .catch(() => {});

    // Fetch suggested questions generated dynamically from real concepts
    api.getSuggestedQuestions(selectedCourseId)
      .then((qs) => {
        if (qs && qs.length > 0) {
          setSuggestedQuestions(qs);
        } else if ((currentCourse as any)?.concepts && (currentCourse as any).concepts.length > 0) {
          setSuggestedQuestions(
            (currentCourse as any).concepts.slice(0, 4).map((c: any) => `Explain ${c.name || c} with an example from the material`)
          );
        }
      })
      .catch(() => {});

    // Fetch concepts for prerequisites panel
    api.getConcepts(selectedCourseId)
      .then((concepts) => {
        setPrereqConcepts(concepts.map((c: any) => ({
          id: c.id,
          name: c.name,
          mastery_probability: c.mastery_probability,
          prerequisites: c.prerequisites
        })));
      })
      .catch(() => {});
  }, [selectedCourseId]);

  const autoTriggeredRef = useRef(false);

  // Handle concept or prompt query param from Upload, Concept Map, or Dashboard
  useEffect(() => {
    if (autoTriggeredRef.current || isProcessing) return;
    if (promptParam) {
      autoTriggeredRef.current = true;
      handleSendMessage(promptParam, 'Simple', 'English');
    } else if (conceptParam) {
      autoTriggeredRef.current = true;
      handleSendMessage(`Explain the concept of ${conceptParam}`, 'Simple', 'English');
    }
  }, [conceptParam, promptParam, isProcessing]);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing]);

  // Send message handler
  const handleSendMessage = async (query: string, style: string, language: string) => {
    if (!query.trim() || isProcessing) return;

    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMsg]);
    setIsProcessing(true);

    try {
      const res = await api.queryTutor({
        course_id: selectedCourseId,
        query: query,
        style: style,
        mode: style,
        language: language,
        document_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
        allow_outside_knowledge: true
      });

      const assistantMsg: ChatMessage = {
        id: `ast_${Date.now()}`,
        role: 'assistant',
        content: res.answer || 'No answer generated.',
        citations: res.citations || [],
        is_outside_knowledge: res.is_outside_knowledge,
        refusal: res.refusal,
        refusal_category: res.refusal_category,
        check_yourself_question: res.check_yourself_question,
        interactive_quiz: res.interactive_quiz,
        decision_trace: res.decision_trace,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err_${Date.now()}`,
        role: 'assistant',
        content: `Error consulting study material: ${err.message || 'Server timeout'}. Please verify connection.`,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsProcessing(false);
    }
  };

  const docCount = documents.length;
  const conceptCount = prereqConcepts.length;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#FAF8F5] text-slate-800">
      
      {/* Header Bar */}
      <header className="h-14 border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between shrink-0 bg-white">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={() => navigate('/dashboard')}
            className="text-slate-400 hover:text-slate-700 transition"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div className="min-w-0">
            <h1 className="text-sm font-bold text-slate-900 truncate">
              {courseName}
            </h1>
            <div className="text-[11px] font-mono text-slate-500">
              {docCount} document{docCount !== 1 ? 's' : ''} • {conceptCount} concept{conceptCount !== 1 ? 's' : ''}
            </div>
          </div>
        </div>

        {/* Action Controls & Sources */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsTeachBackOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 text-xs font-semibold shadow-xs transition"
            title="Teach-Back Mode: Articulate concepts in your own words to verify your mental model against course documents"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span className="hidden sm:inline">Teach it back</span>
          </button>

          <SourcesPopover
            documents={documents}
            selectedDocIds={selectedDocIds}
            onChangeSelectedDocIds={setSelectedDocIds}
          />
        </div>
      </header>


      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Chat Scroll Column */}
        <div className="flex-1 flex flex-col h-full overflow-hidden">
          <div className="flex-1 overflow-y-auto">
            {messages.length === 0 ? (
              /* Empty / Welcome State Generated from Real Concepts */
              <div className="max-w-2xl mx-auto p-6 sm:p-10 space-y-6 text-center">
                <div className="h-12 w-12 rounded-2xl bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center mx-auto shadow-xs">
                  <Bot className="h-6 w-6" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-900">
                    Ask anything about {courseName}
                  </h2>
                  <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                    All answers are strictly synthesized and cited from your course notes, slides, and syllabus.
                  </p>
                </div>

                {/* Suggested Questions */}
                {suggestedQuestions.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400 block">
                      Suggested Questions
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                      {suggestedQuestions.slice(0, 4).map((q, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => handleSendMessage(q, 'Simple', 'English')}
                          className="p-3 rounded-xl border border-slate-200 bg-white hover:bg-blue-50/50 hover:border-blue-300 text-xs text-slate-700 transition cursor-pointer text-left shadow-xs"
                        >
                          <span className="font-medium">{q}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <MessageList
                messages={messages}
                onSelectCitation={setSelectedCitation}
                onFollowupClick={(prompt) => handleSendMessage(prompt, 'Simple', 'English')}
                isProcessing={isProcessing}
              />
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Composer with 2 controls */}
          <Composer
            onSendMessage={handleSendMessage}
            isProcessing={isProcessing}
            activeCourseName={courseName}
          />
        </div>

        {/* Right Collapsible Prerequisite Panel */}
        {prereqConcepts.length > 0 && (
          <aside className="hidden lg:block w-72 border-l border-slate-200 bg-white p-4 overflow-y-auto">
            <PrerequisitePanel
              concepts={prereqConcepts}
              onSelectConcept={(name) => handleSendMessage(`Explain prerequisite concept: ${name}`, 'Simple', 'English')}
            />
          </aside>
        )}

      </div>

      {/* Source Viewer Modal */}
      {selectedCitation && (
        <SourceViewerModal
          citation={selectedCitation}
          onClose={() => setSelectedCitation(null)}
        />
      )}

      {/* Teach-Back Mode Modal */}
      <TeachBackModal
        isOpen={isTeachBackOpen}
        onClose={() => setIsTeachBackOpen(false)}
        courseId={selectedCourseId}
        conceptId={conceptParam || prereqConcepts[0]?.name || 'con_2ae7295a'}
        conceptName={prereqConcepts[0]?.name || 'Data Locality Preservation'}
      />
    </div>
  );
};

