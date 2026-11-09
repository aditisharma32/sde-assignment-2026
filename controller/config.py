"""Controller configuration and hyperparameter constants."""
from dataclasses import dataclass

@dataclass
class ControllerConfig:
    # Sim advance step in minutes (must be multiple of tick_minutes, default 15)
    tick_step_minutes: int = 15

    # Storage
    db_path: str = "controller_audit.db"

    # Statistical testing & variant experimentation (C6)
    min_sample_size_per_arm: int = 180   # minimum connected calls before declaring a winner
    confidence_level: float = 0.95       # 95% confidence (p < 0.05)
    bonferroni_correction: bool = True   # control family-wise error rate
    min_relative_lift: float = 0.03      # minimum 3% lift required to justify change

    # Exploration vs exploitation
    explore_weight: float = 0.20         # keep 20% traffic on exploration/alternatives
    exploit_weight: float = 0.80

    # Caller ID (DID) health (C5)
    did_min_dials_to_evaluate: int = 80
    did_degradation_drop_ratio: float = 0.70  # pickup rate < 70% of peer average

    # Hallucination incident detection (C8)
    halluc_min_connected: int = 80
    halluc_alert_rate: float = 0.048     # 4.8% flag rate triggers incident (normal is ~1.4%, P2 is ~5.3%)
    validation_sample_size: int = 200    # costs ceil(n/100) = 2 credits per validation

    # Decay detection (C7)
    decay_eval_window_days: int = 2
    decay_drop_threshold: float = 0.08   # 8% drop from peak engagement triggers rollback

    # Governance & Approvers (C9)
    # Avoid proposing if expires within this many hours of approver shift start
    approver_safety_margin_hours: float = 1.0
