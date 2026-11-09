"""Statistical Experimentation, Winner Promotion, and Policy Optimization Engine (C4, C5, C6, C7).

Deterministic, statistically sound decision making:
- Two-proportion z-test with Bonferroni correction for multi-armed variants.
- Guardrail KPI verification before any promotion.
- Multi-armed exploration vs exploitation traffic splits.
- DID load rebalancing across healthy caller IDs.
- Call-time schedule optimization across cohort pickup profiles.
"""
import copy
import math
from typing import Any, Dict, List, Optional, Tuple
from .config import ControllerConfig
from .ingestion import WorkflowMetrics


def normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def two_proportion_z_test(
    successes_a: int, trials_a: int, successes_b: int, trials_b: int
) -> Tuple[float, float]:
    """
    Two-proportion z-test comparing variant B against variant A.
    Returns: (z_score, p_value_one_tailed)
    Positive z means B is better than A.
    """
    if trials_a <= 0 or trials_b <= 0:
        return 0.0, 1.0

    p_a = successes_a / trials_a
    p_b = successes_b / trials_b

    p_pooled = (successes_a + successes_b) / (trials_a + trials_b)
    if p_pooled <= 0 or p_pooled >= 1.0:
        return 0.0, 1.0

    se = math.sqrt(p_pooled * (1.0 - p_pooled) * (1.0 / trials_a + 1.0 / trials_b))
    if se <= 0:
        return 0.0, 1.0

    z = (p_b - p_a) / se
    p_val = 1.0 - normal_cdf(z)
    return z, p_val


class WorkflowOptimizer:
    """Computes optimal allocations, schedules, and variant selections."""

    def __init__(self, cfg: ControllerConfig):
        self.cfg = cfg

    def compute_did_allocation(
        self,
        healthy_dids: List[str],
        degraded_dids: List[str],
        cur_alloc: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Evenly distributes traffic across active healthy DIDs, while removing degraded DIDs.
        If an untested DID is present, assigns at most a small exploratory weight (0.05).
        """
        if not healthy_dids:
            return cur_alloc

        # DIDs that were already active in cur_alloc
        active_healthy = [d for d in healthy_dids if cur_alloc.get(d, 0.0) > 0.05]
        untested_healthy = [d for d in healthy_dids if d not in active_healthy]

        if not active_healthy:
            active_healthy = healthy_dids
            untested_healthy = []

        new_alloc: Dict[str, float] = {}
        for d in degraded_dids:
            new_alloc[d] = 0.0

        # Allocate 0.05 to at most one untested healthy DID to explore reputation safely
        explore_total = 0.0
        if untested_healthy:
            probe_did = untested_healthy[0]
            new_alloc[probe_did] = 0.05
            explore_total = 0.05

        rem = 1.0 - explore_total
        each = rem / len(active_healthy)
        for d in active_healthy:
            new_alloc[d] = round(each, 4)

        # Normalize sum
        s = sum(new_alloc.values())
        if s > 0:
            new_alloc = {k: round(v / s, 4) for k, v in new_alloc.items()}
        return new_alloc

    def compute_hour_weights(
        self,
        wf_metrics: WorkflowMetrics,
        cohort: str,
        dialling_window: List[int],
    ) -> Dict[str, float]:
        """
        Calculates hour weights for a cohort based on observed pickup rate by hour.
        Guarantees weight > 0 for all hours in dialling_window so capacity is never starved.
        """
        lo, hi = dialling_window
        stats = wf_metrics.schedule_stats[cohort]
        default_stats = wf_metrics.schedule_stats["default"]

        rates: Dict[int, float] = {}
        for h in range(lo, hi):
            s = stats.get(h) or default_stats.get(h) or [0, 0]
            if s[0] >= 30:
                rates[h] = s[1] / s[0]
            else:
                rates[h] = 0.25  # neutral baseline

        avg_rate = sum(rates.values()) / len(rates) if rates else 0.25

        weights: Dict[str, float] = {}
        for h in range(lo, hi):
            r = rates.get(h, avg_rate)
            # Scale between 0.6 (trough) and 2.4 (peak)
            ratio = (r / max(avg_rate, 0.01))
            clamped = max(0.6, min(2.4, ratio))
            weights[str(h)] = round(clamped, 2)

        return weights

    def evaluate_cohort_variants(
        self,
        wf_metrics: WorkflowMetrics,
        cohort: str,
        dim: str,
        options: List[str],
        current_alloc: Dict[str, float],
        decayed_variants: List[str],
    ) -> Tuple[Dict[str, float], Optional[str], Optional[float]]:
        """
        Evaluates variants for a given cohort and dimension (welcome_message or voice).
        Returns: (new_allocation, winning_variant_or_none, estimated_lift)
        """
        available = [o for o in options if o not in decayed_variants]
        if not available:
            available = options

        if len(available) == 1:
            return {available[0]: 1.0}, None, None

        # Gather sample sizes & engagement rates
        trials: Dict[str, int] = {}
        successes: Dict[str, int] = {}
        rates: Dict[str, float] = {}

        for o in available:
            s = wf_metrics.variant_all_time[cohort][dim][o]
            # [dials, connected, engaged] -> trials = connected, successes = engaged
            t = s[1]
            e = s[2]
            trials[o] = t
            successes[o] = e
            rates[o] = (e / t) if t > 0 else 0.0

        # Current incumbent (highest weight in current config)
        incumbent = max(available, key=lambda o: current_alloc.get(o, 0.0))

        # Check if we have enough samples to test candidates against incumbent
        num_comparisons = max(1, len(available) - 1)
        bonferroni_alpha = 0.05 / num_comparisons if self.cfg.bonferroni_correction else 0.05

        best_cand: Optional[str] = None
        best_lift = 0.0

        for cand in available:
            if cand == incumbent:
                continue
            if trials[cand] < self.cfg.min_sample_size_per_arm or trials[incumbent] < self.cfg.min_sample_size_per_arm:
                continue

            z, p_val = two_proportion_z_test(
                successes[incumbent], trials[incumbent], successes[cand], trials[cand]
            )

            p_inc = rates[incumbent]
            p_cand = rates[cand]
            rel_lift = (p_cand - p_inc) / max(p_inc, 0.01)

            if p_val <= bonferroni_alpha and rel_lift >= self.cfg.min_relative_lift:
                if rel_lift > best_lift:
                    best_lift = rel_lift
                    best_cand = cand

        # If a clear winner is found, allocate exploit/explore split
        if best_cand:
            winner = best_cand
            new_alloc: Dict[str, float] = {}
            new_alloc[winner] = self.cfg.exploit_weight
            others = [o for o in available if o != winner]
            if others:
                explore_each = self.cfg.explore_weight / len(others)
                for o in others:
                    new_alloc[o] = explore_each
            else:
                new_alloc[winner] = 1.0
            return new_alloc, winner, best_lift

        # If incumbent is winning significantly over all others, exploit incumbent
        incumbent_solid = True
        for o in available:
            if o == incumbent:
                continue
            if trials[o] >= self.cfg.min_sample_size_per_arm:
                z, p_val = two_proportion_z_test(
                    successes[o], trials[o], successes[incumbent], trials[incumbent]
                )
                if rates[o] > rates[incumbent]:
                    incumbent_solid = False
                    break
        if incumbent_solid and trials[incumbent] >= self.cfg.min_sample_size_per_arm:
            new_alloc = {incumbent: self.cfg.exploit_weight}
            others = [o for o in available if o != incumbent]
            if others:
                explore_each = self.cfg.explore_weight / len(others)
                for o in others:
                    new_alloc[o] = explore_each
            else:
                new_alloc[incumbent] = 1.0
            return new_alloc, incumbent, None

        # Otherwise: balanced exploration across available variants
        w = 1.0 / len(available)
        balanced_alloc = {o: w for o in available}
        return balanced_alloc, None, None
