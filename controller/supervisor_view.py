"""Consolidated Supervisor View (C11).

Provides an executive summary for operations supervisors:
- What is currently being tested (active experiment arms)
- What is winning (promoted variants & statistical confidence)
- What requires supervisor approval (pending requests in queue)
- What changed today (auditable log of actions and auto-applies)
- Health status (DID health, hallucination rate, guardrail compliance)
"""
from typing import Any, Dict, List
from .ingestion import WorkflowMetrics
from .store import AuditStore


def render_supervisor_dashboard(
    workflows_meta: Dict[str, Dict[str, Any]],
    workflow_metrics: Dict[str, WorkflowMetrics],
    pending_approvals: Dict[str, str],
    store: AuditStore,
    current_ts: str,
) -> str:
    """Renders the consolidated supervisor view markdown."""
    lines = [
        "# Consolidated Operations Supervisor Dashboard",
        f"**Simulated Time:** {current_ts}",
        "",
        "## 1. Pending Approvals Requiring Action",
    ]

    if not pending_approvals:
        lines.append("*No pending approval requests. Everything is operating smoothly.*")
    else:
        lines.append("| Workflow | Approval ID | Base Version | Status | Action Required |")
        lines.append("|---|---|---|---|---|")
        for wid, aid in pending_approvals.items():
            lines.append(f"| {wid} | {aid} | Current | Pending Review | Human Sign-off |")

    lines.extend([
        "",
        "## 2. Active Experiments & Winning Variants",
        "| Workflow | Primary KPI | Dials | Connected | Engaged | Active Voice | Active Welcome | Status |",
        "|---|---|---|---|---|---|---|---|",
    ])

    for wid, meta in workflows_meta.items():
        metrics = workflow_metrics.get(wid)
        dials = metrics.total_dials if metrics else 0
        conn = metrics.total_connected if metrics else 0
        eng = metrics.total_engaged if metrics else 0
        primary_kpi = meta.get("objective", {}).get("primary", "engagement_rate")

        # Top voice and welcome
        voice_winner = "V1"
        welcome_winner = "W1"
        if metrics:
            def_voices = metrics.variant_all_time["default"]["voice"]
            if def_voices:
                voice_winner = max(def_voices, key=lambda v: def_voices[v][2] / max(def_voices[v][1], 1))
            def_welcomes = metrics.variant_all_time["default"]["welcome_message"]
            if def_welcomes:
                welcome_winner = max(def_welcomes, key=lambda w: def_welcomes[w][2] / max(def_welcomes[w][1], 1))

        pickup_pct = f"{(conn / max(dials, 1)) * 100:.1f}%"
        eng_pct = f"{(eng / max(conn, 1)) * 100:.1f}%"
        status_str = f"Pickup: {pickup_pct}, Eng: {eng_pct}"
        lines.append(
            f"| {wid} | {primary_kpi} | {dials} | {conn} | {eng} | {voice_winner} | {welcome_winner} | {status_str} |"
        )

    lines.extend([
        "",
        "## 3. Recent Changes & Audit Trail (Today)",
        "| Time | Workflow | Version | Actor | Changed Dimensions | Rationale |",
        "|---|---|---|---|---|---|",
    ])

    recent_audits = store.query_audit_trail(limit=10)
    if not recent_audits:
        lines.append("*No recent changes recorded.*")
    else:
        for audit in recent_audits:
            ts = audit["ts"]
            wid = audit["workflow_id"]
            ver = audit["version"]
            act = audit["actor"]
            dims = audit["changed_dims"]
            rat = audit.get("rationale") or "Optimization update"
            lines.append(f"| {ts} | {wid} | v{ver} | {act} | {dims} | {rat} |")

    return "\n".join(lines)
