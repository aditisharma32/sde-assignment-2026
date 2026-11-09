"""Population-Level Anomaly, Drift, and Incident Detector (C5, C7, C8).

Threshold-based detection operating on populations, never on anecdotes or single calls.
"""
from typing import Any, Dict, List, Optional, Set, Tuple
from .config import ControllerConfig
from .ingestion import WorkflowMetrics


class AnomalyDetector:
    """Detects caller-ID degradation, hallucination incidents, and variant decay."""

    def __init__(self, cfg: ControllerConfig):
        self.cfg = cfg

    def detect_degraded_dids(
        self, wf_metrics: WorkflowMetrics, all_dids: List[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Detects caller IDs that have suffered reputation degradation or spam-flagging.
        Returns: (healthy_dids, degraded_dids)
        """
        rates: Dict[str, float] = {}
        counts: Dict[str, int] = {}

        for did in all_dids:
            rolling = wf_metrics.did_rolling[did]
            if len(rolling) >= self.cfg.did_min_dials_to_evaluate:
                rates[did] = sum(rolling) / len(rolling)
                counts[did] = len(rolling)
            else:
                all_t = wf_metrics.did_all_time[did]
                if all_t[0] >= self.cfg.did_min_dials_to_evaluate:
                    rates[did] = all_t[1] / all_t[0]
                    counts[did] = all_t[0]

        if len(rates) < 2:
            return all_dids, []

        healthy: List[str] = []
        degraded: List[str] = []

        for did in all_dids:
            if did not in rates:
                # Untested DID
                healthy.append(did)
                continue

            # Peer average among evaluated DIDs excluding this DID
            peers = [r for d, r in rates.items() if d != did]
            peer_avg = sum(peers) / len(peers) if peers else rates[did]

            # If pickup rate is severely below peer average
            if peer_avg > 0.10 and rates[did] < peer_avg * self.cfg.did_degradation_drop_ratio:
                degraded.append(did)
            else:
                healthy.append(did)

        # Always keep at least one DID healthy
        if not healthy and degraded:
            best_did = max(degraded, key=lambda d: rates.get(d, 0.0))
            healthy.append(best_did)
            degraded.remove(best_did)

        return healthy, degraded

    def detect_hallucination_incident(
        self, wf_metrics: WorkflowMetrics, current_prompt: str
    ) -> Optional[Dict[str, Any]]:
        """
        Detects abnormal spikes in hallucination flags on connected calls.
        Normal baseline hallucination flag rate is ~1.4%; an incident spikes to >5%.
        """
        calls_on_cur = [flag for prompt, flag in wf_metrics.recent_qa_calls if prompt == current_prompt]
        if len(calls_on_cur) < self.cfg.halluc_min_connected:
            return None

        flag_count = sum(calls_on_cur)
        flag_rate = flag_count / len(calls_on_cur)

        if flag_rate >= self.cfg.halluc_alert_rate:
            return {
                "workflow_id": wf_metrics.workflow_id,
                "current_prompt": current_prompt,
                "sample_size": len(calls_on_cur),
                "flag_count": flag_count,
                "flag_rate": round(flag_rate, 4),
                "threshold": self.cfg.halluc_alert_rate,
            }
        return None

    def detect_variant_decay(
        self,
        wf_metrics: WorkflowMetrics,
        cohort: str,
        dim: str,
        active_variant: str,
        current_day: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Detects if an active winning variant has started decaying in engagement.
        Compares recent 2-day performance vs earlier days.
        """
        recent_conn = 0
        recent_eng = 0
        for d in range(max(0, current_day - self.cfg.decay_eval_window_days + 1), current_day + 1):
            s = wf_metrics.variant_by_day[d][cohort][dim][active_variant]
            recent_conn += s[1]
            recent_eng += s[2]

        if recent_conn < 60:
            return None

        recent_rate = recent_eng / recent_conn

        # Historical peak before recent window
        historical_conn = 0
        historical_eng = 0
        for d in range(0, max(0, current_day - self.cfg.decay_eval_window_days + 1)):
            s = wf_metrics.variant_by_day[d][cohort][dim][active_variant]
            historical_conn += s[1]
            historical_eng += s[2]

        if historical_conn < 80:
            return None

        historical_rate = historical_eng / historical_conn

        if historical_rate > 0.30 and (historical_rate - recent_rate) / historical_rate >= self.cfg.decay_drop_threshold:
            return {
                "cohort": cohort,
                "dim": dim,
                "variant": active_variant,
                "historical_rate": round(historical_rate, 4),
                "recent_rate": round(recent_rate, 4),
                "drop_pct": round((historical_rate - recent_rate) / historical_rate, 4),
            }
        return None
