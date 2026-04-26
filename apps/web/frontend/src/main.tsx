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
    return <Gate title="Praetor is not initialized" body="Complete onboarding in the existing Praetor setup flow before entering the Office." href="/app/praetor" action="Open onboarding" />;
  }

  if (!session.authenticated) {
    return <Gate title="Owner login required" body="The Office contains company memory, agent activity, and execution status. Sign in as the owner to continue." href="/app/login?next=/office" action="Login" />;
  }

  if (!snapshot) {
    return <LoadingState />;
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
            <button className="rail-toggle" type="button" onClick={() => setRailOpen((value) => !value)} title={railOpen ? "Hide executive rail" : "Show executive rail"}>
              {railOpen ? <PanelRightClose size={17} /> : <PanelRightOpen size={17} />}
              {railOpen ? "Hide rail" : "Show rail"}
            </button>
          </div>
        </header>

        {error ? <div className="error-banner">{error}</div> : null}

        <section className="metric-grid">
          <Metric icon={<AlertTriangle />} label="Needs decision" value={snapshot.approvals.length + pendingEscalations.length} tone={snapshot.approvals.length + pendingEscalations.length > 0 ? "risk" : "normal"} />
          <Metric icon={<CirclePause />} label="Missions at risk" value={atRiskMissions.length} tone={atRiskMissions.length > 0 ? "risk" : "normal"} />
          <Metric icon={<Activity />} label="Running work" value={runningMissions.length} />
          <Metric icon={<CheckCircle2 />} label="Ready or done" value={completedMissions.length} />
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
          <OrganizationPanel organization={snapshot.organization} selectedMissionId={selectedMission?.id ?? null} />
          <MissionRoom
            mission={selectedMission}
            timeline={timeline}
            agentActivity={snapshot.agent_activity}
            agentMessages={agentMessages}
          />
        </section>
      </main>

      {railOpen ? <aside className="executive-rail">
        <RailSection title="Decisions">
          {snapshot.approvals.length === 0 ? <p>No pending approvals.</p> : snapshot.approvals.map((approval) => (
            <div className="rail-item" key={approval.id}>
              <strong>{readableCategory(approval.category)}</strong>
              <span>{approval.reason}</span>
            </div>
          ))}
        </RailSection>
        <RailSection title="Escalations">
          {snapshot.organization.escalations.filter((item) => item.status === "pending").length === 0 ? <p>No pending escalations.</p> : snapshot.organization.escalations.filter((item) => item.status === "pending").slice(0, 6).map((item) => (
            <div className="rail-item action-skipped" key={item.id}>
              <strong>{labelize(item.to_level)}</strong>
              <span>{item.reason}</span>
              <small>{readableCategory(item.category)}</small>
            </div>
          ))}
        </RailSection>
        <RailSection title="CEO actions">
          {visibleActions.length === 0 ? <p>No planner actions yet.</p> : visibleActions.map((action) => (
            <div className={`rail-item action-${action.status}`} key={action.id}>
              <strong>{readableAction(action.type)}</strong>
              <span>{action.title}</span>
              <small>{readableStatus(action.status)}{action.result_id ? ` · ${shortId(action.result_id)}` : ""}</small>
            </div>
          ))}
        </RailSection>
        <RailSection title="Agent activity">
          {snapshot.agent_activity.slice(0, 8).map((event) => (
            <div className="rail-item" key={event.id}>
              <strong>{labelize(event.actor)}</strong>
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
            <small>{readablePriority(mission.priority)} · {readableManager(mission.manager_layer)}</small>
            <em>{readableStatus(mission.status)}</em>
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
              <div><dt>Status</dt><dd>{readableStatus(mission.status)}</dd></div>
              <div><dt>Priority</dt><dd>{readablePriority(mission.priority)}</dd></div>
              <div><dt>PM</dt><dd>{mission.pm_required ? "Required" : "Direct"}</dd></div>
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
                      <span className={`event-type event-${event.type}`}>{readableEventType(event.type)} · {labelize(event.actor)}</span>
                      <strong>{readableEventTitle(event)}</strong>
                      {event.body ? <p>{eventSummary(event)}</p> : null}
                      {event.status ? <em>{readableStatus(event.status)}</em> : null}
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
                    <strong>{labelize(message.role)}</strong>
                    <p>{agentMessageSummary(message)}</p>
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

function OrganizationPanel({ organization, selectedMissionId }: {
  organization: OrganizationSnapshot;
  selectedMissionId: string | null;
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
          <p className="eyebrow">AI organization</p>
          <h2>編組、交辦、升級</h2>
        </div>
        <UsersRound />
      </div>
      <div className="org-grid">
        <div>
          <div className="thread-title"><UsersRound size={16} /> Org chart</div>
          <OrgChart agents={agents} />
          <div className="thread-title compact-title"><UsersRound size={16} /> Mission team</div>
          <div className="agent-roster">
            {agents.length === 0 ? <p>No mission agents yet.</p> : agents.map((agent) => (
              <div className="agent-card" key={agent.id}>
                <strong>{agent.role_name}</strong>
                <span>Reports to {labelize(agent.supervisor_role)}</span>
                <p>{agentSummary(agent)}</p>
                <small>{agent.skills.slice(0, 3).join(" · ") || "mission context"}</small>
                <details>
                  <summary>Authority and escalation</summary>
                  <p>{agent.decision_authority.slice(0, 3).join("; ") || "No special decision authority."}</p>
                  <p>{agent.escalation_triggers.slice(0, 3).join("; ") || "Escalate unclear scope or risk."}</p>
                </details>
              </div>
            ))}
          </div>
        </div>
        <div>
          <div className="thread-title"><GitBranch size={16} /> Delegations</div>
          <div className="agent-roster">
            {delegations.length === 0 ? <p>No delegations yet.</p> : delegations.slice(0, 6).map((delegation) => (
              <div className="agent-card" key={delegation.id}>
                <strong>{labelize(delegation.from_role)} → {delegation.to_role}</strong>
                <span>{readableStatus(delegation.status)}</span>
                <p>{delegation.title}</p>
                <small>{delegation.success_criteria.slice(0, 2).join(" · ") || "report blockers and completion"}</small>
              </div>
            ))}
          </div>
        </div>
        <div>
          <div className="thread-title"><AlertTriangle size={16} /> Escalation rules</div>
          <div className="agent-roster">
            {escalations.length === 0 ? organization.standing_orders.slice(0, 4).map((order) => (
              <div className="agent-card" key={order.id}>
                <strong>{labelize(order.scope)}</strong>
                <span>{labelize(order.effect)}</span>
                <p>{order.instruction}</p>
              </div>
            )) : escalations.slice(0, 6).map((escalation) => (
              <div className="agent-card" key={escalation.id}>
                <strong>{labelize(escalation.from_role)} → {labelize(escalation.to_level)}</strong>
                <span>{readableStatus(escalation.status)}</span>
                <p>{escalation.reason}</p>
                <small>{readableCategory(escalation.category)}</small>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function OrgChart({ agents }: { agents: OrganizationSnapshot["agents"] }) {
  const ceoChildren = agents.filter((agent) => normalizeRole(agent.supervisor_role) === "ceo");
  const pmChildren = agents.filter((agent) => normalizeRole(agent.supervisor_role) === "project_manager");
  const otherAgents = agents.filter(
    (agent) => normalizeRole(agent.supervisor_role) !== "ceo" && normalizeRole(agent.supervisor_role) !== "project_manager"
  );
  return (
    <div className="org-chart">
      <div className="org-node chairman">Chairman</div>
      <div className="org-line" />
      <div className="org-node ceo">CEO</div>
      <div className="org-branches">
        {[...ceoChildren, ...pmChildren, ...otherAgents].slice(0, 8).map((agent) => (
          <div className={`org-node ${normalizeRole(agent.role_name)}`} key={agent.id}>
            {agent.role_name}
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

function labelize(value: string) {
  const normalized = value.toLowerCase().replaceAll(" ", "_");
  const labels: Record<string, string> = {
    ceo: "CEO",
    project_manager: "Project Manager",
    developer: "Developer",
    reviewer: "Reviewer",
    security_officer: "Security Officer",
    legal_counsel: "Legal Counsel",
    chairman: "Chairman",
    owner: "Owner",
  };
  if (labels[normalized]) return labels[normalized];
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

function readableStatus(value: string) {
  const labels: Record<string, string> = {
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
  };
  return labels[value] ?? labelize(value);
}

function readablePriority(value: string) {
  const labels: Record<string, string> = { normal: "Normal", high: "High", critical: "Critical" };
  return labels[value] ?? labelize(value);
}

function readableManager(value: string) {
  const labels: Record<string, string> = { praetor_direct: "CEO direct", pm_auto: "PM managed" };
  return labels[value] ?? labelize(value);
}

function readableCategory(value: string) {
  const labels: Record<string, string> = {
    delete_files: "Delete files",
    overwrite_important_files: "Overwrite important files",
    external_communication: "External communication",
    spending_money: "Spending money",
    change_strategy: "Strategy decision",
    shell_commands: "Shell command",
  };
  return labels[value] ?? labelize(value);
}

function readableAction(value: string) {
  const labels: Record<string, string> = {
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
  };
  return labels[value] ?? labelize(value);
}

function readableEventType(value: string) {
  const labels: Record<string, string> = {
    mission: "Mission",
    agent_message: "Agent",
    approval: "Decision",
    delegation: "Delegation",
    escalation: "Escalation",
    team: "Team",
    run: "Run",
    task: "Task",
  };
  return labels[value] ?? labelize(value);
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
