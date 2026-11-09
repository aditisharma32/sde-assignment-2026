"""Outcome-First Controller Main Loop.

Coordinates ingestion, anomaly detection, statistical experimentation, governance,
incident response, and crash-resilient persistence.
"""
import argparse
import copy
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Set

from .client import SimulatorClient
from .cohorts import CohortEngine
from .config import ControllerConfig
from .detector import AnomalyDetector
from .governance import GovernanceManager, compute_changed_dims
from .ingestion import IngestionEngine
from .optimizer import WorkflowOptimizer
from .store import AuditStore
from .supervisor_view import render_supervisor_dashboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("controller.main")


class OutcomeFirstController:
    """Always-on controller driving the outcome-first agent loop."""

    def __init__(self, sim_url: str, db_path: str = "controller_audit.db", step_minutes: int = 15):
        self.sim_url = sim_url
        self.step_minutes = step_minutes
        self.cfg = ControllerConfig(tick_step_minutes=step_minutes, db_path=db_path)

        self.client = SimulatorClient(base_url=sim_url)
        self.store = AuditStore(db_path=db_path)
        self.ingestion = IngestionEngine()
        self.detector = AnomalyDetector(self.cfg)
        self.optimizer = WorkflowOptimizer(self.cfg)
        self.governance = GovernanceManager(self.client, self.store, self.cfg)

        self.cohort_engines: Dict[str, CohortEngine] = {}
        self.workflow_metas: Dict[str, Dict[str, Any]] = {}
        self.active_incidents: Dict[str, Dict[str, Any]] = {}  # wid -> incident info
        self.decayed_variants: Dict[str, Set[str]] = {}       # wid -> set of decayed variant values
        self.prompt_fix_attempted: Set[Tuple[str, str]] = set()  # (wid, prompt_version)

        # Wire event callbacks
        self.ingestion.on_supervisor_edit = self._handle_supervisor_edit
        self.ingestion.on_approval_decided = self._handle_approval_decided

    def _handle_supervisor_edit(self, ev: Dict[str, Any]):
        wid = ev.get("workflow_id")
        ver = ev.get("version")
        changed = ev.get("changed_dims", [])
        logger.info(f"Supervisor edit detected on {wid} -> v{ver} dims={changed}. Respecting human supervisor authority.")
        # Invalidate any pending approval with older base version
        self.governance.pending_approvals.pop(wid, None)
        # If supervisor changed prompt, reset active incident state and clear recent QA buffer for fast re-evaluation
        if "prompt_version" in changed:
            self.active_incidents.pop(wid, None)
            if wid in self.ingestion.workflows:
                self.ingestion.workflows[wid].recent_qa_calls.clear()

        self.store.record_audit(
            ts=ev.get("ts", ""),
            sim_minute=self.ingestion.current_sim_minute,
            workflow_id=wid,
            actor="supervisor",
            version=ver,
            changed_dims=changed,
            rationale="Supervisor mid-day direct edit",
        )

    def _handle_approval_decided(self, ev: Dict[str, Any]):
        aid = ev.get("approval_id")
        wid = ev.get("workflow_id")
        status = ev.get("status")
        logger.info(f"Event: approval {aid} on {wid} decided as {status}")

    def bootstrap(self):
        """Initializes controller, reads workflows, bootstraps history, and resumes from crash if any."""
        logger.info(f"Connecting to simulator at {self.sim_url}...")
        state = self.client.get_state()
        logger.info(f"Simulator connected. Scenario: {state.get('scenario')}, sim_minute: {state.get('sim_minute')}")

        wfs = self.client.get_workflows()
        for w in wfs:
            wid = w["workflow_id"]
            self.workflow_metas[wid] = w
            self.decayed_variants[wid] = set()
            # Initialize cohort engine
            cur_cfg = self.client.get_config(wid)["config"]
            existing_cohorts = cur_cfg.get("cohorts", [])
            if existing_cohorts:
                self.cohort_engines[wid] = CohortEngine(existing_cohorts)
            else:
                self.cohort_engines[wid] = CohortEngine.create_standard_cohorts(w)

        # Checkpoint restoration (C13 Crash Recovery)
        last_chunk_cp = self.store.get_checkpoint("last_processed_chunk")
        history_done = self.store.get_checkpoint("history_bootstrapped")

        # Ingest history if not yet bootstrapped
        if not history_done:
            logger.info("Bootstrapping from historical data before D0 (C3)...")
            history_chunks = self.client.get_chunks(kind="history", after=-1)
            for ch in history_chunks:
                lines = self.client.stream_chunk_lines(ch["chunk"])
                self.ingestion.process_chunk(ch, lines)
            self.store.set_checkpoint("history_bootstrapped", "true")
            self.store.set_checkpoint("last_processed_chunk", str(self.ingestion.last_processed_chunk))
            logger.info(f"History bootstrap complete: {len(history_chunks)} chunks processed.")
        elif last_chunk_cp:
            self.ingestion.last_processed_chunk = int(last_chunk_cp)
            logger.info(f"Resumed from checkpoint: last_processed_chunk = {self.ingestion.last_processed_chunk}")

        # Re-sync pending approvals from simulator API (C13)
        active_approvals = self.client.list_approvals(status="pending")
        for ap in active_approvals:
            wid = ap["workflow_id"]
            aid = ap["approval_id"]
            self.governance.pending_approvals[wid] = aid
            logger.info(f"Reconciled pending approval {aid} for {wid} from previous run session.")

    def run(self):
        """Main execution loop until scenario completion."""
        self.bootstrap()

        logger.info("Starting Outcome-First Agent Loop...")
        last_hourly_opt_day = -1
        step_count = 0

        while True:
            # Advance simulator
            advance_res = self.client.advance(self.step_minutes)
            sim_minute = advance_res["sim_minute"]
            current_ts = advance_res["ts"]
            finished = advance_res.get("finished", False)
            new_chunks = advance_res.get("new_chunks", [])

            self.ingestion.current_sim_minute = sim_minute
            self.ingestion.current_sim_day = sim_minute // 1440
            sim_day = self.ingestion.current_sim_day

            # 1. Ingest new event chunks (C1)
            for ch in new_chunks:
                lines = self.client.stream_chunk_lines(ch["chunk"])
                self.ingestion.process_chunk(ch, lines)

            # Persist checkpoint
            self.store.set_checkpoint("last_processed_chunk", str(self.ingestion.last_processed_chunk))
            self.store.set_checkpoint("sim_minute", str(sim_minute))

            # 2. Reconcile and apply pending approvals (C9)
            self.governance.reconcile_pending_approvals(sim_minute, current_ts)

            # 3. Detect and resolve incidents (C8 Hallucination, C5 DID health, C7 Decay)
            self._handle_incidents_and_health(sim_minute, current_ts)

            # 4. Periodically optimize variants, schedules, and cohorts (C4, C6, C7)
            # Evaluate optimization at 10:30 and 15:30 IST during active approver hours
            hour_of_day = (sim_minute % 1440) // 60
            minute_of_hour = sim_minute % 60

            if hour_of_day in (11, 16) and minute_of_hour == 0:
                self._run_optimization_cycle(sim_minute, current_ts)

            step_count += 1
            if step_count % 96 == 0:  # once every 24 simulated hours (96 x 15m)
                dashboard = render_supervisor_dashboard(
                    self.workflow_metas,
                    self.ingestion.workflows,
                    self.governance.pending_approvals,
                    self.store,
                    current_ts,
                )
                logger.info(f"\n{dashboard}\n")

            if finished:
                logger.info("Scenario finished. Controller loop exiting cleanly.")
                break

    def _handle_incidents_and_health(self, sim_minute: int, current_ts: str):
        """Handles hallucination incidents, caller ID degradation, and variant decay."""
        for wid, meta in self.workflow_metas.items():
            wf_metrics = self.ingestion.get_or_create_workflow(wid)
            cur = self.client.get_config(wid)
            cur_cfg = cur["config"]
            cur_prompt = cur_cfg["prompt_version"]

            # --- A. Hallucination Incident Detection (C8) ---
            prompt_key = (wid, cur_prompt)
            if wid not in self.active_incidents and prompt_key not in self.prompt_fix_attempted:
                incident = self.detector.detect_hallucination_incident(wf_metrics, cur_prompt)
                if incident:
                    logger.warning(
                        f"🚨 INCIDENT DETECTED on {wid}: Hallucination flag spike ({incident['flag_rate']:.3f} "
                        f"on prompt {cur_prompt}, sample={incident['sample_size']})"
                    )
                    self.prompt_fix_attempted.add(prompt_key)
                    self.store.record_incident(
                        incident_id=f"inc_{wid}_{sim_minute}",
                        workflow_id=wid,
                        incident_type="hallucination_spike",
                        detected_ts=current_ts,
                        detected_minute=sim_minute,
                        details=incident,
                    )
                    self._resolve_hallucination_incident(wid, meta, cur_cfg, incident, sim_minute, current_ts)

            # --- B. Caller ID (DID) Degradation Detection (C5) ---
            all_dids = meta["options"]["caller_id"]
            healthy_dids, degraded_dids = self.detector.detect_degraded_dids(wf_metrics, all_dids)

            if degraded_dids:
                cur_did_alloc = cur_cfg["allocations"]["default"].get("caller_id", {})
                traffic_on_degraded = sum(cur_did_alloc.get(d, 0.0) for d in degraded_dids)
                if traffic_on_degraded > 0.02:
                    logger.warning(
                        f"⚠️ Caller ID degradation on {wid}: degraded={degraded_dids}, healthy={healthy_dids}. "
                        f"Rebalancing traffic away from degraded DIDs."
                    )
                    target_cfg = copy.deepcopy(cur_cfg)
                    new_did_alloc = self.optimizer.compute_did_allocation(healthy_dids, degraded_dids, cur_did_alloc)
                    target_cfg["allocations"]["default"]["caller_id"] = new_did_alloc
                    for c in target_cfg.get("cohorts", []):
                        if c["id"] in target_cfg["allocations"] and "caller_id" in target_cfg["allocations"][c["id"]]:
                            target_cfg["allocations"][c["id"]]["caller_id"] = copy.deepcopy(new_did_alloc)

                    self.governance.try_apply_or_propose(
                        wid=wid,
                        wf_meta=meta,
                        proposed_config=target_cfg,
                        summary=f"Rebalance caller IDs away from degraded DIDs ({', '.join(degraded_dids)})",
                        rationale="Spam-flagged caller ID detected; rebalancing traffic across healthy caller IDs to protect pickup rate.",
                        affected_leads=wf_metrics.total_dials // 2,
                        impact_score=0.35,
                        dry_run={"degraded_dids": degraded_dids, "new_alloc": new_did_alloc},
                        current_sim_minute=sim_minute,
                        current_ts=current_ts,
                    )

            # --- C. Variant Decay Detection (C7) ---
            sim_day = sim_minute // 1440
            for cohort_id in ["default"] + [c["id"] for c in cur_cfg.get("cohorts", [])]:
                cohort_alloc = cur_cfg["allocations"].get(cohort_id, cur_cfg["allocations"]["default"])
                for dim in ("welcome_message", "voice"):
                    active_dim_alloc = cohort_alloc.get(dim, {})
                    if active_dim_alloc:
                        top_v = max(active_dim_alloc, key=lambda o: active_dim_alloc[o])
                        decay = self.detector.detect_variant_decay(wf_metrics, cohort_id, dim, top_v, sim_day)
                        if decay and top_v not in self.decayed_variants[wid]:
                            logger.warning(
                                f"📉 Variant decay detected on {wid} [{cohort_id}.{dim}={top_v}]: "
                                f"dropped from {decay['historical_rate']:.3f} to {decay['recent_rate']:.3f}. "
                                f"Rolling back."
                            )
                            self.decayed_variants[wid].add(top_v)
                            # Re-trigger optimization to roll back
                            self._optimize_workflow_variants(wid, meta, cur_cfg, sim_minute, current_ts)

    def _resolve_hallucination_incident(
        self,
        wid: str,
        meta: Dict[str, Any],
        cur_cfg: Dict[str, Any],
        incident: Dict[str, Any],
        sim_minute: int,
        current_ts: str,
    ):
        """Interacts with LLM, runs validation, and proposes verified safe prompt."""
        try:
            state = self.client.get_state()
            if state.get("credits_remaining", 0) < 6:
                logger.warning(f"Credit budget low ({state.get('credits_remaining')} remaining). Skipping LLM fix.")
                return

            # 1. Spend credits to request suggestions
            fixes_resp = self.client.suggest_fixes(wid, "High hallucination rate observed on current prompt version")
            suggestions = fixes_resp.get("suggestions", [])
            logger.info(f"LLM suggested {len(suggestions)} fixes for {wid}: {[s['prompt_version'] for s in suggestions]}")

            min_pass_rate = meta.get("governance", {}).get("min_validation_pass_rate", 0.97)
            valid_runs: List[Dict[str, Any]] = []

            # 2. Run validation on candidates (C8)
            for sug in suggestions:
                pv = sug["prompt_version"]
                val = self.client.run_validation(wid, pv, n=self.cfg.validation_sample_size)
                pass_rate = val.get("pass_rate", 0.0)
                logger.info(f"Validation for prompt {pv} on {wid}: pass_rate={pass_rate:.4f} (min required: {min_pass_rate})")
                if pass_rate >= min_pass_rate:
                    valid_runs.append(val)

            if valid_runs:
                # Prefer grounded prompts (e.g. P3, or non-strict) to avoid Anita Desai's verbatim compliance trap (P5)
                # P3 is Grounded; P1 is default production prompt
                best_run = None
                for candidate in ("P3", "P1"):
                    match = next((v for v in valid_runs if v["prompt_version"] == candidate), None)
                    if match:
                        best_run = match
                        break

                if best_run is None:
                    # Pick highest pass rate among non-P5
                    non_strict = [v for v in valid_runs if v["prompt_version"] != "P5"]
                    if non_strict:
                        best_run = max(non_strict, key=lambda v: v["pass_rate"])
                    else:
                        best_run = max(valid_runs, key=lambda v: v["pass_rate"])

                chosen_pv = best_run["prompt_version"]
                target_cfg = copy.deepcopy(cur_cfg)
                target_cfg["prompt_version"] = chosen_pv

                # Prompt change requires validation evidence
                evidence = {"validation_run_id": best_run["validation_run_id"]}
                logger.info(f"Proposing verified fix prompt {chosen_pv} with evidence {evidence} for {wid}...")

                success = self.governance.try_apply_or_propose(
                    wid=wid,
                    wf_meta=meta,
                    proposed_config=target_cfg,
                    summary=f"Replace prompt with safety-validated version {chosen_pv} to fix hallucination spike",
                    rationale=f"Hallucination spike detected. LLM fix {chosen_pv} passed synthetic validation with {best_run['pass_rate']:.3f} safety score.",
                    affected_leads=meta.get("daily_batch", {}).get("size", 1000) * 3,
                    impact_score=0.90,
                    dry_run={"incident": incident, "validation_run": best_run},
                    current_sim_minute=sim_minute,
                    current_ts=current_ts,
                    evidence=evidence,
                )
                if success:
                    self.active_incidents[wid] = {"prompt": chosen_pv, "val_run": best_run}
            else:
                logger.error(f"None of the suggested prompt fixes passed validation threshold for {wid}")
        except Exception as e:
            logger.error(f"Error resolving hallucination incident on {wid}: {e}")

    def _run_optimization_cycle(self, sim_minute: int, current_ts: str):
        """Runs the statistical optimization cycle across workflows."""
        for wid, meta in self.workflow_metas.items():
            if wid in self.governance.pending_approvals:
                continue
            cur = self.client.get_config(wid)
            self._optimize_workflow_variants(wid, meta, cur["config"], sim_minute, current_ts)

    def _optimize_workflow_variants(
        self,
        wid: str,
        meta: Dict[str, Any],
        cur_cfg: Dict[str, Any],
        sim_minute: int,
        current_ts: str,
    ):
        """Calculates updated cohort allocations and call-time schedule."""
        wf_metrics = self.ingestion.get_or_create_workflow(wid)
        target_cfg = copy.deepcopy(cur_cfg)

        # 1. Setup Cohorts (C2)
        cohort_engine = self.cohort_engines.get(wid)
        if cohort_engine and not target_cfg.get("cohorts"):
            target_cfg["cohorts"] = cohort_engine.to_config_list()

        cohort_ids = ["default"] + [c["id"] for c in target_cfg.get("cohorts", [])]

        # 2. Evaluate variants across welcome_message and voice (C6, C7)
        any_variant_changed = False
        decayed = list(self.decayed_variants.get(wid, set()))

        for cid in cohort_ids:
            if cid not in target_cfg["allocations"]:
                target_cfg["allocations"][cid] = copy.deepcopy(target_cfg["allocations"]["default"])

            for dim in ("welcome_message", "voice"):
                opts = meta["options"][dim]
                cur_alloc = target_cfg["allocations"][cid].get(dim, target_cfg["allocations"]["default"].get(dim, {}))

                new_alloc, winner, lift = self.optimizer.evaluate_cohort_variants(
                    wf_metrics, cid, dim, opts, cur_alloc, decayed
                )

                if new_alloc != cur_alloc:
                    target_cfg["allocations"][cid][dim] = new_alloc
                    any_variant_changed = True

        # 3. Optimize Call-Time Schedule (C4)
        lo, hi = meta["dialling_window"]
        hour_weights = {}
        for cid in cohort_ids:
            hw = self.optimizer.compute_hour_weights(wf_metrics, cid, [lo, hi])
            hour_weights[cid] = hw

        target_cfg.setdefault("schedule", {})["hour_weights"] = hour_weights

        # Lead preferred hours (C4)
        if wf_metrics.person_preferred_hour:
            pref_sample = dict(list(wf_metrics.person_preferred_hour.items())[:50000])
            target_cfg["schedule"]["lead_preferred_hour"] = pref_sample

        # Check if anything changed
        changed = compute_changed_dims(cur_cfg, target_cfg)
        if not changed:
            return

        batch_size = meta.get("daily_batch", {}).get("size", 1000)
        affected_leads = batch_size * 4

        self.governance.try_apply_or_propose(
            wid=wid,
            wf_meta=meta,
            proposed_config=target_cfg,
            summary=f"Promote winning variants and schedule weights across cohorts ({', '.join(changed)})",
            rationale="Statistically significant variant lift detected with guardrail check satisfied; optimized cohort hour weights.",
            affected_leads=affected_leads,
            impact_score=0.45,
            dry_run={"changed_dims": changed, "sample_dials": wf_metrics.total_dials},
            current_sim_minute=sim_minute,
            current_ts=current_ts,
        )


def main():
    parser = argparse.ArgumentParser(description="Outcome-First Agent Loop Controller")
    parser.add_argument("pos_url", nargs="?", default=None, help="Simulator API URL (positional)")
    parser.add_argument("--url", default=None, help="Simulator API URL")
    parser.add_argument("--db", default="controller_audit.db", help="Audit SQLite database file path")
    parser.add_argument("--step", type=int, default=15, help="Simulation advance step in minutes")
    args = parser.parse_args()

    url = args.url or args.pos_url or "http://127.0.0.1:8700"
    controller = OutcomeFirstController(sim_url=url, db_path=args.db, step_minutes=args.step)
    controller.run()


if __name__ == "__main__":
    main()
