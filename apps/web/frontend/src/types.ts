export type Mission = {
  id: string;
  title: string;
  summary?: string | null;
  status: string;
  priority: string;
  domains: string[];
  manager_layer: string;
  pm_required: boolean;
  complexity_score: number;
  updated_at: string;
};

export type Approval = {
  id: string;
  category: string;
  mission_id: string;
  raised_by: string;
  reason: string;
  status: string;
  created_at: string;
};

export type ConversationMessage = {
  id: string;
  thread_id: string;
  role: "chairman" | "ceo" | "system";
  body: string;
  created_at: string;
  related_mission_id?: string | null;
};

export type TimelineEvent = {
  id: string;
  mission_id?: string | null;
  type: string;
  title: string;
  body?: string | null;
  actor: string;
  status?: string | null;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type AgentMessage = {
  id: string;
  mission_id: string;
  role: string;
  body: string;
  created_at: string;
  task_id?: string | null;
  run_id?: string | null;
};

export type PlannerAction = {
  id: string;
  type: "mission_draft" | "approval_request" | "memory_update" | "briefing" | "staffing_proposal" | "agent_create" | "delegation_create" | "decision_escalation" | "mission_closeout" | "standing_order_update";
  status: "proposed" | "applied" | "skipped";
  title: string;
  body?: string | null;
  mission_id?: string | null;
  result_id?: string | null;
  metadata: Record<string, unknown>;
};

export type AgentInstance = {
  id: string;
  role_name: string;
  display_name: string;
  mission_id?: string | null;
  supervisor_role: string;
  status: string;
  charter: string;
  skills: string[];
  decision_authority: string[];
  escalation_triggers: string[];
};

export type MissionTeam = {
  id: string;
  mission_id: string;
  name: string;
  lead_agent_id?: string | null;
  member_agent_ids: string[];
  status: string;
};

export type DelegationRecord = {
  id: string;
  mission_id: string;
  from_role: string;
  to_role: string;
  title: string;
  instructions: string;
  success_criteria: string[];
  constraints: string[];
  status: string;
};

export type EscalationRecord = {
  id: string;
  mission_id?: string | null;
  from_role: string;
  to_level: string;
  category: string;
  reason: string;
  status: string;
};

export type StandingOrder = {
  id: string;
  scope: string;
  instruction: string;
  effect: string;
};

export type OrganizationSnapshot = {
  agents: AgentInstance[];
  teams: MissionTeam[];
  delegations: DelegationRecord[];
  escalations: EscalationRecord[];
  standing_orders: StandingOrder[];
};

export type ConversationResult = {
  messages: ConversationMessage[];
  created_mission?: Mission | null;
  created_approval?: Approval | null;
  agent_messages: AgentMessage[];
  actions: PlannerAction[];
  intent: string;
};

export type OfficeSnapshot = {
  briefing: {
    active_missions: number;
    paused_missions: number;
    approvals_pending: number;
    recent_missions: Mission[];
  };
  missions: Mission[];
  approvals: Approval[];
  recent_runs: Array<Record<string, unknown>>;
  audit_events: Array<Record<string, unknown>>;
  ceo_thread: ConversationMessage[];
  agent_activity: TimelineEvent[];
  recent_planner_actions: PlannerAction[];
  runtime_health: Record<string, unknown>;
  organization: OrganizationSnapshot;
};

export type Session = {
  initialized: boolean;
  authenticated: boolean;
  owner_name?: string | null;
  csrf_token: string;
};

export type ApiEnvelope<T> = {
  ok: boolean;
  data: T;
  error?: { code: string; message: string } | null;
};
