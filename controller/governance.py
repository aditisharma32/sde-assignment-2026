"""Governance Manager, Approval Lifecycle, and Auto-Apply Engine (C9, C10).

Manages:
- Proposal state machine: pending -> approved | rejected | expired, approved -> applied | lapsed.
- Approver timing (approver_hours) & fatigue protection (max_requests_per_24h).
- Total-Variation Distance step-clamping for compliant Auto-Apply.
- Honest impact scores, affected lead estimates, and counterfactual dry runs (C10).
- Stale base version handling on supervisor edits.
"""
import copy
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from .client import SimulatorClient
from .config import ControllerConfig
from .store import AuditStore

logger = logging.getLogger("controller.governance")

AGENT_DIMS = ["welcome_message", "voice", "caller_id"]
CHANGE_DIMS = ["cohorts"] + AGENT_DIMS + ["prompt_version", "schedule"]


def compute_changed_dims(old: Dict[str, Any], new: Dict[str, Any]) -> List[str]:
    ch = []
    if old.get("cohorts") != new.get("cohorts"):
        ch.append("cohorts")

    keys = set(old.get("allocations", {})) | set(new.get("allocations", {}))

    def _dist(cfg, k, d):
        return (cfg.get("allocations", {}).get(k) or {}).get(d) or cfg.get("allocations", {}).get("default", {}).get(d, {})

    for dim in AGENT_DIMS:
        if any(_dist(old, k, dim) != _dist(new, k, dim) for k in keys):
            ch.append(dim)

    if old.get("prompt_version") != new.get("prompt_version"):
        ch.append("prompt_version")
    if old.get("schedule") != new.get("schedule"):
        ch.append("schedule")
    return [d for d in CHANGE_DIMS if d in ch]


def compute_max_shift(old: Dict[str, Any], new: Dict[str, Any]) -> float:
    """Largest total-variation distance of any agent-dim allocation across cohorts."""
    keys = {"default"} | {c["id"] for c in old.get("cohorts", [])} | {c["id"] for c in new.get("cohorts", [])}
    worst = 0.0

    def _dist(cfg, k, d):
        return (cfg.get("allocations", {}).get(k) or {}).get(d) or cfg.get("allocations", {}).get("default", {}).get(d, {})

    for k in keys:
        for dim in AGENT_DIMS:
            a, b = _dist(old, k, dim), _dist(new, k, dim)
            tv = 0.5 * sum(abs(a.get(o, 0.0) - b.get(o, 0.0)) for o in set(a) | set(b))
            worst = max(worst, tv)
    return worst


def clamp_shift_toward(old: Dict[str, Any], target: Dict[str, Any], max_shift: float) -> Dict[str, Any]:
    """
    If total variation distance exceeds max_shift, linearly interpolates toward target
    such that shift <= max_shift.
    """
    current_shift = compute_max_shift(old, target)
    if current_shift <= max_shift + 1e-9:
        return target

    # Scale step alpha
    alpha = max_shift / max(current_shift, 1e-6)
    result = copy.deepcopy(old)

    keys = set(old.get("allocations", {})) | set(target.get("allocations", {}))
    for k in keys:
        if k not in result.setdefault("allocations", {}):
            result["allocations"][k] = {}
        for dim in AGENT_DIMS:
            old_d = (old.get("allocations", {}).get(k) or {}).get(dim) or old.get("allocations", {}).get("default", {}).get(dim, {})
            tgt_d = (target.get("allocations", {}).get(k) or {}).get(dim) or target.get("allocations", {}).get("default", {}).get(dim, {})
            opts = set(old_d) | set(tgt_d)
            blended = {}
            for o in opts:
                blended[o] = (1.0 - alpha) * old_d.get(o, 0.0) + alpha * tgt_d.get(o, 0.0)
            s = sum(blended.values())
            if s > 0:
                result["allocations"][k][dim] = {o: w / s for o, w in blended.items()}

    # Copy schedule and cohorts if permitted
    result["cohorts"] = copy.deepcopy(target.get("cohorts", []))
    result["schedule"] = copy.deepcopy(target.get("schedule", {}))
    return result


class GovernanceManager:
    """Coordinates proposal creation, validation, auto-apply, and approval tracking."""

    def __init__(self, client: SimulatorClient, store: AuditStore, cfg: ControllerConfig):
        self.client = client
        self.store = store
        self.cfg = cfg
        # workflow_id -> active approval_id
        self.pending_approvals: Dict[str, str] = {}
        # workflow_id -> list of proposal request minutes in last 24h
        self.request_history_24h: Dict[str, List[int]] = {}

    def is_approver_active_now(self, wf_meta: Dict[str, Any], current_sim_minute: int) -> bool:
        """Checks if approver is currently working or will be awake before proposal TTL."""
        gov = wf_meta.get("governance", {})
        lo, hi = gov.get("approver_hours", [10, 19])
        ttl_hours = gov.get("proposal_ttl_hours", 24)

        mod = current_sim_minute % 1440
        hour = mod // 60

        # Currently in working hours?
        if lo <= hour < hi:
            return True

        # If outside working hours, will proposal survive until next working window?
        # Minutes until next start of working hours:
        if hour < lo:
            mins_until_lo = (lo - hour) * 60 - (mod % 60)
        else:
            mins_until_lo = (24 - hour + lo) * 60 - (mod % 60)

        ttl_mins = ttl_hours * 60
        # If TTL has plenty of margin after approver shift starts
        if ttl_mins >= mins_until_lo + 180:
            return True
        return False

    def can_request_approval(self, wid: str, wf_meta: Dict[str, Any], current_sim_minute: int) -> bool:
        """Verifies approver fatigue limits (max_requests_per_24h) and pending locks."""
        if wid in self.pending_approvals:
            return False

        gov = wf_meta.get("governance", {})
        max_req = gov.get("max_requests_per_24h", 3)

        history = self.request_history_24h.get(wid, [])
        # Prune older than 24h (1440 mins)
        recent = [m for m in history if m > current_sim_minute - 1440]
        self.request_history_24h[wid] = recent

        if len(recent) >= max_req:
            return False

        return self.is_approver_active_now(wf_meta, current_sim_minute)

    def reconcile_pending_approvals(self, current_sim_minute: int, current_ts: str):
        """Polls simulator for any pending approvals and applies approved changes."""
        for wid, aid in list(self.pending_approvals.items()):
            try:
                ap = self.client.get_approval(aid)
                status = ap.get("status")

                if status == "approved":
                    resp = self.client.apply_approval(wid, aid)
                    if resp.status_code == 200:
                        v = resp.json().get("version")
                        changed = resp.json().get("changed_dims", [])
                        logger.info(f"Applied approved proposal {aid} on {wid} -> v{v}")
                        self.store.record_audit(
                            ts=current_ts,
                            sim_minute=current_sim_minute,
                            workflow_id=wid,
                            actor="controller_approved",
                            version=v,
                            changed_dims=changed,
                            approval_id=aid,
                            rationale="Approved change applied",
                        )
                    self.pending_approvals.pop(wid, None)
                    self.store.update_proposal_status(
                        proposal_id=ap.get("proposal_id", aid),
                        status=status,
                        decided_minute=current_sim_minute,
                        decided_ts=current_ts,
                        reasons=ap.get("reasons"),
                    )

                elif status in ("rejected", "expired", "lapsed"):
                    logger.info(f"Proposal {aid} on {wid} resolved with {status}: {ap.get('reasons')}")
                    self.pending_approvals.pop(wid, None)
                    self.store.update_proposal_status(
                        proposal_id=ap.get("proposal_id", aid),
                        status=status,
                        decided_minute=current_sim_minute,
                        decided_ts=current_ts,
                        reasons=ap.get("reasons"),
                    )
            except Exception as e:
                logger.warning(f"Error checking approval {aid} on {wid}: {e}")

    def try_apply_or_propose(
        self,
        wid: str,
        wf_meta: Dict[str, Any],
        proposed_config: Dict[str, Any],
        summary: str,
        rationale: str,
        affected_leads: int,
        impact_score: float,
        dry_run: Dict[str, Any],
        current_sim_minute: int,
        current_ts: str,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Attempts to apply via policy-permitted Auto-Apply if eligible.
        Otherwise routes through human approval if within approver capacity.
        """
        cur = self.client.get_config(wid)
        base_version = cur["version"]
        current_config = cur["config"]

        changed = compute_changed_dims(current_config, proposed_config)
        if not changed:
            return False

        gov = wf_meta.get("governance", {})
        auto_pol = gov.get("auto_apply", {})

        # Check Auto-Apply eligibility
        can_auto_apply = (
            auto_pol.get("enabled", False)
            and all(d in auto_pol.get("allowed_dims", []) for d in changed)
        )

        proposal_id = f"prop_{uuid.uuid4().hex[:12]}"

        if can_auto_apply:
            max_sh = auto_pol.get("max_shift", 0.5)
            # Clamp shift to max_shift if necessary
            target_cfg = clamp_shift_toward(current_config, proposed_config, max_sh)
            diff = {"changed_dims": changed}

            body = {
                "proposal_id": proposal_id,
                "base_version": base_version,
                "proposed_config": target_cfg,
                "rationale": rationale,
            }
            if evidence:
                body["evidence"] = evidence

            resp = self.client.auto_apply(wid, body)
            if resp.status_code == 200:
                v = resp.json().get("version")
                actual_changed = resp.json().get("changed_dims", changed)
                logger.info(f"Auto-applied config on {wid} -> v{v} dims={actual_changed}")
                self.store.record_audit(
                    ts=current_ts,
                    sim_minute=current_sim_minute,
                    workflow_id=wid,
                    actor="controller_auto",
                    version=v,
                    changed_dims=actual_changed,
                    proposal_id=proposal_id,
                    rationale=rationale,
                    impact_score=impact_score,
                    affected_leads=affected_leads,
                    dry_run=dry_run,
                )
                return True
            else:
                logger.warning(f"Auto-apply returned {resp.status_code}: {resp.text}")

        # Human Approval Path
        if not self.can_request_approval(wid, wf_meta, current_sim_minute):
            return False

        diff = {"changed_dims": changed}
        body = {
            "proposal_id": proposal_id,
            "workflow_id": wid,
            "base_version": base_version,
            "proposed_config": proposed_config,
            "change_summary": summary,
            "diff": diff,
            "affected_leads": max(0, int(affected_leads)),
            "dry_run": dry_run,
            "impact_score": max(0.0, min(1.0, float(impact_score))),
            "rationale": rationale,
        }
        if evidence:
            body["evidence"] = evidence

        resp = self.client.request_approval(body)
        if resp.status_code == 200:
            data = resp.json()
            aid = data.get("approval_id")
            self.pending_approvals[wid] = aid
            self.request_history_24h.setdefault(wid, []).append(current_sim_minute)
            logger.info(f"Submitted approval {aid} for {wid} (impact: {impact_score:.2f})")
            self.store.record_proposal(
                proposal_id=proposal_id,
                workflow_id=wid,
                base_version=base_version,
                actor="controller_requested",
                created_minute=current_sim_minute,
                created_ts=current_ts,
                expires_ts=data.get("expires_at", ""),
                request=body,
            )
            return True
        else:
            logger.warning(f"Approval request failed ({resp.status_code}): {resp.text}")
            return False
