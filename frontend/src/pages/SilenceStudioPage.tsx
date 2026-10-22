import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Volume2,
  VolumeX,
  Sparkles,
  BookOpen,
  Sliders,
  Type,
  HelpCircle,
  RotateCcw,
  History,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileCode,
} from 'lucide-react';
import { api } from '../services/api';
import {
  SilenceAtlas,
  SilenceDecision,
  SilenceReplaySession,
  SilenceReplayTick,
  SilenceSessionStats,
  SilenceSpokenMessage,
} from '../types';
import { SilenceMeter } from '../components/silence/SilenceMeter';
import { HeartbeatStrip } from '../components/silence/HeartbeatStrip';
import { GhostMargin } from '../components/silence/GhostMargin';
import { TimeMachineScrubber } from '../components/silence/TimeMachineScrubber';

interface Props {
  activeCourseId?: string;
}

const PRESET_PROBLEMS = [
  {
    title: 'Dynamic Programming: Longest Common Subsequence',
    problem:
      'Given two strings text1 and text2, return the length of their longest common subsequence. Formulate the recurrence relation and identify the base cases.',
    starter:
      '# Problem: LCS(text1, text2)\n# Let DP[i][j] represent the length of LCS for text1[0..i] and text2[0..j]\n\n',
  },
  {
    title: 'Binary Search: Rotated Sorted Array',
    problem:
      'Given an integer array nums sorted in ascending order (with distinct values) and rotated at an unknown pivot index, search for target in O(log n) time.',
    starter:
      'def search(nums, target):\n    left, right = 0, len(nums) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if nums[mid] == target:\n            return mid\n',
  },
  {
    title: 'Graph Theory: Dijkstra Shortest Path Proof',
    problem:
      'Why does Dijkstra\'s algorithm fail on graphs with negative edge weights? Write down the invariant and explain the step where the greedy choice breaks.',
    starter:
      'Invariant: When a node u is extracted from the priority queue, dist[u] is optimal.\nIf an edge (u, v) has negative weight w < 0:\n',
  },
];

export const SilenceStudioPage: React.FC<Props> = ({ activeCourseId }) => {
  // Session State
  const [sessionId, setSessionId] = useState<string>('');
  const [problemText, setProblemText] = useState<string>(PRESET_PROBLEMS[0].problem);
  const [scratchpad, setScratchpad] = useState<string>(PRESET_PROBLEMS[0].starter);
  const [atlas, setAtlas] = useState<SilenceAtlas | null>(null);
  const [showAtlas, setShowAtlas] = useState<boolean>(false);

  // Live Signals & Decisions
  const [lastDecision, setLastDecision] = useState<SilenceDecision | null>(null);
  const [spokenMessage, setSpokenMessage] = useState<SilenceSpokenMessage | null>(null);
  const [stats, setStats] = useState<SilenceSessionStats | null>(null);
  const [ticksHistory, setTicksHistory] = useState<SilenceReplayTick[]>([]);
  const [feedbackGiven, setFeedbackGiven] = useState<boolean>(false);

  // UI Settings
  const [fontMode, setFontMode] = useState<'mono' | 'serif'>('mono');
  const [patience, setPatience] = useState<number>(0.5);
  const [isTyping, setIsTyping] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'studio' | 'timemachine'>('studio');
  const [replaySession, setReplaySession] = useState<SilenceReplaySession | null>(null);
  const [selectedTick, setSelectedTick] = useState<SilenceReplayTick | null>(null);

  // Timing refs
  const lastKeystrokeTimeRef = useRef<number>(Date.now());
  const longestPauseRef = useRef<number>(0);
  const debounceTimerRef = useRef<any>(null);
  const heartbeatTimerRef = useRef<any>(null);
  const typingBurstTimerRef = useRef<any>(null);
  const lastTickTextRef = useRef<string>('');

  // Start a new session
  const startNewSession = async (customProblem?: string, starter?: string) => {
    const prob = customProblem || problemText;
    try {
      const res = await api.startSilenceSession({
        problem: prob,
        course_id: activeCourseId || 'demo_course',
        course_name: 'Computer Science & Algorithms',
        topics: ['Dynamic Programming', 'Binary Search', 'Graph Algorithms'],
      });
      setSessionId(res.session_id);
      setAtlas(res.atlas);
      setLastDecision(null);
      setSpokenMessage(null);
      setStats(null);
      setTicksHistory([]);
      setFeedbackGiven(false);
      setSelectedTick(null);
      if (starter !== undefined) {
        setScratchpad(starter);
        lastTickTextRef.current = starter;
      }
    } catch (err) {
      console.error('Failed to start silence session:', err);
    }
  };

  useEffect(() => {
    startNewSession();
    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
      if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current);
      if (typingBurstTimerRef.current) clearTimeout(typingBurstTimerRef.current);
    };
  }, []);

  // Dispatch a tick to the server (async, non-blocking)
  const sendTick = useCallback(
    async (textToSend: string) => {
      if (!sessionId) return;
      const now = Date.now();
      const secSinceKey = (now - lastKeystrokeTimeRef.current) / 1000.0;

      try {
        const res = await api.sendSilenceTick({
          session_id: sessionId,
          text: textToSend,
          keystroke_meta: {
            seconds_since_last_keystroke: secSinceKey,
            longest_recent_pause: longestPauseRef.current,
            delete_rewrite_ratio: 0.15,
            changed_line_indices: [textToSend.split('\n').length - 1],
          },
        });

        if (res && res.decision) {
          setLastDecision(res.decision);
          setStats(res.session_stats || null);
          if (res.spoken_message) {
            setSpokenMessage(res.spoken_message);
            setFeedbackGiven(false);
          }

          // Append to local tick strip
          const newTick: SilenceReplayTick = {
            tick_index: res.tick_index || Date.now(),
            timestamp: now,
            scratchpad: textToSend,
            diff: res.decision.held_back_by || '',
            probabilities: res.decision.probabilities || {},
            rung: res.decision.rung,
            rung_name: res.decision.rung_name,
            token_class: res.decision.token_class,
            held_back_by: res.decision.held_back_by,
            action_type: res.decision.action_type,
            spoken: res.decision.spoken,
            spoken_text: res.spoken_message?.text || null,
            spoken_target_line: res.spoken_message?.target_line ?? null,
            decider_mode: res.decision.decider_mode,
            decider_ms: res.decision.latency_ms,
            llm_tokens: res.spoken_message
              ? res.spoken_message.input_tokens + res.spoken_message.output_tokens
              : 0,
          };
          setTicksHistory((prev) => [...prev.slice(-39), newTick]);
        }
      } catch (err) {
        console.error('Tick error:', err);
      }
    },
    [sessionId]
  );

  // Scratchpad typing change handler (Debounced ~900ms)
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newText = e.target.value;
    setScratchpad(newText);

    const now = Date.now();
    const pauseDuration = (now - lastKeystrokeTimeRef.current) / 1000.0;
    if (pauseDuration > longestPauseRef.current) {
      longestPauseRef.current = pauseDuration;
    }
    lastKeystrokeTimeRef.current = now;

    // Visual eye indicator: typing burst
    setIsTyping(true);
    if (typingBurstTimerRef.current) clearTimeout(typingBurstTimerRef.current);
    typingBurstTimerRef.current = setTimeout(() => {
      setIsTyping(false);
    }, 600);

    // Debounce tick
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(() => {
      lastTickTextRef.current = newText;
      sendTick(newText);
    }, 900);
  };

  // Heartbeat idle tick (every ~4 seconds if paused)
  useEffect(() => {
    heartbeatTimerRef.current = setInterval(() => {
      const now = Date.now();
      const secSinceKey = (now - lastKeystrokeTimeRef.current) / 1000.0;
      if (secSinceKey >= 3.5 && sessionId) {
        sendTick(lastTickTextRef.current || scratchpad);
      }
    }, 4000);

    return () => clearInterval(heartbeatTimerRef.current);
  }, [sessionId, scratchpad, sendTick]);

  // Patience dial adjustment
  const handlePatienceChange = async (val: number) => {
    setPatience(val);
    if (sessionId) {
      try {
        await api.setSilencePatience({ session_id: sessionId, patience: val });
      } catch (err) {
        console.error('Failed to update patience dial:', err);
      }
    }
  };

  // Student feedback handler
  const handleFeedback = async (helpful: boolean) => {
    if (!sessionId) return;
    try {
      await api.sendSilenceFeedback({
        session_id: sessionId,
        helpful,
        rung: lastDecision?.rung || 2,
      });
      setFeedbackGiven(true);
    } catch (err) {
      console.error('Failed to send feedback:', err);
    }
  };

  // Manual hint request button (starts at Rung 3)
  const handleAskHintMyself = () => {
    const hintText = scratchpad + '\n# Tutor, can you give me a hint?';
    setScratchpad(hintText);
    lastTickTextRef.current = hintText;
    sendTick(hintText);
  };

  // Load Replay for Time Machine
  const loadReplayData = async () => {
    if (!sessionId) return;
    try {
      const res = await api.getSilenceReplay(sessionId);
      setReplaySession(res);
    } catch (err) {
      console.error('Failed to load replay session:', err);
    }
  };

  useEffect(() => {
    if (activeTab === 'timemachine') {
      loadReplayData();
    }
  }, [activeTab]);

  return (
    <div className="flex flex-col h-full w-full overflow-y-auto bg-[#FAF8F5] text-slate-800 p-4 md:p-6 lg:p-8 space-y-6">
      {/* Header bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-blue-100 text-blue-700 border border-blue-200">
              STRANDS DECIDER 2B
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-200">
              #POLICY
            </span>
            <span className="text-[11px] font-mono text-slate-400">AWS Builder Center Hackathon</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-slate-900 font-sans">
            StudyMind Silence Studio ✨
          </h1>
          <p className="text-xs md:text-sm text-slate-500 font-serif italic mt-0.5">
            &ldquo;The tutor that watched you struggle for 4 minutes and said 9 words.&rdquo;
          </p>
        </div>

        {/* Tab switcher: Live Studio vs Time Machine & Duel */}
        <div className="flex items-center gap-2 self-start lg:self-center">
          <div className="flex items-center bg-slate-200/80 p-1 rounded-xl text-xs font-medium">
            <button
              onClick={() => setActiveTab('studio')}
              className={`px-3 py-1.5 rounded-lg transition cursor-pointer flex items-center gap-1.5 ${
                activeTab === 'studio'
                  ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <FileCode className="h-3.5 w-3.5" />
              <span>Live Studio</span>
            </button>
            <button
              onClick={() => setActiveTab('timemachine')}
              className={`px-3 py-1.5 rounded-lg transition cursor-pointer flex items-center gap-1.5 ${
                activeTab === 'timemachine'
                  ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <History className="h-3.5 w-3.5" />
              <span>Time Machine & Duel</span>
            </button>
          </div>
        </div>
      </div>

      {activeTab === 'studio' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Main Work Area: Left 8 cols */}
          <div className="lg:col-span-8 space-y-4">
            {/* Problem Card */}
            <div className="p-4 bg-white border border-slate-200/90 rounded-2xl shadow-sm space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <BookOpen className="h-4 w-4 text-blue-600" />
                  <span className="text-xs font-bold text-slate-800">Problem & Task</span>
                </div>

                {/* Preset problem picker */}
                <div className="flex items-center gap-2">
                  <select
                    onChange={(e) => {
                      const idx = parseInt(e.target.value, 10);
                      const p = PRESET_PROBLEMS[idx];
                      if (p) {
                        setProblemText(p.problem);
                        startNewSession(p.problem, p.starter);
                      }
                    }}
                    className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-slate-700 cursor-pointer"
                  >
                    {PRESET_PROBLEMS.map((p, i) => (
                      <option key={i} value={i}>
                        Preset {i + 1}: {p.title}
                      </option>
                    ))}
                  </select>

                  <button
                    onClick={() => setShowAtlas(!showAtlas)}
                    className="text-xs font-mono px-2 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 flex items-center gap-1 transition cursor-pointer"
                    title="Toggle Misconception Atlas teacher notes"
                  >
                    <span>Teacher&#39;s Notes</span>
                    {showAtlas ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                  </button>
                </div>
              </div>

              <p className="text-xs text-slate-700 leading-relaxed font-sans">{problemText}</p>

              {/* Collapsible Misconception Atlas (Bedrock Teacher Notes) */}
              {showAtlas && atlas && (
                <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-xl space-y-2 text-xs font-mono text-amber-950 animate-in fade-in duration-200">
                  <div className="flex items-center justify-between font-bold text-[11px] text-amber-900 border-b border-amber-200/60 pb-1">
                    <span>Misconception Atlas (Compiled by Bedrock Haiku once)</span>
                    <span className="text-[10px] text-amber-700 uppercase">
                      {atlas.generated_by}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
                    <div>
                      <span className="font-bold text-amber-800 block mb-1">Likely Misconceptions:</span>
                      <ul className="list-disc list-inside space-y-0.5 text-slate-700 font-sans">
                        {atlas.misconceptions.map((m) => (
                          <li key={m.id}>
                            <strong>{m.name}:</strong> {m.description}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <span className="font-bold text-amber-800 block mb-1">Milestones:</span>
                      <ol className="list-decimal list-inside space-y-0.5 text-slate-700 font-sans">
                        {atlas.milestones.map((s, idx) => (
                          <li key={idx}>{s}</li>
                        ))}
                      </ol>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Live Scratchpad Card */}
            <div className="bg-white border border-slate-200/90 rounded-2xl shadow-sm overflow-hidden flex flex-col">
              {/* Scratchpad toolbar */}
              <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200/80 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-800">Live Scratchpad</span>
                  <span className="text-[10px] font-mono text-slate-400">
                    Type your steps or code freely — tutor observes in silence
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {/* Font toggle */}
                  <button
                    onClick={() => setFontMode(fontMode === 'mono' ? 'serif' : 'mono')}
                    className="p-1 rounded-md text-slate-500 hover:text-slate-800 hover:bg-slate-200 text-xs flex items-center gap-1 transition cursor-pointer"
                    title="Toggle Monospace / Serif"
                  >
                    <Type className="h-3.5 w-3.5" />
                    <span className="text-[10px] font-mono font-semibold uppercase">{fontMode}</span>
                  </button>

                  {/* Manual hint override */}
                  <button
                    onClick={handleAskHintMyself}
                    className="px-2.5 py-1 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 text-xs font-medium flex items-center gap-1 transition cursor-pointer"
                    title="Ask tutor for a hint directly (Rung 3)"
                  >
                    <HelpCircle className="h-3.5 w-3.5 text-blue-600" />
                    <span>Ask for a hint</span>
                  </button>
                </div>
              </div>

              {/* Editor + Ghost Margin Split */}
              <div className="grid grid-cols-1 md:grid-cols-12 min-h-[360px] divide-y md:divide-y-0 md:divide-x divide-slate-200">
                {/* Scratchpad Text Area */}
                <div className="md:col-span-8 p-4 relative">
                  <textarea
                    value={scratchpad}
                    onChange={handleTextChange}
                    spellCheck={false}
                    className={`w-full h-full min-h-[320px] resize-none outline-none text-slate-900 bg-transparent leading-relaxed ${
                      fontMode === 'mono' ? 'font-mono text-xs' : 'font-serif text-sm'
                    }`}
                    placeholder="Type your reasoning, equations, code, or rough steps here..."
                  />

                  {/* Soft wavy underline visual cue for Rung 1 */}
                  {lastDecision?.rung === 1 && (
                    <div className="absolute bottom-3 left-4 right-4 text-[10px] text-amber-700 font-mono flex items-center gap-1.5 opacity-90 animate-pulse">
                      <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                      <span>Ghost underline softly anchored to suspect reasoning step.</span>
                    </div>
                  )}
                </div>

                {/* Right Margin: Ghost Margin for Rungs 1-4 */}
                <div className="md:col-span-4 p-4 bg-slate-50/50 flex flex-col justify-start">
                  <GhostMargin
                    spokenMessage={spokenMessage}
                    suspectLines={lastDecision?.suspect_lines || []}
                    currentRung={lastDecision?.rung || 0}
                    onFeedback={handleFeedback}
                    feedbackGiven={feedbackGiven}
                  />
                  {!spokenMessage && lastDecision?.rung === 0 && (
                    <div className="h-full flex flex-col items-center justify-center text-center p-4 text-slate-400">
                      <VolumeX className="h-6 w-6 mb-2 text-slate-300" />
                      <p className="text-xs font-medium text-slate-500">Tutor is silent</p>
                      <p className="text-[11px] text-slate-400 mt-1 leading-normal font-serif">
                        {lastDecision?.held_back_by || 'Leaving you in flow to productively struggle.'}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Bottom Strip: The Heartbeat */}
            <HeartbeatStrip
              ticks={ticksHistory}
              onSelectTick={(tick) => setSelectedTick(tick)}
              selectedTickIndex={selectedTick?.tick_index}
            />
          </div>

          {/* Right Column: Silence Meter & Controls (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            {/* Big Animated Silence Meter */}
            <SilenceMeter
              stats={stats}
              isTyping={isTyping}
              deciderMode={lastDecision?.decider_mode || 'model'}
              avgLatencyMs={stats?.avg_decider_ms || 115}
              lastHeldBackBy={lastDecision?.held_back_by}
            />

            {/* Patience Dial Card */}
            <div className="p-4 bg-white border border-slate-200/90 rounded-2xl shadow-sm space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800">
                  <Sliders className="h-3.5 w-3.5 text-blue-600" />
                  <span>Patience Dial</span>
                </div>
                <span className="text-[10px] font-mono text-slate-500">
                  {patience < 0.4 ? 'Patient (Quiet)' : patience > 0.6 ? 'Eager' : 'Balanced'}
                </span>
              </div>

              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={patience}
                onChange={(e) => handlePatienceChange(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />

              <div className="flex justify-between text-[10px] font-mono text-slate-400">
                <span>Interrupt me less</span>
                <span>Interrupt me more</span>
              </div>
              <p className="text-[10px] text-slate-500 font-sans leading-relaxed">
                Controls the tutor&#39;s threshold for stepping up rungs. Adaptive calibration
                adjusts this automatically when you click &ldquo;You interrupted me&rdquo;.
              </p>
            </div>

            {/* The Escalation Ladder Reference */}
            <div className="p-4 bg-white border border-slate-200/90 rounded-2xl shadow-sm space-y-2.5">
              <div className="text-xs font-bold text-slate-800 flex items-center justify-between">
                <span>The Escalation Ladder</span>
                <span className="text-[10px] font-mono text-slate-400">Tokens</span>
              </div>

              <div className="space-y-1.5 text-xs font-mono">
                {[
                  { r: 'R0', name: 'Silence', desc: 'Flow preserved', cost: '0' },
                  { r: 'R1', name: 'Ghost Underline', desc: 'Zero words', cost: '0' },
                  { r: 'R2', name: 'Margin Question', desc: '≤ 15 words', cost: 'tiny' },
                  { r: 'R3', name: 'Margin Hint', desc: '≤ 30 words', cost: 'small' },
                  { r: 'R4', name: 'One Step Only', desc: '≤ 45 words', cost: 'small' },
                  { r: 'RB', name: 'Human Breather', desc: 'Calm reassurance', cost: 'tiny' },
                ].map((item) => {
                  const isActive =
                    (item.r === 'RB' && lastDecision?.rung === 'B') ||
                    (item.r !== 'RB' && lastDecision?.rung === parseInt(item.r.slice(1), 10));

                  return (
                    <div
                      key={item.r}
                      className={`flex items-center justify-between p-1.5 rounded-lg transition-colors ${
                        isActive
                          ? 'bg-blue-50 text-blue-900 font-bold border border-blue-200'
                          : 'text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="w-6 text-[10px] font-bold text-slate-400">{item.r}</span>
                        <span className="text-[11px] font-medium">{item.name}</span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400">{item.cost}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Time Machine & Duel View */
        <TimeMachineScrubber
          session={replaySession}
          onScrubTick={(tick) => {
            setSelectedTick(tick);
            setScratchpad(tick.scratchpad);
          }}
        />
      )}
    </div>
  );
};
export default SilenceStudioPage;
