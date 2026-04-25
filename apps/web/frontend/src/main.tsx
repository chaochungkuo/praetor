import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  MessagesSquare,
  AudioLines,
  Bot,
  BriefcaseBusiness,
  CheckCircle2,
  CirclePause,
  Command,
  Gauge,
  Loader2,
  Mic,
  Send,
  ShieldCheck,
  Sparkles,
  UserRound
} from "lucide-react";
import { getMissionAgentMessages, getMissionTimeline, getOfficeSnapshot, getSession, sendCeoMessage } from "./api";
import type { AgentMessage, ConversationMessage, Mission, OfficeSnapshot, Session, TimelineEvent } from "./types";
import "./styles.css";

type BrowserSpeechRecognition = {
  lang: string;
  interimResults: boolean;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  onresult: ((event: BrowserSpeechRecognitionEvent) => void) | null;
  start: () => void;
};

type BrowserSpeechRecognitionEvent = {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
};

type BrowserSpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [snapshot, setSnapshot] = useState<OfficeSnapshot | null>(null);
  const [selectedMissionId, setSelectedMissionId] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [agentMessages, setAgentMessages] = useState<AgentMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [listening, setListening] = useState(false);

  useEffect(() => {
    void bootstrap();
    const timer = window.setInterval(() => void refreshOffice(false), 8000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!selectedMissionId) {
      setTimeline([]);
      return;
    }
    Promise.all([getMissionTimeline(selectedMissionId), getMissionAgentMessages(selectedMissionId)])
      .then(([events, messages]) => {
        setTimeline(events);
        setAgentMessages(messages);
      })
      .catch((err: Error) => setError(err.message));
  }, [selectedMissionId]);

  async function bootstrap() {
    try {
      const sessionData = await getSession();
      setSession(sessionData);
      if (sessionData.initialized && sessionData.authenticated) {
        const office = await getOfficeSnapshot();
        setSnapshot(office);
        setSelectedMissionId(office.missions[0]?.id ?? null);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function refreshOffice(showErrors = true) {
    try {
      const office = await getOfficeSnapshot();
      setSnapshot(office);
      if (!selectedMissionId && office.missions.length > 0) {
        setSelectedMissionId(office.missions[0].id);
      }
    } catch (err) {
      if (showErrors) setError((err as Error).message);
    }
  }

  async function handleSend() {
    if (!input.trim() || !session?.csrf_token) return;
    setIsSending(true);
    setError(null);
    try {
      const result = await sendCeoMessage(input.trim(), session.csrf_token);
      setInput("");
      setSnapshot((current) =>
        current ? { ...current, ceo_thread: [...current.ceo_thread, ...result.messages] } : current
      );
      await refreshOffice(false);
      if (result.created_mission) {
        setSelectedMissionId(result.created_mission.id);
        setAgentMessages(result.agent_messages);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsSending(false);
    }
  }

  function handleVoiceInput() {
    const SpeechRecognitionCtor =
      window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      setError("This browser does not expose speech recognition. The backend transcription interface is reserved for provider integration.");
      return;
    }
    const recognizer = new SpeechRecognitionCtor();
    recognizer.lang = "zh-TW";
    recognizer.interimResults = false;
    recognizer.onstart = () => setListening(true);
    recognizer.onend = () => setListening(false);
    recognizer.onerror = () => {
      setListening(false);
      setError("Voice input failed. Please try again or type the instruction.");
    };
    recognizer.onresult = (event: BrowserSpeechRecognitionEvent) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript ?? "")
        .join(" ")
        .trim();
      if (transcript) setInput((current) => `${current}${current ? " " : ""}${transcript}`);
    };
    recognizer.start();
  }

  if (!session) {
    return <LoadingState />;
  }

  if (!session.initialized) {
    return <Gate title="Praetor is not initialized" body="Complete onboarding in the existing Praetor setup flow before entering the Office." href="/app/praetor" action="Open onboarding" />;
  }

  if (!session.authenticated) {
    return <Gate title="Owner login required" body="The Office contains company memory, agent activity, and execution status. Sign in as the owner to continue." href="/app/login?next=/office" action="Login" />;
  }

  if (!snapshot) {
    return <LoadingState />;
  }

  const selectedMission = snapshot.missions.find((mission) => mission.id === selectedMissionId) ?? snapshot.missions[0];

  return (
    <div className="office-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Command size={24} /></div>
          <div>
            <strong>Praetor</strong>
            <span>Chairman's Office</span>
          </div>
        </div>
        <nav className="nav">
          <a className="active" href="/office"><BriefcaseBusiness size={18} /> Office</a>
          <a href="/app/tasks"><Activity size={18} /> Missions</a>
          <a href="/app/decisions"><ShieldCheck size={18} /> Decisions</a>
          <a href="/app/memory"><Sparkles size={18} /> Memory</a>
          <a href="/app/models"><Gauge size={18} /> Operations</a>
        </nav>
        <div className="sidebar-footer">
          <span>Owner</span>
          <strong>{session.owner_name ?? "Owner"}</strong>
        </div>
      </aside>

      <main className="main">
        <header className="office-header">
          <div>
            <p className="eyebrow">Executive cockpit</p>
            <h1>董事長辦公室</h1>
            <p>CEO briefing, mission control, and AI organization telemetry in one working room.</p>
          </div>
          <div className="header-actions">
            <StatusBadge label="Runtime" value={String(snapshot.runtime_health.healthy ? "ready" : "needs setup")} />
            <StatusBadge label="Mode" value={String(snapshot.runtime_health.mode ?? "unknown")} />
          </div>
        </header>

        {error ? <div className="error-banner">{error}</div> : null}

        <section className="metric-grid">
          <Metric icon={<Activity />} label="Active missions" value={snapshot.briefing.active_missions} />
          <Metric icon={<CirclePause />} label="Paused" value={snapshot.briefing.paused_missions} />
          <Metric icon={<ShieldCheck />} label="Approvals" value={snapshot.approvals.length} />
          <Metric icon={<CheckCircle2 />} label="Total missions" value={snapshot.missions.length} />
        </section>

        <section className="office-grid">
          <CeoChat
            messages={snapshot.ceo_thread}
            input={input}
            setInput={setInput}
            isSending={isSending}
            listening={listening}
            onSend={handleSend}
            onVoice={handleVoiceInput}
          />
          <MissionControl
            missions={snapshot.missions}
            selectedMissionId={selectedMission?.id ?? null}
            onSelect={setSelectedMissionId}
          />
        </section>

        <section className="mission-room">
          <MissionRoom
            mission={selectedMission}
            timeline={timeline}
            agentActivity={snapshot.agent_activity}
            agentMessages={agentMessages}
          />
        </section>
      </main>

      <aside className="executive-rail">
        <RailSection title="Decisions">
          {snapshot.approvals.length === 0 ? <p>No pending approvals.</p> : snapshot.approvals.map((approval) => (
            <div className="rail-item" key={approval.id}>
              <strong>{approval.category.replaceAll("_", " ")}</strong>
              <span>{approval.reason}</span>
            </div>
          ))}
        </RailSection>
        <RailSection title="Agent activity">
          {snapshot.agent_activity.slice(0, 8).map((event) => (
            <div className="rail-item" key={event.id}>
              <strong>{event.actor.replaceAll("_", " ")}</strong>
              <span>{event.body ?? event.title}</span>
            </div>
          ))}
        </RailSection>
      </aside>
    </div>
  );
}

function CeoChat(props: {
  messages: ConversationMessage[];
  input: string;
  setInput: (value: string) => void;
  isSending: boolean;
  listening: boolean;
  onSend: () => void;
  onVoice: () => void;
}) {
  const messages = props.messages.length > 0 ? props.messages : [{
    id: "seed",
    thread_id: "office",
    role: "ceo" as const,
    body: "我在這裡。你可以用文字或語音給我方向，我會把它整理成任務、決策或公司記憶。",
    created_at: new Date().toISOString()
  }];
  return (
    <section className="surface ceo-chat">
      <div className="surface-header">
        <div>
          <p className="eyebrow">CEO channel</p>
          <h2>和 CEO 對話</h2>
        </div>
        <Bot />
      </div>
      <div className="chat-scroll">
        {messages.map((message) => (
          <div className={`chat-message ${message.role}`} key={message.id}>
            <strong>{message.role === "chairman" ? "Chairman" : "CEO"}</strong>
            <p>{message.body}</p>
          </div>
        ))}
      </div>
      <div className="composer">
        <button className={`icon-button ${props.listening ? "listening" : ""}`} type="button" onClick={props.onVoice} title="Voice input">
          {props.listening ? <AudioLines /> : <Mic />}
        </button>
        <textarea
          value={props.input}
          onChange={(event) => props.setInput(event.target.value)}
          placeholder="給 CEO 一個方向，例如：整理目前所有任務的風險，告訴我哪裡需要我決策。"
          rows={3}
        />
        <button className="send-button" type="button" disabled={props.isSending} onClick={props.onSend}>
          {props.isSending ? <Loader2 className="spin" /> : <Send />}
          Send
        </button>
      </div>
    </section>
  );
}

function MissionControl({ missions, selectedMissionId, onSelect }: {
  missions: Mission[];
  selectedMissionId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <section className="surface">
      <div className="surface-header">
        <div>
          <p className="eyebrow">Mission portfolio</p>
          <h2>任務進度</h2>
        </div>
        <BriefcaseBusiness />
      </div>
      <div className="mission-list">
        {missions.length === 0 ? <p>No missions yet.</p> : missions.map((mission) => (
          <button
            className={`mission-card ${mission.id === selectedMissionId ? "selected" : ""}`}
            key={mission.id}
            type="button"
            onClick={() => onSelect(mission.id)}
          >
            <span className={`status-dot ${mission.status}`} />
            <strong>{mission.title}</strong>
            <small>{mission.priority} · {mission.manager_layer}</small>
            <em>{mission.status}</em>
          </button>
        ))}
      </div>
    </section>
  );
}

function MissionRoom({ mission, timeline, agentActivity, agentMessages }: {
  mission?: Mission;
  timeline: TimelineEvent[];
  agentActivity: TimelineEvent[];
  agentMessages: AgentMessage[];
}) {
  const visibleEvents = timeline.length > 0 ? timeline : agentActivity;
  return (
    <section className="surface">
      <div className="surface-header">
        <div>
          <p className="eyebrow">Mission room</p>
          <h2>{mission?.title ?? "No mission selected"}</h2>
        </div>
        {mission ? <a className="open-link" href={`/app/missions/${mission.id}`}>Open classic detail</a> : null}
      </div>
      {mission ? (
        <div className="room-layout">
          <div className="mission-brief">
            <p>{mission.summary ?? "No summary provided."}</p>
            <dl>
              <div><dt>Status</dt><dd>{mission.status}</dd></div>
              <div><dt>Priority</dt><dd>{mission.priority}</dd></div>
              <div><dt>PM</dt><dd>{mission.pm_required ? "required" : "not required"}</dd></div>
              <div><dt>Complexity</dt><dd>{mission.complexity_score.toFixed(2)}</dd></div>
            </dl>
          </div>
          <div className="mission-thread-grid">
            <div>
              <div className="thread-title"><Activity size={16} /> Timeline</div>
              <div className="timeline">
                {visibleEvents.length === 0 ? <p>No timeline events yet.</p> : visibleEvents.map((event) => (
                  <div className="timeline-event" key={event.id}>
                    <div className="timeline-marker" />
                    <div>
                      <span>{event.actor.replaceAll("_", " ")}</span>
                      <strong>{event.title}</strong>
                      {event.body ? <p>{event.body}</p> : null}
                      {event.status ? <em>{event.status}</em> : null}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <div className="thread-title"><MessagesSquare size={16} /> AI internal conversation</div>
              <div className="agent-thread">
                {agentMessages.length === 0 ? <p>No agent conversation yet.</p> : agentMessages.map((message) => (
                  <div className={`agent-bubble ${message.role}`} key={message.id}>
                    <strong>{message.role.replaceAll("_", " ")}</strong>
                    <p>{message.body}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : <p>Create a mission to open the live room.</p>}
    </section>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="metric">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function StatusBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="status-badge">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function RailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rail-section">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function LoadingState() {
  return (
    <div className="gate">
      <Loader2 className="spin" />
      <p>Loading Praetor Office...</p>
    </div>
  );
}

function Gate({ title, body, href, action }: { title: string; body: string; href: string; action: string }) {
  return (
    <div className="gate">
      <div className="gate-panel">
        <UserRound size={34} />
        <h1>{title}</h1>
        <p>{body}</p>
        <a href={href}>{action}</a>
      </div>
    </div>
  );
}

declare global {
  interface Window {
    SpeechRecognition?: BrowserSpeechRecognitionConstructor;
    webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor;
  }
}

createRoot(document.getElementById("root")!).render(<App />);
