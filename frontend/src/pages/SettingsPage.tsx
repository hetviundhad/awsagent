import React, { useState, useEffect } from 'react';
import { 
  Settings as SettingsIcon, Database, Key, Shield, RefreshCw, 
  CheckCircle2, AlertCircle, Bot, Zap, Cpu, Server, Sparkles, Terminal
} from 'lucide-react';
import { api } from '../services/api';
import { Card } from '../components/ui/Card';
import { Pill } from '../components/ui/Pill';
import { Button } from '../components/ui/Button';

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<any>(null);
  const [supabaseUrl, setSupabaseUrl] = useState('');
  const [supabaseKey, setSupabaseKey] = useState('');
  
  // AI Provider State
  const [llmProvider, setLlmProvider] = useState('mock');
  const [llmModel, setLlmModel] = useState('');
  const [geminiApiKey, setGeminiApiKey] = useState('');
  const [groqApiKey, setGroqApiKey] = useState('');
  const [openaiApiKey, setOpenaiApiKey] = useState('');
  const [customApiBase, setCustomApiBase] = useState('');
  const [customApiKey, setCustomApiKey] = useState('');
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');

  const [confidenceThreshold, setConfidenceThreshold] = useState(0.20);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [loading, setLoading] = useState(true);

  const [aiHealth, setAiHealth] = useState<any>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const [data, health] = await Promise.all([
        api.getSettings(),
        api.getAiHealth().catch((err) => ({
          llm_ok: false,
          model: 'unknown',
          embedding_ok: false,
          vision_ok: false,
          stt_ok: false,
          error: String(err?.message || err),
        })),
      ]);
      setSettings(data);
      setAiHealth(health);
      setSupabaseUrl(data.supabase_url || '');
      setLlmProvider(data.llm_provider || 'mock');
      setLlmModel(data.llm_model || '');
      setCustomApiBase(data.custom_api_base || '');
      setOllamaUrl(data.ollama_url || 'http://localhost:11434');
      setConfidenceThreshold(data.confidence_threshold || 0.20);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage('');
    try {
      const res = await api.updateSettings({
        supabase_url: supabaseUrl,
        supabase_key: supabaseKey,
        llm_provider: llmProvider,
        llm_model: llmModel,
        gemini_api_key: geminiApiKey,
        groq_api_key: groqApiKey,
        openai_api_key: openaiApiKey,
        custom_api_base: customApiBase,
        custom_api_key: customApiKey,
        ollama_url: ollamaUrl,
        confidence_threshold: confidenceThreshold,
      });
      setMessage(`Settings saved! Active Engine: ${res.active_provider.toUpperCase()}`);
      loadSettings();
    } catch (err) {
      setMessage('Failed to update settings');
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const payload: any = {
        llm_provider: llmProvider,
        llm_model: llmModel,
      };
      if (llmProvider === 'gemini') payload.api_key = geminiApiKey;
      if (llmProvider === 'groq') payload.api_key = groqApiKey;
      if (llmProvider === 'openai') payload.api_key = openaiApiKey;
      if (llmProvider === 'custom') {
        payload.api_key = customApiKey;
        payload.base_url = customApiBase;
      }
      if (llmProvider === 'ollama') payload.base_url = `${ollamaUrl.replace(/\/$/, '')}/v1`;

      const res = await api.testLlm(payload);
      if (res.status === 'success') {
        setTestResult(`✅ Connected successfully to ${llmProvider.toUpperCase()}! Sample response: "${res.response}"`);
      } else {
        setTestResult(`❌ Connection error: ${res.error}`);
      }
    } catch (e: any) {
      setTestResult(`❌ Test failed: ${e.message}`);
    } finally {
      setTesting(false);
    }
  };

  const handleLoadSampleCourse = async () => {
    try {
      await api.loadSampleCourse();
      alert('Sample course loaded successfully from fixtures (Sample data)!');
    } catch (e) {
      alert('Failed to load sample course');
    }
  };

  if (loading) {
    return (
      <div className="flex-1 p-8 text-[#7B766C] font-mono text-xs bg-[#FAF8F5] min-h-screen">
        Reading system parameters...
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 lg:p-8 space-y-6 overflow-y-auto max-w-4xl mx-auto bg-[#FAF8F5] min-h-screen">
      {/* Header */}
      <div className="border-b border-[#EAE6DF] pb-5">
        <div className="flex items-center space-x-2">
          <Pill variant="neutral" size="sm">SYSTEM ARCHITECTURE</Pill>
          <span className="text-xs font-mono text-[#7B766C]">· Grounding Parameters & API Gateway</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-serif font-bold text-[#16130F] tracking-tight mt-1">
          System Settings & AI Configuration
        </h1>
        <p className="text-sm text-[#5E5A52] mt-1">
          Connect multimodal LLM providers (Gemini, Groq, OpenAI, Ollama, OpenRouter, or Mock Engine), configure vector persistence, and adjust the syllabus retrieval confidence threshold.
        </p>
      </div>

      {message && (
        <div className="p-4 rounded-xl bg-[#059669]/10 border border-[#059669]/20 text-[#059669] text-xs flex items-center space-x-2 font-mono">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-[#059669]" />
          <span>{message}</span>
        </div>
      )}

      {testResult && (
        <div className={`p-4 rounded-xl text-xs flex items-center space-x-2 font-mono ${
          testResult.startsWith('✅')
            ? 'bg-[#059669]/10 border border-[#059669]/20 text-[#059669]'
            : 'bg-red-50 border border-red-200 text-red-700'
        }`}>
          <span>{testResult}</span>
        </div>
      )}

      {/* AI System Health Live Diagnostic Card */}
      {aiHealth && (
        <Card className="p-5 border border-[#EAE6DF] space-y-4">
          <div className="flex items-center justify-between border-b border-[#EAE6DF] pb-3">
            <div className="flex items-center space-x-2.5">
              <Sparkles className="h-4 w-4 text-[#1D4ED8]" />
              <h3 className="font-serif text-sm font-bold text-[#16130F]">
                AI Infrastructure Live Health (/api/health/ai)
              </h3>
            </div>
            <button
              type="button"
              onClick={() => api.getAiHealth().then(setAiHealth)}
              className="text-xs font-mono text-[#1D4ED8] hover:underline cursor-pointer flex items-center gap-1"
            >
              <RefreshCw className="h-3 w-3" /> Refresh Check
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
            <div className={`p-3 rounded-xl border ${aiHealth.llm_ok ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-red-50 border-red-200 text-red-900'}`}>
              <div className="text-[10px] uppercase font-bold text-slate-500">LLM Provider</div>
              <div className="font-bold mt-0.5">{aiHealth.llm_ok ? '✅ Operational' : '❌ Failed'}</div>
              <div className="text-[10px] text-slate-600 truncate mt-1">Model: {aiHealth.model}</div>
            </div>

            <div className={`p-3 rounded-xl border ${aiHealth.embedding_ok ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-red-50 border-red-200 text-red-900'}`}>
              <div className="text-[10px] uppercase font-bold text-slate-500">Embeddings</div>
              <div className="font-bold mt-0.5">{aiHealth.embedding_ok ? '✅ Operational' : '❌ Failed'}</div>
              <div className="text-[10px] text-slate-600 mt-1">384-dim dense</div>
            </div>

            <div className={`p-3 rounded-xl border ${aiHealth.vision_ok ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-amber-50 border-amber-200 text-amber-900'}`}>
              <div className="text-[10px] uppercase font-bold text-slate-500">Vision OCR</div>
              <div className="font-bold mt-0.5">{aiHealth.vision_ok ? '✅ Operational' : '⚠️ Disabled'}</div>
              <div className="text-[10px] text-slate-600 truncate mt-1" title={aiHealth.vision_reason || 'Slide diagrams'}>
                {aiHealth.vision_reason || (aiHealth.vision_ok ? 'Slide diagrams' : 'VISION_MODEL not set')}
              </div>
            </div>

            <div className={`p-3 rounded-xl border ${aiHealth.stt_ok ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-red-50 border-red-200 text-red-900'}`}>
              <div className="text-[10px] uppercase font-bold text-slate-500">Whisper STT</div>
              <div className="font-bold mt-0.5">{aiHealth.stt_ok ? '✅ Operational' : '❌ Failed'}</div>
              <div className="text-[10px] text-slate-600 mt-1">Video audio</div>
            </div>
          </div>

          {aiHealth.error && (
            <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs font-mono">
              <strong>Error Notice:</strong> {aiHealth.error}
            </div>
          )}
        </Card>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Universal AI Provider Card */}
        <Card className="p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-[#EAE6DF] pb-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg bg-[#FAF8F5] border border-[#EAE6DF] text-[#1D4ED8]">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-serif text-base font-bold text-[#16130F]">
                  Universal AI Provider & Inference Engine
                </h3>
                <p className="text-xs text-[#5E5A52]">Select cloud LLM gateway or local Ollama runtime</p>
              </div>
            </div>

            <span className="text-xs font-mono font-medium px-2.5 py-1 rounded-md bg-[#FFE45C]/30 text-[#16130F] border border-[#FFE45C]">
              Active: {llmProvider.toUpperCase()}
            </span>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-mono uppercase text-[#7B766C] mb-1.5">
                Target AI Engine:
              </label>
              <select
                value={llmProvider}
                onChange={(e) => {
                  setLlmProvider(e.target.value);
                  if (e.target.value === 'groq' && !llmModel) setLlmModel('llama-3.3-70b-versatile');
                  if (e.target.value === 'gemini' && !llmModel) setLlmModel('gemini-1.5-flash');
                  if (e.target.value === 'openai' && !llmModel) setLlmModel('gpt-4o-mini');
                  if (e.target.value === 'ollama' && !llmModel) setLlmModel('llama3');
                }}
                className="w-full px-3 py-2 text-xs rounded-lg bg-[#FAF8F5] border border-[#EAE6DF] text-[#16130F] font-mono focus:outline-none focus:border-[#1D4ED8]"
              >
                <option value="mock">Smart Offline Mock (Built-in Academic Knowledge Engine)</option>
                <option value="gemini">Google Gemini (Gemini 1.5 Flash, 2.0 Flash, 1.5 Pro)</option>
                <option value="groq">Groq LPU (Ultra-Fast Llama 3.3 70B, Mixtral 8x7B)</option>
                <option value="openai">OpenAI (GPT-4o, GPT-4o-mini, o1)</option>
                <option value="ollama">Ollama (Local LLM via http://localhost:11434)</option>
                <option value="custom">Custom OpenAI-Compatible (OpenRouter, DeepSeek, Together, LM Studio)</option>
              </select>
            </div>

            {/* Provider specific inputs */}
            {llmProvider === 'gemini' && (
              <div className="space-y-3 p-4 rounded-xl bg-[#FAF8F5] border border-[#EAE6DF]">
                <div>
                  <label className="block text-xs font-mono uppercase text-[#7B766C] mb-1">Gemini API Key:</label>
                  <input
                    type="password"
                    placeholder="AIzaSy..."
                    value={geminiApiKey}
                    onChange={(e) => setGeminiApiKey(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-white border border-[#EAE6DF] text-[#16130F] font-mono focus:border-[#1D4ED8] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono uppercase text-[#7B766C] mb-1">Model Name:</label>
                  <input
                    type="text"
                    placeholder="gemini-1.5-flash"
                    value={llmModel || 'gemini-1.5-flash'}
                    onChange={(e) => setLlmModel(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-white border border-[#EAE6DF] text-[#16130F] font-mono focus:outline-none"
                  />
                </div>
              </div>
            )}

            {llmProvider === 'groq' && (
              <div className="space-y-3 p-4 rounded-xl bg-[#FAF8F5] border border-[#EAE6DF]">
                <div>
                  <label className="block text-xs font-mono uppercase text-[#7B766C] mb-1">Groq API Key:</label>
                  <input
                    type="password"
                    placeholder="gsk_..."
                    value={groqApiKey}
                    onChange={(e) => setGroqApiKey(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-white border border-[#EAE6DF] text-[#16130F] font-mono focus:border-[#1D4ED8] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono uppercase text-[#7B766C] mb-1">Groq Model Identifier:</label>
                  <input
                    type="text"
                    placeholder="llama-3.3-70b-versatile"
                    value={llmModel || 'llama-3.3-70b-versatile'}
                    onChange={(e) => setLlmModel(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-white border border-[#EAE6DF] text-[#16130F] font-mono focus:outline-none"
                  />
                </div>
              </div>
            )}

            {llmProvider === 'openai' && (
              <div className="space-y-3 p-4 rounded-xl bg-[#FAF8F5] border border-[#EAE6DF]">
                <div>
                  <label className="block text-xs font-mono uppercase text-[#7B766C] mb-1">OpenAI API Key:</label>
                  <input
                    type="password"
                    placeholder="sk-proj-..."
                    value={openaiApiKey}
                    onChange={(e) => setOpenaiApiKey(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-white border border-[#EAE6DF] text-[#16130F] font-mono focus:border-[#1D4ED8] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono uppercase text-[#7B766C] mb-1">Model Name:</label>
                  <input
                    type="text"
                    placeholder="gpt-4o-mini"
                    value={llmModel || 'gpt-4o-mini'}
                    onChange={(e) => setLlmModel(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-white border border-[#EAE6DF] text-[#16130F] font-mono focus:outline-none"
                  />
                </div>
              </div>
            )}

            {llmProvider === 'ollama' && (
              <div className="space-y-3 p-4 rounded-xl bg-[#FAF8F5] border border-[#EAE6DF]">
                <div>
                  <label className="block text-xs font-mono uppercase text-[#7B766C] mb-1">Ollama Base URL:</label>
                  <input
                    type="text"
                    placeholder="http://localhost:11434"
                    value={ollamaUrl}
                    onChange={(e) => setOllamaUrl(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-white border border-[#EAE6DF] text-[#16130F] font-mono focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono uppercase text-[#7B766C] mb-1">Local Tag / Model:</label>
                  <input
                    type="text"
                    placeholder="llama3"
                    value={llmModel || 'llama3'}
                    onChange={(e) => setLlmModel(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-white border border-[#EAE6DF] text-[#16130F] font-mono focus:outline-none"
                  />
                </div>
              </div>
            )}

            {llmProvider === 'custom' && (
              <div className="space-y-3 p-4 rounded-xl bg-[#FAF8F5] border border-[#EAE6DF]">
                <div>
                  <label className="block text-xs font-mono uppercase text-[#7B766C] mb-1">API Base URL:</label>
                  <input
                    type="text"
                    placeholder="https://openrouter.ai/api/v1"
                    value={customApiBase}
                    onChange={(e) => setCustomApiBase(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-white border border-[#EAE6DF] text-[#16130F] font-mono focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono uppercase text-[#7B766C] mb-1">API Key:</label>
                  <input
                    type="password"
                    placeholder="sk-or-..."
                    value={customApiKey}
                    onChange={(e) => setCustomApiKey(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-white border border-[#EAE6DF] text-[#16130F] font-mono focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-mono uppercase text-[#7B766C] mb-1">Model Name:</label>
                  <input
                    type="text"
                    placeholder="meta-llama/llama-3.3-70b-instruct"
                    value={llmModel}
                    onChange={(e) => setLlmModel(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg bg-white border border-[#EAE6DF] text-[#16130F] font-mono focus:outline-none"
                  />
                </div>
              </div>
            )}

            <div className="pt-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={handleTestConnection}
                disabled={testing}
                className="flex items-center space-x-1.5"
              >
                <Zap className="h-4 w-4 text-[#1D4ED8]" />
                <span>{testing ? 'Probing Gateway...' : 'Test AI Connection'}</span>
              </Button>
            </div>
          </div>
        </Card>

        {/* Database & RAG Parameters Card */}
        <Card className="p-6 space-y-6">
          <div className="flex items-center space-x-3 border-b border-[#EAE6DF] pb-4">
            <div className="p-2 rounded-lg bg-[#FAF8F5] border border-[#EAE6DF] text-[#059669]">
              <Database className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-serif text-base font-bold text-[#16130F]">
                Vector Indexing & Hybrid Retrieval Parameters
              </h3>
              <p className="text-xs text-[#5E5A52]">Supabase pgvector persistence and grounding guardrails</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-mono uppercase text-[#7B766C] mb-1">
                Supabase Project URL:
              </label>
              <input
                type="text"
                placeholder="https://your-project.supabase.co"
                value={supabaseUrl}
                onChange={(e) => setSupabaseUrl(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg bg-[#FAF8F5] border border-[#EAE6DF] text-[#16130F] focus:outline-none focus:border-[#1D4ED8] font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-mono uppercase text-[#7B766C] mb-1">
                Supabase Anon / Service Role Key:
              </label>
              <input
                type="password"
                placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                value={supabaseKey}
                onChange={(e) => setSupabaseKey(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg bg-[#FAF8F5] border border-[#EAE6DF] text-[#16130F] focus:outline-none focus:border-[#1D4ED8] font-mono"
              />
            </div>

            <div className="p-4 rounded-xl bg-[#FAF8F5] border border-[#EAE6DF] space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="font-serif font-bold text-[#16130F]">
                  Unsupported Refusal Threshold (τ):
                </span>
                <span className="font-mono text-[#1D4ED8] font-bold">
                  {(confidenceThreshold).toFixed(2)} ({Math.round(confidenceThreshold * 100)}%)
                </span>
              </div>
              <input
                type="range"
                min={0.10}
                max={0.70}
                step={0.05}
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                className="w-full accent-[#1D4ED8] cursor-pointer"
              />
              <p className="text-[11px] text-[#5E5A52]">
                Queries whose fused retrieval score falls below τ = {(confidenceThreshold).toFixed(2)} are gracefully refused with a designed syllabus boundary notice to prevent hallucinations.
              </p>
            </div>

            {/* Hybrid Retrieval & Self-RAG Settings */}
            <div className="pt-2 border-t border-[#EAE6DF] space-y-3">
              <div>
                <label className="block text-xs font-mono uppercase text-[#7B766C] mb-1">
                  Hybrid Fusion Strategy:
                </label>
                <select
                  defaultValue="rrf"
                  className="w-full px-3 py-2 text-xs rounded-lg bg-[#FAF8F5] border border-[#EAE6DF] text-[#16130F] font-mono focus:outline-none focus:border-[#1D4ED8]"
                >
                  <option value="rrf">Reciprocal Rank Fusion (RRF: Dense 384-dim + BM25 Okapi, k=60) [Default]</option>
                  <option value="linear">Linear Weighted Hybrid (70% Semantic Dense + 30% BM25)</option>
                  <option value="dense_only">Dense Vector Cosine Similarity Only</option>
                  <option value="bm25_only">Lexical BM25 (rank_bm25) Only</option>
                </select>
                <p className="text-[11px] text-[#5E5A52] mt-1">
                  Reciprocal Rank Fusion fuses sparse keyword precision with dense semantic embeddings.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-[#FAF8F5] border border-[#EAE6DF] flex items-center justify-between text-xs">
                <div>
                  <div className="font-serif font-bold text-[#16130F] flex items-center space-x-1.5">
                    <Shield className="h-4 w-4 text-[#059669]" />
                    <span>Self-RAG Claim Verification Guardrail</span>
                  </div>
                  <div className="text-[11px] text-[#5E5A52] mt-0.5">
                    Splits responses into atomic claims and verifies grounding against retrieved source chunks.
                  </div>
                </div>
                <Pill variant="verified" size="sm">ACTIVE</Pill>
              </div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row justify-between items-center gap-3 pt-4 border-t border-[#EAE6DF]">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleLoadSampleCourse}
              className="flex items-center space-x-1.5 w-full sm:w-auto"
            >
              <RefreshCw className="h-4 w-4 text-[#7B766C]" />
              <span>Load Sample Course (Sample data)</span>
            </Button>

            <Button
              type="submit"
              variant="primary"
              size="md"
              disabled={saving}
              className="w-full sm:w-auto"
            >
              {saving ? 'Writing Configurations...' : 'Save All Settings'}
            </Button>
          </div>
        </Card>
      </form>
    </div>
  );
};
