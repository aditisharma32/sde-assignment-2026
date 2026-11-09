"""Event Ingestion and Compact Analytics Aggregator (C1, C2).

Streams NDJSON chunks, performs lead/cohort joins, and aggregates metrics incrementally
without storing millions of raw event objects in memory.
Backlog-safe, idempotent, and restartable.
"""
from collections import defaultdict, deque
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("controller.ingestion")


class WorkflowMetrics:
    """Compact in-memory analytics for a single workflow."""

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        # cohort -> dim -> option -> [dials, connected, engaged]
        self.variant_all_time = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0, 0])))
        # day -> cohort -> dim -> option -> [dials, connected, engaged]
        self.variant_by_day = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))))

        # caller_id -> [dials, connected] all-time and rolling
        self.did_all_time = defaultdict(lambda: [0, 0])
        self.did_rolling = defaultdict(lambda: deque(maxlen=250))  # bool: connected

        # cohort -> hour -> [dials, connected]
        self.schedule_stats = defaultdict(lambda: defaultdict(lambda: [0, 0]))
        # person_id -> preferred hour (when they answered/engaged)
        self.person_preferred_hour: Dict[str, int] = {}

        # prompt_version -> [connected, halluc_flags]
        self.prompt_stats = defaultdict(lambda: [0, 0])
        # rolling window of (prompt_version, halluc_flag) for last 200 connected calls
        self.recent_qa_calls: deque = deque(maxlen=200)

        # Totals
        self.total_dials = 0
        self.total_connected = 0
        self.total_engaged = 0
        self.leads_uploaded = 0

    def record_call(self, ev: Dict[str, Any], sim_day: int):
        self.total_dials += 1
        conn = bool(ev.get("connected", False))
        eng = bool(ev.get("engaged", False))

        if conn:
            self.total_connected += 1
        if eng:
            self.total_engaged += 1

        cohort = ev.get("cohort_id") or "default"
        variant = ev.get("variant", {})
        cid = variant.get("caller_id")
        prompt = variant.get("prompt_version")

        # DID stats
        if cid:
            self.did_all_time[cid][0] += 1
            self.did_all_time[cid][1] += int(conn)
            self.did_rolling[cid].append(conn)

        # Variant stats (welcome_message, voice)
        for dim in ("welcome_message", "voice"):
            val = variant.get(dim)
            if val:
                s = self.variant_all_time[cohort][dim][val]
                s[0] += 1
                s[1] += int(conn)
                s[2] += int(eng)

                s_day = self.variant_by_day[sim_day][cohort][dim][val]
                s_day[0] += 1
                s_day[1] += int(conn)
                s_day[2] += int(eng)

        # Call-time schedule stats
        ts = ev.get("ts", "")
        if len(ts) >= 13:
            try:
                hour = int(ts[11:13])
                self.schedule_stats[cohort][hour][0] += 1
                self.schedule_stats[cohort][hour][1] += int(conn)

                # Track per-person successful pickup hour
                pid = ev.get("person_id")
                if pid and conn:
                    self.person_preferred_hour[pid] = hour
            except ValueError:
                pass

        # QA and Hallucination stats
        if conn and prompt:
            qa = ev.get("qa") or {}
            halluc_flag = bool(qa.get("hallucination_flag", False))
            self.prompt_stats[prompt][0] += 1
            self.prompt_stats[prompt][1] += int(halluc_flag)
            self.recent_qa_calls.append((prompt, halluc_flag))


class IngestionEngine:
    """Processes event chunks from simulator and updates compact analytics."""

    def __init__(self):
        self.workflows: Dict[str, WorkflowMetrics] = {}
        self.last_processed_chunk = -1
        self.last_event_id = 0
        self.current_sim_minute = 0
        self.current_sim_day = 0

        # Event listeners for supervisor edits, approvals, etc.
        self.on_supervisor_edit: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_approval_decided: Optional[Callable[[Dict[str, Any]], None]] = None

    def get_or_create_workflow(self, wid: str) -> WorkflowMetrics:
        if wid not in self.workflows:
            self.workflows[wid] = WorkflowMetrics(wid)
        return self.workflows[wid]

    def process_chunk(self, chunk_meta: Dict[str, Any], lines_iter):
        """Processes a single NDJSON chunk line by line."""
        chunk_num = chunk_meta["chunk"]
        for line in lines_iter:
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue

            ev_id = ev.get("event_id", 0)
            if ev_id <= self.last_event_id and self.last_event_id > 0:
                # Idempotency check: skip already processed events
                continue

            self.last_event_id = max(self.last_event_id, ev_id)
            ev_type = ev.get("type")

            if ev_type == "call":
                wid = ev.get("workflow_id")
                if wid:
                    wf = self.get_or_create_workflow(wid)
                    wf.record_call(ev, self.current_sim_day)

            elif ev_type == "campaign_created":
                wid = ev.get("workflow_id")
                if wid:
                    wf = self.get_or_create_workflow(wid)
                    wf.leads_uploaded += ev.get("leads", 0)

            elif ev_type == "config_changed":
                actor = ev.get("actor")
                if actor == "supervisor" and self.on_supervisor_edit:
                    self.on_supervisor_edit(ev)

            elif ev_type == "approval_decided":
                if self.on_approval_decided:
                    self.on_approval_decided(ev)

        self.last_processed_chunk = max(self.last_processed_chunk, chunk_num)
