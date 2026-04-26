import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  MessagesSquare,
  AudioLines,
  Bot,
  BriefcaseBusiness,
  CirclePause,
  Command,
  Gauge,
  CheckCircle2,
  Loader2,
  Mic,
  PanelRightClose,
  PanelRightOpen,
  Send,
  ShieldCheck,
  Sparkles,
  UserRound,
  UsersRound,
  GitBranch,
  AlertTriangle
} from "lucide-react";
import { getMissionAgentMessages, getMissionTimeline, getOfficeSnapshot, getSession, sendCeoMessage } from "./api";
import type { AgentMessage, ConversationMessage, Mission, OfficeSnapshot, OrganizationSnapshot, PlannerAction, Session, TimelineEvent } from "./types";
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
type Language = "en" | "zh-TW";
type Translator = (key: string) => string;

const OFFICE_TEXT: Record<Language, Record<string, string>> = {
  en: {
    office_not_initialized: "Praetor is not initialized",
    office_not_initialized_body: "Complete onboarding in the existing Praetor setup flow before entering the Office.",
    open_onboarding: "Open onboarding",
    login_required: "Owner login required",
    login_required_body: "The Office contains company memory, agent activity, and execution status. Sign in as the owner to continue.",
    login: "Login",
    chairman_office: "Chairman's Office",
    office: "Office",
    missions: "Missions",
    decisions: "Decisions",
    memory: "Memory",
    operations: "Operations",
    owner: "Owner",
    executive_cockpit: "Executive cockpit",
    office_title: "董事長辦公室",
    office_subtitle: "CEO briefing, mission control, and AI organization telemetry in one working room.",
    runtime: "Runtime",
    mode: "Mode",
    ready: "Ready",
    needs_setup: "Needs setup",
    unknown: "Unknown",
    hide_rail: "Hide rail",
    show_rail: "Show rail",
    needs_decision: "Needs decision",
    missions_at_risk: "Missions at risk",
    running_work: "Running work",
    ready_or_done: "Ready or done",
    ceo_channel: "CEO channel",
    chat_with_ceo: "和 CEO 對話",
    chairman: "Chairman",
    send: "Send",
    voice_input: "Voice input",
    mission_portfolio: "Mission portfolio",
    mission_progress: "任務進度",
    no_missions: "No missions yet.",
    mission_room: "Mission room",
    no_mission_selected: "No mission selected",
    open_classic_detail: "Open classic detail",
    no_summary: "No summary provided.",
    status: "Status",
    priority: "Priority",
    pm: "PM",
    complexity: "Complexity",
    required: "Required",
    direct: "Direct",
    timeline: "Timeline",
    no_timeline: "No timeline events yet.",
    ai_internal_conversation: "AI internal conversation",
    no_agent_conversation: "No agent conversation yet.",
    create_mission_to_open: "Create a mission to open the live room.",
    ai_organization: "AI organization",
    organization_title: "編組、交辦、升級",
    org_chart: "Org chart",
    mission_team: "Mission team",
    no_mission_agents: "No mission agents yet.",
    reports_to: "Reports to",
    mission_context: "mission context",
    authority: "Authority and escalation",
    no_authority: "No special decision authority.",
    unclear_risk: "Escalate unclear scope or risk.",
    delegations: "Delegations",
    no_delegations: "No delegations yet.",
    report_blockers: "report blockers and completion",
    escalation_rules: "Escalation rules",
    escalations: "Escalations",
    ceo_actions: "CEO actions",
    agent_activity: "Agent activity",
    no_pending_approvals: "No pending approvals.",
    no_pending_escalations: "No pending escalations.",
    no_planner_actions: "No planner actions yet.",
    loading: "Loading Praetor Office...",
  },
  "zh-TW": {
    office_not_initialized: "Praetor 尚未初始化",
    office_not_initialized_body: "請先完成 Praetor 初始化，再進入董事長辦公室。",
    open_onboarding: "開始初始化",
    login_required: "需要擁有者登入",
    login_required_body: "董事長辦公室包含公司記憶、AI 活動與執行狀態。請先以擁有者身份登入。",
    login: "登入",
    chairman_office: "董事長辦公室",
    office: "辦公室",
    missions: "任務",
    decisions: "決策",
    memory: "記憶",
    operations: "執行",
    owner: "擁有者",
    executive_cockpit: "董事長主控台",
    office_title: "董事長辦公室",
    office_subtitle: "在同一個工作空間查看 CEO 簡報、任務進度與 AI 組織狀態。",
    runtime: "執行環境",
    mode: "模式",
    ready: "就緒",
    needs_setup: "需要設定",
    unknown: "未知",
    hide_rail: "收合側欄",
    show_rail: "打開側欄",
    needs_decision: "需要決策",
    missions_at_risk: "有風險任務",
    running_work: "進行中工作",
    ready_or_done: "已準備或完成",
    ceo_channel: "CEO 頻道",
    chat_with_ceo: "和 CEO 對話",
    chairman: "董事長",
    send: "送出",
    voice_input: "語音輸入",
    mission_portfolio: "任務組合",
    mission_progress: "任務進度",
    no_missions: "目前還沒有任務。",
    mission_room: "任務室",
    no_mission_selected: "尚未選擇任務",
    open_classic_detail: "打開傳統詳細頁",
    no_summary: "目前沒有摘要。",
    status: "狀態",
    priority: "優先級",
    pm: "PM",
    complexity: "複雜度",
    required: "需要",
    direct: "直接",
    timeline: "時間線",
    no_timeline: "目前沒有時間線事件。",
    ai_internal_conversation: "AI 內部對話",
    no_agent_conversation: "目前沒有 AI 對話。",
    create_mission_to_open: "建立任務後即可打開任務室。",
    ai_organization: "AI 組織",
    organization_title: "編組、交辦、升級",
    org_chart: "組織圖",
    mission_team: "任務團隊",
    no_mission_agents: "目前沒有任務 AI。",
    reports_to: "回報給",
    mission_context: "任務脈絡",
    authority: "權限與升級規則",
    no_authority: "沒有特別決策權限。",
    unclear_risk: "遇到範圍不清或風險時向上升級。",
    delegations: "交辦",
    no_delegations: "目前沒有交辦事項。",
    report_blockers: "回報阻礙與完成狀態",
    escalation_rules: "升級規則",
    escalations: "升級事項",
    ceo_actions: "CEO 行動",
    agent_activity: "AI 活動",
    no_pending_approvals: "目前沒有待核准事項。",
    no_pending_escalations: "目前沒有待處理升級事項。",
    no_planner_actions: "目前沒有 planner 行動。",
    loading: "正在載入 Praetor Office...",
  },
};

function officeTranslator(language?: string | null): { language: Language; t: Translator } {
  const resolved: Language = language === "zh-TW" ? "zh-TW" : "en";
  return {
    language: resolved,
    t: (key: string) => OFFICE_TEXT[resolved][key] ?? OFFICE_TEXT.en[key] ?? key,
  };
}

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [snapshot, setSnapshot] = useState<OfficeSnapshot | null>(null);
  const [selectedMissionId, setSelectedMissionId] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [agentMessages, setAgentMessages] = useState<AgentMessage[]>([]);
  const [input, setInput] = useState("");
  const [lastActions, setLastActions] = useState<PlannerAction[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [listening, setListening] = useState(false);
  const [railOpen, setRailOpen] = useState(true);
  const { language, t } = officeTranslator(session?.ui_language);

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
      setLastActions(result.actions);
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
    return <Gate title={t("office_not_initialized")} body={t("office_not_initialized_body")} href="/app/praetor" action={t("open_onboarding")} />;
  }

  if (!session.authenticated) {
    return <Gate title={t("login_required")} body={t("login_required_body")} href="/app/login?next=/office" action={t("login")} />;
  }

  if (!snapshot) {
    return <LoadingState message={t("loading")} />;
  }

  const selectedMission = snapshot.missions.find((mission) => mission.id === selectedMissionId) ?? snapshot.missions[0];
  const pendingEscalations = snapshot.organization.escalations.filter((item) => item.status === "pending");
  const runningMissions = snapshot.missions.filter((mission) => ["active", "resumed", "review", "reviewing"].includes(mission.status));
  const riskMissionIds = new Set(pendingEscalations.map((item) => item.mission_id).filter(Boolean));
  const atRiskMissions = snapshot.missions.filter((mission) =>
    riskMissionIds.has(mission.id) || ["failed", "waiting_approval", "paused", "needs_decision"].includes(mission.status)
  );
  const completedMissions = snapshot.missions.filter((mission) => ["completed", "ready_for_ceo"].includes(mission.status));
  const visibleActions = lastActions.length > 0 ? lastActions : snapshot.recent_planner_actions;

  return (
    <div className={`office-shell ${railOpen ? "" : "rail-collapsed"}`}>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Command size={24} /></div>
          <div>
            <strong>Praetor</strong>
            <span>{t("chairman_office")}</span>
          </div>
        </div>
        <nav className="nav">
          <a className="active" href="/office"><BriefcaseBusiness size={18} /> {t("office")}</a>
          <a href="/app/tasks"><Activity size={18} /> {t("missions")}</a>
          <a href="/app/decisions"><ShieldCheck size={18} /> {t("decisions")}</a>
          <a href="/app/memory"><Sparkles size={18} /> {t("memory")}</a>
          <a href="/app/models"><Gauge size={18} /> {t("operations")}</a>
        </nav>
        <div className="sidebar-footer">
          <span>{t("owner")}</span>
          <strong>{session.owner_name ?? t("owner")}</strong>
        </div>
      </aside>

      <main className="main">
        <header className="office-header">
          <div>
            <p className="eyebrow">{t("executive_cockpit")}</p>
            <h1>{t("office_title")}</h1>
            <p>{t("office_subtitle")}</p>
          </div>
          <div className="header-actions">
            <StatusBadge label={t("runtime")} value={String(snapshot.runtime_health.healthy ? t("ready") : t("needs_setup"))} />
            <StatusBadge label={t("mode")} value={readableStatus(String(snapshot.runtime_health.mode ?? "unknown"), language)} />
            <button className="rail-toggle" type="button" onClick={() => setRailOpen((value) => !value)} title={railOpen ? t("hide_rail") : t("show_rail")}>
              {railOpen ? <PanelRightClose size={17} /> : <PanelRightOpen size={17} />}
              {railOpen ? t("hide_rail") : t("show_rail")}
            </button>
          </div>
        </header>

        {error ? <div className="error-banner">{error}</div> : null}

        <section className="metric-grid">
          <Metric icon={<AlertTriangle />} label={t("needs_decision")} value={snapshot.approvals.length + pendingEscalations.length} tone={snapshot.approvals.length + pendingEscalations.length > 0 ? "risk" : "normal"} />
          <Metric icon={<CirclePause />} label={t("missions_at_risk")} value={atRiskMissions.length} tone={atRiskMissions.length > 0 ? "risk" : "normal"} />
          <Metric icon={<Activity />} label={t("running_work")} value={runningMissions.length} />
          <Metric icon={<CheckCircle2 />} label={t("ready_or_done")} value={completedMissions.length} />
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
            t={t}
          />
          <MissionControl
            missions={snapshot.missions}
            selectedMissionId={selectedMission?.id ?? null}
            onSelect={setSelectedMissionId}
            language={language}
            t={t}
          />
        </section>

        <section className="mission-room">
          <OrganizationPanel organization={snapshot.organization} selectedMissionId={selectedMission?.id ?? null} language={language} t={t} />
          <MissionRoom
            mission={selectedMission}
            timeline={timeline}
            agentActivity={snapshot.agent_activity}
            agentMessages={agentMessages}
            language={language}
            t={t}
          />
        </section>
      </main>

      {railOpen ? <aside className="executive-rail">
        <RailSection title={t("decisions")}>
          {snapshot.approvals.length === 0 ? <p>{t("no_pending_approvals")}</p> : snapshot.approvals.map((approval) => (
            <div className="rail-item" key={approval.id}>
              <strong>{readableCategory(approval.category, language)}</strong>
              <span>{approval.reason}</span>
            </div>
          ))}
        </RailSection>
        <RailSection title={t("escalations")}>
          {snapshot.organization.escalations.filter((item) => item.status === "pending").length === 0 ? <p>{t("no_pending_escalations")}</p> : snapshot.organization.escalations.filter((item) => item.status === "pending").slice(0, 6).map((item) => (
            <div className="rail-item action-skipped" key={item.id}>
              <strong>{labelize(item.to_level, language)}</strong>
              <span>{item.reason}</span>
              <small>{readableCategory(item.category, language)}</small>
            </div>
          ))}
        </RailSection>
        <RailSection title={t("ceo_actions")}>
          {visibleActions.length === 0 ? <p>{t("no_planner_actions")}</p> : visibleActions.map((action) => (
            <div className={`rail-item action-${action.status}`} key={action.id}>
              <strong>{readableAction(action.type, language)}</strong>
              <span>{action.title}</span>
              <small>{readableStatus(action.status, language)}{action.result_id ? ` · ${shortId(action.result_id)}` : ""}</small>
            </div>
          ))}
        </RailSection>
        <RailSection title={t("agent_activity")}>
          {snapshot.agent_activity.slice(0, 8).map((event) => (
            <div className="rail-item" key={event.id}>
              <strong>{labelize(event.actor, language)}</strong>
              <span>{eventSummary(event)}</span>
            </div>
          ))}
        </RailSection>
      </aside> : null}
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
  t: Translator;
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
          <p className="eyebrow">{props.t("ceo_channel")}</p>
          <h2>{props.t("chat_with_ceo")}</h2>
        </div>
        <Bot />
      </div>
      <div className="chat-scroll">
        {messages.map((message) => (
          <div className={`chat-message ${message.role}`} key={message.id}>
            <strong>{message.role === "chairman" ? props.t("chairman") : "CEO"}</strong>
            <p>{message.body}</p>
          </div>
        ))}
      </div>
      <div className="composer">
        <button className={`icon-button ${props.listening ? "listening" : ""}`} type="button" onClick={props.onVoice} title={props.t("voice_input")}>
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
          {props.t("send")}
        </button>
      </div>
    </section>
  );
}

function MissionControl({ missions, selectedMissionId, onSelect, language, t }: {
  missions: Mission[];
  selectedMissionId: string | null;
  onSelect: (id: string) => void;
  language: Language;
  t: Translator;
}) {
  return (
    <section className="surface">
      <div className="surface-header">
        <div>
          <p className="eyebrow">{t("mission_portfolio")}</p>
          <h2>{t("mission_progress")}</h2>
        </div>
        <BriefcaseBusiness />
      </div>
      <div className="mission-list">
        {missions.length === 0 ? <p>{t("no_missions")}</p> : missions.map((mission) => (
          <button
            className={`mission-card ${mission.id === selectedMissionId ? "selected" : ""}`}
            key={mission.id}
            type="button"
            onClick={() => onSelect(mission.id)}
          >
            <span className={`status-dot ${mission.status}`} />
            <strong>{mission.title}</strong>
            <small>{readablePriority(mission.priority, language)} · {readableManager(mission.manager_layer, language)}</small>
            <em>{readableStatus(mission.status, language)}</em>
          </button>
        ))}
      </div>
    </section>
  );
}

function MissionRoom({ mission, timeline, agentActivity, agentMessages, language, t }: {
  mission?: Mission;
  timeline: TimelineEvent[];
  agentActivity: TimelineEvent[];
  agentMessages: AgentMessage[];
  language: Language;
  t: Translator;
}) {
  const visibleEvents = timeline.length > 0 ? timeline : agentActivity;
  return (
    <section className="surface">
      <div className="surface-header">
        <div>
          <p className="eyebrow">{t("mission_room")}</p>
          <h2>{mission?.title ?? t("no_mission_selected")}</h2>
        </div>
        {mission ? <a className="open-link" href={`/app/missions/${mission.id}`}>{t("open_classic_detail")}</a> : null}
      </div>
      {mission ? (
        <div className="room-layout">
          <div className="mission-brief">
            <p>{mission.summary ?? t("no_summary")}</p>
            <dl>
              <div><dt>{t("status")}</dt><dd>{readableStatus(mission.status, language)}</dd></div>
              <div><dt>{t("priority")}</dt><dd>{readablePriority(mission.priority, language)}</dd></div>
              <div><dt>{t("pm")}</dt><dd>{mission.pm_required ? t("required") : t("direct")}</dd></div>
              <div><dt>{t("complexity")}</dt><dd>{mission.complexity_score.toFixed(2)}</dd></div>
            </dl>
          </div>
          <div className="mission-thread-grid">
            <div>
              <div className="thread-title"><Activity size={16} /> {t("timeline")}</div>
              <div className="timeline">
                {visibleEvents.length === 0 ? <p>{t("no_timeline")}</p> : visibleEvents.map((event) => (
                  <div className="timeline-event" key={event.id}>
                    <div className="timeline-marker" />
                    <div>
                      <span className={`event-type event-${event.type}`}>{readableEventType(event.type, language)} · {labelize(event.actor, language)}</span>
                      <strong>{readableEventTitle(event)}</strong>
                      {event.body ? <p>{eventSummary(event)}</p> : null}
                      {event.status ? <em>{readableStatus(event.status, language)}</em> : null}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <div className="thread-title"><MessagesSquare size={16} /> {t("ai_internal_conversation")}</div>
              <div className="agent-thread">
                {agentMessages.length === 0 ? <p>{t("no_agent_conversation")}</p> : agentMessages.map((message) => (
                  <div className={`agent-bubble ${message.role}`} key={message.id}>
                    <strong>{labelize(message.role, language)}</strong>
                    <p>{agentMessageSummary(message)}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : <p>{t("create_mission_to_open")}</p>}
    </section>
  );
}

function OrganizationPanel({ organization, selectedMissionId, language, t }: {
  organization: OrganizationSnapshot;
  selectedMissionId: string | null;
  language: Language;
  t: Translator;
}) {
  const agents = selectedMissionId
    ? organization.agents.filter((agent) => agent.mission_id === selectedMissionId)
    : organization.agents;
  const delegations = selectedMissionId
    ? organization.delegations.filter((item) => item.mission_id === selectedMissionId)
    : organization.delegations;
  const escalations = selectedMissionId
    ? organization.escalations.filter((item) => item.mission_id === selectedMissionId)
    : organization.escalations;
  return (
    <section className="surface organization-panel">
      <div className="surface-header">
        <div>
          <p className="eyebrow">{t("ai_organization")}</p>
          <h2>{t("organization_title")}</h2>
        </div>
        <UsersRound />
      </div>
      <div className="org-grid">
        <div>
          <div className="thread-title"><UsersRound size={16} /> {t("org_chart")}</div>
          <OrgChart agents={agents} language={language} t={t} />
          <div className="thread-title compact-title"><UsersRound size={16} /> {t("mission_team")}</div>
          <div className="agent-roster">
            {agents.length === 0 ? <p>{t("no_mission_agents")}</p> : agents.map((agent) => (
              <div className="agent-card" key={agent.id}>
                <strong>{labelize(agent.role_name, language)}</strong>
                <span>{t("reports_to")} {labelize(agent.supervisor_role, language)}</span>
                <p>{agentSummary(agent)}</p>
                <small>{agent.skills.slice(0, 3).join(" · ") || t("mission_context")}</small>
                <details>
                  <summary>{t("authority")}</summary>
                  <p>{agent.decision_authority.slice(0, 3).join("; ") || t("no_authority")}</p>
                  <p>{agent.escalation_triggers.slice(0, 3).join("; ") || t("unclear_risk")}</p>
                </details>
              </div>
            ))}
          </div>
        </div>
        <div>
          <div className="thread-title"><GitBranch size={16} /> {t("delegations")}</div>
          <div className="agent-roster">
            {delegations.length === 0 ? <p>{t("no_delegations")}</p> : delegations.slice(0, 6).map((delegation) => (
              <div className="agent-card" key={delegation.id}>
                <strong>{labelize(delegation.from_role, language)} → {labelize(delegation.to_role, language)}</strong>
                <span>{readableStatus(delegation.status, language)}</span>
                <p>{delegation.title}</p>
                <small>{delegation.success_criteria.slice(0, 2).join(" · ") || t("report_blockers")}</small>
              </div>
            ))}
          </div>
        </div>
        <div>
          <div className="thread-title"><AlertTriangle size={16} /> {t("escalation_rules")}</div>
          <div className="agent-roster">
            {escalations.length === 0 ? organization.standing_orders.slice(0, 4).map((order) => (
              <div className="agent-card" key={order.id}>
                <strong>{labelize(order.scope, language)}</strong>
                <span>{labelize(order.effect, language)}</span>
                <p>{order.instruction}</p>
              </div>
            )) : escalations.slice(0, 6).map((escalation) => (
              <div className="agent-card" key={escalation.id}>
                <strong>{labelize(escalation.from_role, language)} → {labelize(escalation.to_level, language)}</strong>
                <span>{readableStatus(escalation.status, language)}</span>
                <p>{escalation.reason}</p>
                <small>{readableCategory(escalation.category, language)}</small>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function OrgChart({ agents, language, t }: { agents: OrganizationSnapshot["agents"]; language: Language; t: Translator }) {
  const ceoChildren = agents.filter((agent) => normalizeRole(agent.supervisor_role) === "ceo");
  const pmChildren = agents.filter((agent) => normalizeRole(agent.supervisor_role) === "project_manager");
  const otherAgents = agents.filter(
    (agent) => normalizeRole(agent.supervisor_role) !== "ceo" && normalizeRole(agent.supervisor_role) !== "project_manager"
  );
  return (
    <div className="org-chart">
      <div className="org-node chairman">{t("chairman")}</div>
      <div className="org-line" />
      <div className="org-node ceo">CEO</div>
      <div className="org-branches">
        {[...ceoChildren, ...pmChildren, ...otherAgents].slice(0, 8).map((agent) => (
          <div className={`org-node ${normalizeRole(agent.role_name)}`} key={agent.id}>
            {labelize(agent.role_name, language)}
            <span>{normalizeRole(agent.supervisor_role) === "project_manager" ? "PM line" : "CEO line"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Metric({ icon, label, value, tone = "normal" }: { icon: React.ReactNode; label: string; value: number; tone?: "normal" | "risk" }) {
  return (
    <div className={`metric metric-${tone}`}>
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function labelize(value: string, language: Language = "en") {
  const normalized = value.toLowerCase().replaceAll(" ", "_");
  const labels: Record<Language, Record<string, string>> = {
    en: {
      ceo: "CEO",
      project_manager: "Project Manager",
      developer: "Developer",
      reviewer: "Reviewer",
      security_officer: "Security Officer",
      legal_counsel: "Legal Counsel",
      chairman: "Chairman",
      owner: "Owner",
    },
    "zh-TW": {
      ceo: "CEO",
      project_manager: "專案經理",
      developer: "開發者",
      reviewer: "審查者",
      security_officer: "資安主管",
      legal_counsel: "法律顧問",
      chairman: "董事長",
      owner: "擁有者",
    },
  };
  if (labels[language][normalized]) return labels[language][normalized];
  if (labels.en[normalized]) return labels.en[normalized];
  return value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function normalizeRole(value: string) {
  return value.toLowerCase().replaceAll(" ", "_").replaceAll("-", "_");
}

function compactText(value: string, limit: number) {
  const text = value.replace(/\s+/g, " ").trim();
  return text.length > limit ? `${text.slice(0, limit - 1)}...` : text;
}

function shortId(value: string) {
  const match = value.match(/[a-z]+_([a-f0-9]{12})/);
  return match ? `${value.split("_")[0]}_${match[1].slice(0, 6)}` : compactText(value, 24);
}

function readableStatus(value: string, language: Language = "en") {
  const labels: Record<Language, Record<string, string>> = {
    en: {
      planned: "Planned",
      active: "Running",
      resumed: "Running",
      review: "In review",
      reviewing: "In review",
      ready_for_ceo: "Ready for CEO",
      needs_decision: "Needs decision",
      waiting_approval: "Waiting approval",
      paused: "Paused",
      completed: "Completed",
      archived: "Archived",
      failed: "Failed",
      pending: "Pending",
      applied: "Applied",
      skipped: "Skipped",
      assigned: "Assigned",
      done: "Done",
      api: "API",
      unknown: "Unknown",
    },
    "zh-TW": {
      planned: "已規劃",
      active: "進行中",
      resumed: "進行中",
      review: "審查中",
      reviewing: "審查中",
      ready_for_ceo: "等待 CEO 確認",
      needs_decision: "需要決策",
      waiting_approval: "等待核准",
      paused: "已暫停",
      completed: "已完成",
      archived: "已封存",
      failed: "失敗",
      pending: "待處理",
      applied: "已套用",
      skipped: "已略過",
      assigned: "已交辦",
      done: "完成",
      api: "API",
      unknown: "未知",
    },
  };
  return labels[language][value] ?? labels.en[value] ?? labelize(value, language);
}

function readablePriority(value: string, language: Language = "en") {
  const labels: Record<Language, Record<string, string>> = {
    en: { normal: "Normal", high: "High", critical: "Critical" },
    "zh-TW": { normal: "一般", high: "高", critical: "關鍵" },
  };
  return labels[language][value] ?? labels.en[value] ?? labelize(value, language);
}

function readableManager(value: string, language: Language = "en") {
  const labels: Record<Language, Record<string, string>> = {
    en: { praetor_direct: "CEO direct", pm_auto: "PM managed" },
    "zh-TW": { praetor_direct: "CEO 直接管理", pm_auto: "PM 管理" },
  };
  return labels[language][value] ?? labels.en[value] ?? labelize(value, language);
}

function readableCategory(value: string, language: Language = "en") {
  const labels: Record<Language, Record<string, string>> = {
    en: {
      delete_files: "Delete files",
      overwrite_important_files: "Overwrite important files",
      external_communication: "External communication",
      spending_money: "Spending money",
      change_strategy: "Strategy decision",
      shell_commands: "Shell command",
    },
    "zh-TW": {
      delete_files: "刪除檔案",
      overwrite_important_files: "覆寫重要檔案",
      external_communication: "對外溝通",
      spending_money: "花費金錢",
      change_strategy: "策略決策",
      shell_commands: "Shell 指令",
    },
  };
  return labels[language][value] ?? labels.en[value] ?? labelize(value, language);
}

function readableAction(value: string, language: Language = "en") {
  const labels: Record<Language, Record<string, string>> = {
    en: {
      mission_draft: "Mission draft",
      approval_request: "Approval request",
      memory_update: "Memory update",
      briefing: "Briefing",
      staffing_proposal: "Staffing proposal",
      agent_create: "Agent created",
      delegation_create: "Delegation",
      decision_escalation: "Escalation",
      mission_closeout: "Closeout",
      standing_order_update: "Standing order",
    },
    "zh-TW": {
      mission_draft: "任務草稿",
      approval_request: "核准請求",
      memory_update: "記憶更新",
      briefing: "簡報",
      staffing_proposal: "人員編組建議",
      agent_create: "建立 AI",
      delegation_create: "交辦",
      decision_escalation: "升級決策",
      mission_closeout: "任務結案",
      standing_order_update: "常設規則",
    },
  };
  return labels[language][value] ?? labels.en[value] ?? labelize(value, language);
}

function readableEventType(value: string, language: Language = "en") {
  const labels: Record<Language, Record<string, string>> = {
    en: {
      mission: "Mission",
      agent_message: "Agent",
      approval: "Decision",
      delegation: "Delegation",
      escalation: "Escalation",
      team: "Team",
      run: "Run",
      task: "Task",
    },
    "zh-TW": {
      mission: "任務",
      agent_message: "AI",
      approval: "決策",
      delegation: "交辦",
      escalation: "升級",
      team: "團隊",
      run: "執行",
      task: "工作",
    },
  };
  return labels[language][value] ?? labels.en[value] ?? labelize(value, language);
}

function readableEventTitle(event: TimelineEvent) {
  if (event.type === "agent_message") return labelize(event.title);
  if (event.type === "approval") return event.title.replace("Approval: change_strategy", "Approval: Strategy decision");
  if (event.type === "escalation") return event.title.replace("chairman", "Chairman").replace("ceo", "CEO");
  return readableBody(event.title);
}

function agentSummary(agent: OrganizationSnapshot["agents"][number]) {
  const primarySkill = agent.skills[0] ? `Focus: ${agent.skills.slice(0, 2).join(", ")}.` : "";
  const trigger = agent.escalation_triggers[0] ? `Escalates: ${agent.escalation_triggers.slice(0, 2).join(", ")}.` : "";
  return [primarySkill, trigger].filter(Boolean).join(" ") || compactText(agent.charter, 160);
}

function readableBody(value: string) {
  return value
    .replaceAll("praetor_direct", "CEO direct")
    .replaceAll("pm_auto", "PM managed")
    .replace(/mission_[a-f0-9]{12}/g, (match) => shortId(match))
    .replace(/\s+/g, " ")
    .trim();
}

function eventSummary(event: TimelineEvent) {
  const body = readableBody(event.body ?? "");
  if (event.type === "agent_message" && body.includes("Charter:")) {
    return compactText(body.split("Charter:")[0].trim() || body, 160);
  }
  return compactText(body, 190);
}

function agentMessageSummary(message: AgentMessage) {
  const body = readableBody(message.body);
  if (body.includes("Charter:")) {
    const charter = body.split("Charter:")[1] ?? body;
    const responsibility = charter.match(/Responsibilities: ([^.]+)/)?.[1];
    const constraints = charter.match(/Constraints: ([^.]+)/)?.[1];
    return compactText(
      [responsibility ? `Responsibilities: ${responsibility}.` : "", constraints ? `Constraints: ${constraints}.` : ""]
        .filter(Boolean)
        .join(" "),
      220
    );
  }
  return compactText(body, 240);
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

function LoadingState({ message = "Loading Praetor Office..." }: { message?: string }) {
  return (
    <div className="gate">
      <Loader2 className="spin" />
      <p>{message}</p>
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
