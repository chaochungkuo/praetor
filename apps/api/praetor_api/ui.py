from __future__ import annotations

from datetime import datetime
from typing import Any
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import (
    ANTHROPIC_STATE_SECRET,
    OPENAI_STATE_SECRET,
    TELEGRAM_BOT_TOKEN_STATE_SECRET,
    TELEGRAM_WEBHOOK_SECRET_STATE_SECRET,
    get_anthropic_api_key,
    get_bridge_base_url,
    get_openai_api_key,
    get_telegram_bot_token,
    get_telegram_webhook_secret,
    write_state_secret,
)
from .models import (
    ApprovalCreateRequest,
    ConversationCreateRequest,
    LoginRequest,
    MissionContinueRequest,
    MissionCreateRequest,
    MissionPauseRequest,
    MissionStopRequest,
    OnboardingAnswers,
    RuntimeSelection,
)
from .security import csrf_token, login_rate_limiter, require_csrf, require_setup_token


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
WEB_DIST_DIR = BASE_DIR.parents[1] / "web" / "dist"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(include_in_schema=False)

UI_COOKIE_NAME = "praetor_ui_lang"
SUPPORTED_LANGUAGES = {
    "en": "English",
    "zh-TW": "中文（繁體）",
}
TRANSLATIONS = {
    "en": {
        "nav_praetor": "Praetor",
        "nav_inbox": "Inbox",
        "nav_overview": "Overview",
        "nav_tasks": "Tasks",
        "nav_agents": "Agents",
        "nav_activity": "Activity",
        "nav_memory": "Memory",
        "nav_decisions": "Decisions",
        "nav_models": "Models & API",
        "nav_meetings": "Meetings",
        "nav_settings": "Settings",
        "brand_tag": "Run your company with an AI CEO",
        "founder_command_center": "Founder command center",
        "runtime_ready": "Runtime ready",
        "runtime_not_configured": "Runtime not configured",
        "login": "Login",
        "logout": "Logout",
        "owner": "Owner",
        "executive_rail": "Executive Rail",
        "active_missions": "Active missions",
        "paused_missions": "Paused missions",
        "approvals_pending": "Approvals pending",
        "complete_onboarding_notice": "Complete onboarding to activate company controls.",
        "pending_approvals": "Pending approvals",
        "no_pending_approvals": "No pending approvals.",
        "approve": "Approve",
        "reject": "Reject",
        "runtime": "Runtime",
        "telegram": "Telegram",
        "telegram_settings": "Telegram CEO access",
        "telegram_settings_desc": "Connect a Telegram bot as an owner-only mobile channel for CEO chat, briefings, and approval notifications.",
        "telegram_enabled": "Enable Telegram integration",
        "telegram_bot_token": "Bot token",
        "telegram_bot_token_help": "Create a bot with @BotFather and paste the token here. Praetor stores it as a local private secret file.",
        "telegram_webhook_secret": "Webhook secret",
        "telegram_webhook_secret_help": "Use a long random value. Telegram sends it in X-Telegram-Bot-Api-Secret-Token so Praetor can reject forged webhooks.",
        "telegram_allowed_user_id": "Allowed Telegram user ID",
        "telegram_allowed_user_id_help": "Optional but recommended. Get it from @userinfobot, then only this account can link and control Praetor.",
        "telegram_notify_approvals": "Send approval notifications",
        "telegram_allow_low_risk_approval": "Allow low-risk approve/reject buttons",
        "telegram_save_settings": "Save Telegram settings",
        "telegram_create_pairing_code": "Create pairing code",
        "telegram_pairing_code": "Pairing code",
        "telegram_pairing_help": "Send /link CODE to your Telegram bot within 15 minutes. Example: /link ABCD1234",
        "telegram_webhook_url": "Webhook URL",
        "telegram_setup_steps": "Configuration steps",
        "telegram_setup_step_1": "1. Create a bot in Telegram with @BotFather.",
        "telegram_setup_step_2": "2. Paste the bot token and a webhook secret here, then save.",
        "telegram_setup_step_3": "3. Expose Praetor over HTTPS and set the Telegram webhook to the URL below.",
        "telegram_setup_step_4": "4. Create a pairing code and send /link CODE to the bot from your Telegram account.",
        "telegram_linked": "Linked",
        "telegram_not_linked": "Not linked",
        "telegram_settings_saved": "Telegram settings saved.",
        "telegram_pairing_created": "Telegram pairing code created.",
        "praetor_briefing_title": "Praetor briefing",
        "praetor_briefing_desc": "Talk to the CEO first. Praetor can turn the conversation into missions, approvals, memory, or staffing plans when needed.",
        "ceo_chat": "Chat with CEO",
        "ceo_chat_desc": "Use this as the chairman's instruction channel. For the full office view with mission telemetry and voice input, open the Chairman's Office.",
        "message_to_ceo": "Message to CEO",
        "message_to_ceo_placeholder": "Tell the CEO what you want to understand, decide, remember, or turn into a mission.",
        "send_to_ceo": "Send to CEO",
        "sending_to_ceo": "Sending...",
        "open_chairman_office": "Open Chairman's Office",
        "recent_ceo_conversation": "Recent CEO conversation",
        "no_ceo_messages": "No CEO conversation yet.",
        "ceo_message_sent": "CEO replied.",
        "ceo_chat_hint": "Praetor may create a mission draft, approval request, memory update, or staffing proposal from this message.",
        "suggested_first_tasks": "Suggested first tasks",
        "create_starter_mission": "Create starter mission",
        "starter_create_project_title": "Create first project",
        "starter_create_project_summary": "Set up a first project workspace and initial status files.",
        "starter_build_wiki_title": "Build company wiki",
        "starter_build_wiki_summary": "Summarize the current company operating context into wiki pages.",
        "starter_review_inbox_title": "Review inbox",
        "starter_review_inbox_summary": "Review the Inbox folder and prepare a concise summary.",
        "no_missions_create_from_ceo": "No missions yet. Ask the CEO what to start first.",
        "runtime_settings": "Runtime settings",
        "runtime_settings_desc": "Choose the model runtime Praetor should use. API keys are stored locally as private secret files and are never displayed after saving.",
        "runtime_settings_saved": "Runtime settings saved.",
        "model_connection_center": "Model and API connection",
        "model_connection_desc": "Connect Praetor to the AI provider it should use for CEO planning and mission execution. You can start without a key and add it later.",
        "connection_step_title": "Connect your AI provider",
        "connection_step_help": "Choose a provider now, or leave the key blank and connect it later. OpenAI-compatible gateways are available under Advanced.",
        "workspace_step_help": "Example: ~/praetor-workspace. Praetor will create Projects, Wiki, Decisions, and Missions folders inside this workspace.",
        "governance_step_help": "Balanced mode is recommended: Praetor can organize low-risk work, but asks before deleting files, spending money, sending external messages, or changing strategy.",
        "skip_api_key": "You can leave this blank and add it later from Models.",
        "api_key": "API key",
        "api_key_placeholder": "Leave blank to keep the existing key",
        "api_key_help": "Paste a provider key only in this browser form. Praetor stores it under the local state directory with private file permissions.",
        "provider_key": "Provider key",
        "configured": "configured",
        "missing": "missing",
        "save_runtime_settings": "Save runtime settings",
        "test_api_connection": "Test connection",
        "testing_connection": "Testing...",
        "api_connection_ok": "Connection verified. Praetor can reach the selected model provider.",
        "api_connection_failed": "Connection test failed. Check the provider, model, key, and base URL.",
        "runtime_auth_error": "The model provider rejected the API key. Check the key in Models & API, then test the connection again.",
        "runtime_network_error": "Praetor could not reach the model provider. Check the Base URL and your network connection.",
        "runtime_not_found_error": "The model provider did not recognize this endpoint or model. Check the Base URL and model name.",
        "bridge_url": "Bridge URL",
        "mode": "Mode",
        "principles": "Principles",
        "principles_notice": "Praetor will derive company DNA during onboarding.",
        "owner_login": "Owner login",
        "owner_login_desc": "Praetor protects the company workspace behind the owner account. Sign in to continue.",
        "password": "Password",
        "welcome_title": "Welcome to Praetor",
        "welcome_desc": "Choose your language first. Then either initialize the company or sign in as the returning owner.",
        "first_time_setup": "First-time setup",
        "continue_setup": "Continue setup",
        "returning_owner": "Returning owner login",
        "company_not_initialized": "This company is not initialized yet. Start with first-time setup.",
        "language_switch": "Language",
        "start_onboarding": "Start onboarding",
        "go_to_login": "Go to login",
        "back_to_welcome": "Back to welcome",
        "onboarding_meeting": "Praetor onboarding meeting",
        "onboarding_desc": "Praetor will help define your company step by step. You answer as the founder. Praetor translates that into company DNA, governance, roles, and runtime configuration.",
        "founder_to_praetor": "Founder to Praetor",
        "wizard_desc": "Praetor will ask practical operating questions, then derive the company style instead of making you choose technical labels.",
        "steps": "steps",
        "owner_name": "Owner name",
        "owner_email": "Owner email",
        "owner_password": "Owner password",
        "confirm_password": "Confirm password",
        "company_language": "Company language",
        "leadership": "Leadership",
        "decision_style": "Decision style",
        "organization_style": "Organization style",
        "autonomy": "Autonomy",
        "risk_priority": "Risk priority",
        "work_style_questions": "Operating questions",
        "work_style_questions_help": "Answer by real situations. Praetor will infer leadership, decision style, autonomy, organization style, and risk priority.",
        "q_interrupt": "When should Praetor interrupt you?",
        "q_interrupt_hands_on": "Before most meaningful decisions.",
        "q_interrupt_strategic": "Only at clear checkpoints and material tradeoffs.",
        "q_interrupt_delegator": "Rarely; move low-risk work forward and report crisply.",
        "q_direction": "If the AI thinks the task direction may be wrong, what should happen?",
        "q_direction_careful": "Stop and ask before changing course.",
        "q_direction_balanced": "Present options and a recommendation.",
        "q_direction_fast": "Fix low-risk direction issues and report afterward.",
        "q_team": "How should the AI company organize work?",
        "q_team_lean": "Keep it small unless a task clearly needs more roles.",
        "q_team_structured": "Use PM, Developer, Reviewer, and risk roles by default.",
        "q_team_flexible": "Form teams dynamically based on task complexity.",
        "q_autonomy": "How much can AI agents do without approval?",
        "q_autonomy_strict": "Draft and recommend only.",
        "q_autonomy_hybrid": "Execute low-risk work; ask for sensitive actions.",
        "q_autonomy_autonomous": "Move autonomously within written boundaries.",
        "q_risk": "Which failure worries you most?",
        "q_risk_wrong": "Wrong decisions.",
        "q_risk_slow": "Moving too slowly.",
        "q_risk_memory": "Losing important context.",
        "q_risk_approval": "Acting without approval.",
        "derived_settings": "Derived operating model",
        "plain_summary": "Plain-language operating summary",
        "plain_summary_default": "Praetor will preserve chairman control for sensitive choices while allowing low-risk execution inside the approved workspace.",
        "technical_summary": "Technical mapping",
        "advanced_provider": "Advanced provider settings",
        "base_url": "Base URL",
        "base_url_help": "For OpenAI-compatible gateways such as LiteLLM, OpenRouter, LM Studio, vLLM, or a company proxy. Leave blank for the provider default.",
        "openai_compatible_notice": "OpenAI-compatible means the API format is compatible; your data goes to the base URL you configure.",
        "workspace_root": "Workspace root",
        "runtime_mode": "Runtime mode",
        "provider": "Provider",
        "model": "Model",
        "executor": "Executor",
        "always_require_approval": "Always require approval",
        "wizard_next": "Next",
        "wizard_back": "Back",
        "wizard_submit": "Initialize Praetor",
        "praetor_recommendation": "Praetor recommendation",
        "step1_prompt": "First, tell me who owns this company and how I should address its working language.",
        "step2_prompt": "I will ask practical questions and infer your company operating style from the answers.",
        "step3_prompt": "Where should this company work? I will only read and write inside the approved workspace.",
        "step4_prompt": "Choose how this company should think and execute: API models, your existing subscription tools, or local models.",
        "step5_prompt": "Define the boundaries that always require your approval. These become the core governance rules for your AI company.",
        "step6_prompt": "I derived the operating model below. Review it in plain language, then initialize Praetor.",
        "summary_language": "Language",
        "summary_leadership": "Leadership",
        "summary_decision_style": "Decision style",
        "summary_organization": "Organization",
        "summary_autonomy": "Autonomy",
        "summary_runtime": "Runtime",
        "summary_provider": "Provider",
        "summary_executor": "Executor",
        "founder_statement": "I want a company where AI agents can manage other AI agents with clear goals, responsibilities, and authority.",
        "praetor_statement": "I will translate your answers into company DNA, role boundaries, approval rules, and a runtime that can safely delegate work downward while escalating decisions upward.",
        "founder_label": "Founder",
        "opt_strategic": "Strategic",
        "opt_hands_on": "Hands-on",
        "opt_delegator": "Delegator",
        "opt_balanced": "Balanced",
        "opt_careful": "Careful",
        "opt_fast": "Fast",
        "opt_lean": "Lean",
        "opt_structured": "Structured",
        "opt_flexible": "Flexible",
        "opt_hybrid": "Hybrid",
        "opt_strict": "Strict",
        "opt_autonomous": "Autonomous",
        "opt_api": "API",
        "opt_subscription_executor": "Subscription executor",
        "opt_local_model": "Local model",
        "opt_openai_compatible": "OpenAI-compatible",
        "principle_1": "Execution flows downward.",
        "principle_2": "Decisions escalate upward.",
        "principle_3": "Memory belongs to the company, not individual agents.",
        "principle_4": "Praetor manages roles and hierarchy, not equal-agent debate.",
        "page_praetor": "Praetor",
        "page_overview": "Overview",
        "page_inbox": "Inbox",
        "page_tasks": "Tasks",
        "page_agents": "Agents",
        "page_activity": "Activity",
        "page_settings": "Settings",
        "page_memory": "Memory",
        "page_decisions": "Decisions",
        "page_models": "Models & API",
        "page_meetings": "Meetings",
        "page_mobile": "Mobile Briefing",
        "active": "Active",
        "paused": "Paused",
        "approvals": "Approvals",
        "total_missions": "Total missions",
        "status_breakdown": "Status breakdown",
        "recent_missions": "Recent missions",
        "recent_audit_events": "Recent audit events",
        "chairman_inbox": "Chairman Inbox",
        "chairman_inbox_desc": "Everything that needs owner attention: approvals, blocked work, runtime risk, and completed missions waiting for review.",
        "governance_review": "Governance review",
        "governance_review_desc": "A quiet company review that only raises formal issues requiring attention.",
        "run_governance_review": "Run review",
        "review_summary": "Review summary",
        "next_review": "Next review",
        "formal_items": "Formal items",
        "needs_attention": "Needs attention",
        "pending_decisions": "Pending decisions",
        "blocked_work": "Blocked work",
        "risk_signals": "Risk signals",
        "completed_for_review": "Completed for review",
        "runtime_watch": "Runtime watch",
        "all_clear": "All clear.",
        "open_mission": "Open mission",
        "review_item": "Review item",
        "agent_directory": "Agent Directory",
        "agent_directory_desc": "The AI organization: roles, active workers, skills, authority, supervisors, and recent internal activity.",
        "role_charter": "Role charter",
        "active_agents": "Active agents",
        "recent_agent_activity": "Recent agent activity",
        "skills": "Skills",
        "authority": "Authority",
        "supervisor": "Supervisor",
        "instances": "Instances",
        "constraints": "Constraints",
        "escalates_on": "Escalates on",
        "no_active_agents": "No active agents yet.",
        "no_agent_activity": "No agent activity yet.",
        "team_operating_model": "Team operating model",
        "mission_board": "Mission board",
        "mission": "Mission",
        "status": "Status",
        "priority": "Priority",
        "domains": "Domains",
        "updated": "Updated",
        "run": "Run",
        "activity_recent_runs": "Recent execution runs",
        "audit_stream": "Audit stream",
        "audit_trail": "Audit trail",
        "event_detail": "Event detail",
        "event_recorded": "Event recorded.",
        "mission_related_event": "Mission-related event.",
        "technical_details": "Technical details",
        "decision_items": "Decision items",
        "open": "Open",
        "company_memory": "Company memory",
        "company_memory_desc": "Shared wiki pages and the retrieval context Praetor can use during missions.",
        "wiki_pages": "Wiki pages",
        "recent_retrieval_previews": "Recent retrieval previews",
        "runtime_health": "Runtime health",
        "usage_by_executor": "Usage by executor",
        "executor": "Executor",
        "runs": "Runs",
        "input": "Input",
        "output": "Output",
        "cost": "Cost",
        "recent_runs": "Recent runs",
        "structured_meetings": "Structured meetings",
        "structured_meetings_desc": "Meeting summaries are generated from mission state, task logs, and execution records.",
        "today": "Today",
        "mission_briefing": "Mission briefing",
        "mobile_briefing_title": "Mobile briefing",
        "quick_links": "Quick links",
        "owner": "Owner",
        "name": "Name",
        "email": "Email",
        "language": "Language",
        "workspace": "Workspace",
        "root": "Root",
        "allow_read": "Allow read",
        "allow_write": "Allow write",
        "deny_write": "Deny write",
        "governance": "Governance",
        "autonomy": "Autonomy",
        "require_approval": "Require approval",
        "auto_execute": "Auto execute",
        "never_allow": "Never allow",
        "roles": "Roles",
        "executor_health": "Executor health",
        "configured": "Configured",
        "healthy": "Healthy",
        "error": "Error",
        "bridge_url": "Bridge URL",
        "none": "none",
        "not_available": "n/a",
        "no_missions_yet": "No missions yet.",
        "no_missions_available": "No missions available.",
        "no_recent_missions": "Praetor has not started any missions yet.",
        "no_audit_events": "No audit events yet.",
        "no_audit_events_recorded": "No audit events recorded yet.",
        "no_execution_runs": "No execution runs recorded yet.",
        "no_usage_records": "No usage records yet.",
        "no_runs_recorded": "No runs recorded yet.",
        "no_wiki_pages": "No wiki pages found.",
        "no_retrieval_preview": "No retrieval preview recorded.",
        "no_executors": "No executors reported by the bridge.",
        "no_runs_yet": "No runs yet.",
        "no_meetings": "No meetings have been generated yet.",
        "no_structured_decisions": "No structured decisions recorded yet.",
        "no_approvals_waiting": "No approvals waiting.",
        "no_summary_yet": "No summary yet.",
        "no_changed_files": "No changed files recorded.",
        "auto": "auto",
        "manual": "manual",
        "enabled": "enabled",
        "disabled": "disabled",
        "yes": "yes",
        "no": "no",
        "run_mission": "Run mission",
        "pause_mission": "Pause",
        "continue_mission": "Continue",
        "stop_mission": "Stop",
        "create_review": "Create review",
        "chairman_view": "Chairman view",
        "more_actions": "More actions",
        "next_decision": "Next decision",
        "owner_decision_needed_desc": "Praetor needs owner judgment before the mission can close cleanly.",
        "no_owner_decision_needed": "No owner decision needed",
        "no_owner_decision_needed_desc": "Praetor can continue within the current mission boundaries.",
        "workspace_health": "Workspace health",
        "healthy": "Healthy",
        "needs_review": "Needs review",
        "review_items": "Review items",
        "files_scanned": "Files scanned",
        "company_context": "Company context",
        "documents_and_memory": "Documents and memory",
        "ai_operations": "AI operations",
        "technical_appendix": "Technical appendix",
        "raw_files": "Raw files",
        "summary": "Summary",
        "manager_layer": "Manager",
        "complexity_score": "Complexity",
        "pm_required": "PM required",
        "escalation_reason": "Escalation reason",
        "requested_outputs": "Requested outputs",
        "task_logs": "Tasks",
        "no_task_logs": "No task logs yet.",
        "work_sessions": "AI work sessions",
        "no_work_sessions": "No AI work sessions yet.",
        "session_turns": "Turns",
        "current_blocker": "Current blocker",
        "completion_contract": "Completion contract",
        "run_attempts": "Run attempts",
        "workspace_scope": "Workspace scope",
        "workflow_contract": "Workflow contract",
        "workspace_steward": "Workspace Steward",
        "workspace_steward_desc": "Praetor registers files by stable IDs so folders can be reorganized without losing document references.",
        "file_assets": "File assets",
        "restructure_plans": "Restructure plans",
        "create_restructure_plan": "Create restructure plan",
        "reconcile_workspace": "Reconcile workspace",
        "reconciliation_reports": "Reconciliation reports",
        "no_file_assets": "No file assets registered yet.",
        "allowed_write": "Allowed write",
        "denied_write": "Denied write",
        "last_event": "Last event",
        "tokens": "Tokens",
        "no_run_attempts": "No run attempts yet.",
        "knowledge_workspace": "Knowledge workspace",
        "client_record": "Client record",
        "matter_record": "Matter record",
        "document_registry": "Document registry",
        "document_versions": "Versions",
        "matter_decisions": "Matter decisions",
        "open_questions": "Open questions",
        "knowledge_updates": "Knowledge updates",
        "board_briefing": "Board briefing",
        "board_briefing_desc": "A PM-led planning team turns the mission into an owner-visible briefing before execution.",
        "create_board_briefing": "Prepare board briefing",
        "no_board_briefing": "No board briefing yet.",
        "recommendations": "Recommendations",
        "assumptions": "Assumptions",
        "risks": "Risks",
        "decisions_needed": "Decisions needed",
        "memory_promotion": "Memory promotion",
        "memory_promotion_desc": "Raw discussion stays as evidence. Only reviewed conclusions become durable company knowledge.",
        "create_memory_promotion": "Create promotion review",
        "promotion_findings": "Findings",
        "no_memory_promotion": "No memory promotion review yet.",
        "no_documents_registered": "No documents registered yet.",
        "no_matter_decisions": "No matter decisions yet.",
        "no_open_questions": "No open questions.",
        "no_knowledge_updates": "No proposed knowledge updates.",
        "folder": "Folder",
        "current_version": "Current version",
        "reason": "Reason",
        "report": "Report",
        "run_budget": "Run budget",
        "max_steps": "Max steps",
        "max_tokens": "Max tokens",
        "max_time_minutes": "Max time minutes",
        "max_cost_eur": "Max cost EUR",
        "latest_run_usage": "Latest run usage",
        "execution_runs": "Execution runs",
        "changed_files": "Changed files",
        "input_tokens": "Input tokens",
        "output_tokens": "Output tokens",
        "stop_reason": "Stop reason",
        "request_approval_checkpoint": "Request approval checkpoint",
        "category": "Category",
        "reason": "Reason",
        "create_approval": "Create approval",
        "manual_checkpoint_reason": "Manual checkpoint requested by owner.",
        "status_file": "Status file",
        "pm_report": "PM report",
        "tasks_file": "Tasks file",
        "mission_run_completed": "Mission run completed.",
        "mission_paused": "Mission paused.",
        "mission_resumed": "Mission resumed.",
        "mission_stopped": "Mission stopped.",
    },
    "zh-TW": {
        "nav_praetor": "Praetor",
        "nav_inbox": "收件匣",
        "nav_overview": "總覽",
        "nav_tasks": "任務",
        "nav_agents": "AI 組織",
        "nav_activity": "動態",
        "nav_memory": "記憶",
        "nav_decisions": "決策",
        "nav_models": "模型與 API",
        "nav_meetings": "會議",
        "nav_settings": "設定",
        "brand_tag": "用 AI CEO 經營你的公司",
        "founder_command_center": "創辦人控制台",
        "runtime_ready": "執行環境已就緒",
        "runtime_not_configured": "執行環境尚未設定",
        "login": "登入",
        "logout": "登出",
        "owner": "擁有者",
        "executive_rail": "董事長欄",
        "active_missions": "進行中任務",
        "paused_missions": "暫停任務",
        "approvals_pending": "待核准事項",
        "complete_onboarding_notice": "完成初始化後即可啟動公司控制台。",
        "pending_approvals": "待核准事項",
        "no_pending_approvals": "目前沒有待核准事項。",
        "approve": "批准",
        "reject": "拒絕",
        "runtime": "執行環境",
        "telegram": "Telegram",
        "telegram_settings": "Telegram CEO 入口",
        "telegram_settings_desc": "把 Telegram bot 連成只有擁有者可用的手機通道，用來和 CEO 對話、看簡報、收 approval 通知。",
        "telegram_enabled": "啟用 Telegram integration",
        "telegram_bot_token": "Bot token",
        "telegram_bot_token_help": "先用 @BotFather 建立 bot，再把 token 貼在這裡。Praetor 會用本機私密檔案保存。",
        "telegram_webhook_secret": "Webhook secret",
        "telegram_webhook_secret_help": "請使用夠長的隨機值。Telegram 會用 X-Telegram-Bot-Api-Secret-Token 傳給 Praetor，避免偽造 webhook。",
        "telegram_allowed_user_id": "允許的 Telegram user ID",
        "telegram_allowed_user_id_help": "選填但建議填。可用 @userinfobot 查詢；填了之後只有這個帳號能綁定與控制 Praetor。",
        "telegram_notify_approvals": "傳送 approval 通知",
        "telegram_allow_low_risk_approval": "允許低風險 approve/reject 按鈕",
        "telegram_save_settings": "儲存 Telegram 設定",
        "telegram_create_pairing_code": "產生配對碼",
        "telegram_pairing_code": "配對碼",
        "telegram_pairing_help": "15 分鐘內把 /link CODE 傳給你的 Telegram bot。例如：/link ABCD1234",
        "telegram_webhook_url": "Webhook URL",
        "telegram_setup_steps": "設定步驟",
        "telegram_setup_step_1": "1. 在 Telegram 用 @BotFather 建立 bot。",
        "telegram_setup_step_2": "2. 把 bot token 和 webhook secret 填到這裡並儲存。",
        "telegram_setup_step_3": "3. 用 HTTPS 對外開放 Praetor，並把 Telegram webhook 設到下面的 URL。",
        "telegram_setup_step_4": "4. 產生配對碼，從你的 Telegram 帳號傳 /link CODE 給 bot。",
        "telegram_linked": "已綁定",
        "telegram_not_linked": "尚未綁定",
        "telegram_settings_saved": "Telegram 設定已儲存。",
        "telegram_pairing_created": "Telegram 配對碼已產生。",
        "praetor_briefing_title": "Praetor 簡報",
        "praetor_briefing_desc": "先跟 CEO 對話。Praetor 會在需要時把對話轉成任務、批准請求、公司記憶或 AI 編組計畫。",
        "ceo_chat": "與 CEO 對話",
        "ceo_chat_desc": "這裡是董事長的指令通道。若要看完整辦公室、任務遙測與語音輸入，請進入董事長辦公室。",
        "message_to_ceo": "給 CEO 的訊息",
        "message_to_ceo_placeholder": "告訴 CEO 你想了解、決定、記住，或轉成任務的事情。",
        "send_to_ceo": "送給 CEO",
        "sending_to_ceo": "傳送中...",
        "open_chairman_office": "進入董事長辦公室",
        "recent_ceo_conversation": "最近 CEO 對話",
        "no_ceo_messages": "目前尚無 CEO 對話。",
        "ceo_message_sent": "CEO 已回覆。",
        "ceo_chat_hint": "Praetor 可能會從這段訊息建立任務草稿、核准請求、記憶更新或 AI 編組建議。",
        "suggested_first_tasks": "建議的第一批任務",
        "create_starter_mission": "建立起始任務",
        "starter_create_project_title": "建立第一個專案",
        "starter_create_project_summary": "建立第一個專案工作區與初始狀態檔。",
        "starter_build_wiki_title": "建立公司 Wiki",
        "starter_build_wiki_summary": "把目前公司的運作脈絡整理成共享 wiki 頁面。",
        "starter_review_inbox_title": "整理收件匣",
        "starter_review_inbox_summary": "檢查 Inbox 資料夾，並準備一份精簡摘要。",
        "no_missions_create_from_ceo": "目前還沒有任務。先問 CEO 應該從哪裡開始。",
        "runtime_settings": "執行環境設定",
        "runtime_settings_desc": "選擇 Praetor 要使用的模型執行環境。API key 會以私密檔案保存在本機，不會在儲存後回顯。",
        "runtime_settings_saved": "執行環境設定已儲存。",
        "model_connection_center": "模型與 API 連接",
        "model_connection_desc": "把 Praetor 連到 CEO 規劃與任務執行要使用的 AI 供應商。你也可以先不填 key，之後再補。",
        "connection_step_title": "連接你的 AI 供應商",
        "connection_step_help": "先選一個供應商；如果還沒有 key，可以留空之後再補。OpenAI-compatible gateway 放在進階設定裡。",
        "workspace_step_help": "例如：~/praetor-workspace。Praetor 會在裡面建立 Projects、Wiki、Decisions、Missions 等資料夾。",
        "governance_step_help": "建議使用平衡模式：Praetor 可以整理低風險工作，但刪檔、花錢、對外傳訊或改策略前要先問你。",
        "skip_api_key": "可以先留空，之後在「模型」頁補上。",
        "api_key": "API key",
        "api_key_placeholder": "留空表示保留既有 key",
        "api_key_help": "請只在這個瀏覽器表單貼上供應商 key。Praetor 會用私密檔案權限保存在本機 state 目錄。",
        "provider_key": "供應商 key",
        "configured": "已設定",
        "missing": "尚未設定",
        "save_runtime_settings": "儲存執行環境設定",
        "test_api_connection": "測試連線",
        "testing_connection": "測試中...",
        "api_connection_ok": "連線已確認。Praetor 可以連到目前選擇的模型供應商。",
        "api_connection_failed": "連線測試失敗。請檢查供應商、模型、key 與 Base URL。",
        "runtime_auth_error": "模型供應商拒絕目前的 API key。請在「模型與 API」檢查 key，然後再測試連線。",
        "runtime_network_error": "Praetor 無法連到模型供應商。請檢查 Base URL 與網路連線。",
        "runtime_not_found_error": "模型供應商找不到這個 endpoint 或模型。請檢查 Base URL 與模型名稱。",
        "bridge_url": "Bridge 位址",
        "mode": "模式",
        "principles": "運作原則",
        "principles_notice": "Praetor 會在初始化過程中建立公司 DNA。",
        "owner_login": "擁有者登入",
        "owner_login_desc": "Praetor 會用擁有者帳號保護整個公司工作區。登入後再繼續。",
        "password": "密碼",
        "welcome_title": "歡迎使用 Praetor",
        "welcome_desc": "請先選擇語言，再決定要首次初始化公司，或以回訪擁有者身份登入。",
        "first_time_setup": "首次設定",
        "continue_setup": "繼續設定",
        "returning_owner": "回訪擁有者登入",
        "company_not_initialized": "這家公司尚未初始化，請先完成首次設定。",
        "language_switch": "語言",
        "start_onboarding": "開始初始化",
        "go_to_login": "前往登入",
        "back_to_welcome": "回到首頁",
        "onboarding_meeting": "Praetor 初始化會議",
        "onboarding_desc": "Praetor 會一步一步協助你定義公司。你用創辦人的角度回答，Praetor 會把答案整理成公司 DNA、治理規則、角色結構與執行環境設定。",
        "founder_to_praetor": "創辦人對 Praetor",
        "wizard_desc": "Praetor 會用實際情境問題推導公司風格，而不是一開始就要求你選技術標籤。",
        "steps": "步",
        "owner_name": "擁有者名稱",
        "owner_email": "擁有者 Email",
        "owner_password": "擁有者密碼",
        "confirm_password": "確認密碼",
        "company_language": "公司語言",
        "leadership": "領導方式",
        "decision_style": "決策風格",
        "organization_style": "組織風格",
        "autonomy": "自主程度",
        "risk_priority": "風險優先",
        "work_style_questions": "運作情境問卷",
        "work_style_questions_help": "用真實情境回答。Praetor 會推導領導方式、決策風格、自主程度、組織風格與風險優先。",
        "q_interrupt": "Praetor 什麼時候應該打擾你？",
        "q_interrupt_hands_on": "多數重要決定前都先問我。",
        "q_interrupt_strategic": "只在明確 checkpoint 和重大取捨時問我。",
        "q_interrupt_delegator": "少打擾；低風險工作先推進，事後清楚回報。",
        "q_direction": "如果 AI 覺得任務方向可能錯了，應該怎麼辦？",
        "q_direction_careful": "停下來，改方向前先問我。",
        "q_direction_balanced": "提出選項和建議，讓我決定。",
        "q_direction_fast": "低風險時自行修正，事後回報。",
        "q_team": "AI 公司應該怎麼組織工作？",
        "q_team_lean": "保持精簡，除非任務明顯需要更多角色。",
        "q_team_structured": "預設使用 PM、Developer、Reviewer 和風險角色。",
        "q_team_flexible": "依任務複雜度動態組成團隊。",
        "q_autonomy": "AI agent 可以在多大範圍內自行行動？",
        "q_autonomy_strict": "只草擬與建議。",
        "q_autonomy_hybrid": "低風險可執行；敏感行為先問我。",
        "q_autonomy_autonomous": "在明確邊界內盡量自主推進。",
        "q_risk": "你最擔心哪種失敗？",
        "q_risk_wrong": "做錯決定。",
        "q_risk_slow": "行動太慢。",
        "q_risk_memory": "重要脈絡遺失。",
        "q_risk_approval": "未經批准就行動。",
        "derived_settings": "推導出的運作模型",
        "plain_summary": "白話運作摘要",
        "plain_summary_default": "Praetor 會保留敏感決策給董事長，同時允許低風險工作在批准的工作區內推進。",
        "technical_summary": "技術映射",
        "advanced_provider": "進階供應商設定",
        "base_url": "Base URL",
        "base_url_help": "給 LiteLLM、OpenRouter、LM Studio、vLLM 或公司 proxy 等 OpenAI-compatible gateway 使用。留空則使用供應商預設值。",
        "openai_compatible_notice": "OpenAI-compatible 只代表 API 格式相容；資料會送到你設定的 base URL。",
        "workspace_root": "工作區路徑",
        "runtime_mode": "執行模式",
        "provider": "模型供應商",
        "model": "模型",
        "executor": "執行器",
        "always_require_approval": "這些行為一定要先經過你的批准",
        "wizard_next": "下一步",
        "wizard_back": "上一步",
        "wizard_submit": "初始化 Praetor",
        "praetor_recommendation": "Praetor 建議",
        "step1_prompt": "先告訴我這家公司由誰擁有，以及整體要使用什麼語言運作。",
        "step2_prompt": "我會用實際情境問題推導這家 AI 公司的運作風格。",
        "step3_prompt": "這家公司應該在哪裡工作？我只會在你批准的工作區裡讀寫。",
        "step4_prompt": "選擇公司要如何思考與執行：API 模型、你現有的訂閱工具，或本地模型。",
        "step5_prompt": "定義哪些事情一定要先問你。這些會成為 AI 公司的核心治理規則。",
        "step6_prompt": "我已推導出下面這套運作模型。請用白話確認後，再初始化 Praetor。",
        "summary_language": "語言",
        "summary_leadership": "領導方式",
        "summary_decision_style": "決策風格",
        "summary_organization": "組織風格",
        "summary_autonomy": "自主程度",
        "summary_runtime": "執行模式",
        "summary_provider": "供應商",
        "summary_executor": "執行器",
        "founder_statement": "我想要一間公司，裡面的 AI agent 可以管理其他 AI agent，而且要有明確的目標、責任和權限階層。",
        "praetor_statement": "我會把你的答案轉換成公司 DNA、角色邊界、批准規則，以及一套可以安全向下委派、向上升級決策的執行架構。",
        "founder_label": "創辦人",
        "opt_strategic": "策略型",
        "opt_hands_on": "親自參與",
        "opt_delegator": "授權型",
        "opt_balanced": "平衡",
        "opt_careful": "謹慎",
        "opt_fast": "快速",
        "opt_lean": "精簡",
        "opt_structured": "結構化",
        "opt_flexible": "彈性",
        "opt_hybrid": "混合",
        "opt_strict": "嚴格",
        "opt_autonomous": "自主",
        "opt_api": "API",
        "opt_subscription_executor": "訂閱執行器",
        "opt_local_model": "本地模型",
        "opt_openai_compatible": "OpenAI-compatible",
        "principle_1": "執行向下流動。",
        "principle_2": "決策向上升級。",
        "principle_3": "記憶屬於公司，不屬於個別 agent。",
        "principle_4": "Praetor 管理的是角色與階層，不是讓平等 agent 無限討論。",
        "page_praetor": "Praetor",
        "page_overview": "總覽",
        "page_inbox": "收件匣",
        "page_tasks": "任務",
        "page_agents": "AI 組織",
        "page_activity": "動態",
        "page_settings": "設定",
        "page_memory": "記憶",
        "page_decisions": "決策",
        "page_models": "模型與 API",
        "page_meetings": "會議",
        "page_mobile": "手機簡報",
        "active": "進行中",
        "paused": "已暫停",
        "approvals": "待核准",
        "total_missions": "任務總數",
        "status_breakdown": "狀態分布",
        "recent_missions": "近期任務",
        "recent_audit_events": "近期系統紀錄",
        "chairman_inbox": "董事長收件匣",
        "chairman_inbox_desc": "集中處理需要你注意的事項：批准、卡住的工作、執行環境風險，以及已完成待驗收的任務。",
        "governance_review": "治理檢查",
        "governance_review_desc": "低噪音的公司檢查，只提出正式需要注意的事項。",
        "run_governance_review": "執行檢查",
        "review_summary": "檢查摘要",
        "next_review": "下次檢查",
        "formal_items": "正式事項",
        "needs_attention": "需要注意",
        "pending_decisions": "待裁示",
        "blocked_work": "卡住的工作",
        "risk_signals": "風險訊號",
        "completed_for_review": "已完成待驗收",
        "runtime_watch": "執行環境監看",
        "all_clear": "目前無需處理。",
        "open_mission": "打開任務",
        "review_item": "查看項目",
        "agent_directory": "AI 組織名錄",
        "agent_directory_desc": "公司的 AI 組織：角色、工作中的 agent、技能、權限、主管與近期內部活動。",
        "role_charter": "角色職責",
        "active_agents": "工作中的 Agent",
        "recent_agent_activity": "近期 AI 內部活動",
        "skills": "技能",
        "authority": "權限",
        "supervisor": "主管",
        "instances": "實例",
        "constraints": "限制",
        "escalates_on": "升級條件",
        "no_active_agents": "目前沒有工作中的 agent。",
        "no_agent_activity": "目前沒有 AI 內部活動。",
        "team_operating_model": "團隊運作模型",
        "mission_board": "任務看板",
        "mission": "任務",
        "status": "狀態",
        "priority": "優先級",
        "domains": "領域",
        "updated": "更新時間",
        "run": "執行",
        "activity_recent_runs": "近期執行紀錄",
        "audit_stream": "系統活動",
        "audit_trail": "決策紀錄",
        "event_detail": "事件摘要",
        "event_recorded": "已記錄事件。",
        "mission_related_event": "任務相關事件。",
        "technical_details": "技術細節",
        "decision_items": "需要決策的事項",
        "open": "打開",
        "company_memory": "公司記憶",
        "company_memory_desc": "Praetor 在任務中可以使用的共享 wiki 與檢索脈絡。",
        "wiki_pages": "Wiki 頁面",
        "recent_retrieval_previews": "近期檢索摘要",
        "runtime_health": "執行環境狀態",
        "usage_by_executor": "執行器使用量",
        "executor": "執行器",
        "runs": "執行次數",
        "input": "輸入",
        "output": "輸出",
        "cost": "估計成本",
        "recent_runs": "近期執行",
        "structured_meetings": "結構化會議",
        "structured_meetings_desc": "會議摘要會根據任務狀態、工作紀錄與執行紀錄產生。",
        "today": "今日",
        "mission_briefing": "任務簡報",
        "mobile_briefing_title": "行動簡報",
        "quick_links": "快速連結",
        "owner": "擁有者",
        "name": "名稱",
        "email": "Email",
        "language": "語言",
        "workspace": "工作區",
        "root": "根目錄",
        "allow_read": "可讀取範圍",
        "allow_write": "可寫入範圍",
        "deny_write": "禁止寫入範圍",
        "governance": "治理規則",
        "autonomy": "自主程度",
        "require_approval": "需要批准",
        "auto_execute": "可自動執行",
        "never_allow": "永不允許",
        "roles": "角色",
        "executor_health": "執行器狀態",
        "configured": "已設定",
        "healthy": "健康",
        "error": "錯誤",
        "bridge_url": "Bridge 位址",
        "none": "無",
        "not_available": "未設定",
        "no_missions_yet": "目前還沒有任務。",
        "no_missions_available": "目前沒有可用任務。",
        "no_recent_missions": "Praetor 尚未開始任何任務。",
        "no_audit_events": "目前沒有系統紀錄。",
        "no_audit_events_recorded": "目前尚未記錄系統活動。",
        "no_execution_runs": "目前沒有執行紀錄。",
        "no_usage_records": "目前沒有使用量紀錄。",
        "no_runs_recorded": "目前沒有執行紀錄。",
        "no_wiki_pages": "目前沒有 wiki 頁面。",
        "no_retrieval_preview": "目前沒有檢索摘要。",
        "no_executors": "Bridge 目前沒有回報可用的執行器。",
        "no_runs_yet": "目前還沒有執行。",
        "no_meetings": "目前還沒有產生會議摘要。",
        "no_structured_decisions": "目前沒有結構化決策紀錄。",
        "no_approvals_waiting": "目前沒有等待核准的事項。",
        "no_summary_yet": "目前沒有摘要。",
        "no_changed_files": "沒有記錄變更檔案。",
        "auto": "自動",
        "manual": "手動",
        "enabled": "啟用",
        "disabled": "停用",
        "yes": "是",
        "no": "否",
        "run_mission": "執行任務",
        "pause_mission": "暫停",
        "continue_mission": "繼續",
        "stop_mission": "停止",
        "create_review": "建立審查",
        "chairman_view": "董事長視圖",
        "more_actions": "更多操作",
        "next_decision": "下一個裁示",
        "owner_decision_needed_desc": "Praetor 需要創辦人的判斷，任務才能乾淨收尾。",
        "no_owner_decision_needed": "目前不需要裁示",
        "no_owner_decision_needed_desc": "Praetor 可以在目前任務邊界內繼續推進。",
        "workspace_health": "工作區健康",
        "healthy": "健康",
        "needs_review": "需要檢視",
        "review_items": "待檢視項目",
        "files_scanned": "已掃描檔案",
        "company_context": "公司脈絡",
        "documents_and_memory": "文件與記憶",
        "ai_operations": "AI 執行狀態",
        "technical_appendix": "技術附錄",
        "raw_files": "原始檔案",
        "summary": "摘要",
        "manager_layer": "管理方式",
        "complexity_score": "複雜度",
        "pm_required": "需要 PM",
        "escalation_reason": "升級原因",
        "requested_outputs": "要求產出",
        "task_logs": "工作紀錄",
        "no_task_logs": "目前沒有工作紀錄。",
        "work_sessions": "AI 工作會話",
        "no_work_sessions": "目前沒有 AI 工作會話。",
        "session_turns": "回合",
        "current_blocker": "目前阻塞",
        "completion_contract": "完成條件",
        "run_attempts": "執行嘗試",
        "workspace_scope": "工作區範圍",
        "workflow_contract": "工作流程規範",
        "workspace_steward": "Workspace Steward",
        "workspace_steward_desc": "Praetor 會用穩定 ID 登記檔案，讓資料夾可以整理而不失去文件引用。",
        "file_assets": "檔案資產",
        "restructure_plans": "整理計畫",
        "create_restructure_plan": "建立整理計畫",
        "reconcile_workspace": "核對工作區",
        "reconciliation_reports": "核對報告",
        "no_file_assets": "目前沒有已登記的檔案資產。",
        "allowed_write": "允許寫入",
        "denied_write": "禁止寫入",
        "last_event": "最後事件",
        "tokens": "Token",
        "no_run_attempts": "目前沒有執行嘗試。",
        "knowledge_workspace": "知識工作區",
        "client_record": "客戶資料",
        "matter_record": "事項資料",
        "document_registry": "文件登錄",
        "document_versions": "版本",
        "matter_decisions": "事項決策",
        "open_questions": "未決問題",
        "knowledge_updates": "知識更新",
        "board_briefing": "董事長簡報",
        "board_briefing_desc": "由 PM 帶領任務小組，把任務整理成可供創辦人裁示的正式簡報，再進入執行。",
        "create_board_briefing": "準備董事長簡報",
        "no_board_briefing": "目前沒有董事長簡報。",
        "recommendations": "建議",
        "assumptions": "假設",
        "risks": "風險",
        "decisions_needed": "需要裁示",
        "memory_promotion": "記憶沉澱",
        "memory_promotion_desc": "原始討論只作為證據保存；只有經過整理的結論會成為公司長期知識。",
        "create_memory_promotion": "建立沉澱審查",
        "promotion_findings": "整理結果",
        "no_memory_promotion": "目前沒有記憶沉澱審查。",
        "no_documents_registered": "目前沒有文件登錄。",
        "no_matter_decisions": "目前沒有事項決策。",
        "no_open_questions": "目前沒有未決問題。",
        "no_knowledge_updates": "目前沒有建議寫入知識庫的更新。",
        "folder": "資料夾",
        "current_version": "目前版本",
        "reason": "原因",
        "report": "報告",
        "run_budget": "執行預算",
        "max_steps": "最多步數",
        "max_tokens": "最多 tokens",
        "max_time_minutes": "最多時間（分鐘）",
        "max_cost_eur": "最高成本（EUR）",
        "latest_run_usage": "最近一次使用量",
        "execution_runs": "執行紀錄",
        "changed_files": "變更檔案",
        "input_tokens": "輸入 tokens",
        "output_tokens": "輸出 tokens",
        "stop_reason": "停止原因",
        "request_approval_checkpoint": "建立批准檢查點",
        "category": "類別",
        "reason": "原因",
        "create_approval": "建立批准",
        "manual_checkpoint_reason": "擁有者手動要求決策檢查點。",
        "status_file": "狀態檔案",
        "pm_report": "PM 報告",
        "tasks_file": "工作檔案",
        "mission_run_completed": "任務執行完成。",
        "mission_paused": "任務已暫停。",
        "mission_resumed": "任務已繼續。",
        "mission_stopped": "任務已停止。",
    },
}

VALUE_LABELS = {
    "en": {
        "planned": "planned",
        "active": "active",
        "running": "running",
        "resumed": "running",
        "paused": "paused",
        "completed": "completed",
        "failed": "failed",
        "pending": "pending",
        "approved": "approved",
        "rejected": "rejected",
        "high": "high",
        "normal": "normal",
        "low": "low",
        "critical": "critical",
        "api": "API",
        "openai_compatible": "OpenAI-compatible",
        "subscription_executor": "subscription executor",
        "local_model": "local model",
        "praetor_direct": "CEO direct",
        "pm_auto": "PM managed",
        "hybrid": "hybrid",
        "change_strategy": "change strategy",
        "overwrite_important_files": "overwrite important files",
        "shell_commands": "shell commands",
        "spending_money": "spending money",
        "delete_files": "delete files",
        "external_communication": "external communication",
        "create_files": "create files",
        "draft_documents": "draft documents",
        "summarize_documents": "summarize documents",
        "organize_workspace": "organize workspace",
        "access_outside_workspace": "access outside workspace",
        "silent_destructive_actions": "silent destructive actions",
        "external_send_without_explicit_rule": "external sending without an explicit rule",
        "operations": "operations",
        "lean": "lean",
        "structured": "structured",
        "flexible": "flexible",
        "chairman": "chairman",
        "ceo": "CEO",
        "project_manager": "project manager",
        "avoid_wrong_decisions": "avoid wrong decisions",
        "avoid_being_slow": "avoid being slow",
        "avoid_losing_information": "avoid losing information",
        "avoid_acting_without_approval": "avoid acting without approval",
        "true": "yes",
        "false": "no",
    },
    "zh-TW": {
        "planned": "已規劃",
        "active": "進行中",
        "running": "執行中",
        "resumed": "進行中",
        "paused": "已暫停",
        "completed": "已完成",
        "failed": "失敗",
        "pending": "待處理",
        "approved": "已批准",
        "rejected": "已拒絕",
        "high": "高",
        "normal": "一般",
        "low": "低",
        "critical": "關鍵",
        "api": "API",
        "openai_compatible": "OpenAI-compatible",
        "subscription_executor": "訂閱執行器",
        "local_model": "本地模型",
        "praetor_direct": "CEO 直接管理",
        "pm_auto": "PM 管理",
        "hybrid": "混合",
        "change_strategy": "策略變更",
        "overwrite_important_files": "覆寫重要檔案",
        "shell_commands": "Shell 指令",
        "spending_money": "花費金錢",
        "delete_files": "刪除檔案",
        "external_communication": "對外溝通",
        "create_files": "建立檔案",
        "draft_documents": "草擬文件",
        "summarize_documents": "摘要文件",
        "organize_workspace": "整理工作區",
        "access_outside_workspace": "存取工作區外部",
        "silent_destructive_actions": "未告知的破壞性操作",
        "external_send_without_explicit_rule": "未有明確規則的對外傳送",
        "operations": "營運",
        "lean": "精簡",
        "structured": "結構化",
        "flexible": "彈性",
        "chairman": "董事長",
        "ceo": "CEO",
        "project_manager": "專案經理",
        "avoid_wrong_decisions": "避免錯誤決策",
        "avoid_being_slow": "避免行動太慢",
        "avoid_losing_information": "避免資訊遺失",
        "avoid_acting_without_approval": "避免未經批准就行動",
        "true": "是",
        "false": "否",
    },
}

ROLE_NAME_LABELS = {
    "zh-TW": {
        "CEO": "CEO",
        "Project Manager": "專案經理",
        "Developer": "開發者",
        "Reviewer": "審查者",
        "Security Officer": "資安主管",
        "Legal Counsel": "法務顧問",
        "Project Execution": "專案執行",
    }
}

PHRASE_LABELS = {
    "zh-TW": {
        "Translate chairman intent into missions, teams, decisions, and durable company memory.": "將董事長意圖轉換成任務、團隊、決策與長期公司記憶。",
        "set strategic intent": "設定策略方向",
        "assign teams": "指派團隊",
        "escalate sensitive decisions": "升級敏感決策",
        "executive planning": "高階規劃",
        "risk triage": "風險分流",
        "memory stewardship": "公司記憶管理",
        "mission staffing": "任務編組",
        "low-risk product execution": "低風險產品執行",
        "internal prioritization": "內部優先級判斷",
        "privacy risk": "隱私風險",
        "security risk": "安全風險",
        "legal exposure": "法律暴露",
        "external spending": "對外支出",
        "Convert CEO direction into scoped work orders, progress tracking, and risk reports.": "將 CEO 方向轉換為明確工作單、進度追蹤與風險報告。",
        "break down work": "拆解工作",
        "coordinate agents": "協調 agent",
        "surface blockers": "提出阻塞點",
        "planning": "規劃",
        "coordination": "協調",
        "status reporting": "狀態回報",
        "scope conflict": "範圍衝突",
        "blocked execution": "執行受阻",
        "role disagreement": "角色意見衝突",
        "task sequencing": "工作排序",
        "low-risk implementation tradeoffs": "低風險實作取捨",
        "Implement scoped engineering tasks and report changed files, tests, and blockers.": "執行已定義範圍的工程任務，並回報變更檔案、測試與阻塞點。",
        "implement": "實作",
        "test": "測試",
        "report": "回報",
        "software engineering": "軟體工程",
        "debugging": "除錯",
        "local verification": "本機驗證",
        "unsafe file operation": "不安全檔案操作",
        "unclear requirement": "需求不清",
        "test failure": "測試失敗",
        "local code structure within assigned scope": "指派範圍內的程式結構",
        "Validate outputs against mission intent, safety boundaries, and completion criteria.": "依任務意圖、安全邊界與完成條件驗證產出。",
        "review outputs": "審查產出",
        "check tests": "檢查測試",
        "block incomplete closeout": "阻擋未完成的結案",
        "quality control": "品質控管",
        "risk review": "風險審查",
        "acceptance testing": "驗收測試",
        "privacy issue": "隱私問題",
        "security issue": "安全問題",
        "missing acceptance criteria": "缺少驗收條件",
        "block mission closeout until criteria pass": "在條件通過前阻擋任務結案",
        "Protect user privacy, files, credentials, and local computer safety.": "保護使用者隱私、檔案、憑證與本機安全。",
        "security review": "安全審查",
        "privacy review": "隱私審查",
        "permission boundary checks": "權限邊界檢查",
        "threat modeling": "威脅建模",
        "secure defaults": "安全預設",
        "data handling review": "資料處理審查",
        "credential exposure": "憑證暴露",
        "user file access": "使用者檔案存取",
        "network data sharing": "網路資料分享",
        "block risky release until mitigated": "在風險緩解前阻擋發布",
        "Identify legal, licensing, contractual, and external communication risks.": "辨識法律、授權、合約與對外溝通風險。",
        "license review": "授權審查",
        "policy review": "政策審查",
        "legal risk memo": "法律風險 memo",
        "legal triage": "法律分流",
        "license classification": "授權分類",
        "policy drafting": "政策草擬",
        "contract": "合約",
        "non-permissive license": "非寬鬆授權",
        "external claim": "外部主張",
        "request legal escalation": "請求法律升級",
        "create and maintain project structure": "建立並維護專案結構",
        "update project status and tasks": "更新專案狀態與工作",
        "review outputs for quality and completeness": "審查產出的品質與完整性",
        "identify missing information or risky changes": "辨識缺漏資訊或高風險變更",
        "own mission context": "掌握任務脈絡",
        "coordinate task sequencing and reporting": "協調工作排序與回報",
        "chairman": "董事長",
        "ceo": "CEO",
        "project_manager": "專案經理",
        "Mission:": "任務：",
        "Role:": "角色：",
        "Responsibilities:": "職責：",
        "Constraints:": "限制：",
        "Onboarded as": "已加入角色：",
        "Charter:": "職責：",
        "must record unresolved risks": "必須記錄未解決風險",
        "cannot approve high-risk policy or privacy changes": "不能批准高風險政策或隱私變更",
        "cannot silently delete or overwrite important user files": "不能靜默刪除或覆寫重要使用者檔案",
        "must escalate privacy, safety, legal, spending, and destructive actions": "必須升級隱私、安全、法律、支出與破壞性操作",
        "must escalate user-data and host-safety risks to chairman": "必須將使用者資料與本機安全風險升級給董事長",
        "cannot provide final legal approval without chairman instruction": "沒有董事長指示時不能提供最終法律批准",
        "CEO raised a decision checkpoint from the chairman conversation.": "CEO 從董事長對話中提出決策檢查點。",
        "Chairman decision checkpoint": "董事長決策檢查點",
        "Mission Resumed": "任務已繼續",
        "Mission Paused": "任務已暫停",
        "Mission Created": "建立任務",
        "Mission Team Created": "建立 AI 團隊",
        "Approval Created": "建立核准請求",
        "Delegation Created": "交辦任務",
        "Decision Escalation Created": "升級決策",
        "Standing Order Created": "更新常設規則",
    }
}

EVENT_LABELS = {
    "en": {
        "owner_login": "Owner signed in",
        "mission_created": "Mission created",
        "mission_team_created": "AI team created",
        "approval_created": "Approval request created",
        "delegation_created": "Task delegated",
        "decision_escalation_created": "Decision escalated",
        "standing_order_created": "Standing order updated",
        "mission_resumed": "Mission resumed",
        "mission_paused": "Mission paused",
        "mission_stopped": "Mission stopped",
        "mission_completed": "Mission completed",
        "ceo_conversation_message": "CEO conversation updated",
        "onboarding_completed": "Company initialized",
    },
    "zh-TW": {
        "owner_login": "擁有者已登入",
        "mission_created": "建立任務",
        "mission_team_created": "建立 AI 團隊",
        "approval_created": "建立核准請求",
        "delegation_created": "交辦任務",
        "decision_escalation_created": "升級決策",
        "standing_order_created": "更新常設規則",
        "mission_resumed": "任務已繼續",
        "mission_paused": "任務已暫停",
        "mission_stopped": "任務已停止",
        "mission_completed": "任務已完成",
        "ceo_conversation_message": "CEO 對話更新",
        "onboarding_completed": "公司初始化完成",
    },
}


def install_ui(app) -> None:
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    if (WEB_DIST_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(WEB_DIST_DIR / "assets")), name="office_assets")
    app.include_router(router)


def _flash(request: Request) -> tuple[str | None, str]:
    return request.query_params.get("flash"), request.query_params.get("level", "info")


def _redirect(path: str, flash: str | None = None, level: str = "info") -> RedirectResponse:
    if flash:
        sep = "&" if "?" in path else "?"
        path = f"{path}{sep}flash={quote(flash)}&level={quote(level)}"
    return RedirectResponse(url=path, status_code=303)


def _safe_redirect_path(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    if not value.startswith("/") or value.startswith("//"):
        return fallback
    return value


def _friendly_runtime_error(exc_or_message: Exception | str, t) -> str:
    message = str(exc_or_message)
    lowered = message.lower()
    if "401" in message or "unauthorized" in lowered or "invalid api key" in lowered:
        return t("runtime_auth_error")
    if "404" in message or "not found" in lowered:
        return t("runtime_not_found_error")
    if "connecterror" in lowered or "connection refused" in lowered or "name or service not known" in lowered:
        return t("runtime_network_error")
    if "timed out" in lowered or "timeout" in lowered:
        return t("runtime_network_error")
    return message


def _save_provider_api_key(provider: str, api_key: str) -> None:
    key = api_key.strip()
    if not key:
        return
    secret_files = {
        "openai": OPENAI_STATE_SECRET,
        "openai_compatible": OPENAI_STATE_SECRET,
        "anthropic": ANTHROPIC_STATE_SECRET,
    }
    filename = secret_files.get(provider)
    if filename is None:
        raise ValueError("Unsupported provider.")
    write_state_secret(filename, key)


def _ui_language(request: Request, initialized_settings) -> str:
    requested = request.query_params.get("lang")
    if requested in SUPPORTED_LANGUAGES:
        return requested
    cookie_value = request.cookies.get(UI_COOKIE_NAME)
    if cookie_value in SUPPORTED_LANGUAGES:
        return cookie_value
    if initialized_settings is not None and initialized_settings.owner.preferred_language in SUPPORTED_LANGUAGES:
        return initialized_settings.owner.preferred_language
    return "en"


def _translator(language: str):
    bundle = TRANSLATIONS.get(language, TRANSLATIONS["en"])
    fallback = TRANSLATIONS["en"]

    def translate(key: str) -> str:
        return bundle.get(key, fallback.get(key, key))

    return translate


def _value_label(language: str):
    labels = VALUE_LABELS.get(language, VALUE_LABELS["en"])
    fallback = VALUE_LABELS["en"]

    def label(value: Any) -> str:
        if value is None:
            return _translator(language)("not_available")
        if isinstance(value, bool):
            value = str(value).lower()
        raw = str(value)
        key = raw.strip().lower()
        return labels.get(key, fallback.get(key, raw.replace("_", " ")))

    return label


def _role_label(language: str):
    labels = ROLE_NAME_LABELS.get(language, {})

    def label(value: Any) -> str:
        raw = str(value or "")
        return labels.get(raw, raw)

    return label


def _phrase_label(language: str):
    labels = PHRASE_LABELS.get(language, {})

    def label(value: Any) -> str:
        raw = str(value or "")
        translated = labels.get(raw)
        if translated is not None:
            return translated
        for source, target in labels.items():
            raw = raw.replace(source, target)
        return raw

    return label


def _event_label(language: str):
    labels = EVENT_LABELS.get(language, EVENT_LABELS["en"])
    fallback = EVENT_LABELS["en"]

    def label(event_type: Any) -> str:
        raw = str(event_type or "")
        return labels.get(raw, fallback.get(raw, raw.replace("_", " ").title()))

    return label


def _format_datetime(language: str):
    def format_value(value: Any) -> str:
        if value is None:
            return ""
        parsed = value
        if isinstance(value, str):
            raw = value.strip()
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            try:
                parsed = datetime.fromisoformat(raw)
            except ValueError:
                return value
        if isinstance(parsed, datetime):
            if language == "zh-TW":
                return parsed.strftime("%Y-%m-%d %H:%M")
            return parsed.strftime("%Y-%m-%d %H:%M")
        return str(value)

    return format_value


def _event_summary(language: str):
    t = _translator(language)
    phrase_label = _phrase_label(language)
    value_label = _value_label(language)

    def summarize(event_or_payload: Any) -> str:
        event_type = ""
        payload = event_or_payload
        if isinstance(event_or_payload, dict) and "payload" in event_or_payload:
            event_type = str(event_or_payload.get("type") or "")
            payload = event_or_payload.get("payload")
        if not isinstance(payload, dict):
            return str(payload or t("event_recorded"))
        for key in ("title", "mission_title", "reason", "content", "message", "summary", "category"):
            value = payload.get(key)
            if value:
                if key == "category":
                    return value_label(value)
                return phrase_label(value)
        if event_type in {"owner_login", "ceo_conversation_message", "standing_order_created", "onboarding_completed"}:
            return t("event_recorded")
        mission_id = payload.get("mission_id")
        if mission_id:
            return t("mission_related_event")
        return t("event_recorded")

    return summarize


def _page_title(current_page: str, fallback: str, t) -> str:
    return t(f"page_{current_page}") if current_page else fallback


def _base_context(request: Request, current_page: str, page_title: str) -> dict:
    service = request.app.state.ctx.service
    initialized_settings = service.get_settings()
    ui_language = _ui_language(request, initialized_settings)
    t = _translator(ui_language)
    display_title = _page_title(current_page, page_title, t)
    authenticated = bool(getattr(request.state, "authenticated", False))
    settings = initialized_settings if authenticated or initialized_settings is None else None
    briefing = None
    runtime_health = None
    if initialized_settings is not None and authenticated:
        briefing = service.praetor_briefing()
        runtime_health = service.runtime_health()
    approvals = service.list_approvals(status="pending") if initialized_settings is not None and authenticated else []
    flash, flash_level = _flash(request)
    if flash and flash_level == "error":
        flash = _friendly_runtime_error(flash, t)
    return {
        "request": request,
        "current_url": f"{request.url.path}{'?' + request.url.query if request.url.query else ''}",
        "current_url_quoted": quote(f"{request.url.path}{'?' + request.url.query if request.url.query else ''}", safe=""),
        "page_title": display_title,
        "current_page": current_page,
        "ui_language": ui_language,
        "t": t,
        "label": _value_label(ui_language),
        "role_label": _role_label(ui_language),
        "phrase_label": _phrase_label(ui_language),
        "event_label": _event_label(ui_language),
        "event_summary": _event_summary(ui_language),
        "format_time": _format_datetime(ui_language),
        "language_options": SUPPORTED_LANGUAGES,
        "settings": settings,
        "settings_initialized": initialized_settings is not None,
        "briefing": briefing,
        "flash": flash,
        "flash_level": flash_level,
        "approvals": approvals,
        "runtime_ready": bool(runtime_health and runtime_health.get("healthy")),
        "runtime_health": runtime_health,
        "bridge_base_url": get_bridge_base_url(),
        "authenticated": authenticated,
        "session_owner": getattr(request.state, "session_owner", None),
        "csrf_token": csrf_token(request),
        "setup_token": request.query_params.get("setup_token", ""),
        "static_asset_version": int((STATIC_DIR / "praetor.css").stat().st_mtime),
    }


def _validate_form_csrf(request: Request, form) -> None:
    require_csrf(request, str(form.get("csrf_token", "")))


def _default_onboarding() -> dict:
    return {
        "owner_name": "Founder",
        "owner_email": "",
        "owner_password": "",
        "owner_password_confirm": "",
        "language": "en",
        "leadership_style": "strategic",
        "decision_style": "balanced",
        "organization_style": "lean",
        "autonomy_mode": "hybrid",
        "risk_priority": "avoid_wrong_decisions",
        "workspace_root": "~/praetor-workspace",
        "runtime_mode": "api",
        "runtime_provider": "openai",
        "runtime_model": "gpt-4.1-mini",
        "runtime_base_url": "",
        "runtime_executor": "codex",
        "require_approval": [
            "delete_files",
            "overwrite_important_files",
            "external_communication",
            "spending_money",
            "change_strategy",
            "shell_commands",
        ],
    }


def _starter_missions(t) -> list[dict[str, str]]:
    return [
        {
            "title": t("starter_create_project_title"),
            "summary": t("starter_create_project_summary"),
            "domain": "operations",
            "priority": "high",
            "requested_outputs": "/workspace/Projects/Alpha/PROJECT.md\n/workspace/Projects/Alpha/STATUS.md",
        },
        {
            "title": t("starter_build_wiki_title"),
            "summary": t("starter_build_wiki_summary"),
            "domain": "operations",
            "priority": "normal",
            "requested_outputs": "/workspace/Wiki/Company.md\n/workspace/Wiki/Strategy.md",
        },
        {
            "title": t("starter_review_inbox_title"),
            "summary": t("starter_review_inbox_summary"),
            "domain": "operations",
            "priority": "normal",
            "requested_outputs": "/workspace/Inbox/INBOX_SUMMARY.md",
        },
    ]


def _mission_by_id(missions: list) -> dict[str, Any]:
    return {mission.id: mission for mission in missions}


def _build_inbox_items(service, t, label, phrase_label, event_label, event_summary) -> dict[str, list[dict[str, Any]]]:
    missions = service.list_missions()
    missions_by_id = _mission_by_id(missions)
    approvals = service.list_approvals(status="pending")
    recent_runs = service.list_recent_runs(limit=20)
    audit_events = service.list_audit_events(limit=20)
    runtime_health = service.runtime_health()
    governance_review = service.latest_governance_review()

    pending_decisions = []
    for approval in approvals:
        pending_decisions.append(
            {
                "title": label(approval.category),
                "body": phrase_label(approval.reason),
                "status": label(approval.status),
                "href": f"/app/missions/{approval.mission_id}" if approval.mission_id else "/app/decisions",
                "kind": t("pending_decisions"),
                "created_at": approval.created_at,
            }
        )

    blocked_work = []
    for mission in missions:
        if mission.status in {"failed", "paused"}:
            blocked_work.append(
                {
                    "title": mission.title,
                    "body": mission.summary or label(mission.status),
                    "status": label(mission.status),
                    "href": f"/app/missions/{mission.id}",
                    "kind": t("blocked_work"),
                    "created_at": mission.updated_at,
                }
            )
    for run in recent_runs:
        status = str(run.get("normalized_status") or run.get("status") or "").lower()
        if status in {"failed", "error"}:
            blocked_work.append(
                {
                    "title": str(run.get("executor") or t("executor")),
                    "body": str(run.get("stderr_tail") or run.get("stdout_tail") or t("event_recorded"))[:320],
                    "status": label(status),
                    "href": "/app/activity",
                    "kind": t("blocked_work"),
                    "created_at": run.get("finished_at") or run.get("started_at"),
                }
            )

    risk_signals = []
    if not runtime_health.get("healthy"):
        risk_signals.append(
            {
                "title": t("runtime_watch"),
                "body": runtime_health.get("error") or t("runtime_not_configured"),
                "status": label(runtime_health.get("mode") or "runtime"),
                "href": "/app/settings",
                "kind": t("risk_signals"),
                "created_at": None,
            }
        )
    risk_event_types = {"approval_created", "decision_escalation_created", "standing_order_created"}
    for event in audit_events:
        if event.get("type") in risk_event_types:
            risk_signals.append(
                {
                    "title": event_label(event.get("type") or "event_recorded"),
                    "body": event_summary(event),
                    "status": t("review_item"),
                    "href": "/app/decisions",
                    "kind": t("risk_signals"),
                    "created_at": event.get("ts"),
                }
            )

    completed_for_review = [
        {
            "title": mission.title,
            "body": mission.summary or t("review_item"),
            "status": label(mission.status),
            "href": f"/app/missions/{mission.id}",
            "kind": t("completed_for_review"),
            "created_at": mission.updated_at,
        }
        for mission in missions
        if mission.status == "completed"
    ]

    return {
        "governance_review": governance_review,
        "formal_items": [
            {
                "title": item.title,
                "body": item.body,
                "status": label(item.severity),
                "href": item.href,
                "kind": label(item.kind),
                "created_at": item.created_at,
            }
            for item in governance_review.items
        ][:8],
        "pending_decisions": pending_decisions[:8],
        "blocked_work": blocked_work[:8],
        "risk_signals": risk_signals[:8],
        "completed_for_review": completed_for_review[:8],
    }


def _build_agent_directory(service) -> dict[str, Any]:
    organization = service.organization_snapshot()
    activity = service.office_snapshot().agent_activity
    agents_by_role: dict[str, list[Any]] = {}
    for agent in organization.agents:
        agents_by_role.setdefault(agent.role_name, []).append(agent)
    activity_by_role: dict[str, list[Any]] = {}
    for event in activity:
        activity_by_role.setdefault(event.actor.replace("_", " ").title(), []).append(event)
    return {
        "organization": organization,
        "agents_by_role": agents_by_role,
        "activity_by_role": activity_by_role,
        "recent_activity": activity,
    }


def _require_initialized(request: Request):
    settings = request.app.state.ctx.service.get_settings()
    if settings is None:
        return None
    return settings


@router.get("/app/set-language/{language_code}")
def set_language(request: Request, language_code: str):
    if language_code not in SUPPORTED_LANGUAGES:
        language_code = "en"
    next_path = request.query_params.get("next", "/app/welcome")
    response = RedirectResponse(url=next_path, status_code=303)
    response.set_cookie(
        UI_COOKIE_NAME,
        language_code,
        max_age=60 * 60 * 24 * 365,
        httponly=False,
        samesite="lax",
    )
    return response


@router.get("/office")
def office_page():
    index = WEB_DIST_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return _redirect("/app/praetor", "Praetor Office frontend has not been built yet.", "error")


@router.get("/app/welcome", response_class=HTMLResponse)
def welcome_page(request: Request):
    ctx = _base_context(request, "welcome", "Welcome")
    if getattr(request.state, "authenticated", False):
        return _redirect("/app/praetor")
    return templates.TemplateResponse(
        request=request,
        name="welcome.html",
        context=ctx,
    )


@router.get("/app/login", response_class=HTMLResponse)
def login_page(request: Request):
    if getattr(request.state, "authenticated", False):
        return _redirect("/app/praetor")
    ctx = _base_context(
        request,
        "login",
        _translator(_ui_language(request, request.app.state.ctx.service.get_settings()))("owner_login"),
    )
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            **ctx,
            "next_path": request.query_params.get("next", "/app/praetor"),
        },
    )


@router.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/app/welcome", status_code=303)


@router.get("/app", response_class=HTMLResponse)
def app_root():
    return RedirectResponse(url="/app/welcome", status_code=303)


@router.get("/app/praetor", response_class=HTMLResponse)
def praetor_page(request: Request):
    ctx = _base_context(request, "praetor", "Praetor")
    service = request.app.state.ctx.service
    settings = ctx["settings"]
    missions = service.list_missions() if settings is not None else []
    ceo_messages = service.list_ceo_messages(limit=8) if settings is not None else []
    return templates.TemplateResponse(
        request=request,
        name="praetor.html",
        context={
            **ctx,
            "missions": missions[:8],
            "ceo_messages": ceo_messages,
            "onboarding_defaults": _default_onboarding(),
            "starter_missions": _starter_missions(ctx["t"]),
        },
    )


@router.get("/app/inbox", response_class=HTMLResponse)
def inbox_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    ctx = _base_context(request, "inbox", "Inbox")
    return templates.TemplateResponse(
        request=request,
        name="inbox.html",
        context={
            **ctx,
            "inbox_items": _build_inbox_items(
                service,
                ctx["t"],
                ctx["label"],
                ctx["phrase_label"],
                ctx["event_label"],
                ctx["event_summary"],
            ),
        },
    )


@router.post("/app/inbox/governance-review")
async def run_governance_review_submit(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    request.app.state.ctx.service.run_governance_review()
    return _redirect("/app/inbox", t("governance_review"), "success")


@router.get("/app/agents", response_class=HTMLResponse)
def agents_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    return templates.TemplateResponse(
        request=request,
        name="agents.html",
        context={
            **_base_context(request, "agents", "Agents"),
            **_build_agent_directory(service),
        },
    )


@router.get("/app/overview", response_class=HTMLResponse)
def overview_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    missions = service.list_missions()
    status_counts: dict[str, int] = {}
    for mission in missions:
        status_counts[mission.status] = status_counts.get(mission.status, 0) + 1
    return templates.TemplateResponse(
        request=request,
        name="overview.html",
        context={
            **_base_context(request, "overview", "Overview"),
            "missions": missions[:12],
            "status_counts": status_counts,
            "audit_events": service.list_audit_events(limit=12),
        },
    )


@router.get("/app/tasks", response_class=HTMLResponse)
def tasks_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    missions = service.list_missions()
    return templates.TemplateResponse(
        request=request,
        name="tasks.html",
        context={
            **_base_context(request, "tasks", "Tasks"),
            "missions": missions,
        },
    )


@router.get("/app/activity", response_class=HTMLResponse)
def activity_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    return templates.TemplateResponse(
        request=request,
        name="activity.html",
        context={
            **_base_context(request, "activity", "Activity"),
            "recent_runs": service.list_recent_runs(limit=20),
            "audit_events": service.list_audit_events(limit=30),
        },
    )


@router.get("/app/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    runtime_health = request.app.state.ctx.service.runtime_health()
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            **_base_context(request, "settings", "Settings"),
            "runtime_health": runtime_health,
            "provider_keys": {
                "openai": bool(get_openai_api_key()),
                "anthropic": bool(get_anthropic_api_key()),
            },
            "telegram_secrets": {
                "bot_token": bool(get_telegram_bot_token()),
                "webhook_secret": bool(get_telegram_webhook_secret()),
            },
            "telegram_pairing_code": request.query_params.get("telegram_pairing_code", ""),
            "telegram_webhook_url": str(request.url_for("telegram_webhook")),
        },
    )


@router.post("/app/settings/runtime")
async def update_runtime_submit(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    provider = str(form.get("runtime_provider", "")).strip().lower() or None
    runtime = RuntimeSelection(
        mode=str(form.get("runtime_mode", "api")).strip() or "api",
        provider=provider,
        model=str(form.get("runtime_model", "")).strip() or None,
        executor=str(form.get("runtime_executor", "")).strip() or None,
        base_url=str(form.get("runtime_base_url", "")).strip() or None,
    )
    try:
        request.app.state.ctx.service.update_runtime(runtime)
        if provider is not None:
            _save_provider_api_key(provider, str(form.get("api_key", "")))
    except Exception as exc:
        return _redirect("/app/settings", str(exc), "error")
    next_path = _safe_redirect_path(str(form.get("next_path", "/app/settings")), "/app/settings")
    return _redirect(next_path, t("runtime_settings_saved"), "success")


@router.post("/app/settings/runtime/test")
async def test_runtime_submit(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    provider = str(form.get("runtime_provider", "")).strip().lower() or None
    runtime = RuntimeSelection(
        mode=str(form.get("runtime_mode", settings.runtime.mode)).strip() or settings.runtime.mode,
        provider=provider,
        model=str(form.get("runtime_model", "")).strip() or settings.runtime.model,
        executor=str(form.get("runtime_executor", "")).strip() or settings.runtime.executor,
        base_url=str(form.get("runtime_base_url", "")).strip() or None,
    )
    next_path = _safe_redirect_path(str(form.get("next_path", "/app/models")), "/app/models")
    try:
        request.app.state.ctx.service.test_runtime_connection(runtime, str(form.get("api_key", "")))
    except Exception as exc:
        return _redirect(next_path, f"{t('api_connection_failed')} {_friendly_runtime_error(exc, t)}", "error")
    return _redirect(next_path, t("api_connection_ok"), "success")


@router.post("/app/settings/telegram")
async def update_telegram_submit(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    bot_token = str(form.get("telegram_bot_token", "")).strip()
    webhook_secret = str(form.get("telegram_webhook_secret", "")).strip()
    if bot_token:
        write_state_secret(TELEGRAM_BOT_TOKEN_STATE_SECRET, bot_token)
    if webhook_secret:
        write_state_secret(TELEGRAM_WEBHOOK_SECRET_STATE_SECRET, webhook_secret)
    allowed_raw = str(form.get("telegram_allowed_user_id", "")).strip()
    try:
        allowed_user_id = int(allowed_raw) if allowed_raw else None
    except ValueError:
        return _redirect("/app/settings", "Telegram user ID must be a number.", "error")
    request.app.state.ctx.service.update_telegram_settings(
        settings.telegram.model_copy(
            update={
                "enabled": bool(form.get("telegram_enabled")),
                "bot_token_set": bool(bot_token or get_telegram_bot_token()),
                "webhook_secret_set": bool(webhook_secret or get_telegram_webhook_secret()),
                "allowed_user_id": allowed_user_id,
                "notify_approvals": bool(form.get("telegram_notify_approvals")),
                "allow_low_risk_approval": bool(form.get("telegram_allow_low_risk_approval")),
            }
        )
    )
    return _redirect("/app/settings", t("telegram_settings_saved"), "success")


@router.post("/app/settings/telegram/pairing-code")
async def create_telegram_pairing_submit(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    code = request.app.state.ctx.service.create_telegram_pairing_code()
    return _redirect(f"/app/settings?telegram_pairing_code={quote(code)}", t("telegram_pairing_created"), "success")


@router.post("/app/ceo/conversation")
async def create_ceo_conversation_submit(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    body = str(form.get("body", "")).strip()
    if not body:
        return _redirect("/app/praetor", t("message_to_ceo_placeholder"), "error")
    try:
        request.app.state.ctx.service.create_ceo_message(ConversationCreateRequest(body=body))
    except Exception as exc:
        return _redirect("/app/praetor", _friendly_runtime_error(exc, t), "error")
    return _redirect("/app/praetor?focus=ceo-chat", t("ceo_message_sent"), "success")


@router.get("/app/memory", response_class=HTMLResponse)
def memory_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    return templates.TemplateResponse(
        request=request,
        name="memory.html",
        context={
            **_base_context(request, "memory", "Memory"),
            "wiki_pages": service.list_wiki_pages(),
            "recent_runs": service.list_recent_runs(limit=10),
            "knowledge": service.knowledge_snapshot(),
        },
    )


@router.get("/app/decisions", response_class=HTMLResponse)
def decisions_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    return templates.TemplateResponse(
        request=request,
        name="decisions.html",
        context={
            **_base_context(request, "decisions", "Decisions"),
            "decision_items": service.list_decision_items(),
            "audit_events": service.list_audit_events(limit=25),
        },
    )


@router.get("/app/models", response_class=HTMLResponse)
def models_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    return templates.TemplateResponse(
        request=request,
        name="models.html",
        context={
            **_base_context(request, "models", "Models"),
            "usage_summary": service.usage_summary(),
            "runtime_health": service.runtime_health(),
            "provider_keys": {
                "openai": bool(get_openai_api_key()),
                "anthropic": bool(get_anthropic_api_key()),
            },
        },
    )


@router.get("/app/meetings", response_class=HTMLResponse)
def meetings_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    return templates.TemplateResponse(
        request=request,
        name="meetings.html",
        context={
            **_base_context(request, "meetings", "Meetings"),
            "meetings": service.list_meetings(),
        },
    )


@router.get("/m/briefing", response_class=HTMLResponse)
def mobile_briefing_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    missions = service.list_missions()
    return templates.TemplateResponse(
        request=request,
        name="mobile_briefing.html",
        context={
            **_base_context(request, "mobile", "Mobile Briefing"),
            "missions": missions[:8],
        },
    )


@router.get("/app/missions/{mission_id}", response_class=HTMLResponse)
def mission_detail_page(request: Request, mission_id: str):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    try:
        mission = service.get_mission(mission_id)
    except KeyError:
        return _redirect("/app/tasks", f"Mission not found: {mission_id}", "error")
    tasks = service.list_mission_tasks(mission_id)
    texts = service.read_mission_texts(mission_id)
    runs = service.list_mission_runs(mission_id)
    work_sessions = service.mission_work_sessions(mission_id)
    knowledge = service.mission_knowledge_snapshot(mission_id)
    memory_promotion_reviews = service.mission_memory_promotion_reviews(mission_id)
    board_briefings = service.list_board_briefings(mission_id)
    workspace_steward = service.workspace_steward_snapshot(mission_id=mission_id)
    run_attempts = service.list_run_attempts(mission_id)
    workspace_scope = service.mission_workspace_scope(mission_id)
    workflow_contract = service.workflow_contract()
    return templates.TemplateResponse(
        request=request,
        name="mission_detail.html",
        context={
            **_base_context(request, "tasks", mission.title),
            "mission": mission,
            "tasks": tasks,
            "texts": texts,
            "runs": runs,
            "work_sessions": work_sessions,
            "knowledge": knowledge,
            "memory_promotion_reviews": memory_promotion_reviews,
            "board_briefings": board_briefings,
            "workspace_steward": workspace_steward,
            "run_attempts": run_attempts,
            "workspace_scope": workspace_scope,
            "workflow_contract": workflow_contract,
        },
    )


@router.post("/app/onboarding")
async def onboarding_submit(request: Request):
    form = await request.form()
    _validate_form_csrf(request, form)
    require_setup_token(request, str(form.get("setup_token", "")) or None)
    require_approval = form.getlist("require_approval")
    answers = OnboardingAnswers(
        owner_name=str(form.get("owner_name", "Founder")),
        owner_email=str(form.get("owner_email", "")) or None,
        owner_password=str(form.get("owner_password", "")).strip() or None,
        language=str(form.get("language", "en")),
        leadership_style=str(form.get("leadership_style", "strategic")),
        decision_style=str(form.get("decision_style", "balanced")),
        organization_style=str(form.get("organization_style", "lean")),
        autonomy_mode=str(form.get("autonomy_mode", "hybrid")),
        risk_priority=str(form.get("risk_priority", "avoid_wrong_decisions")),
        workspace_root=str(form.get("workspace_root", "~/praetor-workspace")),
        runtime={
            "mode": str(form.get("runtime_mode", "api")),
            "provider": str(form.get("runtime_provider", "")).strip() or None,
            "model": str(form.get("runtime_model", "")).strip() or None,
            "executor": str(form.get("runtime_executor", "codex")),
            "base_url": str(form.get("runtime_base_url", "")).strip() or None,
        },
        require_approval=[str(item) for item in require_approval],
    )
    password_confirm = str(form.get("owner_password_confirm", "")).strip()
    if answers.owner_password != password_confirm:
        return _redirect("/app/praetor", "Password confirmation does not match.", "error")
    try:
        settings = request.app.state.ctx.service.complete_onboarding(answers)
        provider = answers.runtime.get("provider") if isinstance(answers.runtime, dict) else answers.runtime.provider
        if provider:
            _save_provider_api_key(str(provider), str(form.get("api_key", "")))
    except Exception as exc:
        return _redirect("/app/praetor", str(exc), "error")
    request.session["authenticated"] = True
    request.session["owner_name"] = settings.owner.name
    request.session["owner_email"] = settings.owner.email
    return _redirect("/app/praetor?focus=ceo-chat", "Praetor is initialized. Start by talking with the CEO.", "success")


@router.post("/app/login")
async def login_submit(request: Request):
    form = await request.form()
    _validate_form_csrf(request, form)
    password = str(form.get("password", "")).strip()
    next_path = str(form.get("next_path", "/app/praetor")).strip() or "/app/praetor"
    rate_key = request.client.host if request.client else "unknown"
    login_rate_limiter.check(rate_key)
    try:
        settings = request.app.state.ctx.service.authenticate_owner(LoginRequest(password=password))
    except Exception as exc:
        login_rate_limiter.record_failure(rate_key)
        return _redirect("/app/login", str(exc), "error")
    login_rate_limiter.reset(rate_key)
    request.session["authenticated"] = True
    request.session["owner_name"] = settings.owner.name
    request.session["owner_email"] = settings.owner.email
    csrf_token(request)
    return _redirect(next_path, "Login successful.", "success")


@router.post("/app/logout")
async def logout_submit(request: Request):
    form = await request.form()
    _validate_form_csrf(request, form)
    request.session.clear()
    return _redirect("/app/login", "Logged out.", "success")


@router.post("/app/missions")
async def create_mission_submit(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    title = str(form.get("title", "")).strip()
    if not title:
        return _redirect("/app/praetor", "Mission title is required.", "error")
    requested_outputs_raw = str(form.get("requested_outputs", "")).strip()
    requested_outputs = [line.strip() for line in requested_outputs_raw.splitlines() if line.strip()]
    mission = request.app.state.ctx.service.create_mission(
        MissionCreateRequest(
            title=title,
            summary=str(form.get("summary", "")).strip() or None,
            domains=[str(form.get("domain", "operations"))],
            priority=str(form.get("priority", "normal")),
            requested_outputs=requested_outputs,
        )
    )
    return _redirect(f"/app/missions/{mission.id}", "Mission created.", "success")


@router.post("/app/missions/{mission_id}/run")
async def run_mission_submit(request: Request, mission_id: str):
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, request.app.state.ctx.service.get_settings()))
    try:
        request.app.state.ctx.service.run_mission(mission_id)
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", _friendly_runtime_error(exc, t), "error")
    return _redirect(f"/app/missions/{mission_id}", t("mission_run_completed"), "success")


@router.post("/app/missions/{mission_id}/pause")
async def pause_mission_submit(request: Request, mission_id: str):
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, request.app.state.ctx.service.get_settings()))
    try:
        request.app.state.ctx.service.pause_mission(mission_id, MissionPauseRequest())
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", _friendly_runtime_error(exc, t), "error")
    return _redirect(f"/app/missions/{mission_id}", t("mission_paused"), "success")


@router.post("/app/missions/{mission_id}/continue")
async def continue_mission_submit(request: Request, mission_id: str):
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, request.app.state.ctx.service.get_settings()))
    try:
        request.app.state.ctx.service.continue_mission(mission_id, MissionContinueRequest())
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", _friendly_runtime_error(exc, t), "error")
    return _redirect(f"/app/missions/{mission_id}", t("mission_resumed"), "success")


@router.post("/app/missions/{mission_id}/stop")
async def stop_mission_submit(request: Request, mission_id: str):
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, request.app.state.ctx.service.get_settings()))
    try:
        request.app.state.ctx.service.stop_mission(mission_id, MissionStopRequest())
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", _friendly_runtime_error(exc, t), "error")
    return _redirect(f"/app/missions/{mission_id}", t("mission_stopped"), "success")


@router.post("/app/missions/{mission_id}/meeting")
async def create_meeting_submit(request: Request, mission_id: str):
    form = await request.form()
    _validate_form_csrf(request, form)
    try:
        meeting = request.app.state.ctx.service.create_review_meeting(mission_id)
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", str(exc), "error")
    return _redirect("/app/meetings", f"Meeting created: {meeting.id}", "success")


@router.post("/app/missions/{mission_id}/memory-promotion")
async def create_memory_promotion_submit(request: Request, mission_id: str):
    form = await request.form()
    _validate_form_csrf(request, form)
    try:
        review = request.app.state.ctx.service.create_memory_promotion_review(mission_id)
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", str(exc), "error")
    return _redirect(f"/app/missions/{mission_id}", f"Memory promotion review created: {review.id}", "success")


@router.post("/app/missions/{mission_id}/workspace-restructure-plan")
async def create_workspace_restructure_plan_submit(request: Request, mission_id: str):
    form = await request.form()
    _validate_form_csrf(request, form)
    try:
        plan = request.app.state.ctx.service.create_workspace_restructure_plan(mission_id=mission_id)
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", str(exc), "error")
    return _redirect(f"/app/missions/{mission_id}", f"Workspace restructure plan created: {plan.id}", "success")


@router.post("/app/missions/{mission_id}/workspace-reconcile")
async def reconcile_workspace_submit(request: Request, mission_id: str):
    form = await request.form()
    _validate_form_csrf(request, form)
    try:
        report = request.app.state.ctx.service.reconcile_workspace(mission_id=mission_id)
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", str(exc), "error")
    issues = (
        len(report.missing_assets)
        + len(report.changed_assets)
        + len(report.moved_candidates)
        + len(report.untracked_files)
        + len(report.git_changes)
    )
    return _redirect(f"/app/missions/{mission_id}", f"Workspace reconciliation completed: {issues} issue(s)", "success")


@router.post("/app/missions/{mission_id}/board-briefing")
async def create_board_briefing_submit(request: Request, mission_id: str):
    form = await request.form()
    _validate_form_csrf(request, form)
    try:
        briefing = request.app.state.ctx.service.create_board_briefing(mission_id)
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", str(exc), "error")
    return _redirect(f"/app/missions/{mission_id}", f"Board briefing ready: {briefing.id}", "success")


@router.post("/app/missions/{mission_id}/approval")
async def create_approval_submit(request: Request, mission_id: str):
    form = await request.form()
    _validate_form_csrf(request, form)
    try:
        request.app.state.ctx.service.create_approval(
            ApprovalCreateRequest(
                mission_id=mission_id,
                category=str(form.get("category", "change_strategy")),
                reason=str(form.get("reason", "Manual checkpoint requested by owner.")),
            )
        )
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", str(exc), "error")
    return _redirect(f"/app/missions/{mission_id}", "Approval checkpoint created.", "success")


@router.post("/app/approvals/{approval_id}/{status}")
async def resolve_approval_submit(request: Request, approval_id: str, status: str):
    form = await request.form()
    _validate_form_csrf(request, form)
    try:
        request.app.state.ctx.service.resolve_approval(approval_id, status)
    except Exception as exc:
        return _redirect("/app/overview", str(exc), "error")
    return _redirect("/app/overview", f"Approval {status}.", "success")
